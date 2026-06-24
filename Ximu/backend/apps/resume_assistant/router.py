"""简历助手（AI Agent）的API路由模块。

本模块提供AI简历助手功能：
1. POST /resume-assistant - AI对话式简历优化（Agent模式）
2. POST /resume-assistant/sub-resumes - 根据JD自动创建子简历

AI助手可以理解用户意图，自动调用工具修改简历内容。
"""  # 模块文档字符串

import uuid  # 导入UUID模块
from typing import Annotated  # 导入Annotated类型注解

from fastapi import (  # 导入FastAPI核心组件
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select  # SQL查询构建器
from sqlalchemy.ext.asyncio import AsyncSession  # 异步数据库会话
from sse_starlette import EventSourceResponse  # SSE响应类

from apps.resume_assistant.agent_service import (
    resume_assistant_service,  # AI助手服务函数
)
from apps.resume_assistant.schemas import (
    ResumeAssistantRequest,  # AI助手请求数据模型
    SubResumeCreateRequest,  # 创建子简历请求数据模型
)
from apps.resume_assistant.task_service import (
    run_sub_resume_task,  # 运行子简历创建任务
)
from shared.api import get_client  # 获取LLM客户端
from shared.database import get_session  # 获取数据库会话
from shared.models import (
    BaseWork,  # 工作任务模型
    Resume,  # 简历模型
    ResumeSection,  # 板块模型
)
from shared.task_state import create_task  # 创建任务状态
from shared.types.task import TaskStatus, TaskType  # 任务状态和类型枚举
from shared.types.work import TaskIdResponse  # 任务ID响应模型

# 创建简历助手模块的API路由器
router = APIRouter(
    prefix="/resume-assistant",  # URL前缀
    tags=["resume-assistant"],  # API文档标签
)


@router.post(
    "",  # URL路径：POST /resume-assistant
    summary="AI简历助手Agent",
)
async def resume_assistant(
    request: Annotated[
        ResumeAssistantRequest,
        Body(description="AI简历助手请求参数"),
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> EventSourceResponse:
    """基于LLM的Agent接口，LLM作为大脑通过工具操作简历数据。

    自动处理多轮工具调用，并将AI回复和工具调用记录自动写入数据库。
    前端通过SSE接收实时响应。

    注意：调用此接口前，用户消息需自行入库。

    Args:
        request: AI助手请求参数（包含简历ID、用户消息等）。
        db: 数据库会话。
    """
    # 查询简历的所有可见板块
    sections_result = await db.execute(
        select(ResumeSection)
        .where(
            ResumeSection.resume_id == request.resume_id,  # 条件：简历ID匹配
            ResumeSection.visible == True,  # 条件：板块可见
        )
        .order_by(ResumeSection.sort_order.asc())  # 按排序升序
    )
    resume_section_list = sections_result.scalars().all()  # 获取所有板块

    sections = [resume.to_pydantic() for resume in resume_section_list]  # 转为Pydantic

    # 查询简历信息
    resume_result = await db.execute(
        select(Resume).where(Resume.id == request.resume_id)
    )
    resume = resume_result.scalar_one_or_none()  # 获取简历

    if resume is None:  # 如果简历不存在
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"简历不存在: {request.resume_id}",
        )

    return await resume_assistant_service(
        request, resume, sections, db
    )  # 调用AI助手服务


@router.post(
    "/sub-resumes",  # URL路径：POST /resume-assistant/sub-resumes
    summary="根据JD自动创建子简历",
)
async def create_sub_resume(
    background_tasks: BackgroundTasks,  # 后台任务管理器
    request: Annotated[
        SubResumeCreateRequest,
        Body(description="子简历创建请求参数"),
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TaskIdResponse:
    """根据职位描述（JD）自动创建优化后的子简历。

    使用AI分析职位描述，自动调整简历内容以匹配岗位要求。
    任务在后台执行，返回task_id供前端轮询状态。

    Args:
        background_tasks: 后台任务管理器。
        request: 创建子简历的请求参数。
        db: 数据库会话。
    """
    # 验证主简历存在
    section_result = await db.execute(
        select(Resume).where(
            Resume.id == request.workspace_id
        )  # 查询数据库，根据主简历ID查找简历
    )
    resume = section_result.scalar_one_or_none()  # 获取查询结果，如果不存在则为None

    if resume is None:  # 如果主简历不存在
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,  # 返回404状态码
            detail=f"简历不存在: {request.workspace_id}",  # 错误详情
        )

    task_id = str(uuid.uuid4())  # 生成唯一的任务ID，后续用于标识这个后台任务

    # 查询主简历的所有板块
    section_result = await db.execute(
        select(ResumeSection)  # 查询板块表
        .where(ResumeSection.resume_id == request.workspace_id)  # 条件：属于这个主简历
        .order_by(ResumeSection.sort_order.asc())  # 按排序序号升序排列
    )
    resume_section_list = section_result.scalars().all()  # 获取所有板块对象
    sections = [
        resume.to_pydantic() for resume in resume_section_list
    ]  # 把ORM对象转成Pydantic模型，后续传给LLM

    # 创建任务记录，保存到数据库
    work = BaseWork(
        id=task_id,  # 任务ID
        task_type=TaskType.JD_GENERATE.value,  # 任务类型：JD生成
        status=TaskStatus.PENDING.value,  # 状态：待处理
        meta_info={  # 元数据，记录这次任务的相关信息
            "job_description": request.job_description,  # 职位描述原文
            "job_title": request.job_title,  # 岗位名称
            "template": request.template,  # 简历模板
            "title": request.title,  # 子简历标题
        },
    )
    db.add(work)  # 把任务记录添加到数据库会话
    await db.commit()  # 提交事务，把任务记录持久化到数据库

    create_task(
        task_id, TaskType.JD_GENERATE
    )  # 在内存中创建任务状态，后续用于跟踪任务进度

    client = get_client(
        request.type, request.api_key, request.base_url
    )  # 根据用户配置获取LLM客户端实例

    background_tasks.add_task(  # 添加后台任务，FastAPI会在响应返回后异步执行
        run_sub_resume_task,  # 执行函数：创建子简历
        db,
        task_id,
        client,
        request,
        sections,  # 传入所有需要的参数
    )

    return TaskIdResponse(task_id=task_id)  # 立即返回任务ID，前端可以用它来轮询任务状态
