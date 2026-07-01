# 简历助手Agent包的初始化模块（LangGraph 版）。

# 对应手写版: agent/__init__.py

# 导出所有 Agent 事件类型，与手写版完全一致。
# 前端通过 SSE 接收到的事件类型不变。


# 从 events 模块导入所有 Agent 事件类
# 手写版也是在 __init__.py 统一导出事件类型，方便外部只 from agent_langgraph import * 就能拿到所有事件
from apps.resume_assistant.agent_langgraph.events import (  # 从 events 模块导入所有事件类（供外部 import * 使用）
    AgentEvent,  # 联合类型：所有 Agent 事件的合集（Union），用于类型标注
    DoneEvent,  # AI 完成事件：表示一轮对话结束了
    ErrorEvent,  # 错误事件：AI 运行出错时触发
    NextEvent,  # 下一轮事件：表示 AI 开始新一轮思考
    TextDeltaEvent,  # 文本增量事件：AI 回复的一小段文字（流式输出用）
    TextStartEvent,  # 文本开始事件：AI 开始输出文字了
    ThinkingDeltaEvent,  # 思考增量事件：AI 内部思考的一小段（不直接给用户看）
    ThinkingStartEvent,  # 思考开始事件：AI 开始内部思考了
    ToolResultEvent,  # 工具执行结果事件：AI 调用的工具返回了结果
    ToolResultMessageEvent,  # 工具结果消息事件：AI 调用的工具返回的完整消息
    ToolUseEvent,  # 工具调用事件：AI 决定调用某个工具
)

# __all__ 定义了 from agent_langgraph import * 时导出的名字
# 和手写版 __all__ 完全一致，保证前端引用的代码不用改
# __all__ 列表：声明此包对外公开的接口名称
# from agent_langgraph import * 时，只导入这些名字
__all__ = [  # 定义对外导出的接口名称列表
    "AgentEvent",  # 联合类型：所有 Agent 事件的合集
    "DoneEvent",  # AI 完成事件
    "ErrorEvent",  # 错误事件
    "NextEvent",  # 下一轮事件
    "TextDeltaEvent",  # 文本增量事件
    "TextStartEvent",  # 文本开始事件
    "ThinkingDeltaEvent",  # 思考增量事件
    "ThinkingStartEvent",  # 思考开始事件
    "ToolResultEvent",  # 工具结果事件
    "ToolResultMessageEvent",  # 工具结果消息事件
    "ToolUseEvent",  # 工具调用事件
]
