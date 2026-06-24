"""简历板块（Section）的API路由模块。

本模块提供简历板块的CRUD操作：
1. GET /resume-section/one - 获取单个板块详情
2. GET /resume-section/{id} - 获取简历的所有板块列表
3. POST /resume-section/create - 创建新板块
4. PUT /resume-section/update - 更新板块（不存在则创建）
5. DELETE /resume-section/delete - 删除单个板块
6. DELETE /resume-section/delete/all - 删除简历的所有板块

简历板块包括：个人信息、个人简介、工作经历、教育背景、技能特长等。
"""  # 模块文档字符串

import json  # 导入JSON模块，用于处理板块内容的JSON序列化
import logging  # 导入日志模块
from typing import Annotated  # 导入Annotated类型注解工具

from fastapi import (  # 从FastAPI框架导入核心组件
    APIRouter,  # API路由器
    Depends,  # 依赖注入
    HTTPException,  # HTTP异常
    Path,  # 路径参数装饰器
    Query,  # 查询参数装饰器
)
from sqlalchemy import delete, select  # SQL查询和删除构建器
from sqlalchemy.ext.asyncio import AsyncSession  # 异步数据库会话

from shared.database import get_session  # 获取数据库会话的依赖函数
from shared.models import ResumeSection  # 简历板块的ORM模型
from shared.types.resume import ResumeSectionSchema  # 简历板块的Pydantic模型

log = logging.getLogger(__name__)  # 创建本模块的日志记录器

# 创建简历板块模块的API路由器
router = APIRouter(
    prefix="/resume-section",  # URL前缀
    tags=["resume-section"],  # API文档标签
)


@router.get(  # 定义GET请求路由
    "/one",  # URL路径：GET /resume-section/one?id=xxx
    summary="根据板块ID获取单个板块详情",  # API文档描述
)
async def get_by_id_and_type(  # 定义异步处理函数
    id: Annotated[str, Query(description="板块ID")],  # 查询参数：板块ID
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> ResumeSectionSchema:  # 返回值类型：板块数据
    """根据板块ID获取单个板块的详情。

    前端用于获取特定板块的完整内容（如编辑时加载数据）。

    Args:
        id: 板块的唯一标识符。
        db: 异步数据库会话。
    """  # 文档字符串
    result = await db.execute(  # 执行数据库查询
        select(ResumeSection).where(ResumeSection.id == id)  # 按ID查询
    )
    resume_section = result.scalar_one_or_none()  # 获取查询结果
    if not resume_section:  # 如果板块不存在
        raise HTTPException(status_code=404, detail="板块不存在")  # 抛出404异常
    return resume_section.to_pydantic()  # 转为Pydantic模型返回


@router.get(  # 定义GET请求路由
    "/{id}",  # URL路径：GET /resume-section/{id}
    summary="根据简历ID获取该简历的所有板块列表",  # API文档描述
)
async def get_by_resumeid(  # 定义异步处理函数
    id: Annotated[str, Path(description="简历ID")],  # 路径参数：简历ID
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> list[ResumeSectionSchema]:  # 返回值类型：板块列表
    """获取指定简历的所有板块列表。

    前端在编辑器页面加载时调用，获取简历的全部板块内容。

    Args:
        id: 简历的唯一标识符。
        db: 异步数据库会话。
    """  # 文档字符串
    result = await db.execute(  # 执行数据库查询
        select(ResumeSection).where(ResumeSection.resume_id == id)  # 按简历ID查询所有板块
    )
    resume_section_list = result.scalars().all()  # 获取所有板块
    return [item.to_pydantic() for item in resume_section_list]  # 批量转为Pydantic模型返回


@router.post("/create", summary="创建新板块")  # POST /resume-section/create
async def create_section(  # 定义异步处理函数
    data: ResumeSectionSchema,  # 请求体：板块数据
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> ResumeSectionSchema:  # 返回值类型：创建的板块数据
    """创建新的简历板块。

    前端用于添加自定义板块（如"证书"、"语言能力"等）。

    Args:
        data: 板块的完整数据。
        db: 异步数据库会话。
    """  # 文档字符串
    section = ResumeSection.from_pydantic(data)  # 将Pydantic对象转为ORM对象
    db.add(section)  # 添加到数据库会话
    try:  # 尝试提交
        await db.commit()  # 提交事务
        await db.refresh(section)  # 刷新对象
    except Exception:  # 提交失败
        await db.rollback()  # 回滚事务
        raise HTTPException(status_code=500, detail="新增板块失败")  # 抛出500异常
    return section.to_pydantic()  # 返回创建的板块


@router.put(  # 定义PUT请求路由
    "/update", summary="更新板块（不存在时自动创建）"  # PUT /resume-section/update
)
async def update_section(  # 定义异步处理函数
    data: ResumeSectionSchema,  # 请求体：板块数据
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> ResumeSectionSchema:  # 返回值类型：更新后的板块数据
    """更新现有板块，如果不存在则创建新板块（Upsert操作）。

    这是前端最常用的接口，用户每次编辑板块内容都会调用。
    content字段会与现有内容合并（浅合并），保留未提交的字段。

    Args:
        data: 包含板块ID和要更新的字段。
        db: 异步数据库会话。
    """  # 文档字符串
    result = await db.execute(  # 执行查询
        select(ResumeSection).where(ResumeSection.id == data.id)  # 按ID查找板块
    )
    resume_section = result.scalar_one_or_none()  # 获取查询结果

    if resume_section is None:  # 如果板块不存在
        # 创建新板块
        section = ResumeSection.from_pydantic(data)  # 转为ORM对象
        db.add(section)  # 添加到数据库会话
        try:  # 尝试提交
            await db.commit()  # 提交事务
            await db.refresh(section)  # 刷新对象
        except Exception:  # 提交失败
            await db.rollback()  # 回滚事务
            raise HTTPException(status_code=500, detail="新增板块失败")  # 抛出500异常
        return section.to_pydantic()  # 返回新创建的板块

    # 更新现有板块
    # data 是一个 Pydantic 模型，model_dump() 把它转成字典。exclude_unset=True 的意思是：只包含前端显式传了的字段，跳过用了默认值的字段。
    updates = data.model_dump(exclude_unset=True)  # 获取请求中传入的字段（排除未设置的）
#     前端只传了部分字段：
# {
#     "id": "xxx",
#     "title": "新标题"
# }
# data.model_dump()
# # {"id": "xxx", "title": "新标题", "sort_order": 0, "visible": True, "content": {}}
# # ↑ 默认值也包含进去了
# data.model_dump(exclude_unset=True)
# # {"id": "xxx", "title": "新标题"}
# # ↑ 只有前端实际传了的字段
    # content字段特殊处理：浅合并，保留现有内容中未被覆盖的字段
    if "content" in updates and updates["content"]:  # 如果传入了content字段
        existing_content = json.loads(resume_section.content)  # 解析现有content为字典
        if isinstance(existing_content, dict):  # 如果现有content是字典类型
            merged = {  # 浅合并：现有内容 + 新内容（新内容覆盖同名字段）
                **existing_content,  # 展开现有内容
                **updates["content"],  # 展开新内容（覆盖同名字段）
            }
            updates["content"] = json.dumps(merged, ensure_ascii=False)  # 序列化合并结果
        else:  # 如果现有content不是字典（如列表）
            updates["content"] = json.dumps(updates["content"], ensure_ascii=False)  # 直接替换
    #         所以当前代码里 existing_content 永远都是 dict，else 分支跑不到。这是一个防御性兜底——如果将来有人加了 content 是 list[Item] 的类型。
    # 所以 dict 做浅合并（保留未传的字段），list 只能直接替换——这是数据结构决定的，不是代码风格差异。不过既然当前所有 content 都是 dict，else 分支实际上走不到。
    for key, value in updates.items():  # 遍历所有要更新的字段
        setattr(resume_section, key, value)  # 动态设置对象属性
    try:  # 尝试提交
        await db.commit()  # 提交事务
        await db.refresh(resume_section)  # 刷新对象
    except Exception as e:  # 提交失败
        await db.rollback()  # 回滚事务
        log.error("更新板块失败: %s", e, exc_info=True)  # 记录错误日志
        raise HTTPException(  # 抛出500异常
            status_code=500, detail=f"修改板块失败: {str(e)}"
        )
    return resume_section.to_pydantic()  # 返回更新后的板块


@router.delete("/delete", summary="删除单个板块")  # DELETE /resume-section/delete?id=xxx
async def delete_section(  # 定义异步处理函数
    id: Annotated[str, Query(description="板块ID")],  # 查询参数：板块ID
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> None:  # 无返回值
    """删除指定ID的板块。

    Args:
        id: 要删除的板块ID。
        db: 异步数据库会话。
    """  # 文档字符串
    await db.execute(delete(ResumeSection).where(ResumeSection.id == id))  # 执行删除
    try:  # 尝试提交
        await db.commit()  # 提交事务
    except Exception:  # 提交失败
        raise HTTPException(status_code=500, detail="删除板块失败")  # 抛出500异常
    return None  # 删除成功


@router.delete(  # 定义DELETE请求路由
    "/delete/all", summary="删除指定简历的所有板块"  # DELETE /resume-section/delete/all?id=xxx
)
async def delete_all(  # 定义异步处理函数
    id: str,  # 查询参数：简历ID
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> None:  # 无返回值
    """删除指定简历下的所有板块。

    通常在删除简历时调用，先删除所有板块，再删除简历本身。

    Args:
        id: 简历ID。
        db: 异步数据库会话。
    """  # 文档字符串
    await db.execute(  # 执行删除
        delete(ResumeSection).where(ResumeSection.resume_id == id)  # 按简历ID删除所有板块
    )
    try:  # 尝试提交
        await db.commit()  # 提交事务
    except Exception:  # 提交失败
        raise HTTPException(status_code=500, detail="删除所有板块失败")  # 抛出500异常
    return None  # 删除成功
