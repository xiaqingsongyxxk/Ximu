"""职位描述分析路由模块。

本模块提供FastAPI路由，用于：
1. 查询简历的职位分析历史列表
2. 查询单个职位分析的详情
3. 创建后台任务进行简历与职位的AI匹配评分

职位分析功能使用LLM（大语言模型）来评估简历与目标职位的匹配度。
"""  # 模块文档字符串

import uuid  # 导入UUID模块，用于生成唯一的任务ID
from typing import Annotated  # 导入Annotated类型注解工具，用于FastAPI参数元数据

from fastapi import (  # 从FastAPI框架导入核心组件
    APIRouter,  # API路由器
    BackgroundTasks,  # 后台任务管理器，用于执行异步任务（如调用LLM）
    Body,  # 请求体装饰器，用于标记请求体参数
    Depends,  # 依赖注入装饰器
    HTTPException,  # HTTP异常类
    status,  # HTTP状态码常量（如404、400、500）
)
from sqlalchemy import select  # SQL查询构建器
from sqlalchemy.ext.asyncio import AsyncSession  # 异步数据库会话

from apps.jd_analysis.schemas import (
    MatchRequest,  # 从apps/jd_analysis/schemas.py导入匹配请求数据模型
)
from apps.jd_analysis.service import (
    run_match_task,  # 从apps/jd_analysis/service.py导入运行匹配任务的函数
)
from shared.api import get_client  # 从shared/api/__init__.py导入获取LLM客户端的函数
from shared.database import (
    get_session,  # 从shared/database.py导入获取数据库会话的依赖函数
)
from shared.models import BaseWork, JobDescriptionAnalysis, Resume  # 导入数据库模型
from shared.task_state import (
    create_task,  # 从shared/task_state.py导入创建任务状态记录的函数
)
from shared.types.jd_analysis import (
    JobDescriptionAnalysisSchema,  # 导入职位分析的Pydantic模型
)
from shared.types.task import TaskStatus, TaskType  # 导入任务状态和任务类型的枚举
from shared.types.work import (
    TaskIdResponse,  # 导入任务ID响应模型（返回给前端的task_id）
)

# 创建职位分析模块的API路由器
router = APIRouter(
    prefix="/jd-analysis",  # URL前缀：所有路由都以 /jd-analysis 开头
    tags=["jd-analysis"],  # API文档标签：在Swagger UI中分组显示
)


@router.get("/list/{resume_id}", summary="获取简历的职位分析列表(按时间降序)")  # GET /jd-analysis/list/{resume_id}
async def list_jd_analysis(  # 定义异步处理函数
    resume_id: str,  # 路径参数：简历ID
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> list[JobDescriptionAnalysisSchema]:  # 返回值类型：职位分析记录列表
    """查询指定简历的所有职位分析记录，按创建时间降序排列。

    返回该简历历史上所有的JD分析结果，
    前端用于显示分析历史列表。

    Args:
        resume_id: 要查询的简历ID。
        db: 异步数据库会话。
    """  # 文档字符串
    result = await db.execute(  # 执行数据库查询
        select(JobDescriptionAnalysis)  # 查询JobDescriptionAnalysis表
        .where(JobDescriptionAnalysis.resume_id == resume_id)  # 条件：简历ID匹配
        .order_by(JobDescriptionAnalysis.created_at.desc())  # 按创建时间降序排列（最新的在前）
    )

    jd_analysis_list = result.scalars().all()  # 获取所有查询结果

    return [  # 列表推导式，将每个ORM对象转为Pydantic模型
        jd_analysis.to_pydantic() for jd_analysis in jd_analysis_list
    ]


@router.get("/{jd_analysis_id}", summary="获取职位分析详情")  # GET /jd-analysis/{jd_analysis_id}
async def get_jd_analysis(  # 定义异步处理函数
    jd_analysis_id: int,  # 路径参数：职位分析记录的ID（整数，自增主键）
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> JobDescriptionAnalysisSchema:  # 返回值类型：单条职位分析记录
    """根据ID查询单条职位分析记录的详情。

    前端用于显示单次分析的完整结果（包括评分、关键词匹配、建议等）。

    Args:
        jd_analysis_id: 职位分析记录的ID。
        db: 异步数据库会话。
    """  # 文档字符串
    result = await db.execute(  # 执行数据库查询
        select(JobDescriptionAnalysis).where(  # 查询JobDescriptionAnalysis表
            JobDescriptionAnalysis.id == jd_analysis_id  # 条件：ID匹配
        )
    )

    jd_analysis = result.scalars().first()  # 获取第一条结果

    return jd_analysis.to_pydantic()  # 转为Pydantic模型返回


@router.post("/match", summary="创建JD匹配评分任务")  # POST /jd-analysis/match
async def create_score_task(  # 定义异步处理函数
    background_tasks: BackgroundTasks,  # FastAPI的后台任务管理器
    data: Annotated[
        MatchRequest, Body(description="JD评分请求参数")  # 请求体：匹配请求数据
    ],
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> TaskIdResponse:  # 返回值类型：包含task_id的响应
    """创建一个后台任务来评估简历与职位的匹配度。

    流程：
    1. 验证简历存在且包含职位描述
    2. 检查是否已有相同任务在运行（防重复）
    3. 创建任务记录（BaseWork）
    4. 启动后台任务调用LLM进行分析
    5. 返回task_id供前端轮询状态

    前端收到task_id后，通过SSE（Server-Sent Events）监听任务进度。
    """  # 文档字符串
    # 第一步：验证简历存在
    result = await db.execute(
        select(Resume).where(Resume.id == data.resume_id)  # 按ID查询简历
    )
    resume = result.scalar_one_or_none()  # 获取结果

    if resume is None:  # 如果简历不存在
        raise HTTPException(  # 抛出404异常
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"简历不存在: {data.resume_id}",
        )

    # 第二步：检查简历是否有职位描述（meta_info中的job_description字段）
    if (
        resume.meta_info is None or "job_description" not in resume.meta_info
    ):  # 如果没有职位描述
        raise HTTPException(  # 抛出400异常（请求参数错误）
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="简历缺少职位描述(job_description)，无法进行评分",
        )

    # 第三步：检查是否已有相同的运行中任务（防止重复提交）
    existing = await db.execute(
        select(BaseWork).where(  # 查询work表
            BaseWork.task_type == TaskType.JD_SCORE.value,  # 任务类型是JD评分
            BaseWork.status == TaskStatus.RUNNING.value,  # 状态是运行中
            BaseWork.meta_info["resume_id"].as_string()  # meta_info中的resume_id
            == data.resume_id,  # 等于当前简历ID
        )
    )
    existing_task = existing.scalar_one_or_none()  # 获取查询结果
    if existing_task is not None:  # 如果已有相同任务
        return TaskIdResponse(task_id=existing_task.id)  # 直接返回已有的task_id，不重复创建

    # 第四步：创建新的任务记录
    meta_info = resume.meta_info  # 获取简历的元数据

    job_description: str = meta_info.get("job_description")  # 提取职位描述文本

    job_title: str | None = meta_info.get("job_title")  # 提取职位名称（可能为空）

    task_id = str(uuid.uuid4())  # 生成唯一的任务ID

    work = BaseWork(  # 创建工作任务数据库记录
        id=task_id,  # 任务ID
        task_type=TaskType.JD_SCORE.value,  # 任务类型：JD评分
        status=TaskStatus.PENDING.value,  # 初始状态：待处理
        meta_info={"resume_id": resume.id},  # 元数据：关联的简历ID
    )
    db.add(work)  # 添加到数据库会话
    await db.commit()  # 提交事务，写入数据库

    # 第五步：获取LLM客户端并启动后台任务
    client = get_client(data.type, data.api_key, data.base_url)  # 根据配置获取OpenAI或Anthropic客户端

    create_task(task_id, TaskType.JD_SCORE)  # 在内存中创建任务状态记录（用于SSE推送）

    # 添加后台任务：FastAPI会在响应返回后异步执行这个函数
    background_tasks.add_task(
        run_match_task,  # 要执行的函数（定义在 apps/jd_analysis/service.py 中）
        db,  # 数据库会话
        task_id,  # 任务ID
        client,  # LLM客户端
        data.model,  # 模型名称（如"gpt-4"）
        data.resume_id,  # 简历ID
        job_description,  # 职位描述文本
        job_title,  # 职位名称
    )

    return TaskIdResponse(task_id=task_id)  # 返回任务ID，前端用它来轮询任务状态
