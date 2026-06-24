"""简历助手的子简历创建任务服务模块。

本模块负责根据职位描述（JD）自动创建优化后的子简历：
1. 调用LLM分析简历和JD
2. 生成优化后的简历内容
3. 创建子简历和板块记录

主要函数：
- run_sub_resume_task: 后台任务入口
- executor_llm: 调用LLM生成优化内容
"""  # 模块文档字符串

import asyncio  # 导入异步IO库
import json  # 导入JSON模块
import logging  # 导入日志模块
import secrets  # 导入安全随机数模块
from datetime import datetime  # 导入日期时间类

import json_repair  # 导入JSON修复模块
from pydantic import ValidationError  # 导入验证错误类
from sqlalchemy import select  # SQL查询构建器
from sqlalchemy.ext.asyncio import AsyncSession  # 异步数据库会话

from apps.resume_assistant.schemas import (  # 导入简历助手的数据模型
    PersonalInfo,
    SubResumeCreateRequest,
    SubResumeResult,
    Summary,
)
from shared.api.client import (  # LLM客户端相关类型
    ApiMessageCompleteEvent,
    ApiMessageRequest,
    ApiTextDeltaEvent,
    SupportsStreamingMessages,
)
from shared.models import (  # 数据库模型
    SHANGHAI_TZ,
    BaseWork,
    Resume,
    ResumeSection,
)
from shared.resume_prompt import (  # 简历提示词构建工具
    ItemFields,
    PersonalInfoFields,
    ResumePromptBuilder,
    SectionHeaderConfig,
)
from shared.resume_section_factory import (  # 板块工厂
    SectionConfig,
    create_resume_sections,
)
from shared.task_state import (  # 任务状态管理
    cleanup_task,
    update_task_error,
    update_task_result,
    update_task_status,
)
from shared.types.messages import ConversationMessage  # 对话消息类型
from shared.types.resume import ResumeSectionSchema  # 板块类型
from shared.types.task import TaskStatus  # 任务状态枚举

log = logging.getLogger(__name__)  # 创建日志记录器

MAX_RETRIES = 3  # 最大重试次数

# 子简历创建的提示词构建器配置
RESUME_PERSONAL_INFO_FIELDS = PersonalInfoFields(  # 包含所有个人信息字段
    full_name=True,
    age=True,
    gender=True,
    email=True,
    phone=True,
    education_level=True,
    job_title=True,
    salary=True,
    location=True,
    political_status=True,
    ethnicity=True,
    hometown=True,
    marital_status=True,
    years_of_experience=True,
    wechat=True,
    website=True,
    linkedin=True,
)
RESUME_ITEM_FIELDS = ItemFields(location=True)  # 条目包含地点
RESUME_SECTION_HEADER = SectionHeaderConfig(include_section_id=False)  # 不包含板块ID

RESUME_ASSISTANT_BUILDER = ResumePromptBuilder(  # 创建提示词构建器
    personal_info_fields=RESUME_PERSONAL_INFO_FIELDS,
    item_fields=RESUME_ITEM_FIELDS,
    section_header=RESUME_SECTION_HEADER,
)


async def executor_llm(
    client: SupportsStreamingMessages,
    model: str,
    sections: list[ResumeSectionSchema],
    job_description: str,
    job_title: str | None = None,
) -> SubResumeResult:
    """调用LLM生成优化后的简历内容。

    Args:
        client: LLM客户端。
        model: 模型名称。
        sections: 原始简历板块列表。
        job_description: 职位描述。
        job_title: 职位名称。

    Returns:
        优化后的简历内容。
    """
    accumulated_content = ""  # 累积LLM输出
    messages = [  # 构建用户消息
        ConversationMessage.from_user_text(
            RESUME_ASSISTANT_BUILDER.build_user_prompt(
                sections, job_description, job_title
            )
        )
    ]
    system_prompt = SYSTEM.format(  # 构建系统提示词
        json_schema=json.dumps(
            SubResumeResult.model_json_schema(), indent=2, ensure_ascii=False
        )
    )

    for i in range(MAX_RETRIES):  # 重试循环，最多尝试MAX_RETRIES次
        complete_event: ApiMessageCompleteEvent | None = (
            None  # 用来保存LLM的完成事件，后续用于重试时构建对话历史
        )
        async for event in client.stream_message(  # 流式调用LLM
            ApiMessageRequest(
                model=model, messages=messages, system_prompt=system_prompt
            )
        ):
            if isinstance(
                event, ApiTextDeltaEvent
            ):  # 如果是文本增量事件（LLM正在输出文字）
                if event.is_think:
                    continue  # 跳过思考内容（有些模型会输出思考过程）
                accumulated_content += event.text  # 把增量文本追加到累积内容中
            elif isinstance(
                event, ApiMessageCompleteEvent
            ):  # 如果是消息完成事件（LLM输出结束）
                complete_event = (
                    event  # 保存完成事件，后续用于重试时把LLM回复加入对话历史
                )

        parser_content = json_repair.loads(
            accumulated_content
        )  # 用json_repair修复LLM可能返回的不完整JSON，然后解析成Python对象

        try:
            result = SubResumeResult.model_validate(
                parser_content
            )  # 用Pydantic验证解析后的数据是否符合SubResumeResult的结构
        except ValidationError as e:  # 如果验证失败（数据结构不对）
            if i == MAX_RETRIES - 1:
                raise e  # 如果是最后一次重试，直接抛出异常
            # 构建错误信息反馈给LLM，让它知道哪里出了问题
            errors = []  # 创建空列表，用来存放所有验证错误的描述
            for err in e.errors():  # 遍历所有验证错误
                field = ".".join(
                    str(loc) for loc in err["loc"]
                )  # 把错误位置拼接成字段路径（如 "personal_info.full_name"）
                errors.append(f"  - {field}: {err['msg']}")  # 格式化错误信息
            error_msg = f"Validation failed:\n" + "\n".join(
                errors
            )  # 把所有错误拼接成一条消息
            messages.append(
                complete_event.message
            )  # 把LLM的回复加入对话历史，让LLM知道它上次说了什么
            messages.append(
                ConversationMessage.from_user_text(error_msg)
            )  # 把错误信息作为用户消息加入，让LLM修正
            continue  # 继续下一次重试
        except Exception as e:  # 如果是其他异常（非验证错误）
            raise e  # 直接抛出，不重试
        return result  # 验证通过，返回结果，后续用于创建子简历

    raise Exception("Max retries exceeded")  # 所有重试都失败了，抛出异常


async def run_sub_resume_task(
    db: AsyncSession,
    task_id: str,
    client: SupportsStreamingMessages,
    request: SubResumeCreateRequest,
    workspace_sections: list[ResumeSectionSchema],
) -> None:
    """后台任务入口：创建子简历。

    Args:
        db: 数据库会话。
        task_id: 任务ID。
        client: LLM客户端。
        request: 创建请求。
        workspace_sections: 主简历的板块列表。
    """
    try:
        await _update_work_status(
            db, task_id, TaskStatus.RUNNING
        )  # 更新数据库中的任务状态为"运行中"
        await update_task_status(
            task_id, TaskStatus.RUNNING
        )  # 更新内存中的任务状态为"运行中"

        result = await executor_llm(  # 调用LLM生成优化后的简历内容
            client,
            request.model,  # 使用的AI模型名称
            workspace_sections,  # 主简历的板块列表，作为LLM的参考
            request.job_description,  # 目标职位的描述
            request.job_title,  # 目标岗位名称
        )

        # 构建元数据，记录这次创建的相关信息
        meta_info = {"job_description": request.job_description}  # 存储职位描述
        if request.job_title:  # 如果提供了岗位名称
            meta_info["job_title"] = request.job_title  # 也存入元数据

        # 创建子简历记录
        resume = Resume(
            id=task_id,  # 用任务ID作为简历ID
            workspace_id=request.workspace_id,  # 关联到主简历（工作区）
            title=request.title,  # 子简历标题
            template=request.template,  # 使用的模板
            theme_config=json.dumps(
                request.theme_config, ensure_ascii=False
            ),  # 主题配置转成JSON字符串
            language=request.language,  # 简历语言
            meta_info=meta_info,  # 元数据
        )
        db.add(resume)  # 把子简历添加到数据库会话

        _create_resume_sections(db, task_id, result)  # 根据LLM生成的内容创建所有板块

        await db.commit()  # 提交事务，把子简历和板块持久化到数据库

        await _update_work_status(
            db, task_id, TaskStatus.SUCCESS
        )  # 更新数据库任务状态为"成功"
        await update_task_result(
            task_id, {"resume_id": task_id}
        )  # 更新内存任务结果，记录简历ID

        asyncio.create_task(cleanup_task(task_id, None))  # 异步清理内存中的任务状态

    except Exception as e:  # 如果任何步骤出错
        await db.rollback()  # 回滚数据库事务，撤销所有未提交的更改
        log.error(f"子简历创建失败: {e}")  # 记录错误日志
        await _update_work_status(
            db, task_id, TaskStatus.ERROR
        )  # 更新数据库任务状态为"错误"
        await update_task_error(
            task_id, f"run_sub_resume_task error: {str(e)}"
        )  # 更新内存任务错误信息
        asyncio.create_task(cleanup_task(task_id, None))  # 异步清理内存中的任务状态
        raise  # 重新抛出异常


def _make_sub_resume_section_configs(
    result: SubResumeResult,
) -> list[SectionConfig]:
    """构建子简历的板块配置列表。"""
    configs: list[SectionConfig] = [
        SectionConfig(
            type="personal_info",  # 板块类型：个人信息
            title="个人信息",  # 板块显示标题
            content_fn=lambda: (
                result.personal_info.model_dump()
            ),  # 从LLM结果中提取个人信息内容
            default_fn=lambda: PersonalInfo().model_dump(),  # 默认值：空的个人信息
            field_name="personal_info",  # 对应SubResumeResult中的字段名
        ),
        SectionConfig(
            type="summary",  # 板块类型：个人简介
            title="个人简介",  # 板块显示标题
            content_fn=lambda: {"text": result.summary.text},  # 从LLM结果中提取简介文本
            default_fn=lambda: Summary().model_dump(),  # 默认值：空的简介
            field_name="summary",  # 对应字段名
        ),
        SectionConfig(
            type="work_experience",  # 板块类型：工作经历
            title="工作经历",  # 板块显示标题
            content_fn=lambda: _build_items_content(
                result.work_experience,
                "work_experience",  # 把工作经历列表转成带ID的items格式
            ),
            default_fn=lambda: {"items": []},  # 默认值：空的items数组
            field_name="work_experience",  # 对应字段名
        ),
        SectionConfig(
            type="education",  # 板块类型：教育背景
            title="教育背景",  # 板块显示标题
            content_fn=lambda: _build_items_content(
                result.education, "education"
            ),  # 把教育经历列表转成带ID的items格式
            default_fn=lambda: {"items": []},  # 默认值：空的items数组
            field_name="education",  # 对应字段名
        ),
        SectionConfig(
            type="skills",  # 板块类型：技能特长
            title="技能特长",  # 板块显示标题
            content_fn=lambda: _build_categories_content(
                result.skills
            ),  # 把技能分类列表转成带ID的categories格式
            default_fn=lambda: {"categories": []},  # 默认值：空的categories数组
            field_name="skills",  # 对应字段名
        ),
        SectionConfig(
            type="projects",  # 板块类型：项目经历
            title="项目经历",  # 板块显示标题
            content_fn=lambda: _build_items_content(
                result.projects, "projects"
            ),  # 把项目列表转成带ID的items格式
            default_fn=lambda: {"items": []},  # 默认值：空的items数组
            field_name="projects",  # 对应字段名
        ),
        SectionConfig(
            type="languages",  # 板块类型：语言能力
            title="语言能力",  # 板块显示标题
            content_fn=lambda: _build_items_content(
                result.languages, "languages"
            ),  # 把语言列表转成带ID的items格式
            default_fn=lambda: {"items": []},  # 默认值：空的items数组
            field_name="languages",  # 对应字段名
        ),
        SectionConfig(
            type="certifications",  # 板块类型：资格证书
            title="资格证书",  # 板块显示标题
            content_fn=lambda: _build_items_content(
                result.education, "education"
            ),  # 注意：这里用的是education，可能是bug
            default_fn=lambda: {"items": []},  # 默认值：空的items数组
            field_name="certifications",  # 对应字段名
        ),
        SectionConfig(
            type="github",  # 板块类型：GitHub项目
            title="GitHub",  # 板块显示标题
            content_fn=lambda: _build_items_content(
                result.github, "github"
            ),  # 把GitHub仓库列表转成带ID的items格式
            default_fn=lambda: {"items": []},  # 默认值：空的items数组
            field_name="github",  # 对应字段名
        ),
    ]
    return configs  # 返回所有板块配置，后续用于创建数据库板块记录


_prefix_store: dict[str, str] = {}  # 前缀缓存，存储每个板块类型对应的随机前缀


def _get_prefix(section_type: str) -> str:
    """获取板块类型的随机前缀。"""
    if section_type not in _prefix_store:  # 如果这个板块类型还没有前缀
        _prefix_store[section_type] = secrets.token_hex(
            4
        )  # 生成8位随机十六进制字符串作为前缀
    return _prefix_store[section_type]  # 返回该板块类型的前缀，后续用于生成条目ID


def _ensure_id_local(obj: dict, prefix: str, index: int) -> dict:
    """确保对象有ID字段。"""
    if "id" not in obj or not obj["id"]:  # 如果对象没有ID字段或者ID为空
        obj["id"] = (
            f"{prefix}-{index:04d}"  # 自动生成ID，格式为"前缀-序号"（如 "a1b2c3d4-0001"）
        )
    return obj  # 返回带有ID的对象


def _build_items_content(items: list, prefix: str) -> dict:
    """构建条目类型内容。"""
    p = _get_prefix(prefix)  # 获取该板块类型的随机前缀
    return {
        "items": [
            _ensure_id_local(item.model_dump(), p, idx)  # 把每个条目转成字典并确保有ID
            for idx, item in enumerate(items, start=1)  # 序号从1开始
        ]
    }


def _build_categories_content(categories: list) -> dict:
    """构建分类类型内容。"""
    p = _get_prefix("skills")  # 获取技能板块的随机前缀
    return {
        "categories": [
            _ensure_id_local(cat.model_dump(), p, idx)  # 把每个分类转成字典并确保有ID
            for idx, cat in enumerate(categories, start=1)  # 序号从1开始
        ]
    }


def _create_custom_sections(
    result: SubResumeResult, resume_id: str, start_sort_order: int
) -> list[ResumeSection]:
    """创建自定义板块。"""
    sections = []  # 用于存放创建的自定义板块
    sort_order = start_sort_order  # 从传入的起始排序序号开始
    for item in result.custom:  # 遍历LLM生成的自定义条目
        sections.append(
            ResumeSection(
                resume_id=resume_id,  # 关联到子简历
                type="custom",  # 板块类型：自定义
                title=item.title,  # 使用条目的标题作为板块标题
                sort_order=sort_order,  # 排序序号
                visible=True,  # 默认可见
                content=json.dumps(
                    item.model_dump(), ensure_ascii=False
                ),  # 把条目内容转成JSON字符串
            )
        )
        sort_order += 1  # 序号递增
    return sections  # 返回创建的自定义板块列表


def _create_resume_sections(
    db: AsyncSession, resume_id: str, result: SubResumeResult
) -> None:
    """创建简历的所有板块。"""
    global _prefix_store  # 声明使用全局变量
    _prefix_store = {}  # 清空前缀缓存，确保每次创建使用新的前缀
    configs = _make_sub_resume_section_configs(result)  # 构建板块配置列表
    create_resume_sections(
        db,
        resume_id,
        result,
        configs,  # 传入板块配置
        extra_sections_fn=_create_custom_sections,  # 自定义板块的创建函数
    )


async def _update_work_status(
    db: AsyncSession, task_id: str, status: TaskStatus, error: str | None = None
) -> None:
    """更新数据库中的任务状态。"""
    result = await db.execute(
        select(BaseWork).where(BaseWork.id == task_id)
    )  # 查询任务记录
    work = result.scalar_one_or_none()  # 获取任务对象
    if work:  # 如果找到了任务记录
        work.status = status.value  # 更新状态值
        work.updated_at = datetime.now(SHANGHAI_TZ)  # 更新修改时间为上海时区的当前时间
        if error:  # 如果有错误信息
            work.error_message = error  # 设置错误消息
        await db.commit()  # 提交事务


# 系统提示词
SYSTEM = """\
You are a professional resume optimization expert and career coach. Please tailor the provided resume to better match the job description (JD).

# Core Rules:
- Return JSON only — no additional text, explanations, or commentary
- Resume optimization is limited to rewording and reformatting existing content only. Never invent or add information not present in the original resume. Even if the job description explicitly requires certain skills, experience, or qualifications you must not fabricate them (e.g., if the original resume does not mention Rust, you cannot claim the candidate is familiar with Rust in the optimized resume)

Below is the JSON schema definition you must follow:
---
{json_schema}
---"""
