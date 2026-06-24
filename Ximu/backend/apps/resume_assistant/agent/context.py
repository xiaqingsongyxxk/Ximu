"""Agent查询上下文模块。

本模块定义了QueryContext类，包含AI Agent运行时的所有依赖和配置。
"""  # 模块文档字符串

from dataclasses import dataclass, field  # 导入dataclass装饰器

from shared.api.client import SupportsStreamingMessages  # LLM客户端接口
from shared.types.base_tool import ToolRegistry  # 工具注册表


@dataclass
class QueryContext:
    """Agent运行时依赖与配置类。

    包含AI Agent运行所需的所有配置和依赖：
    - API客户端和工具注册表
    - 模型配置（model, max_tokens, temperature）
    - Agent配置（max_iterations, stop_reasons）
    - 元数据
    """

    api_client: SupportsStreamingMessages  # LLM客户端（支持流式消息）
    tool_registry: ToolRegistry  # 工具注册表（包含所有可用工具）

    model: str  # 模型名称（如"gpt-4o"）
    max_tokens: int | None = None  # 最大token数（None表示不限制）
    temperature: float = 1.0  # 温度参数（0=确定性，1=创造性）

    max_iterations: int = 30  # 最大迭代次数（防止无限循环）
    stop_reasons: set[str] = field(  # 停止原因集合
        default_factory=lambda: {"end_turn", "stop"}  # 默认：对话结束或主动停止
    )

    metadata: dict = field(default_factory=dict)  # 元数据（存储额外信息）
