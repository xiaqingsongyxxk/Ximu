"""简历解析任务的业务逻辑模块。

本模块负责执行简历文件的AI解析流程：
1. 推断文件类型（目前支持PDF）
2. 提取PDF文本内容
3. 调用LLM将非结构化文本转为结构化简历数据
4. 创建简历和板块记录
5. 管理任务状态

主要函数：
- run_parser_task: 新建解析任务的入口
- retry_parser_task: 重试失败任务的入口
- infer_parser_type: 推断文件类型
"""  # 模块文档字符串

import asyncio  # 导入异步IO库，用于创建后台清理任务
import logging  # 导入日志模块
import secrets  # 导入安全随机数模块，用于生成板块ID的随机前缀
from datetime import datetime  # 导入日期时间类
from pathlib import Path  # 导入路径操作类

from sqlalchemy import select  # SQL查询构建器
from sqlalchemy.ext.asyncio import AsyncSession  # 异步数据库会话

from apps.parser.call_llm import (
    executor_llm,
)  # 从apps/parser/call_llm.py导入LLM调用函数
from apps.parser.pdf_parser import (
    pdf_parser,
)  # 从apps/parser/pdf_parser.py导入PDF解析器
from apps.parser.schemas import (
    ParserResult,
)  # 从apps/parser/schemas.py导入解析结果数据模型
from shared.api.client import (
    SupportsStreamingMessages,  # 支持流式消息的LLM客户端接口
)
from shared.database import async_session  # 从shared/database.py导入异步会话生成器
from shared.models import (
    SHANGHAI_TZ,  # 上海时区常量
    BaseWork,  # 工作任务ORM模型
    Resume,  # 简历ORM模型
)
from shared.resume_section_factory import (
    SectionConfig,  # 板块配置类
    create_resume_sections,  # 创建简历板块的工厂函数
)
from shared.task_state import (  # 任务状态管理函数
    cleanup_task,  # 清理任务资源
    update_task_error,  # 更新任务为错误状态
    update_task_result,  # 更新任务结果
    update_task_status,  # 更新任务状态
)
from shared.types.resume import (  # 简历板块内容类型
    CertificationsContent,  # 资格证书内容
    EducationContent,  # 教育背景内容
    LanguagesContent,  # 语言能力内容
    PersonalInfo,  # 个人信息内容
    ProjectsContent,  # 项目经历内容
    SkillsContent,  # 技能特长内容
    Summary,  # 个人简介内容
    WorkExperienceContent,  # 工作经历内容
)
from shared.types.task import TaskStatus  # 任务状态枚举

log = logging.getLogger(__name__)  # 创建本模块的日志记录器

# 模块级字典：缓存板块类型的随机前缀
# 每个板块类型（如work_experience）有一个固定的随机前缀
# 用于为板块内的条目生成唯一ID（如 "a1b2c3d4-0001"）
_prefix_store: dict[str, str] = {}


def _get_prefix(section_type: str) -> str:
    """获取或生成板块类型的随机前缀。

    每个板块类型第一次调用时生成8位随机十六进制字符串作为前缀，
    后续调用直接返回缓存的前缀。

    Args:
        section_type: 板块类型标识（如"work_experience"）。

    Returns:
        8位随机十六进制字符串前缀。
    """
    if section_type not in _prefix_store:  # 如果该类型还没有缓存前缀
        _prefix_store[section_type] = secrets.token_hex(4)  # 生成8位随机十六进制字符串
    return _prefix_store[section_type]  # 返回缓存的前缀


def _make_parser_section_configs(
    result: ParserResult,
) -> list[SectionConfig]:
    """根据LLM解析结果构建板块配置列表。

    每个板块配置包含：类型、标题、内容获取函数、默认内容函数。
    如果LLM没有返回某个板块的数据，会使用默认空内容。

    Args:
        result: LLM返回的解析结果。

    Returns:
        板块配置列表。
    """
    configs: list[SectionConfig] = [
        SectionConfig(  # 个人信息板块
            type="personal_info",  # 板块类型标识
            title="个人信息",  # 板块显示标题
            content_fn=lambda: (
                result.personal_info.model_dump()
            ),  # 获取LLM解析的个人信息
            default_fn=lambda: PersonalInfo().model_dump(),  # 默认空个人信息
            field_name="personal_info",  # ParserResult中的字段名
        ),
        SectionConfig(  # 个人简介板块
            type="summary",
            title="个人简介",
            content_fn=lambda: {"text": result.summary},  # 将简介文本包装为字典
            default_fn=lambda: Summary().model_dump(),  # 默认空简介
            field_name="summary",
        ),
        SectionConfig(  # 工作经历板块
            type="work_experience",
            title="工作经历",
            content_fn=lambda: _build_items_content(  # 构建条目类型内容
                result.work_experiences, WorkExperienceContent, "work_experience"
            ),
            default_fn=lambda: WorkExperienceContent().model_dump(),
            field_name="work_experiences",
        ),
        SectionConfig(  # 教育背景板块
            type="education",
            title="教育背景",
            content_fn=lambda: _build_items_content(
                result.education, EducationContent, "education"
            ),
            default_fn=lambda: EducationContent().model_dump(),
            field_name="education",
        ),
        SectionConfig(  # 技能特长板块
            type="skills",
            title="技能特长",
            content_fn=lambda: _build_categories_content(
                result.skills
            ),  # 构建分类类型内容
            default_fn=lambda: SkillsContent().model_dump(),
            field_name="skills",
        ),
        SectionConfig(  # 项目经历板块
            type="projects",
            title="项目经历",
            content_fn=lambda: _build_items_content(
                result.projects, ProjectsContent, "projects"
            ),
            default_fn=lambda: ProjectsContent().model_dump(),
            field_name="projects",
        ),
        SectionConfig(  # 语言能力板块
            type="languages",
            title="语言能力",
            content_fn=lambda: _build_items_content(
                result.languages, LanguagesContent, "languages"
            ),
            default_fn=lambda: LanguagesContent().model_dump(),
            field_name="languages",
        ),
        SectionConfig(  # 资格证书板块
            type="certifications",
            title="资格证书",
            content_fn=lambda: _build_items_content(
                result.certifications, CertificationsContent, "certifications"
            ),
            default_fn=lambda: CertificationsContent().model_dump(),
            field_name="certifications",
        ),
    ]
    return configs


def _build_items_content(items: list | None, content_cls: type, prefix: str) -> dict:
    """构建条目类型板块的内容（如工作经历、教育背景等）。

    为每个条目确保有唯一ID，ID格式为"前缀-序号"。

    Args:
        items: 条目列表（LLM解析结果）。
        content_cls: 内容类（如WorkExperienceContent）。
        prefix: 板块类型前缀（用于生成ID）。

    Returns:
        序列化后的字典。
    """
    p = _get_prefix(prefix)  # 获取该板块类型的随机前缀

    if items:  # 如果有条目数据
        return content_cls(  # 使用内容类构造对象
            items=[
                _ensure_id(item.model_dump(), p, idx)  # 为每个条目确保有ID
                for idx, item in enumerate(items, start=1)  # 从1开始编号
            ]
        ).model_dump()  # 转为字典
    return content_cls().model_dump()  # 无数据返回空内容


def _build_categories_content(categories: list | None) -> dict:
    """构建分类类型板块的内容（如技能特长）。

    技能使用分类结构（categories），而不是简单的条目列表。

    Args:
        categories: 分类列表（LLM解析结果）。

    Returns:
        序列化后的字典。
    """
    p = _get_prefix("skills")  # 获取技能类型的随机前缀

    if categories:  # 如果有分类数据
        return SkillsContent(  # 构造技能内容对象
            categories=[
                _ensure_id(cat.model_dump(), p, idx)  # 为每个分类确保有ID
                for idx, cat in enumerate(categories, start=1)
            ]
        ).model_dump()
    return SkillsContent().model_dump()  # 无数据返回空技能内容


def _ensure_id(obj: dict, prefix: str, index: int) -> dict:
    """确保对象有id字段。

    如果对象没有id或id为空，自动生成格式化的ID。

    Args:
        obj: 要检查的字典对象。
        prefix: ID前缀（8位随机十六进制字符串）。
        index: 序号。

    Returns:
        确保有id字段的字典。
    """
    if "id" not in obj or not obj["id"]:  # 如果没有id或id为空
        obj["id"] = f"{prefix}-{index:04d}"  # 生成格式化ID（如"a1b2c3d4-0001"）
    return obj


def _create_resume_sections(
    db: AsyncSession,
    resume_id: str,
    result: ParserResult,
) -> None:
    """创建简历的所有板块。

    按照预定义的固定顺序创建板块，缺失的板块使用默认空内容填充。
    不自行commit/rollback，由调用方管理事务。

    Args:
        db: 数据库会话。
        resume_id: 简历ID。
        result: LLM解析结果。
    """
    global _prefix_store  # 声明使用全局变量
    _prefix_store = {}  # 清空前缀缓存，确保每次解析使用新的随机前缀
    configs = _make_parser_section_configs(result)  # 构建板块配置列表
    create_resume_sections(db, resume_id, result, configs)  # 调用工厂函数创建所有板块


def infer_parser_type(filename: str, content_type: str | None) -> str:
    """根据文件名和MIME类型推断解析器类型。

    Args:
        filename: 上传文件的名称。
        content_type: 文件的MIME类型（可选）。

    Returns:
        解析器类型标识（如"pdf"）。

    Raises:
        ValueError: 如果文件类型不支持。
    """
    ext = filename.lower().split(".")[-1] if "." in filename else ""  # 提取文件扩展名

    if ext == "pdf" or content_type == "application/pdf":  # 如果是PDF文件
        return "pdf"  # 返回PDF解析器类型

    raise ValueError(
        f"不支持的文件类型: {ext or content_type or '未知'}"
    )  # 不支持的类型


async def _update_work_status(
    task_id: str,
    status: TaskStatus,
    error: str | None = None,
) -> None:
    """更新数据库中的任务状态。

    Args:
        task_id: 任务ID。
        status: 新状态。
        error: 错误信息（状态为ERROR时传入）。
    """
    async with async_session() as session:  # 创建新的数据库会话
        result = await session.execute(
            select(BaseWork).where(BaseWork.id == task_id)  # 按ID查询任务
        )
        work = result.scalar_one_or_none()  # 获取结果
        if work:  # 如果任务存在
            work.status = status.value  # 更新状态
            work.updated_at = datetime.now(SHANGHAI_TZ)  # 更新时间戳
            if error:  # 如果有错误信息
                work.error_message = error  # 设置错误消息
            await session.commit()  # 提交事务


async def _execute_parse_flow(
    db: AsyncSession,
    task_id: str,
    file_path: str,
    client: SupportsStreamingMessages,
    model: str,
    template: str,
    title: str,
    *,
    delete_file: bool,
) -> None:
    """执行解析流程的核心逻辑。

    编排整个解析流程：PDF文本提取 → LLM解析 → 创建简历。

    Args:
        db: 数据库会话（调用方管理事务）。
        task_id: 任务ID。
        file_path: PDF文件绝对路径。
        client: LLM客户端。
        model: 模型名称。
        template: 模板名称。
        title: 简历标题。
        delete_file: 是否在清理时删除上传文件。
    """
    # 更新任务状态为运行中
    await update_task_status(task_id, TaskStatus.RUNNING)  # 更新内存状态
    await _update_work_status(task_id, TaskStatus.RUNNING)  # 更新数据库状态

    # 执行解析
    result = await pdf_parser.parse(file_path)  # 第一步：提取PDF文本内容
    result = await executor_llm(
        client, model, result["text"]
    )  # 第二步：调用LLM解析文本

    # 创建简历记录
    resume = Resume(
        id=task_id,  # 使用任务ID作为简历ID
        title=title,
        template=template,
    )
    db.add(resume)  # 添加到数据库会话

    # 创建简历板块
    _create_resume_sections(db, task_id, result)  # 创建所有板块

    # 更新任务状态为成功
    await _update_work_status(task_id, TaskStatus.SUCCESS)
    await update_task_result(task_id, {"resume_id": task_id})  # 存储简历ID

    # 定义清理函数
    async def cleanup() -> None:
        if delete_file and file_path:  # 如果需要删除文件
            Path(file_path).unlink(missing_ok=True)  # 删除文件

    asyncio.create_task(cleanup_task(task_id, cleanup))  # 创建后台清理任务


async def run_parser_task(
    db: AsyncSession,
    task_id: str,
    file_path: str,
    client: SupportsStreamingMessages,
    model: str,
    template: str,
    title: str,
) -> None:
    """新建解析任务的后台执行入口。

    由 router.py 中的 parse_document 函数调用。

    Args:
        db: 数据库会话。
        task_id: 任务ID。
        file_path: PDF文件路径。
        client: LLM客户端。
        model: 模型名称。
        template: 模板名称。
        title: 简历标题。
    """
    try:
        await _execute_parse_flow(  # 执行解析流程
            db,
            task_id,
            file_path,
            client,
            model,
            template,
            title,
            delete_file=True,  # 成功后删除上传文件
        )
        await db.commit()  # 提交事务
    except Exception as e:  # 解析失败
        await db.rollback()  # 回滚事务
        log.error("解析失败: %s", e)  # 记录错误日志
        await _update_work_status(
            task_id, TaskStatus.ERROR, error=f"解析失败: {str(e)}"
        )
        await update_task_error(task_id, f"解析失败: {str(e)}")
        asyncio.create_task(cleanup_task(task_id, None))  # 清理任务状态
        raise  # 重新抛出异常


async def retry_parser_task(
    db: AsyncSession,
    task_id: str,
    file_path: str,
    client: SupportsStreamingMessages,
    model: str,
    template: str,
    title: str,
) -> None:
    """重试解析任务的后台执行入口。

    由 router.py 中的 retry_failed_task 函数调用。

    Args:
        db: 数据库会话。
        task_id: 任务ID。
        file_path: PDF文件路径。
        client: LLM客户端。
        model: 模型名称。
        template: 模板名称。
        title: 简历标题。
    """
    try:
        await _execute_parse_flow(  # 执行解析流程
            db,
            task_id,
            file_path,
            client,
            model,
            template,
            title,
            delete_file=True,  # 成功后删除上传文件
        )
        await db.commit()  # 提交事务
    except Exception as e:  # 解析失败
        await db.rollback()  # 回滚事务
        log.error("解析失败: %s", e)  # 记录错误日志
        await _update_work_status(
            task_id, TaskStatus.ERROR, error=f"解析失败: {str(e)}"
        )
        await update_task_error(task_id, f"解析失败: {str(e)}")
        asyncio.create_task(cleanup_task(task_id, None))  # 清理任务状态
        raise  # 重新抛出异常
