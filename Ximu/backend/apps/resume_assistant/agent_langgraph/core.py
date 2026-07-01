# Agent 核心循环模块（LangGraph 版）。

# 对应手写版: agent/core.py (AgentCore.run 的 while 循环)

# 手写版用 while + if 控制循环，LangGraph 用 StateGraph + 条件边。
# 但本模块暴露的接口与手写版完全一致：
# core = AgentCore(context, tool_executor)
# async for event in core.run(initial_state, sections, system_template, ...):
# yield event  # 与手写版完全相同的 AgentEvent / InternalEvent

# 或者使用纯 LangGraph 版：
# async for event in run_langgraph_stream(messages, sections, ...):
# yield event  # 相同的 AgentEvent / InternalEvent

# 内部实现差异：
# ┌────────────────────────────────────────────────────────────────┐
# │ 手写版 (agent/core.py)         LangGraph 版 (本文件)          │
# ├────────────────────────────────────────────────────────────────┤
# │ while state.count < max_iter:   StateGraph                     │
# │   state.count += 1              prepare 节点 → count += 1      │
# │   formatter.reset()             新图执行自动重置                │
# │   make_current_resume_info      prepare 节点内计算              │
# │   if resume_info changed:       prepare 节点内判断              │
# │     rebuild system                  → 更新 state.system        │
# │     rebuild tools_schema            → 更新 state.tools_schema  │
# │   auto_compact_if_needed         prepare 节点内调用            │
# │     → yield MessagesCompacted    → _was_compacted 标志         │
# │   insert_resume_info             prepare 节点内调用            │
# │   yield NextEvent                从 on_chain_start 映射        │
# │   call LLM → stream events       agent 节点 → LLM.invoke       │
# │     → formatter.format           → on_chat_model_stream 映射   │
# │   append assistant message       add_messages 自动追加          │
# │   yield AssistantMessageEvent    on_chain_end → 映射           │
# │   if tool_uses:                  should_continue → "tools"     │
# │     handle_tool_calls            call_tools_node               │
# │     yield ToolResultMessageEvent on_chain_end → 映射           │
# │   if stop_reason: break          should_continue → "__end__"   │
# │     yield DoneEvent              图结束时映射                   │
# └────────────────────────────────────────────────────────────────┘


import json  # 导入 json 模块
import logging  # 导入 logging 模块
from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
)  # 从 collections.abc 导入 AsyncIterator, Awaitable, Callable
from typing import Any  # 从 typing 导入 Any

from langchain_core.messages import (  # 从 langchain_core.messages 导入 (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.checkpoint.memory import (
    MemorySaver,
)  # 从 langgraph.checkpoint.memory 导入 MemorySaver
from langgraph.graph import END, StateGraph  # 从 langgraph.graph 导入 END, StateGraph

from apps.resume_assistant.agent_langgraph.events import (  # 从 apps.resume_assistant.agent_langgraph.events 导入 (
    AgentEvent,
    AssistantMessageEvent,
    DoneEvent,
    ErrorEvent,
    InternalEvent,
    MessagesCompactedEvent,
    NextEvent,
    ToolResultEvent,
    ToolResultMessageEvent,
    ToolUseEvent,
)
from apps.resume_assistant.agent_langgraph.formatters import (
    StreamingFormatter,
)  # 从 apps.resume_assistant.agent_langgraph.formatters 导入 StreamingFormatter
from apps.resume_assistant.agent_langgraph.state import (
    ResumeState,
)  # 从 apps.resume_assistant.agent_langgraph.state 导入 ResumeState
from apps.resume_assistant.agent_langgraph.tools import (
    tools as lc_tools,
)  # 从 apps.resume_assistant.agent_langgraph.tools 导入 tools
from apps.resume_assistant.prompt import (
    build_sections_prompt,
)  # 从 apps.resume_assistant.prompt 导入 build_sections_prompt
from shared.types.messages import (  # 从 shared.types.messages 导入 (
    ConversationMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)

log = logging.getLogger(__name__)  # 将 logging.getLogger(__name__) 赋值给 log


def _convert_messages_to_langchain(  # 定义函数 _convert_messages_to_langchain
    msgs: list[Any],
) -> list[AnyMessage]:
    # 将手写版 ConversationMessage 转换为 LangChain AnyMessage。

    # Args:
    # msgs: ConversationMessage 列表（可能混有已转换的 AnyMessage）。

    # Returns:
    # LangChain AnyMessage 列表。

    # 初始化一个空的列表，用于存放转换后的 LangChain 消息对象
    # （后续会返回给调用方，供 LangGraph 图处理）
    result: list[AnyMessage] = []  # 将 [] 赋值给 result: list[AnyMessage]
    # 遍历每一条原始消息
    for msg in msgs:
        # 如果该消息已经是 LangChain 类型（AnyMessage），直接保留不需要转换
        # （混合传入的场景下避免重复转换）
        if not isinstance(msg, ConversationMessage):
            result.append(msg)
            continue
        # 从消息内容中筛选出文本块（TextBlock），用于构造 HumanMessage 或 AIMessage
        text_list = [
            b for b in msg.content if isinstance(b, TextBlock)
        ]  # 将 [b for b in msg.content if isi 赋值给 text_list
        # 从消息内容中筛选出工具调用块（ToolUseBlock），用于挂载到 AIMessage.tool_calls
        tool_list = [
            b for b in msg.content if isinstance(b, ToolUseBlock)
        ]  # 将 [b for b in msg.content if isi 赋值给 tool_list
        # 从消息内容中筛选出工具结果块（ToolResultBlock），用于构造 ToolMessage
        result_list = [
            b for b in msg.content if isinstance(b, ToolResultBlock)
        ]  # 将 [b for b in msg.content if isi 赋值给 result_list
        # 将多个文本块拼接成一个完整字符串
        # （LLM 接收的是纯文本，不能是块数组）
        text = "".join(
            b.text for b in text_list
        )  # 将 "".join(b.text for b in text_l 赋值给 text
        # 如果有工具结果块，说明这条消息是工具执行结果的回执
        if result_list:
            # 每个工具结果块单独转为一条 ToolMessage
            for rb in result_list:
                result.append(
                    # ToolMessage 需要 content（结果内容）和 tool_call_id（关联到哪次调用）
                    ToolMessage(
                        content=rb.content, tool_call_id=rb.tool_use_id
                    )  # 将 rb.content, tool_call_id=rb.to 赋值给 ToolMessage(content
                )
        # 用户角色 → 转为 HumanMessage
        elif msg.role == "user":
            result.append(
                HumanMessage(content=text)
            )  # 将 text)) 赋值给 result.append(HumanMessage(content
        # Assistant 角色 → 转为 AIMessage（可能包含工具调用）
        elif msg.role == "assistant":
            # 创建 AIMessage，文本内容为本消息的纯文本部分
            aim = AIMessage(content=text)  # 将 AIMessage(content=text) 赋值给 aim
            # 如果消息中有工具调用块，挂载到 AIMessage.tool_calls 上
            if tool_list:
                # LangChain 的 tool_calls 格式为 [{id, name, args}, ...]
                aim.tool_calls = [  # 将 [ 赋值给 aim.tool_calls
                    {"id": tb.id, "name": tb.name, "args": tb.input} for tb in tool_list
                ]
            # 如果消息包含思考过程（reasoning），放入 additional_kwargs
            # （某些模型如 Claude 在流式响应中会输出 reasoning 字段）
            if hasattr(msg, "_reasoning") and msg._reasoning:
                aim.additional_kwargs = {
                    "reasoning": msg._reasoning
                }  # 将 {"reasoning": msg._reasoning} 赋值给 aim.additional_kwargs
            # 将构建好的 AIMessage 加入结果列表
            result.append(aim)
    # 返回转换后的 LangChain 消息列表
    # （调用方（如 run_langgraph_stream）需要 LangChain 格式来驱动 StateGraph）
    return result

    # 工具执行器类型（与手写版相同）
    # 工具执行器的类型签名：接收一个 ToolUseBlock、板块列表和上下文，返回工具结果
    # 与手写版 agent/core.py 中的 ToolExecutor 类型完全相同


ToolExecutor = Callable[  # 将 Callable[ 赋值给 ToolExecutor
    [ToolUseBlock, list[dict[str, Any]], Any],
    Awaitable[tuple[ToolResultEvent, ToolResultBlock, dict | None]],
]

# 构建板块提示词的函数类型：接收板块列表，返回拼接后的提示词字符串
BuildSectionsPromptFn = Callable[
    [list[dict[str, Any]]], str
]  # 将 Callable[[list[dict[str, Any]] 赋值给 BuildSectionsPromptFn


async def make_current_resume_info(
    sections: list[dict[str, Any]],
) -> str:  # 定义异步函数 make_current_resume_info
    # 生成当前简历信息的 JSON 字符串。

    # 与手写版 agent/core.py 中 make_current_resume_info 完全相同。

    # 定义一个内部序列化函数，处理 Python 对象中无法直接转 JSON 的类型
    # （json.dumps 不认识 datetime、Pydantic 模型等对象时需要这个兜底）
    def json_serializer(obj: Any) -> Any:
        # 如果是 datetime 等有 isoformat 方法的对象，转成 ISO 格式字符串
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        # 如果是 Pydantic v2 模型，用 model_dump() 转成字典
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        # 如果是普通 Python 对象，用 __dict__ 获取属性字典
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        # 以上都不满足时抛异常，提示开发者补全序列化逻辑
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    # 将 sections（简历板块列表）序列化为 JSON 字符串
    # ensure_ascii=False 表示保留中文等非 ASCII 字符；default 兜底处理特殊类型
    # （这个 JSON 字符串后续会注入到系统提示词或消息中，让 LLM 知道当前简历内容）
    return json.dumps(
        sections, ensure_ascii=False, default=json_serializer
    )  # 将 False, default=json_serializer 赋值给 return json.dumps(sections, ensure_ascii


async def insert_resume_info(
    messages: list, resume_info: str, count: int
) -> list:  # 定义异步函数 insert_resume_info
    # 在消息中注入简历信息。

    # 与手写版 agent/core.py insert_resume_info 完全相同。
    # 在第一次对话时在用户消息前插入简历信息；
    # 后续轮次在工具结果中合并简历信息。

    # 如果消息列表为空，直接返回，无需注入
    if not messages:
        return messages

    # 获取最后一条消息，判断它的角色和类型来决定注入方式
    last_msg = messages[-1]  # 将 messages[-1] 赋值给 last_msg

    # 第一次对话（count == 1）且最后一条是用户消息：
    # 在用户消息前插入一条包含简历信息的 HumanMessage
    # 效果：[..., HumanMessage(简历信息), 用户原来的消息]
    if count == 1 and getattr(last_msg, "role", "") == "user":
        return [
            *messages[:-1],
            HumanMessage(
                content=f"Current Resume Information: \n---\n{resume_info}\n---"  # 将 f"Current Resume Information:  赋值给 content
            ),
            messages[-1],
        ]
    # 后续轮次（count != 1），且最后一条是 ToolMessage（工具结果）：
    # 将简历信息合并到工具结果中，让 LLM 在下一轮看到最新简历
    elif (
        count != 1
        and getattr(last_msg, "role", "") == "user"
        and isinstance(last_msg, ToolMessage)
    ):
        # 把原始工具结果和简历信息打包成一个 JSON 字符串
        new_content = json.dumps(  # 将 json.dumps( 赋值给 new_content
            {"content": last_msg.content, "resume_info": resume_info},
            ensure_ascii=False,  # 将 False, 赋值给 ensure_ascii
        )
        # 替换最后一条消息为包含简历信息的 ToolMessage
        return [
            *messages[:-1],
            ToolMessage(
                content=new_content, tool_call_id=last_msg.tool_call_id
            ),  # 将 new_content, tool_call_id=last 赋值给 ToolMessage(content
        ]

    # 不满足上述条件的情况，直接返回原消息列表，不做任何修改
    return messages


def _convert_lc_assistant_to_conversation_message(  # 定义函数 _convert_lc_assistant_to_conversation_message
    msg: AIMessage,
) -> ConversationMessage:
    # 将 LangChain AIMessage 转换为手写版 ConversationMessage。

    # 用于 DB 持久化：手写版存 ConversationMessageRecord.content 为
    # JSON 数组 [{"type": "text", "text": "..."}, {"type": "tool_use", ...}]

    # 局部导入手写版的消息类型（避免循环依赖）
    from shared.types.messages import TextBlock, ToolUseBlock

    # 初始化空的内容列表，用于存放 TextBlock 和 ToolUseBlock
    # （ConversationMessage.content 是一个 Block 列表）
    content = []  # 将 [] 赋值给 content
    # 如果 AIMessage 有文本内容，转为 TextBlock
    if msg.content:
        content.append(
            TextBlock(
                # 确保 content 是字符串；如果是列表就转成字符串
                text=msg.content
                if isinstance(msg.content, str)
                else str(msg.content)  # 将 msg.content if isinstance(msg. 赋值给 text
            )
        )
    # 如果 AIMessage 有工具调用，转为 ToolUseBlock
    if hasattr(msg, "tool_calls") and msg.tool_calls:
        for tc in msg.tool_calls:
            content.append(
                ToolUseBlock(
                    id=tc.get("id", ""),  # 将 tc.get("id", ""), 赋值给 id
                    name=tc.get("name", ""),  # 将 tc.get("name", ""), 赋值给 name
                    input=tc.get("args", {}),  # 将 tc.get("args", {}), 赋值给 input
                )
            )
    # 构建手写版的 ConversationMessage，角色为 assistant
    # （这个对象会用于 DB 持久化，因为手写版的 ConversationMessageRecord 只认这个格式）
    return ConversationMessage(
        role="assistant", content=content
    )  # 将 "assistant", content=content) 赋值给 return ConversationMessage(role

    # ====================================================================
    # LangGraph 节点定义
    # ====================================================================


async def prepare_node(
    state: ResumeState, config: dict | None = None
) -> dict:  # 定义异步函数 prepare_node
    # 准备节点：一轮迭代开始前的准备工作。

    # 对应手写版 AgentCore.run 中以下部分：
    # 1. state.count += 1
    # 2. formatter.reset()
    # 3. make_current_resume_info
    # 4. if resume_info changed → rebuild system + tools_schema
    # 5. auto_compact_if_needed → _was_compacted 标记
    # 6. insert_resume_info

    # 轮次计数 +1：相当于手写版 AgentCore.run 中 state.count += 1
    # （LangGraph 的 count 存在 state 里，每次 prepare 节点执行时递增）
    count = state.get("count", 0) + 1  # 将 state.get("count", 0) + 1 赋值给 count
    # 将当前简历板块转为 JSON 字符串，用于判断简历是否发生变化
    # 如果变了就需要重建系统提示词（让 LLM 看到最新简历）
    resume_info = await make_current_resume_info(
        state["sections"]
    )  # 将 await make_current_resume_info 赋值给 resume_info

    # 先取出当前系统提示词和工具 schema，后面判断是否需要更新
    system_text = state.get(
        "system", ""
    )  # 将 state.get("system", "") 赋值给 system_text
    tools_schema = state.get(
        "tools_schema", []
    )  # 将 state.get("tools_schema", []) 赋值给 tools_schema
    # 如果简历信息变了（与缓存的 _cached_resume_info 不同）
    # 对应手写版：if resume_info != state._cached_resume_info 内的逻辑
    if resume_info != state.get("cached_resume_info"):
        # 用模板 + 当前板块内容重建系统提示词
        sections_prompt = build_sections_prompt(
            state["sections"]
        )  # 将 build_sections_prompt(state["s 赋值给 sections_prompt
        system_text = state.get(
            "system_template", "{sections}"
        ).format(  # 将 state.get("system_template", " 赋值给 system_text
            sections=sections_prompt  # 将 sections_prompt 赋值给 sections
        )
        # 工具 schema 也需要重新生成（板块变化可能导致可用工具变化）
        tools_schema = state.get(
            "tools_schema", []
        )  # 将 state.get("tools_schema", []) 赋值给 tools_schema

    # 拷贝一份消息列表（不可变操作，避免污染 state 中的原始列表）
    messages = list(state["messages"])  # 将 list(state["messages"]) 赋值给 messages
    # 将简历信息注入到消息中（第一次对话插在用户消息前，后续合并到工具结果中）
    messages = await insert_resume_info(
        messages, resume_info, count
    )  # 将 await insert_resume_info(messa 赋值给 messages

    # 当 enable_compact 开启时，如果消息太长就自动压缩历史
    was_compacted = False  # 将 False 赋值给 was_compacted
    if config:
        cfg = config.get(
            "configurable", {}
        )  # 将 config.get("configurable", {}) 赋值给 cfg
        if cfg.get("enable_compact"):
            from apps.resume_assistant.agent_langgraph.compact import (
                auto_compact_langchain,
            )

            # 调用压缩函数，保留最近 6 条消息，超过 100K token 就压缩
            (
                messages,
                was_compacted,
            ) = await auto_compact_langchain(  # 将 await auto_compact_langchain( 赋值给 messages, was_compacted
                messages,
                max_tokens=100_000,
                preserve_recent=6,  # 将 100_000, preserve_recent=6 赋值给 messages, max_tokens
            )

    # 返回更新后的 state 字段，LangGraph 会自动合并到全局 state 中
    # 注意：_was_compacted 会被 event 映射函数读取并 yield MessagesCompactedEvent
    return {
        "count": count,
        "resume_info": resume_info,
        "cached_resume_info": resume_info,
        "system": system_text,
        "tools_schema": tools_schema,
        "messages": messages,
        "_was_compacted": was_compacted,
    }


async def agent_node(
    state: ResumeState, config: dict | None = None
) -> dict:  # 定义异步函数 agent_node
    # Agent 节点：调用 LLM（流式）。

    # 使用 config 中传入的 LLM 实例（动态配置），
    # 用 astream 产生流式 token，收集完整响应后返回。

    # 尝试从 config 中获取外部传入的 LLM 实例
    # （run_langgraph_stream 会在 config 中注入 llm，这里接收）
    llm = None  # 将 None 赋值给 llm
    if config:
        llm = config.get("configurable", {}).get(
            "llm"
        )  # 将 config.get("configurable", {}) 赋值给 llm

    # 如果外部没有传入 LLM，则自己创建一个兜底
    # （这样 standalone 调用 agent_node 也不会报错）
    if llm is None:
        from apps.resume_assistant.agent_langgraph.context import AgentConfig

        cfg = AgentConfig(  # 将 AgentConfig( 赋值给 cfg
            provider=state.get(
                "provider", "anthropic"
            ),  # 将 state.get("provider", "anthrop 赋值给 provider
            model=state.get(
                "model", "claude-sonnet-4-20250514"
            ),  # 将 state.get("model", "claude-son 赋值给 model
        )
        llm = cfg.build_llm()  # 将 cfg.build_llm() 赋值给 llm
        # 给 LLM 绑定 LangGraph 格式的工具定义，让 LLM 知道可以调用哪些工具
        llm = llm.bind_tools(lc_tools)  # 将 llm.bind_tools(lc_tools) 赋值给 llm

    # 将系统提示词包装成 LangChain 的 SystemMessage
    system = SystemMessage(
        content=state.get("system", "")
    )  # 将 SystemMessage(content=state.ge 赋值给 system
    # 构建完整的 LLM 输入：[系统提示词, 历史消息...]
    # 对应手写版：api_request = ApiMessageRequest(system_prompt=..., messages=...)
    chat_messages = [system] + list(
        state.get("messages", [])
    )  # 将 [system] + list(state.get("mes 赋值给 chat_messages

    # 用 astream 流式调用 LLM，逐块收集响应
    # 对应手写版：async for api_event in api_client.stream_message(api_request)
    collected_content: list[str] = []  # 将 [] 赋值给 collected_content: list[str]
    collected_tool_calls: dict[
        int, dict
    ] = {}  # 将 {} 赋值给 collected_tool_calls: dict[int, dict]
    response_metadata: dict | None = (
        None  # 将 None 赋值给 response_metadata: dict | None
    )

    async for chunk in llm.astream(chat_messages):
        # 从流式块中提取文本片段并累积
        # 对应手写版：ApiTextDeltaEvent 的处理
        if chunk.content:
            # 如果 content 是列表（多模态情况），找到 text 类型的块
            if isinstance(chunk.content, list):
                for block in chunk.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        collected_content.append(block.get("text", ""))
            # 如果 content 是纯字符串，直接追加
            elif isinstance(chunk.content, str):
                collected_content.append(chunk.content)

        # 从流式块中提取工具调用片段并累积
        # （LLM 的 tool_call 也是流式返回的，需要逐块拼接参数 JSON）
        if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
            for tc_chunk in chunk.tool_call_chunks:
                # index 标识是第几个工具调用（可能同时调用多个工具）
                idx = tc_chunk.get("index", 0)  # 将 tc_chunk.get("index", 0) 赋值给 idx
                # 如果是第一次见到这个 index，初始化条目
                if idx not in collected_tool_calls:
                    collected_tool_calls[
                        idx
                    ] = {  # 将 { 赋值给 collected_tool_calls[idx]
                        "id": tc_chunk.get("id", ""),
                        "name": tc_chunk.get("name", ""),
                        "args": tc_chunk.get("args", ""),
                    }
                # 否则将新块的数据合并到已有条目中
                else:
                    existing = collected_tool_calls[
                        idx
                    ]  # 将 collected_tool_calls[idx] 赋值给 existing
                    # id 和 name 通常第一个块就有，后面的块用来补全 args
                    if tc_chunk.get("id"):
                        existing["id"] = tc_chunk[
                            "id"
                        ]  # 将 tc_chunk["id"] 赋值给 existing["id"]
                    if tc_chunk.get("name"):
                        existing["name"] = tc_chunk[
                            "name"
                        ]  # 将 tc_chunk["name"] 赋值给 existing["name"]
                    if tc_chunk.get("args"):
                        existing["args"] += tc_chunk[
                            "args"
                        ]  # 将 tc_chunk["args"] 赋值给 existing["args"] +

        # 保留最后一个块的 response_metadata（里面包含 stop_reason 等信息）
        if hasattr(chunk, "response_metadata") and chunk.response_metadata:
            response_metadata = (
                chunk.response_metadata
            )  # 将 chunk.response_metadata 赋值给 response_metadata

    # 将所有收集到的文本片段拼接成完整响应
    full_text = "".join(
        collected_content
    )  # 将 "".join(collected_content) 赋值给 full_text

    # 将收集到的 tool_call 片段转换为 LangChain 标准格式
    final_tool_calls: list[dict] = []  # 将 [] 赋值给 final_tool_calls: list[dict]
    for idx in sorted(collected_tool_calls.keys()):
        tc = collected_tool_calls[idx]  # 将 collected_tool_calls[idx] 赋值给 tc
        # 只有 id 和 name 都非空才认为是有效的工具调用
        if tc["id"] and tc["name"]:
            import json as _json

            # 将 args 从 JSON 字符串解析为 Python 字典
            try:
                parsed_args = (
                    _json.loads(tc["args"]) if tc["args"] else {}
                )  # 将 _json.loads(tc["args"]) if tc[ 赋值给 parsed_args
            except _json.JSONDecodeError:
                # 如果 JSON 解析失败（极端情况），用空字典兜底
                parsed_args = {}  # 将 {} 赋值给 parsed_args
            final_tool_calls.append(
                {
                    "id": tc["id"],
                    "name": tc["name"],
                    "args": parsed_args,
                }
            )

    # 用收集到的文本和工具调用构建 AIMessage
    # 这个 message 会被 LangGraph 自动追加到 state.messages 中（add_messages reducer）
    response = AIMessage(  # 将 AIMessage( 赋值给 response
        content=full_text,  # 将 full_text, 赋值给 content
        tool_calls=final_tool_calls
        if final_tool_calls
        else None,  # 将 final_tool_calls if final_tool 赋值给 tool_calls
    )
    # 保留 response_metadata（供 should_continue 读取 stop_reason）
    if response_metadata:
        response.response_metadata = (
            response_metadata  # 将 response_metadata 赋值给 response.response_metadata
        )

    # 从元数据中提取 stop_reason（LLM 停止生成的原因）
    # 对应手写版：complete_event.stop_reason
    stop_reason = None  # 将 None 赋值给 stop_reason
    if response_metadata:
        stop_reason = response_metadata.get(
            "stop_reason"
        )  # 将 response_metadata.get("stop_re 赋值给 stop_reason

    # 将 LangChain 的 AIMessage 转回手写版 ConversationMessage
    # （用于持久化到 DB，因为 DB 只存储手写版格式）
    conv_msg = _convert_lc_assistant_to_conversation_message(
        response
    )  # 将 _convert_lc_assistant_to_conve 赋值给 conv_msg

    # 返回 state 更新
    # messages 会被 add_messages reducer 追加；last_stop_reason 供 should_continue 判断
    return {
        "messages": [response],
        "last_stop_reason": stop_reason,
        "_pending_msgs": [conv_msg],
    }


def should_continue(state: ResumeState) -> str:  # 定义函数 should_continue
    # 条件边：判断下一步走向。

    # 对应手写版:
    # - if tool_uses → _handle_tool_calls → 继续循环
    # - if stop_reason → DoneEvent → break

    # 从 state 中取出当前的消息列表，检查最后一条消息
    # 对应手写版：complete_event.message.tool_uses 和 stop_reason 的判断
    messages = state.get("messages", [])  # 将 state.get("messages", []) 赋值给 messages
    # 如果没有消息（空状态），直接结束
    if not messages:
        return "__end__"

    # 取最后一条消息（即 agent_node 刚刚追加的 AIMessage）
    last = messages[-1]  # 将 messages[-1] 赋值给 last
    # 判断最后一条消息是否包含工具调用
    # 对应手写版：if complete_event.message.tool_uses
    has_tools = (
        hasattr(last, "tool_calls") and last.tool_calls
    )  # 将 hasattr(last, "tool_calls") an 赋值给 has_tools

    # 如果有工具调用 → 走 "tools" 分支去执行工具
    if has_tools:
        return "tools"

    # 如果 LLM 返回了停止原因（end_turn / stop）→ 完成任务，结束循环
    stop_reason = state.get(
        "last_stop_reason"
    )  # 将 state.get("last_stop_reason") 赋值给 stop_reason
    if stop_reason in state.get("stop_reasons", {"end_turn", "stop"}):
        return "__end__"

    # 既没有工具调用，也没有停止 → 继续下一轮（让 LLM 继续思考）
    return "prepare"


async def call_tools_node(state: ResumeState) -> dict:  # 定义异步函数 call_tools_node
    # 工具调用节点（替代 ToolNode，支持 InjectedToolArg 注入）。

    # 从 state 中读取 sections、section_id_to_type、
    # client、model 等运行时参数，注入到工具函数中调用。

    # 从 state 中取出当前消息列表的副本
    messages = list(
        state.get("messages", [])
    )  # 将 list(state.get("messages", []) 赋值给 messages
    # 如果消息列表为空，无需处理工具调用
    if not messages:
        return {}

    # 取最后一条消息（即 agent_node 输出的 AIMessage）
    last_msg = messages[-1]  # 将 messages[-1] 赋值给 last_msg
    # 如果最后一条消息没有工具调用，跳过
    if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
        return {}

    from langchain_core.messages import ToolMessage

    # 将工具列表按名称建立索引，方便快速查找
    tool_map = {
        t.name: t for t in lc_tools
    }  # 将 {t.name: t for t in lc_tools} 赋值给 tool_map
    # 存放执行结果（ToolMessage），执行完后会追加到 state.messages
    tool_messages: list[
        ToolMessage
    ] = []  # 将 [] 赋值给 tool_messages: list[ToolMessage]
    pending_msgs: list[Any] = []  # 将 [] 赋值给 pending_msgs: list[Any]

    # 遍历 LLM 请求的每一个工具调用
    for tc in last_msg.tool_calls:
        tool_name = tc.get("name", "")  # 将 tc.get("name", "") 赋值给 tool_name
        tool_fn = tool_map.get(tool_name)  # 将 tool_map.get(tool_name) 赋值给 tool_fn
        # 如果工具名不在已注册的工具列表中，返回错误信息
        if tool_fn is None:
            tool_messages.append(
                ToolMessage(
                    content=f"Unknown tool: {tool_name}",  # 将 f"Unknown tool: {tool_name}", 赋值给 content
                    tool_call_id=tc.get(
                        "id", ""
                    ),  # 将 tc.get("id", ""), 赋值给 tool_call_id
                    status="error",  # 将 "error", 赋值给 status
                )
            )
            continue

        # 从 state 中提取运行时参数，准备注入到工具函数
        # 对应手写版：self.tool_executor(tool_use, sections, self.context)
        inject_kwargs = {  # 将 { 赋值给 inject_kwargs
            "sections": state.get("sections", []),
            "section_id_to_type": state.get("section_id_to_type", {}),
            "llm": state.get("_llm"),
        }
        # 检查工具函数的参数签名，只注入它实际需要的参数
        # （InjectedToolArg 标记的参数由这里注入，LLM 不需要提供）
        import inspect

        sig = inspect.signature(
            tool_fn.func if hasattr(tool_fn, "func") else tool_fn
        )  # 将 inspect.signature(tool_fn.func 赋值给 sig
        tool_kwargs = dict(
            tc.get("args", {})
        )  # 将 dict(tc.get("args", {})) 赋值给 tool_kwargs
        for param_name in sig.parameters:
            if param_name in inject_kwargs and inject_kwargs[param_name] is not None:
                tool_kwargs[param_name] = inject_kwargs[
                    param_name
                ]  # 将 inject_kwargs[param_name] 赋值给 tool_kwargs[param_name]

        # 调用工具函数（支持同步和异步两种形式）
        try:
            if inspect.iscoroutinefunction(
                tool_fn.func if hasattr(tool_fn, "func") else tool_fn
            ):
                result = await tool_fn.ainvoke(
                    tool_kwargs
                )  # 将 await tool_fn.ainvoke(tool_kwa 赋值给 result
            else:
                result = tool_fn.invoke(
                    tool_kwargs
                )  # 将 tool_fn.invoke(tool_kwargs) 赋值给 result
        except Exception as e:
            log.error("Tool %s error: %s", tool_name, e)
            result = f"Error executing {tool_name}: {e}"  # 将 f"Error executing {tool_name}: 赋值给 result

        # 确保结果是字符串（ToolMessage.content 必须是字符串）
        if not isinstance(result, str):
            result = str(result)  # 将 str(result) 赋值给 result

        # 将工具执行结果包装成 ToolMessage
        tool_messages.append(
            ToolMessage(
                content=result,  # 将 result, 赋值给 content
                tool_call_id=tc.get(
                    "id", ""
                ),  # 将 tc.get("id", ""), 赋值给 tool_call_id
            )
        )

    # 返回工具执行结果，LangGraph 通过 add_messages reducer 将其追加到 state.messages
    # _tool_done 标记本轮工具已执行完毕（目前未使用，保留供未来扩展）
    return {"messages": tool_messages, "_tool_done": True}


# ====================================================================
# 纯 LangGraph 版执行函数（不使用 AgentCore 包装）
# ====================================================================


async def run_langgraph(  # 定义异步函数 run_langgraph
    initial_messages: list,
    sections: list[dict],
    section_id_to_type: dict[str, str],
    system_template: str,
    *,
    llm: Any = None,  # 将 None, 赋值给 llm: Any
    model: str | None = None,  # 将 None, 赋值给 model: str | None
    max_iterations: int = 30,  # 将 30, 赋值给 max_iterations: int
    stop_reasons: set[str]
    | None = None,  # 将 None, 赋值给 stop_reasons: set[str] | None
) -> AsyncIterator[dict]:
    # 纯 LangGraph 执行（不经过 AgentCore 包装）。

    # 直接使用 StateGraph.compile + astream_events。
    # 适用于不需要 SSE 流式事件的生产场景。

    # 与 AgentCore.run() 的区别：
    # - AgentCore.run() 产生与手写版完全相同的事件（用于前端 SSE）
    # - run_langgraph() 产生 LangGraph 原生事件（用于纯后端调用）

    # 如果没有传入 stop_reasons，使用默认值
    # （LLM 返回 end_turn 或 stop 时认为任务完成）
    if stop_reasons is None:
        stop_reasons = {
            "end_turn",
            "stop",
        }  # 将 {"end_turn", "stop"} 赋值给 stop_reasons

    # 如果调用方没有传入 LLM 实例，自己创建一个默认的 Anthropic LLM
    if llm is None:
        from apps.resume_assistant.agent_langgraph.context import AgentConfig

        cfg = AgentConfig(  # 将 AgentConfig( 赋值给 cfg
            provider="anthropic",  # 将 "anthropic", 赋值给 provider
            model=model
            or "claude-sonnet-4-20250514",  # 将 model or "claude-sonnet-4-2025 赋值给 model
        )
        llm = cfg.build_llm()  # 将 cfg.build_llm() 赋值给 llm
    # 给 LLM 绑定工具定义，让它知道可以调用哪些函数
    llm_bound = llm.bind_tools(lc_tools)  # 将 llm.bind_tools(lc_tools) 赋值给 llm_bound

    # ===== 构建 LangGraph StateGraph =====
    graph = StateGraph(ResumeState)  # 将 StateGraph(ResumeState) 赋值给 graph

    # 注册三个节点：prepare（准备）、agent（调用 LLM）、tools（执行工具）
    graph.add_node("agent", agent_node)
    graph.add_node("tools", call_tools_node)
    graph.add_node("prepare", prepare_node)

    # 起点 → prepare（先做准备工作）
    graph.set_entry_point("prepare")
    # prepare 完成后直接进入 agent（调用 LLM）
    graph.add_edge("prepare", "agent")
    # agent 完成后通过 should_continue 条件边决定下一步
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",  # 有工具调用 → 执行工具
            "prepare": "prepare",  # 没有工具也没有停止 → 继续下一轮
            "__end__": END,  # 停止 → 结束
        },
    )
    # 工具执行完后回到 agent（让 LLM 看到工具结果后继续生成）
    graph.add_edge("tools", "agent")

    # 使用 MemorySaver 作为检查点存储器（支持断点续传，但这里主要用于 state 管理）
    checkpointer = MemorySaver()  # 将 MemorySaver() 赋值给 checkpointer
    compiled = graph.compile(
        checkpointer=checkpointer
    )  # 将 graph.compile(checkpointer=che 赋值给 compiled

    # 构建初始状态（字典格式，LangGraph State 要求）
    initial_state = {  # 将 { 赋值给 initial_state
        "messages": initial_messages,
        "sections": sections,
        "section_id_to_type": section_id_to_type,
        "system": system_template,
        "system_template": system_template,
        "tools_schema": [],
        "resume_info": "",
        "cached_resume_info": None,
        "count": 0,
        "max_iterations": max_iterations,
        "stop_reasons": stop_reasons,
        "last_stop_reason": None,
        "pending_messages": [],
        # 运行时注入参数（供 call_tools_node 读取注入）
        "_llm": llm,
    }

    # 图执行的配置：thread_id 用于检查点标识，llm 传入绑定好工具的 LLM 实例
    config = {
        "configurable": {"thread_id": "default", "llm": llm_bound}
    }  # 将 {"configurable": {"thread_id": 赋值给 config

    # 用 astream_events 驱动图执行，产生原生 LangGraph 事件
    # 调用方直接消费这些事件做自定义处理
    async for event in compiled.astream_events(
        initial_state,
        config=config,  # 将 config, 赋值给 config
        version="v2",  # 将 "v2", 赋值给 version
    ):
        yield event

        # ====================================================================
        # run_langgraph_stream — 与 AgentCore.run 相同事件接口的流式版本
        # ====================================================================


async def run_langgraph_stream(  # 定义异步函数 run_langgraph_stream
    initial_messages: list,
    sections: list[dict],
    section_id_to_type: dict[str, str],
    system_template: str,
    system_suffix: str | None,
    build_sections_prompt_fn: BuildSectionsPromptFn,
    *,
    llm: Any = None,  # 将 None, 赋值给 llm: Any
    model: str | None = None,  # 将 None, 赋值给 model: str | None
    max_iterations: int = 30,  # 将 30, 赋值给 max_iterations: int
    stop_reasons: set[str]
    | None = None,  # 将 None, 赋值给 stop_reasons: set[str] | None
) -> AsyncIterator[AgentEvent | InternalEvent]:
    # 运行 LangGraph 并产生与 AgentCore.run 完全相同的事件流。

    # 与 AgentCore.run() 的区别：
    # - AgentCore.run() 用 while 循环 + API client
    # - run_langgraph_stream() 用 StateGraph + astream_events
    # 两者产生的 AsyncIterator[AgentEvent | InternalEvent] 完全一致。

    # Args:
    # initial_messages: 初始消息列表（ConversationMessage 或 AnyMessage）。
    # sections: 简历板块列表（可变引用）。
    # section_id_to_type: 板块 ID → 类型映射。
    # system_template: 系统提示词模板，包含 {sections} 占位符。
    # system_suffix: 系统提示词后缀（包含 JD 信息）。
    # build_sections_prompt_fn: 构建板块提示词的函数。
    # llm: LangChain LLM 实例（由 AgentConfig.build_llm 创建）。
    # model: 模型名称（llm 为 None 时用于自动创建）。
    # max_iterations: 最大迭代次数。
    # stop_reasons: 停止原因集合。

    # Yields:
    # AgentEvent（前端 SSE 事件）或 InternalEvent（内部持久化事件）。

    # 设置默认停止原因（与 AgentCore.run 中的 self.context.stop_reasons 对应）
    if stop_reasons is None:
        stop_reasons = {
            "end_turn",
            "stop",
        }  # 将 {"end_turn", "stop"} 赋值给 stop_reasons

    # === 创建 LLM ===
    # 如果没有传入 LLM，根据 provider/model 构建默认 Anthropic LLM
    if llm is None:
        from apps.resume_assistant.agent_langgraph.context import AgentConfig

        cfg = AgentConfig(  # 将 AgentConfig( 赋值给 cfg
            provider="anthropic",  # 将 "anthropic", 赋值给 provider
            model=model
            or "claude-sonnet-4-20250514",  # 将 model or "claude-sonnet-4-2025 赋值给 model
        )
        llm = cfg.build_llm()  # 将 cfg.build_llm() 赋值给 llm
    # 绑定工具定义，让 LLM 知道可以调用哪些函数
    llm_bound = llm.bind_tools(lc_tools)  # 将 llm.bind_tools(lc_tools) 赋值给 llm_bound

    # === 构建 LangGraph StateGraph ===
    # 注册三个节点（与 run_langgraph 中的图结构完全相同）
    graph = StateGraph(ResumeState)  # 将 StateGraph(ResumeState) 赋值给 graph
    graph.add_node("agent", agent_node)
    graph.add_node("tools", call_tools_node)
    graph.add_node("prepare", prepare_node)
    graph.set_entry_point("prepare")
    graph.add_edge("prepare", "agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "prepare": "prepare",
            "__end__": END,
        },
    )
    graph.add_edge("tools", "agent")

    checkpointer = MemorySaver()  # 将 MemorySaver() 赋值给 checkpointer
    compiled = graph.compile(
        checkpointer=checkpointer
    )  # 将 graph.compile(checkpointer=che 赋值给 compiled

    # 将手写版的 ConversationMessage 转为 LangChain 的 AnyMessage
    # （StateGraph 内部的消息 reducer add_messages 要求 LangChain 类型）
    converted = _convert_messages_to_langchain(
        initial_messages
    )  # 将 _convert_messages_to_langchain 赋值给 converted

    # 将 system_suffix（通常包含职位描述 JD）拼接到系统提示词模板后面
    effective_template = system_template  # 将 system_template 赋值给 effective_template
    if system_suffix:
        effective_template += (
            system_suffix  # 将 system_suffix 赋值给 effective_template +
        )

    # 构建初始状态（所有字段初始化）
    # 注意：messages 已转为 LangChain 类型，sections 仍保持手写版格式
    initial_state = {  # 将 { 赋值给 initial_state
        "messages": converted,
        "sections": sections,
        "section_id_to_type": section_id_to_type,
        "system": effective_template,
        "system_template": effective_template,
        "tools_schema": [],
        "resume_info": "",
        "cached_resume_info": None,
        "count": 0,
        "max_iterations": max_iterations,
        "stop_reasons": stop_reasons,
        "last_stop_reason": None,
        "pending_messages": [],
        # 运行时注入参数（供 call_tools_node 使用，替代手写版的 _api_client / _model）
        "_llm": llm,
    }

    # 图配置：将 LLM 实例和其他运行时参数通过 configurable 传入
    # 这样 prepare_node 和 agent_node 可以在执行时通过 config 参数读取
    graph_config = {  # 将 { 赋值给 graph_config
        "configurable": {
            "thread_id": "run_langgraph_stream",
            "llm": llm_bound,
            # 只要有 llm 实例就启用自动压缩
            "enable_compact": llm is not None,
        }
    }

    # 创建流式格式化器，用于将 LLM 的流式 token 映射为前端 SSE 事件
    formatter = StreamingFormatter()  # 将 StreamingFormatter() 赋值给 formatter
    formatter.reset()

    # === 驱动图执行，将 LangGraph 原生事件映射为 AgentCore.run 兼容的事件 ===
    try:
        async for event in compiled.astream_events(
            initial_state,
            config=graph_config,  # 将 graph_config, 赋值给 config
            version="v2",  # 将 "v2", 赋值给 version
        ):
            # 从 LangGraph 事件中提取类型（event）、节点名（name）和数据（data）
            kind = event["event"]  # 将 event["event"] 赋值给 kind
            name = event.get("name", "")  # 将 event.get("name", "") 赋值给 name
            data = event.get("data", {})  # 将 event.get("data", {}) 赋值给 data

            # prepare 节点开始 → 对应手写版中 formatter.reset() + yield NextEvent()
            if kind == "on_chain_start" and name == "prepare":
                formatter.reset()
                yield NextEvent()

            # prepare 节点结束 → 检查是否有压缩发生
            # 对应手写版：if was_compacted: yield MessagesCompactedEvent()
            elif kind == "on_chain_end" and name == "prepare":
                if data.get("output", {}).get("_was_compacted"):
                    yield MessagesCompactedEvent()

            # LLM 流式输出 token → 映射为前端的 TextDelta / ThinkingDelta 事件
            # 对应手写版：async for api_event in api_client.stream_message()
            elif kind == "on_chat_model_stream":
                chunk = data.get("chunk")  # 将 data.get("chunk") 赋值给 chunk
                if chunk is None:
                    continue
                content = getattr(
                    chunk, "content", None
                )  # 将 getattr(chunk, "content", None 赋值给 content
                if content is None:
                    continue
                # LLM 返回的 content 可能是列表（含 text 和 thinking 混合）或纯字符串
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        bt = block.get("type", "")  # 将 block.get("type", "") 赋值给 bt
                        if bt == "text":
                            # 普通文本 token → yield TextDelta 事件
                            text = block.get(
                                "text", ""
                            )  # 将 block.get("text", "") 赋值给 text
                            if text:
                                for ae in formatter.format_text(
                                    text, is_think=False
                                ):  # 将 False): 赋值给 for ae in formatter.format_text(text, is_think
                                    yield ae
                        elif bt == "thinking":
                            # 思考过程 token → yield ThinkingDelta 事件
                            # （Claude 模型会在最终回答前输出思考过程）
                            text = block.get(
                                "thinking", ""
                            )  # 将 block.get("thinking", "") 赋值给 text
                            if text:
                                for ae in formatter.format_text(
                                    text, is_think=True
                                ):  # 将 True): 赋值给 for ae in formatter.format_text(text, is_think
                                    yield ae
                elif isinstance(content, str) and content:
                    # 纯字符串 content 直接按普通文本处理
                    for ae in formatter.format_text(
                        content, is_think=False
                    ):  # 将 False): 赋值给 for ae in formatter.format_text(content, is_think
                        yield ae

            # agent 节点结束 → LLM 完成了完整响应
            # 对应手写版：yield AssistantMessageEvent(message=complete_event.message)
            elif kind == "on_chain_end" and name == "agent":
                output = data.get(
                    "output", {}
                )  # 将 data.get("output", {}) 赋值给 output
                msgs = output.get(
                    "messages", []
                )  # 将 output.get("messages", []) 赋值给 msgs
                if msgs:
                    last = msgs[-1]  # 将 msgs[-1] 赋值给 last
                    if hasattr(last, "content"):
                        # 将 LangChain AIMessage 转换回手写版的 ConversationMessage
                        conv_msg = _convert_lc_assistant_to_conversation_message(
                            last
                        )  # 将 _convert_lc_assistant_to_conve 赋值给 conv_msg
                        yield AssistantMessageEvent(
                            message=conv_msg
                        )  # 将 conv_msg) 赋值给 yield AssistantMessageEvent(message

            # tools 节点开始 → 即将执行工具
            # 对应手写版：yield ToolUseEvent(...)
            elif kind == "on_chain_start" and name == "tools":
                input_state = data.get(
                    "input", {}
                )  # 将 data.get("input", {}) 赋值给 input_state
                in_msgs = input_state.get(
                    "messages", []
                )  # 将 input_state.get("messages", [] 赋值给 in_msgs
                if in_msgs:
                    last = in_msgs[-1]  # 将 in_msgs[-1] 赋值给 last
                    if hasattr(last, "tool_calls") and last.tool_calls:
                        for tc in last.tool_calls:
                            yield ToolUseEvent(
                                name=tc.get(
                                    "name", ""
                                ),  # 将 tc.get("name", ""), 赋值给 name
                                id=tc.get("id", ""),  # 将 tc.get("id", ""), 赋值给 id
                                input=tc.get(
                                    "args", {}
                                ),  # 将 tc.get("args", {}), 赋值给 input
                            )

            # tools 节点结束 → 工具执行完毕
            # 对应手写版：yield ToolResultEvent + yield ToolResultMessageEvent
            elif kind == "on_chain_end" and name == "tools":
                output = data.get(
                    "output", {}
                )  # 将 data.get("output", {}) 赋值给 output
                out_msgs = output.get(
                    "messages", []
                )  # 将 output.get("messages", []) 赋值给 out_msgs
                if not out_msgs:
                    continue
                tool_blocks: list[
                    ToolResultBlock
                ] = []  # 将 [] 赋值给 tool_blocks: list[ToolResultBlock]
                for msg in out_msgs:
                    # LangChain 的 ToolMessage 的 type 为 "tool"
                    if hasattr(msg, "type") and getattr(msg, "type", "") == "tool":
                        is_err = (
                            getattr(msg, "status", "") == "error"
                        )  # 将 getattr(msg, "status", "") ==  赋值给 is_err
                        yield ToolResultEvent(
                            is_error=is_err,  # 将 is_err, 赋值给 is_error
                            tool_use_id=getattr(
                                msg, "tool_call_id", ""
                            ),  # 将 getattr(msg, "tool_call_id", " 赋值给 tool_use_id
                            content=getattr(msg, "content", "")
                            or "",  # 将 getattr(msg, "content", "") or 赋值给 content
                        )
                        tool_blocks.append(
                            ToolResultBlock(
                                tool_use_id=getattr(
                                    msg, "tool_call_id", ""
                                ),  # 将 getattr(msg, "tool_call_id", " 赋值给 tool_use_id
                                content=getattr(msg, "content", "")
                                or "",  # 将 getattr(msg, "content", "") or 赋值给 content
                                is_error=is_err,  # 将 is_err, 赋值给 is_error
                            )
                        )
                # 如果有工具结果，打包成一条 ConversationMessage 发送给前端
                if tool_blocks:
                    yield ToolResultMessageEvent(
                        message=ConversationMessage(
                            role="user", content=tool_blocks
                        )  # 将 ConversationMessage(role="user 赋值给 message
                    )
    except Exception as e:
        # 图执行过程中出现任何异常 → yield ErrorEvent
        log.error("LangGraph stream error: %s", e)
        yield ErrorEvent(message=str(e))  # 将 str(e)) 赋值给 yield ErrorEvent(message

    # 图执行结束（正常或异常）→ yield DoneEvent
    # 对应手写版：yield DoneEvent() 后的 break
    yield DoneEvent()
