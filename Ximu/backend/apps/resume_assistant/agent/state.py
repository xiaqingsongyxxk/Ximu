"""Agent迭代状态模块。

本模块定义了IterationState类，用于跟踪AI Agent的执行状态。
在多轮对话和工具调用过程中，Agent需要维护各种状态信息。
"""  # 模块文档字符串

from dataclasses import dataclass, field  # 导入dataclass装饰器和field函数

from shared.types.messages import ConversationMessage  # 对话消息类型


@dataclass
class IterationState:
    """Agent迭代状态类。

    跟踪AI Agent在多轮对话中的状态信息。
    每次LLM调用和工具执行都会更新状态。
    """

    messages: list[ConversationMessage] = field(default_factory=list)  # 对话消息列表
    resume_info: str = ""  # 简历信息文本（用于构建提示词）
    system: str = ""  # 系统提示词
    tools_schema: list[dict] = field(default_factory=list)  # 工具Schema列表
    count: int = 0  # 迭代计数器（当前轮次）
    _cached_resume_info: str | None = None  # 缓存的简历信息（避免重复构建）
