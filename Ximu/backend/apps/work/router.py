"""工作任务管理的API路由模块。

本模块提供工作任务的管理功能：
1. GET /work/list - 查询任务列表（支持按类型、状态、meta_info过滤）
2. GET /work/{id} - 查询单个任务详情
3. DELETE /work/delete/{id} - 删除任务
4. GET /work/stream/{task_id} - 通过SSE实时推送任务状态

工作任务用于跟踪后台异步任务的状态（如JD评分、PDF导出等）。
"""  # 模块文档字符串

import json  # 导入JSON模块，用于解析meta_info过滤条件
from typing import Annotated  # 导入Annotated类型注解工具

from fastapi import APIRouter, Depends, HTTPException, Query  # 导入FastAPI核心组件
from sqlalchemy import and_, select  # 导入SQLAlchemy查询和逻辑操作符
from sqlalchemy.ext.asyncio import AsyncSession  # 导入异步数据库会话
from sse_starlette.sse import EventSourceResponse  # 导入SSE响应类（Server-Sent Events）

from apps.work.sse import sse_event_generator  # 从apps/work/sse.py导入SSE事件生成器
from shared.database import get_session  # 获取数据库会话的依赖函数
from shared.models import BaseWork  # 工作任务的ORM模型
from shared.task_state import tasks  # 从shared/task_state.py导入内存中的任务状态字典
from shared.types.work import WorkSchema  # 工作任务的Pydantic模型

# 创建工作任务模块的API路由器
router = APIRouter(prefix="/work", tags=["work"])  # URL前缀：/work


@router.get("/list", summary="查询任务列表")  # GET /work/list
async def get_work_list(  # 定义异步处理函数
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
    task_type: Annotated[  # 查询参数：任务类型（可选）
        str | None, Query(description="任务类型（如jd_score、export_pdf）")
    ] = None,
    status: Annotated[  # 查询参数：任务状态（可选）
        str | None, Query(description="任务状态（如pending、running、success、error）")
    ] = None,
    meta_contains: Annotated[  # 查询参数：meta_info包含条件（可选）
        str | None, Query(description='meta_info包含的JSON，如{"resume_id":"xxx"}')
    ] = None,
) -> list[WorkSchema]:  # 返回值类型：任务列表
    """查询任务列表，支持多条件过滤。

    可以按任务类型、状态、meta_info内容进行过滤。
    meta_contains参数用于查询特定简历关联的任务。

    Args:
        db: 异步数据库会话。
        task_type: 任务类型过滤。
        status: 任务状态过滤。
        meta_contains: meta_info字段的JSON过滤条件。
    """  # 文档字符串
    query = select(BaseWork)  # 初始化查询：选择所有工作任务
    if task_type:  # 如果提供了任务类型
        query = query.where(BaseWork.task_type == task_type)  # 添加类型过滤条件
    if status:  # 如果提供了任务状态
        query = query.where(BaseWork.status == status)  # 添加状态过滤条件
    if meta_contains:  # 如果提供了meta_info过滤条件
        try:  # 尝试解析JSON
            filter_dict = json.loads(meta_contains)  # 将JSON字符串解析为字典
            if not isinstance(filter_dict, dict):  # 如果解析结果不是字典
                raise HTTPException(  # 抛出400异常
                    status_code=400,
                    detail="meta_contains必须是JSON对象",
                )
            json_filters = [  # 构建JSON字段过滤条件列表
                BaseWork.meta_info[k].as_string() == str(v)  # 对每个键值对创建等值过滤
                for k, v in filter_dict.items()  # 遍历过滤字典
            ]
            query = query.where(and_(*json_filters))  # 添加所有过滤条件（AND逻辑）
        except json.JSONDecodeError:  # 如果JSON解析失败
            raise HTTPException(  # 抛出400异常
                status_code=400, detail="meta_contains必须是有效JSON"
            )
    result = await db.execute(query)  # 执行查询
    work_list = result.scalars().all()  # 获取所有结果
    return [  # 列表推导式
        WorkSchema.model_validate(item) for item in work_list  # 转为Pydantic模型
    ]
# 1. 侧边栏通知 — 自动轮询错误任务
# Sidebar.tsx:21-24
# useQuery refetchInterval: 15000  ← 每 15 秒自动拉一次
# 目的：拿到所有 parse 和 jd_generate 类型中状态为 error 的任务，在通知列表里显示，让用户看到哪些任务失败了。
# GET /work/list?task_type=parse&status=error
# GET /work/list?task_type=jd_generate&status=error
# 2. 提交匹配分析前 — 用户点击按钮时自动调用
# WorkspaceDetail.tsx:542
# ScoreDetailModal.tsx:284
# 目的：用户点击"匹配分析"按钮后，先查一下这个简历是否已经有 running 中的 JD 评分任务。如果有，直接提示"已有任务进行中"并返回，不重复提交。
# GET /work/list?task_type=jd_score&status=running&meta_contains={"resume_id":"xxx"}
# 一句话总结
# 调用时机	查什么	为什么要查
# 每 15 秒自动	所有失败的解析/生成任务	在通知列表显示错误
# 用户点击"匹配分析"时	该简历是否有 running 的评分任务	防止重复提交，秒级提示

@router.get("/{id}", summary="查询单个任务详情")  # GET /work/{id}
async def get_by_id(  # 定义异步处理函数
    id: str,  # 路径参数：任务ID
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> WorkSchema:  # 返回值类型：任务数据
    """根据ID查询单个任务的详情。

    Args:
        id: 任务的唯一标识符。
        db: 异步数据库会话。
    """  # 文档字符串
    result = await db.execute(  # 执行查询
        select(BaseWork).where(BaseWork.id == id)  # 按ID查找
    )
    item = result.scalar_one_or_none()  # 获取结果
    if not item:  # 如果任务不存在
        raise HTTPException(status_code=404, detail="任务不存在")  # 抛出404异常
    return WorkSchema.model_validate(item)  # 转为Pydantic模型返回


@router.delete("/delete/{id}", summary="删除任务")  # DELETE /work/delete/{id}
async def delete_by_id(  # 定义异步处理函数
    id: str,  # 路径参数：任务ID
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> WorkSchema:  # 返回值类型：被删除的任务数据
    """删除指定ID的任务记录。

    Args:
        id: 要删除的任务ID。
        db: 异步数据库会话。
    """  # 文档字符串
    result = await db.execute(  # 执行查询
        select(BaseWork).where(BaseWork.id == id)  # 按ID查找
    )
    work = result.scalar_one_or_none()  # 获取结果
    if not work:  # 如果任务不存在
        raise HTTPException(status_code=404, detail="任务不存在")  # 抛出404异常
    try:  # 尝试删除
        await db.delete(work)  # 删除任务记录
        await db.commit()  # 提交事务
    except Exception:  # 删除失败
        await db.rollback()  # 回滚事务
        raise HTTPException(status_code=500, detail="删除任务失败")  # 抛出500异常
    return WorkSchema.model_validate(work)  # 返回被删除的任务数据


@router.get("/stream/{task_id}", summary="通过SSE实时推送任务状态")  # GET /work/stream/{task_id}
async def stream_task_result(task_id: str):  # 定义异步处理函数
    """通过SSE（Server-Sent Events）实时推送任务状态变化。

    前端通过EventSource连接此接口，可以实时收到任务状态更新，
    而不需要频繁轮询。适用于长时间运行的任务（如LLM分析）。

    Args:
        task_id: 要监听的任务ID。
    """  # 文档字符串
    if task_id not in tasks:  # 如果任务ID不在内存中的任务字典里
        raise HTTPException(status_code=404, detail="任务不存在")  # 抛出404异常
    return EventSourceResponse(  # 返回SSE响应
        sse_event_generator(task_id)  # 使用SSE事件生成器（定义在apps/work/sse.py中）
    )
