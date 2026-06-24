"""简历助手Agent包的初始化模块。

本模块导出所有Agent事件类型：
1. AgentEvent - 事件基类
2. TextDeltaEvent - 文本增量事件
3. TextStartEvent - 文本开始事件
4. ThinkingDeltaEvent - 思考增量事件
5. ThinkingStartEvent - 思考开始事件
6. ToolUseEvent - 工具调用事件
7. ToolResultEvent - 工具结果事件
8. NextEvent - 下一步事件
9. DoneEvent - 完成事件
10. ErrorEvent - 错误事件

这些事件用于SSE流式返回AI助手的执行过程。
"""  # 模块文档字符串

from apps.resume_assistant.agent.events import (  # 从events模块导入所有事件类型
    AgentEvent,  # 事件基类
    DoneEvent,  # 完成事件
    ErrorEvent,  # 错误事件
    NextEvent,  # 下一步事件
    TextDeltaEvent,  # 文本增量事件
    TextStartEvent,  # 文本开始事件
    ThinkingDeltaEvent,  # 思考增量事件
    ThinkingStartEvent,  # 思考开始事件
    ToolResultEvent,  # 工具结果事件
    ToolUseEvent,  # 工具调用事件
)

# 导出所有事件类型
__all__ = [
    "AgentEvent",  # 事件基类
    "DoneEvent",  # 完成事件
    "ErrorEvent",  # 错误事件
    "NextEvent",  # 下一步事件
    "TextDeltaEvent",  # 文本增量事件
    "TextStartEvent",  # 文本开始事件
    "ThinkingDeltaEvent",  # 思考增量事件
    "ThinkingStartEvent",  # 思考开始事件
    "ToolResultEvent",  # 工具结果事件
    "ToolUseEvent",  # 工具调用事件
]
