# Agent 服务模块（LangGraph 版）。

# 对应手写版: agent_service.py + agent/runtime.py

# 手写版：
# ConversationStore.read() → IterationState → AgentRuntime.execute()
# → core.run() → generate SSE events

# LangGraph 版：
# ConversationStore.read() → messages → AgentRuntime.execute()
# → run_langgraph_stream() → generate SSE events

# 完全相同的接口和输出，内部使用 StateGraph 实现。


import logging  # 导入 logging 模块，记录服务运行日志（方便排查问题）
from typing import Any  # 导入 Any 类型，用于不确定元素类型的列表

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)  # 导入异步数据库会话（后面要把消息存到 SQLite）
from sse_starlette import (
    EventSourceResponse,
)  # 导入 SSE 响应类（把异步生成器包装成 HTTP 流）

from apps.resume_assistant.agent_langgraph.runtime import (
    AgentRuntime,
)  # 导入 LangGraph 版运行时（核心在 core.py）
from apps.resume_assistant.agent_langgraph.store import (
    ConversationStore,
)  # 导入对话历史存储（和手写版同一个）
from apps.resume_assistant.prompt import (
    SUB_SYSTEM,
    SYSTEM,
    build_sections_prompt,
)  # 导入系统提示词模板
from apps.resume_assistant.schemas import (
    ResumeAssistantRequest,
)  # 导入前端请求的数据结构
from shared.models import Resume  # 导入数据库中的简历模型
from shared.types.messages import (
    ConversationMessage,
)  # 导入消息类型（手写版定义，LangGraph 版复用）
from shared.types.resume import ResumeSectionSchema  # 导入简历板块的数据模型

# log 是用来记录运行日志的
# 手写版也是这么用的，比如 log.info("Service started")
log = logging.getLogger(__name__)  # 创建一个日志记录器，输出时自动标明模块名


async def resume_assistant_service(  # 定义 AI 简历助手的核心服务函数（LangGraph 版）
    request: ResumeAssistantRequest,  # 前端发来的请求
    resume: Resume,  # 当前简历数据
    sections: list[ResumeSectionSchema],  # 简历板块列表
    db: AsyncSession,  # 数据库会话
) -> EventSourceResponse:  # 返回值类型：SSE（Server-Sent Events）响应
    # """AI 简历助手的核心服务函数（LangGraph 版）。

    # 与手写版完全相同的接口：
    # - 同样的请求参数
    # - 同样的返回类型（SSE 事件流）
    # - 同样的对话历史处理

    # 使用 LangGraph 版的 AgentRuntime（内部用 LangGraph），
    # 但外部行为与手写版完全相同。

    # 这个函数被 FastAPI 路由调用，返回的 EventSourceResponse 直接发给前端。
    # """
    # sections_list：把板块数据从 Pydantic 模型转成普通 dict
    # 因为工具函数直接操作 list[dict]，不用 Pydantic 模型
    sections_list: list[  # 定义一个列表，用来装转换后的板块字典
        dict[str, Any]  # 列表元素类型：字符串键 → 任意值的字典
    ] = []  # 创建一个空列表，后面用来装转换后的板块字典
    # id_to_type：板块 ID 到类型的映射
    # 工具函数通过这个映射知道"这个板块是什么类型的"
    id_to_type: dict[  # 定义一个字典，用来记录板块 ID 对应的类型
        str, str  # 键是字符串（板块 ID），值也是字符串（板块类型）
    ] = {}  # 创建一个空字典，后面记录每个板块的 ID 对应什么类型

    # 遍历所有板块，构建 sections_list 和 id_to_type
    for section in sections:  # 从数据库查出来的每一个板块（ResumeSectionSchema 对象）
        id_to_type[section.id] = (  # 记下"这个板块的 ID 是什么类型"
            section.type  # 比如 "abc-123" → "work_experience"
        )  # 记录板块 ID 到类型的映射
        sections_list.append(  # 把转换后的板块字典追加到列表
            section.model_dump()  # 把 Pydantic 对象转成普通 dict
        )  # 工具函数操作 list[dict] 而不是 Pydantic 对象

    # 返回 SSE 响应
    # EventSourceResponse 把 generate_content 这个异步生成器包装成 HTTP 流
    # 前端用 new EventSource() 接收，事件会一条一条推送过来
    return EventSourceResponse(  # 创建一个 SSE 响应对象，返回给 FastAPI
        generate_content(  # 传入异步生成器函数
            request,
            resume,
            sections_list,
            id_to_type,
            db,  # 传给生成器的参数
        )  # FastAPI 会迭代这个生成器，逐条发 SSE 事件给前端
    )  # 前端就收到了一个 HTTP 长连接，开始收事件


async def generate_content(  # 定义生成 AI 响应的异步生成器（LangGraph 版）
    request: ResumeAssistantRequest,  # 前端请求（包含用户输入、模型选择）
    resume: Resume,  # 简历数据（包含个人信息、板块、JD 等）
    sections: list[dict[str, Any]],  # 板块 dict 列表（工具函数会修改它）
    id_to_type: dict[str, str],  # 板块 ID → 类型映射
    db: AsyncSession,  # 数据库会话
):  # 返回值是异步生成器，逐条产出 SSE 事件
    """生成 AI 响应的内容生成器（LangGraph 版）。

    与手写版完全相同的流程：
    1. 检查数据库中有没有历史消息
    2. 初始化 AgentRuntime
    3. 构造系统提示词
    4. 执行 agent 循环
    5. 产生 SSE 事件
    """
    # 1. 读取历史对话
    store = ConversationStore()  # 创建对话存储实例
    messages: list[ConversationMessage] = store.read(
        request.resume_id
    )  # 从 JSONL 文件读取历史消息
    messages.append(
        ConversationMessage.from_user_text(request.input)
    )  # 把用户当前输入追加到消息列表

    # 2. 初始化 AgentRuntime
    runtime = AgentRuntime(
        db=db,  # 数据库会话
        store=store,  # 对话 JSONL 存储
        model=request.model,  # 模型名称
        max_tokens=getattr(request, "max_tokens", None),  # 最大输出 token
        temperature=getattr(request, "temperature", 1.0),  # 温度参数
    )

    # 3. 执行 agent 循环，逐条 yield SSE 事件给前端
    async for sse_event in runtime.execute(
        request=request,  # 前端请求（包含简历 ID、用户输入等）
        initial_state=messages,  # 消息列表作为初始状态
        sections=sections,  # 简历板块列表
        system_template=SYSTEM,  # 系统提示词模板
        sub_system_template=SUB_SYSTEM,  # 子系统提示词模板（含 JD 信息）
        build_sections_prompt_fn=build_sections_prompt,  # 构建板块提示词的函数
        id_to_type=id_to_type,  # 板块 ID → 类型映射
        resume=resume,  # 简历数据
    ):
        yield sse_event  # 将 SSE 事件产出给 EventSourceResponse，前端实时接收
