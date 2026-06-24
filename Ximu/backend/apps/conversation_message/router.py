# ruff: noqa: I001
"""会话消息管理的API路由模块。

本模块提供对话消息的CRUD操作：
1. GET /conversation-message/list/{conversation_id} - 获取会话消息列表
2. POST /conversation-message/create - 创建用户消息
3. DELETE /conversation-message/delete - 删除单条消息
4. DELETE /conversation-message/delete/conversation - 删除会话的所有消息
"""

import json  # 把消息内容转成JSON字符串存到数据库（数据库不认识Python对象，只认识文本）
from typing import Annotated  # 给函数参数加说明，告诉FastAPI这个参数需要特殊处理

from fastapi import (  # FastAPI是搭建网络API的工具箱
    APIRouter,  # 把"网址"和"处理函数"绑定，比如访问 /list 就交给 get_message_list 处理
    Body,  # 从POST请求的JSON里提取内容转成Python对象
    Depends,  # 自动准备好依赖（比如数据库连接），函数直接拿来用
    HTTPException,  # 出错了（如找不到数据），返回标准错误信息给前端
    Query,  # 从网址?后面取参数，如 /delete?id=123 中的123
)
from pydantic import BaseModel, ConfigDict, alias_generators  # 定义数据结构、校验格式、自动转字段名（user_name ↔ userName）
from sqlalchemy import delete, select  # 数据库查数据/删数据
from sqlalchemy.ext.asyncio import AsyncSession  # 数据库连接通道，所有数据库操作都通过它进行

from shared.database import get_session  # 每次调用返回一个新数据库连接，确保每个请求都有自己的通道
from shared.models import ConversationMessageRecord  # 数据库消息表模型，定义了消息有哪些字段（ID、会话ID、角色、内容等）
from shared.types.messages import ConversationMessageSchema  # 返回给前端时的格式校验，确保数据结构正确

# 创建路由器，所有对话消息相关的网址都以 /conversation-message 开头
# tags 只是给API文档分组的，方便在文档页面找到这一组接口
router = APIRouter(prefix="/conversation-message", tags=["conversation-message"])


class CreateMessageRequest(BaseModel):
    """创建消息的请求数据结构。"""
    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,  # 前端传conversationId或conversation_id都认
    )

    conversation_id: str  # 这条消息属于哪个会话？后续查某个会话的所有消息就是靠这个ID筛选
    user_input: str  # 用户说了什么？这是消息正文，要存到数据库，AI回复时也会用到


@router.get("/list/{conversation_id}", summary="获取会话消息列表")
async def get_message_list(
    conversation_id: str,  # 会话ID，实际就是简历ID（resume_id），前端打开哪个简历就传哪个ID
    db: Annotated[AsyncSession, Depends(get_session)],  # 自动创建数据库连接传进来，所有查/写数据都通过它
) -> list[ConversationMessageSchema]:  # 返回消息列表，前端拿到后按顺序展示在对话界面上
    """获取指定会话的所有消息，按创建时间排序。"""
    stmt = (
        select(ConversationMessageRecord)  # 从消息表查数据
        .where(ConversationMessageRecord.conversation_id == conversation_id)  # 只查当前会话的消息，不加这个条件会把所有人的消息都查出来
        .order_by(ConversationMessageRecord.created_at)  # 按创建时间排，最早的消息在最前面，这样对话顺序才正确
    )
    result = await db.execute(stmt)  # 把查询语句发给数据库执行，await的意思是等数据库查完再继续
    record_list = result.scalars().all()  # 从数据库返回的结果里提取出真正的消息数据，变成一个列表
    return [record.to_pydantic() for record in record_list]  # 把数据库格式转成前端能用的格式再返回


@router.post("/create", summary="创建用户消息")
async def create_message(
    request: Annotated[CreateMessageRequest, Body()],  # 从请求体JSON中提取创建消息所需的信息，自动转成CreateMessageRequest对象
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ConversationMessageSchema:  # 返回创建成功的消息完整信息（含数据库自动生成的ID、时间等），前端拿到后立刻显示在界面上
    """创建一条用户消息。"""
#     在 agent/runtime.py:588 可以看到：
# ConversationMessageRecord(
#     conversation_id=resume_id,  # 对话ID就是简历ID
# 所以流程是：
# 1. 用户打开某个简历（比如 /resume/abc-123）
# 2. 前端已经从 URL/路由参数里拿到了 resume_id = "abc-123"
# 3. 前端直接用这个 resume_id 当 conversation_id 发请求：
#       GET /conversation-message/list/abc-123
#    4. 后端就从数据库查出该简历关联的所有对话消息
# 消息表定义 conversation_id 字段的用意就是：*每个简历就是一个"会话"*，简历 ID 就是会话 ID。
    record = ConversationMessageRecord(
        conversation_id=request.conversation_id,  # 填入会话ID，后续靠这个ID找到这条消息属于哪个对话
        role="user",  # 填入角色，"user"表示是用户发的。AI回复时填"assistant"。前端靠这个区分消息样式
        content=json.dumps(
            [{"type": "text", "text": request.user_input}],  # 包装成标准内容列表格式，目前只有文本，后续可扩展图片、文件等
            ensure_ascii=False,  # 允许中文直接存，不转成\uXXXX乱码
        ),
    )
    db.add(record)  # 告诉数据库我准备存一条新记录，但还没真正写入
    try:
        await db.commit()  # 正式提交，消息才真正存到数据库。不调用commit的话程序重启数据就丢了
        await db.refresh(record)  # 从数据库重新读取，把自动生成的ID、创建时间等字段值取回来，确保返回给前端的数据完整
    except Exception:
        await db.rollback()  # 出错了就撤销，回到之前的状态，避免留下半截垃圾数据
        raise HTTPException(status_code=500, detail="创建失败")  # 告诉前端服务器内部出错了，消息没保存成功
    return record.to_pydantic()  # 转成前端友好格式返回，前端拿到后显示在对话界面上


@router.delete("/delete", summary="删除单条消息")
async def delete_message(
    id: Annotated[int, Query(description="消息ID")],  # 从网址?后面取消息ID（如 /delete?id=123）。这个id是创建消息时数据库自动生成的，通过POST /create 的返回值给了前端，前端存下来，删除时传回来
    db: Annotated[AsyncSession, Depends(get_session)],
) -> None:  # 没有返回值，前端收到HTTP 200就知道删除成功了
    """删除指定ID的消息。"""
    await db.execute(delete(ConversationMessageRecord).where(ConversationMessageRecord.id == id))  # 告诉数据库要删哪一行（id是自增主键，创建时由数据库自动生成，不是前端传的）
    try:
        await db.commit()  # 正式提交，删除才真正生效。不commit的话程序重启数据还在
    except Exception:
        await db.rollback()  # 撤销操作，回到删除前的状态
        raise HTTPException(status_code=500, detail="删除失败")
    return None  # 删除成功，返回空。前端从界面上移除这条消息


@router.delete("/delete/conversation", summary="删除会话的所有消息")
async def delete_message_by_conversation_id(
    conversation_id: Annotated[str, Query(description="会话ID")],  # 从网址?后面取会话ID，前端清空对话时调用这个接口
    db: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """删除指定会话的所有消息。"""
    await db.execute(
        delete(ConversationMessageRecord).where(
            ConversationMessageRecord.conversation_id == conversation_id
        )
    )
    try:
        await db.commit()  # 正式提交，该会话下所有消息才真正从数据库消失
    except Exception:
        await db.rollback()  # 出错了就撤销，防止只删了一半留下不完整的对话数据
        raise HTTPException(status_code=500, detail="删除失败")
    return None  # 清空成功，返回空。前端收到后清空对话界面
# 后端和前端的关系如下：
# 后端关系
# 两者是平级模块，都在 main.py 独立注册路由：
# # main.py:102-107
# app.include_router(resume_assistant_router)       # → POST /resume-assistant
# app.include_router(conversation_message_router)    # → GET  /conversation-message/list/{id}
#                                                   #   POST /conversation-message/create
#                                                   #   DELETE ...
# 没有互相调用。但它们在数据层面共享同一个数据库表 conversation_messages：
# resume_assistant/agent/runtime.py:586-599
#     ↓ 直接操作 ConversationMessageRecord（写DB）
#     ↓
# conversation_messages 表
#     ↑
# conversation_message/router.py（REST API，供前端查/写）
# 前端关系
# 前端使用两个接口，分工不同：
# 1. 打开简历页面时 → 调 conversation_message 接口加载历史
# 前端 → GET /conversation-message/list/{resume_id}
#      → 从 DB 读出该简历的所有历史消息
#      → 渲染到对话界面上（用户看到之前的对话记录）
# 2. 用户发新消息时 → 调 resume_assistant 接口
# 前端 → POST /resume-assistant（SSE 流式）
#      → 后端 Agent 开始跑
#          ├── 回复消息 → 写入 DB（ConversationMessageRecord）
#          ├── 回复消息 → 写入 JSONL 文件
#          └── SSE 推给前端实时显示
# 完整数据流
# 用户打开简历
#     ↓
# 前端 GET /conversation-message/list/{resume_id}  ← 从 DB 拉历史
#     ↓
# 渲染对话界面（看到之前的所有对话）
#     ↓
# 用户输入新消息
#     ↓
# 前端 POST /resume-assistant（SSE）
#     ↓
# 后端 Agent 运行 → 回复一条消息
#     ├── 写入 DB（ConversationMessageRecord） → 下次刷新页面时从这里读
#     ├── 写入 JSONL 文件（conversation_store） → Agent 自己下次运行时从这里读
#     └── SSE 推给前端 → 界面实时显示
# 关键点
#  	conversation_message 路由
# 谁调	前端（加载历史、管理消息）
# 读历史	从 DB 读 → 展示给用户
# 写消息	前端手动创建消息时用
# 所以 conversation_message 路由是给前端直接调 REST API 的，不是给 resume_assistant 模块内部用的。 两边的数据最终汇集在同一个数据库表里，前端各取所需。