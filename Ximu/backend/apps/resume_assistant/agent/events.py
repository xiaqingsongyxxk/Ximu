"""Agent事件类型定义模块。

本模块定义了AI Agent执行过程中产生的所有事件类型。
这些事件通过SSE流式返回给前端，用于实时显示AI的执行过程。

事件类型：
1. NextEvent - 新轮次开始
2. ThinkingStartEvent - AI思考开始
3. ThinkingDeltaEvent - AI思考文本片段
4. TextStartEvent - AI回复开始
5. TextDeltaEvent - AI回复文本片段
6. ToolUseEvent - 工具调用
7. ToolResultEvent - 工具执行结果
8. DoneEvent - 完成
9. ErrorEvent - 错误
"""  # 模块文档字符串

from dataclasses import dataclass  # 导入dataclass装饰器

from shared.types.messages import ConversationMessage  # 对话消息类型


@dataclass
class NextEvent:
    """新轮次开始事件。

    触发条件：每次迭代循环开始时。
    语义：通知客户端开始新的对话轮次。
    """

    pass


@dataclass
class ThinkingStartEvent:
    """AI思考开始事件。

    触发条件：收到首个思考类型的delta事件。
    语义：通知客户端开始流式传输AI思考过程。
    """

    pass


@dataclass
class ThinkingDeltaEvent:
    """AI思考文本片段事件。

    触发条件：每个思考类型的delta事件。
    语义：流式传输AI思考过程的文本片段。
    """

    text: str  # 思考文本片段


@dataclass
class TextStartEvent:
    """AI回复开始事件。

    触发条件：收到首个非思考类型的delta事件。
    语义：通知客户端开始流式传输正式回复文本。
    """

    pass


@dataclass
class TextDeltaEvent:
    """AI回复文本片段事件。

    触发条件：每个非思考类型的delta事件。
    语义：流式传输正式回复的文本片段。
    """

    text: str  # 回复文本片段


@dataclass
class ToolUseEvent:
    """工具调用事件。

    触发条件：遍历工具调用块时。
    语义：通知客户端即将执行工具调用。
    """

    name: str  # 工具名称
    id: str  # 工具调用ID
    input: dict  # 工具输入参数


@dataclass
class ToolResultEvent:
    """工具执行结果事件。

    触发条件：工具执行完成后。
    语义：向客户端返回工具执行结果。
    """

    is_error: bool  # 是否出错
    tool_use_id: str  # 工具调用ID
    content: str  # 结果内容
    section_content: dict | None = None  # 板块内容（可选）


@dataclass
class DoneEvent:
    """完成事件。

    触发条件：对话正常结束（stop_reason为end_turn或stop）。
    语义：通知客户端本轮对话成功结束。
    """

    pass


@dataclass
class ErrorEvent:
    """错误事件。

    触发条件：捕获任何异常。
    语义：通知客户端发生错误，生成流程终止。
    """

    message: str  # 错误消息


@dataclass
class AssistantMessageEvent:
    """助手消息事件（内部使用）。

    触发条件：API返回完整的assistant消息。
    语义：用于持久化新的assistant消息。
    """

    message: ConversationMessage


@dataclass
class ToolResultMessageEvent:
    """工具结果消息事件（内部使用）。

    触发条件：工具调用结果作为user消息追加。
    语义：用于持久化新的tool_result消息。
    """

    message: ConversationMessage


@dataclass
class MessagesCompactedEvent:
    """消息压缩事件（内部使用）。

    触发条件：发生自动压缩，messages被重写。
    语义：用于追踪/日志。
    """

    pass


# Agent事件联合类型（SSE返回给前端的事件）
AgentEvent = (
    NextEvent
    | ThinkingStartEvent
    | ThinkingDeltaEvent
    | TextStartEvent
    | TextDeltaEvent
    | ToolUseEvent
    | ToolResultEvent
    | DoneEvent
    | ErrorEvent
)

# 内部事件联合类型（不返回给前端，用于内部处理）
InternalEvent = AssistantMessageEvent | ToolResultMessageEvent | MessagesCompactedEvent
