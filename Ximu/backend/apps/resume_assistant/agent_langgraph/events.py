# Agent 事件类型定义模块（LangGraph 版）。

# 与手写版 agent/events.py 完全一致。
# 所有事件类型、字段、联合类型均相同，确保前端 SSE 解析兼容。


# 从 dataclasses 导入 dataclass 装饰器
# dataclass 是 Python 自带的"数据类"工具，自动帮我们生成 __init__、__repr__ 等方法
# 手写版也是用 dataclass 定义事件，两者完全一样
from dataclasses import dataclass  # 导入数据类装饰器（自动生成构造函数）

# ConversationMessage 是手写版定义的消息类型
# LangGraph 版复用了它，保证和手写版的消息格式一致，前端不用改代码
from shared.types.messages import (
    ConversationMessage,
)  # 导入手写版定义的消息类型（LangGraph 版复用）


# @dataclass 让 Python 自动为这个类生成 __init__、__repr__ 等方法
# 这样我们只需要写字段名和类型，不用写重复的 __init__ 代码
@dataclass  # 自动生成构造函数的装饰器
class NextEvent:  # 新轮次开始事件
    # 新轮次开始事件。

    # 手写版和 LangGraph 版都用这个事件通知前端"AI 开始新一轮了"。

    # pass 表示这个类没有自己的字段，只是一个"信号"
    pass  # 空类体，没有额外字段


# 每个事件类的 @dataclass 都做同样的事情：自动生成构造函数
@dataclass  # 自动生成构造函数的装饰器
class ThinkingStartEvent:  # AI 思考开始事件
    # AI 思考开始事件。

    # 手写版和 LangGraph 版都用这个事件通知前端"AI 开始内部思考了"。
    # 前端收到后可以显示"思考中..."的提示。

    # pass 表示没有字段，只是一个开始信号
    pass  # 空类体，没有额外字段


# @dataclass 装饰器：自动生成构造函数，text 字段就变成了 __init__ 的参数
@dataclass  # 自动生成构造函数的装饰器
class ThinkingDeltaEvent:  # AI 思考文本片段事件
    # AI 思考文本片段。

    # 手写版和 LangGraph 版都用这个事件把 AI 的思考过程逐段推给前端。
    # 前端可以选择把思考内容折叠显示。

    # text: 思考文本的一段增量
    # 前端收到后追加到"思考气泡"里
    text: str  # 思考文本的增量片段（前端逐段追加）


@dataclass  # 自动生成构造函数的装饰器
class TextStartEvent:  # AI 输出文字开始事件
    # AI 输出文字开始事件。

    # 手写版和 LangGraph 版都用这个事件通知前端"AI 开始输出正式回答了"。

    # pass 表示这个类没有字段，只是一个开始信号
    pass  # 空类体，没有额外字段


@dataclass  # 自动生成构造函数的装饰器
class TextDeltaEvent:  # 文字增量事件
    # AI 回答文字片段。

    # 前端收到后追加到对话气泡中，实现"一个字一个字显示"的流式效果。

    # text: 回答文本的一段增量
    text: str  # 回答文本的增量片段（前端逐字追加）


@dataclass  # 自动生成构造函数的装饰器
class ToolUseEvent:  # AI 调用工具事件
    # AI 决定调用工具的事件。

    # 通知前端"AI 调用了哪个工具"。
    # 手写版和 LangGraph 版字段完全一样。

    name: str  # 工具名称（比如 "update_section"）
    id: str  # 工具调用 ID（用来匹配结果）
    input: dict  # 工具参数（传给工具的 JSON 参数）


@dataclass  # 自动生成构造函数的装饰器
class ToolResultEvent:  # 工具执行结果事件
    # 工具执行结果事件。

    # 通知前端"AI 调用的工具有结果了"。
    # 手写版和 LangGraph 版字段完全一样。

    is_error: bool  # 是否执行出错
    tool_use_id: str  # 对应的工具调用 ID
    content: str  # 工具返回的内容文本


@dataclass  # 自动生成构造函数的装饰器
class DoneEvent:  # AI 完成事件
    # AI 完成事件。

    # 通知前端"本轮 AI 回答结束了"。
    # 前端收到后可以更新 UI：关闭加载状态，启用输入框。

    # pass 表示此事件只是信号
    pass  # 空类体，没有额外字段


@dataclass  # 自动生成构造函数的装饰器
class ErrorEvent:  # 错误事件
    # AI 运行出错事件。

    # 当 AI 运行出错时通知前端，前端可以显示错误提示给用户。

    message: str  # 错误描述（显示给用户）


@dataclass  # 自动生成构造函数的装饰器
class AssistantMessageEvent:  # AI 完整消息事件
    # AI 完整消息事件。

    # 当 AI 生成完整的一条消息时触发。
    # 后端的 runtime 模块收到后，会把这条消息存到数据库，
    # 这样下次用户再来时能看到历史记录。

    message: ConversationMessage  # AI 生成的完整消息（用于持久化）


@dataclass  # 自动生成构造函数的装饰器
class MessagesCompactedEvent:  # 对话压缩事件
    # 对话压缩事件。

    # 当对话历史被自动压缩时触发。
    # 后端收到后可以记录"对话已压缩"的日志。
    pass  # 空类体，没有额外字段


@dataclass  # 自动生成构造函数的装饰器
class ToolResultMessageEvent:  # 工具结果消息事件
    # 工具执行结果消息事件。

    # 当工具执行完毕后，将工具结果打包成一条完整消息时触发。
    # 后端的 runtime 模块收到后，会把这条消息存到数据库。

    message: ConversationMessage  # 包含工具结果的完整消息（用于持久化）


# 定义类型别名：AgentEvent 是所有对外（前端）可见事件的联合类型
# 前端收到这些事件后，根据 event 类型做不同的渲染
AgentEvent = (  # 前端可见事件的联合类型（手写版完全一致）
    DoneEvent  # AI 完成
    | ErrorEvent  # 出错
    | NextEvent  # 新轮次
    | TextDeltaEvent  # 文本增量
    | TextStartEvent  # 文本开始
    | ThinkingDeltaEvent  # 思考增量
    | ThinkingStartEvent  # 思考开始
    | ToolResultEvent  # 工具结果
    | ToolUseEvent  # 工具调用
)

# InternalEvent 是对前端不可见的事件合集（只用于后端内部持久化）
# 手写版和 LangGraph 版完全一致
InternalEvent = (  # 内部事件联合类型（只用于后端，不发给前端）
    AssistantMessageEvent  # AI 完整消息
    | MessagesCompactedEvent  # 对话压缩
    | ToolResultMessageEvent  # 工具结果消息
)
