# Agent 事件格式化模块（LangGraph 版）。

# 对应手写版: agent/formatters.py

# 与手写版完全相同:
# - StreamingFormatter: 将 LLM 流式事件转为 Agent 事件 (区分 thinking/text)
# - to_sse_event: 将 Agent 事件转为 SSE 格式
# - _DateTimeEncoder: 自定义 JSON 编码器

# 不同点: LangGraph 版从 LangChain 的 AIMessageChunk 中提取 text/reasoning，构造 Agent 事件
# - 使用 format_text(text, is_think) 替代手写版的 format(ApiTextDeltaEvent)


import json  # 导入 json 模块，后面要把事件数据转成 JSON 字符串发给前端
from collections.abc import (
    Iterator,
)  # 导入 Iterator（迭代器类型），format_text 方法一次可能 yield 多个事件
from datetime import datetime  # 导入 datetime，后面要序列化时间对象

from apps.resume_assistant.agent_langgraph.events import (  # 导入本模块定义的各种 Agent 事件类型
    AgentEvent,  # 联合类型：所有 Agent 事件的合集
    TextDeltaEvent,  # 文本增量事件
    TextStartEvent,  # 文本开始事件
    ThinkingDeltaEvent,  # 思考增量事件
    ThinkingStartEvent,  # 思考开始事件
)


class _DateTimeEncoder(
    json.JSONEncoder
):  # 自定义 JSON 编码器：支持序列化 datetime 对象
    # 自定义 JSON 编码器，支持 datetime 序列化。

    # 手写版也有完全相同的类。Python 自带的 json.dumps 不能直接序列化 datetime，
    # 这个编码器遇到 datetime 对象自动转成 ISO 格式字符串。

    def default(self, obj):  # 重写 default 方法，自定义序列化逻辑
        # 重写 JSONEncoder 的 default 方法。
        if isinstance(obj, datetime):  # 如果当前对象是 datetime 类型
            return obj.isoformat()  # 转成 ISO 格式字符串（比如 "2024-01-15T10:30:00"）

        return super().default(obj)  # 其他类型交给父类处理（会抛出 TypeError）


class StreamingFormatter:  # 流式事件格式化器：将 LLM 文本增量转成前端可读的事件流
    # 流式事件格式化器。

    # 手写版也有完全相同的类，负责把 LLM 返回的文本流分成"思考过程"和"正式回答"两个通道。

    def __init__(self):  # 初始化格式化器：重置所有发送状态
        # 初始化格式化器。
        self._sent_thinking_start = False  # 是否已经发送过思考开始事件（防止重复发送）
        # 是否已发送 text 开始的标记
        self._sent_text_start = False  # 是否已经发送过文字开始事件

    def format_text(
        self, text: str, is_think: bool
    ) -> Iterator[AgentEvent]:  # 按文本块格式化
        # 直接按文本块格式化，跳过 ApiTextDeltaEvent 构造。
        # LangGraph 版特有的方法，直接从 LangChain 的 chunk 中提取文本，
        # 跳过 ApiTextDeltaEvent 的构造步骤。行为与 format() 完全一致。

        if is_think:  # 如果当前文本是"思考过程"
            if not self._sent_thinking_start:  # 如果还没发过思考开始信号
                self._sent_thinking_start = True  # 标记为已发送
                yield ThinkingStartEvent()  # 发一个"思考开始"事件

            yield ThinkingDeltaEvent(text=text)  # 发一个"思考增量"事件
        else:  # 如果当前文本是"正式回答"
            if not self._sent_text_start:  # 如果还没发过文字开始信号
                self._sent_text_start = True  # 标记为已发送
                yield TextStartEvent()  # 发一个"文字开始"事件

            yield TextDeltaEvent(text=text)  # 发一个"文字增量"事件

    def reset(self):  # 重置发送状态（每轮对话开始时调用）
        # 重置发送标记。

        # 手写版在 while 循环每轮开头调用 reset()。
        # LangGraph 版在 prepare 节点开始时调用 reset()。

        self._sent_thinking_start = False  # 重置思考开始标记
        self._sent_text_start = False  # 重置文字开始标记


def to_sse_event(event: AgentEvent) -> dict[str, str]:  # 将 Agent 事件转为 SSE 字典格式
    # 将 Agent 事件转为 SSE 事件字典。
    # 返回值直接传给 sse_starlette 的 EventSourceResponse。
    # 前端收到后根据 event 字段判断事件类型。
    return {  # 返回一个字典包含事件类型、ID 和 JSON 数据
        "event": type(
            event
        ).__name__,  # 事件类型名（如 "TextDeltaEvent"），前端据此判断类型
        "id": "",  # 事件 ID（当前为空字符串，暂未使用）
        "data": json.dumps(
            event, cls=_DateTimeEncoder
        ),  # 事件数据 JSON 字符串（用自定义编码器处理 datetime）
    }
