# Agent 状态定义模块（LangGraph 版）。

# 对应手写版: agent/state.py (IterationState)

# 手写版用 dataclass 手动管理状态，LangGraph 用 TypedDict + reducer。
# 核心差异：
# - add_messages: 自动追加消息、去重，替代手动 messages.append()
# - count / system / tools_schema 字段通过 reducer 自动更新


# 从 collections.abc 导入 Sequence（序列类型）
# Sequence 表示"有序的只读列表"，TypedDict 里用 Sequence 而不是 list 是因为 add_messages 返回的是 tuple
from collections.abc import Sequence  # 导入序列类型，用于定义只读消息列表

# 导入 Annotated（类型注解工具）和 TypedDict（带类型的字典）
# Annotated 给类型加"额外说明"，LangGraph 用它来识别 reducer
from typing import (
    Annotated,
    TypedDict,
)  # 导入类型注解工具：Annotated 给类型加说明，TypedDict 定义带类型的字典

# langchain_core 的 AnyMessage 是所有 LangChain 消息的基类
# 手写版用的自定义 ConversationMessage，LangGraph 版用 LangChain 的消息体系
from langchain_core.messages import (
    AnyMessage,
)  # 导入 LangChain 的消息基类（LangGraph 版用，手写版用 ConversationMessage）

# add_messages 是 LangGraph 提供的 reducer
# 手写版手动 messages.append()，LangGraph 版加 add_messages 后自动追加去重
from langgraph.graph import (
    add_messages,
)  # 导入 LangGraph 的消息追加器（自动合并新消息到列表）


class ResumeState(
    TypedDict
):  # 定义状态字典类型：所有图节点共享的数据容器（对应手写版 IterationState）
    # Agent 状态类——LangGraph 版。

    # 对应 IterationState 字段映射：
    # ────────────────────────────────────────
    # IterationState            ResumeState
    # ────────────────────────────────────────
    # messages (list)           messages (Sequence[AnyMessage])
    # add_messages → 自动追加/去重
    # resume_info (str)         resume_info (str)
    # system (str)              system (str)  当前系统提示词
    # tools_schema (list)       tools_schema (list[dict])
    # count (int)               count (int)   迭代计数器
    # _cached_resume_info       cached_resume_info (str | None)
    # ────────────────────────────────────────
    # 新增字段（用于工具执行和数据传递）:
    # - sections: 简历板块列表（可变引用，工具直接修改）
    # - section_id_to_type: 板块 ID → 类型映射
    # - last_stop_reason: LLM 最后一次停止原因
    # - pending_messages: 待持久化的消息列表
    # - stop_reasons: 停止原因集合

    # messages 字段：存 AI 对话历史
    # Annotated[Sequence[AnyMessage], add_messages] 的意思是：
    # "这个字段的类型是 Sequence[AnyMessage]，并且 LangGraph 要用 add_messages 来更新它"
    # add_messages 自动做三件事：追加新消息、去重（按 ID）、把 list 转 tuple
    # 手写版是手动 messages.append()，LangGraph 版靠这个注解自动完成
    messages: Annotated[
        Sequence[AnyMessage], add_messages
    ]  # 对话消息列表（add_messages 自动处理追加和去重）

    # sections: 简历的各个板块数据（比如"工作经验"、"教育背景"）
    # 这是一个 list[dict]，工具函数（update_section 等）直接修改这个列表
    # 手写版也是同样的方式：可变引用，工具直接改内容
    sections: list[dict]  # 简历板块数据列表（工具函数直接修改这个可变引用）

    # section_id_to_type: 板块 ID 到板块类型的映射
    # 比如 {"abc-123": "work_experience", "def-456": "education"}
    # 工具函数通过这个映射知道某个 ID 对应什么类型
    section_id_to_type: dict[
        str, str
    ]  # 板块 ID → 类型映射（工具用此判断某个 ID 是什么类型的板块）

    # system: 当前系统提示词（告诉 AI 它的角色和任务）
    # 每次简历信息变化时重建
    system: str  # 当前系统提示词（定义 AI 的角色，简历信息变了就重建）

    # tools_schema: 工具的 JSON Schema 定义（告诉 AI 有哪些工具可用）
    tools_schema: list[dict]  # 工具的 JSON Schema 列表（让 AI 知道可以调用什么工具）

    # resume_info: 当前简历信息的 JSON 字符串
    # 每次迭代时重新生成，对比 cached_resume_info 判断简历是否变了
    resume_info: str  # 当前简历信息的 JSON 字符串（用于检测简历是否有变化）

    # cached_resume_info: 缓存的上一轮简历信息
    # 和 resume_info 比较：如果不同 → 重建 system 和 tools_schema
    cached_resume_info: (
        str | None
    )  # 上一轮的简历信息缓存（和 resume_info 比较判断是否变化）

    # count: 当前是第几轮迭代
    # 手写版在 while 循环开头手动 count += 1，LangGraph 版在 prepare 节点返回
    count: int  # 当前迭代轮数（从 0 开始，每轮加 1，防止无限循环）

    # max_iterations: 最多迭代次数（防止 AI 无限循环下去）
    max_iterations: int  # 最大迭代次数上限（超了就直接结束）

    # stop_reasons: 遇到哪些 stop_reason 就停止迭代
    # 比如 {"end_turn", "stop_sequence"}，对应手写版 stop_reasons 集合
    stop_reasons: set[str]  # 停止原因集合（LLM 返回这些原因时结束本轮）

    # last_stop_reason: LLM 最后一次返回的停止原因
    # 在 agent 节点中设置，在 should_continue 中判断是否需要继续
    last_stop_reason: str | None  # LLM 最后一次的 stop_reason（判断本轮是否应该结束）

    # LLM 最后一条消息的 stop_reason。
    # 在 agent 节点中设置，在 check_continue 中判断。

    # pending_messages: 等待存到数据库的消息列表
    # agent 节点和 tools 节点执行后会往这里追加消息，
    # runtime 模块在每轮迭代结束后把这里面的消息写入 SQLite 和 JSONL 文件
    pending_messages: list[
        AnyMessage
    ]  # 待持久化的消息列表（每轮结束后写入数据库和 JSONL）

    # 待持久化的消息列表。
    # agent 节点和 tools 节点执行后追加到这里，
    # runtime 在每轮迭代后将其写入 DB 和 JSONL。
