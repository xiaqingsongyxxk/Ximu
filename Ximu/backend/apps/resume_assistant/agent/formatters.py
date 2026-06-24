"""Agent事件格式化模块。

本模块提供事件格式化功能：
1. StreamingFormatter - 将LLM流式事件转换为Agent事件
2. to_sse_event - 将Agent事件转换为SSE格式
"""  # 模块文档字符串

import json  # 导入JSON模块
from collections.abc import Iterator  # 导入迭代器类型
from datetime import datetime  # 导入日期时间类

from apps.resume_assistant.agent.events import (  # Agent事件类型
    AgentEvent,
    TextDeltaEvent,
    TextStartEvent,
    ThinkingDeltaEvent,
    ThinkingStartEvent,
)
from shared.api.client import ApiTextDeltaEvent  # LLM文本增量事件


class _DateTimeEncoder(json.JSONEncoder):
    """自定义JSON编码器，用于序列化datetime对象。"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()  # 转为ISO格式字符串
        return super().default(obj)#当无法序列化对象时，会抛出 TypeError 异常
# 这是 Python 的 钩子模式（hook pattern）。你不是直接调用 default，是*注册一个"后备方案"*给 json.dumps，当它自己搞不定的时候会主动来调用你。
# 看 json.JSONEncoder 的简化源码就知道了
# Python 内置的 json.JSONEncoder 核心逻辑大致是这样：
# class JSONEncoder:
#     def __init__(self, ...):
#         ...
#     def encode(self, o):
#         # 这是入口，内部会调用 iterencode
#         ...
#     def default(self, o):
#         # 默认实现：直接抛异常
#         raise TypeError(f'Object of type {type(o).__name__} is not JSON serializable')
#     def _make_iterencode(self, ...):
#         # 内部序列化逻辑
#         ...
#     def _iterencode(self, o, ...):
#         # 核心方法：对不同类型的 o 做不同处理
#         if isinstance(o, str):
#             yield _str(o)
#         elif isinstance(o, dict):
#             ... 逐一 encode value ...
#         elif isinstance(o, (int, float, bool)):
#             ...
#         elif o is None:
#             yield 'null'
#         else:
#             # ★ 关键：所有内置类型都处理完了还匹配不上
#             # 就调用 default(o) 作为最后手段
#             yield self.default(o)
# 关键行：self.default(o)
# json.dumps 内部的 _iterencode 会遍历你传的数据结构中的每一个值。对于每个值，它会按顺序检查：
# 这个值是不是 str？     → 直接序列化 ✅
# 这个值是不是 dict？    → 递归处理每个 value
# 这个值是不是 int？     → 直接序列化 ✅
# 这个值是不是 datetime？ → ❌ 不是 str/dict/int/float/bool/None/...
#                           ↓
#                         self.default(datetime_obj)
#                           ↓
#                         抛 TypeError（原始 JSONEncoder）
#                         或 → obj.isoformat()（你的 _DateTimeEncoder）
# 所以 cls=_DateTimeEncoder 做了两件事：
# 1. 告诉 json.dumps：用 _DateTimeEncoder 代替 JSONEncoder
# 2. 继承 _iterencode 等全部序列化逻辑，只替换 default 这一个方法
# 当 _iterencode 遇到不认识的对象时，代码里写死了 self.default(o)。因为你传了 cls=_DateTimeEncoder，所以 self 是你的类的实例，自然调的是你重写的 default。

class StreamingFormatter:
    """将LLM流式事件转换为Agent事件的格式化器。

    跟踪思考和文本的状态，确保每个类型的Start事件只发送一次。
    """

    def __init__(self):
        self._sent_thinking_start = False  # 是否已发送思考开始事件
        self._sent_text_start = False  # 是否已发送文本开始事件

    def format(self, event: ApiTextDeltaEvent) -> Iterator[AgentEvent]:
        """将LLM文本增量事件转换为Agent事件。

        Args:
            event: LLM文本增量事件。

        Yields:
            Agent事件（ThinkingStartEvent/ThinkingDeltaEvent/TextStartEvent/TextDeltaEvent）。
        """
        if event.is_think:  # 如果是思考内容
            if not self._sent_thinking_start:  # 如果还没发送过思考开始事件
                self._sent_thinking_start = True
                yield ThinkingStartEvent()  # 发送思考开始事件
            yield ThinkingDeltaEvent(text=event.text)  # 发送思考文本片段
        else:  # 如果是正式回复
            if not self._sent_text_start:  # 如果还没发送过文本开始事件
                self._sent_text_start = True
                yield TextStartEvent()  # 发送文本开始事件
            yield TextDeltaEvent(text=event.text)  # 发送回复文本片段

    def reset(self):
        """重置状态（每轮迭代开始时调用）。"""
        self._sent_thinking_start = False
        self._sent_text_start = False


def to_sse_event(event: AgentEvent) -> dict[str, str]:
    """将Agent事件转换为SSE格式。

    Args:
        event: Agent事件。

    Returns:
        SSE格式的字典（包含event和data字段）。
    """
    # 事件类型映射
    event_type_map = {
        "NextEvent": "next",
        "ThinkingStartEvent": "thinking_start",
        "ThinkingDeltaEvent": "thinking_delta",
        "TextStartEvent": "text_start",
        "TextDeltaEvent": "text_delta",
        "ToolUseEvent": "tool_use",
        "ToolResultEvent": "tool_result",
        "DoneEvent": "done",
        "ErrorEvent": "error",
    }

    event_name = event.__class__.__name__  # 获取事件类名
    event_type = event_type_map.get(event_name, event_name.lower())  # 获取事件类型

    # 提取事件数据（排除None值）
    if hasattr(event, "__dict__"):
        data = {k: v for k, v in event.__dict__.items() if v is not None}
#         这句就是把 event 的所有属性名和值拿出来，过滤掉 None 值的属性，拼成一个字典：
# Event	__dict__	过滤后 data
# ToolUseEvent(name="update", ...)	{"name":"update", "id":"xxx", "input":{...}}	{"name":"update", "id":"xxx", "input":{...}}
# TextDeltaEvent(text="你好")	{"text":"你好"}	{"text":"你好"}
# NextEvent()	{}	{}
# DoneEvent()	{}	{}
    else:
        data = {}

    return {
        "event": event_type,  # 事件类型
        "data": json.dumps(
            data, ensure_ascii=False, cls=_DateTimeEncoder
        ),  # 事件数据（JSON字符串）
    }
