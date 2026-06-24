"""职位描述分析服务层模块。

本模块包含JD匹配任务的业务逻辑，包括：
1. 查询必要的数据（简历板块信息）
2. 调用LLM进行匹配分析
3. 将分析结果持久化到数据库
4. 更新任务状态（运行中、成功、失败）
"""  # 模块文档字符串

import asyncio  # 导入异步IO模块，用于创建异步任务（如清理任务）
import json  # 导入JSON模块，用于将Python对象序列化为JSON字符串存入数据库
import logging  # 导入日志模块，用于记录运行时信息和错误
from datetime import datetime  # 导入datetime模块，用于获取当前时间

from sqlalchemy import select  # 从SQLAlchemy导入查询构建器，用于构建SELECT语句
from sqlalchemy.ext.asyncio import AsyncSession  # 导入异步数据库会话类型

from apps.jd_analysis.call_llm import (
    executor_llm,
)  # 导入LLM执行器函数，用于调用大语言模型
from shared.api import (
    SupportsStreamingMessages,
)  # 导入流式消息支持接口，LLM客户端需实现此接口
from shared.models import (
    SHANGHAI_TZ,
    BaseWork,
    JobDescriptionAnalysis,
    ResumeSection,
)  # 导入数据库模型：时区常量、工作任务表、JD分析表、简历板块表
from shared.task_state import (  # 从任务状态管理模块导入状态更新函数
    cleanup_task,  # 清理任务状态的函数（任务完成后从内存中移除）
    update_task_error,  # 更新任务为错误状态的函数
    update_task_result,  # 更新任务结果的函数（成功时调用）
    update_task_status,  # 更新任务状态的函数（如从待处理改为运行中）
)
from shared.types.task import (
    TaskStatus,
)  # 导入任务状态枚举（PENDING、RUNNING、SUCCESS、ERROR）

log = logging.getLogger(__name__)  # 获取当前模块的logger实例，用于记录日志


async def run_match_task(  # 定义异步函数：运行JD匹配任务
    db: AsyncSession,  # 参数：异步数据库会话
    task_id: str,  # 参数：任务唯一标识符
    client: SupportsStreamingMessages,  # 参数：支持流式消息的LLM客户端
    model: str,  # 参数：LLM模型名称（如"gpt-4"、"claude-3"）
    resume_id: str,  # 参数：要分析的简历ID
    job_description: str,  # 参数：职位描述文本
    job_title: str | None = None,  # 参数：职位名称（可选，默认为None）
) -> None:  # 返回值：无返回值，结果直接写入数据库
    """运行JD匹配任务。

    该函数负责协调整个匹配分析流程：
    1. 查询简历的可见板块信息
    2. 更新任务状态为运行中
    3. 调用LLM进行匹配分析
    4. 将分析结果保存到数据库
    5. 更新任务状态为成功或失败

    Args:
        db: 异步数据库会话，用于查询和持久化数据。
        task_id: 任务唯一标识符。
        client: 支持流式消息的LLM客户端实例。
        model: 要使用的LLM模型名称。
        resume_id: 要分析的简历ID。
        job_description: 职位描述文本。
        job_title: 职位名称（可选）。

    Returns:
        None. 该函数直接在数据库中更新结果。

    Raises:
        Exception: 发生未预期的错误时，记录日志并更新任务状态后重新抛出。
    """  # 函数文档字符串（Google风格）

    try:  # 开始try块，捕获可能发生的异常
        # 查询简历的可见板块信息
        sections_result = await db.execute(  # 执行数据库查询
            select(ResumeSection)  # 查询ResumeSection表
            .where(  # 添加查询条件
                ResumeSection.resume_id == resume_id,  # 条件：简历ID匹配
                ResumeSection.visible == True,  # 条件：板块可见（未被隐藏）
            )
            .order_by(ResumeSection.sort_order)  # 按排序顺序排列
        )

        resume_section_list = sections_result.scalars().all()  # 获取所有查询结果

        sections = [
            resume.to_pydantic() for resume in resume_section_list
        ]  # 将ORM对象列表转为Pydantic模型列表

        await _update_work_status(
            db, task_id, TaskStatus.RUNNING
        )  # 更新数据库中的任务状态为运行中
        await update_task_status(
            task_id, TaskStatus.RUNNING
        )  # 更新内存中的任务状态为运行中（用于SSE推送）

        match_result = await executor_llm(  # 调用LLM执行器进行匹配分析
            client,  # LLM客户端
            model,  # 模型名称
            sections,  # 简历板块列表
            job_description,  # 职位描述
            job_title,  # 职位名称
        )
        # LLM 分析结果包含以下字段：
        # summary - 分析摘要（AI生成的文字总结）
        # overall_score - 总体匹配分（0-100分）
        # ats_score - ATS兼容性评分（0-100分）
        # keyword_matches - 匹配的关键词列表
        # missing_keywords - 缺失的关键词列表
        # suggestions - 优化建议列表

        job_description_analysis = JobDescriptionAnalysis(  # 创建JD分析记录的ORM对象
            resume_id=resume_id,  # 关联的简历ID
            job_description=job_description,  # 职位描述文本
            summary=match_result.summary,  # 分析摘要
            overall_score=match_result.overall_score,  # 总体匹配分
            ats_score=match_result.ats_score,  # ATS兼容性评分
            keyword_matches=json.dumps(  # 将匹配关键词列表序列化为JSON字符串
                match_result.keyword_matches,  # 匹配的关键词列表
                ensure_ascii=False,  # 允许中文直接显示（不转义为\uXXXX）
            ),
            missing_keywords=json.dumps(  # 将缺失关键词列表序列化为JSON字符串
                match_result.missing_keywords,  # 缺失的关键词列表
                ensure_ascii=False,  # 允许中文直接显示
            ),
            suggestions=json.dumps(  # 将优化建议列表序列化为JSON字符串
                [
                    s.model_dump() for s in match_result.suggestions
                ],  # 将每个建议对象转为字典
                ensure_ascii=False,  # 允许中文直接显示
            ),
        )
        db.add(job_description_analysis)  # 将分析记录添加到数据库会话
        await db.commit()  # 提交事务，将数据写入数据库
        await db.refresh(
            job_description_analysis
        )  # 刷新对象，获取数据库生成的值（如自增ID、创建时间）

        await _update_work_status(
            db, task_id, TaskStatus.SUCCESS
        )  # 更新数据库中的任务状态为成功
        await update_task_result(  # 更新内存中的任务结果（用于SSE推送）
            task_id,  # 任务ID
            {  # 结果数据
                "jd_analysis_id": job_description_analysis.id,  # 返回新创建的分析记录ID
            },
        )

        asyncio.create_task(
            cleanup_task(task_id, None)
        )  # 创建异步任务清理内存中的任务状态

    except Exception as e:  # 捕获所有异常
        await db.rollback()  # 回滚数据库事务，撤销所有未提交的更改
        log.error(f"run_match_task error: {str(e)}")  # 记录错误日志
        await _update_work_status(
            db, task_id, TaskStatus.ERROR
        )  # 更新数据库中的任务状态为失败
        await update_task_error(
            task_id, f"run_match_task error: {str(e)}"
        )  # 更新内存中的任务错误信息
        asyncio.create_task(
            cleanup_task(task_id, None)
        )  # 创建异步任务清理内存中的任务状态
        raise  # 重新抛出异常，让调用者知道任务失败


async def _update_work_status(  # 定义私有异步函数：更新工作任务状态
    db: AsyncSession,  # 参数：异步数据库会话
    task_id: str,  # 参数：任务ID
    status: TaskStatus,  # 参数：新的任务状态
    error: str | None = None,  # 参数：错误信息（可选，仅在状态为ERROR时传入）
) -> None:  # 返回值：无
    """更新任务状态到数据库。

    根据任务ID查找对应的工作任务记录，并更新其状态和更新时间。
    如果提供了错误信息，还会记录错误消息。

    Args:
        db: 异步数据库会话。
        task_id: 任务ID。
        status: 新的任务状态。
        error: 错误信息（当状态为ERROR时传入）。
    """  # 函数文档字符串（Google风格）
    result = await db.execute(
        select(BaseWork).where(BaseWork.id == task_id)
    )  # 按任务ID查询工作任务记录
    work = result.scalar_one_or_none()  # 获取查询结果，不存在则返回None
    if work:  # 如果找到了工作任务记录
        work.status = status.value  # 更新任务状态（枚举转为字符串值）
        work.updated_at = datetime.now(SHANGHAI_TZ)  # 更新时间为当前上海时区时间
        if error:  # 如果提供了错误信息
            work.error_message = error  # 记录错误消息
        await db.commit()  # 提交事务，将更新写入数据库
