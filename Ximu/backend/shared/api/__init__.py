"""共享API包的初始化模块。

本模块导出API客户端相关的核心类型和工厂函数：
1. AnthropicApiClient - Anthropic API客户端
2. OpenAICompatibleClient - OpenAI兼容客户端
3. ChirenApiError - API错误基类
4. UsageSnapshot - 使用量快照
5. get_client - 客户端工厂函数
"""  # 模块文档字符串

from shared.api.client import AnthropicApiClient  # 导入Anthropic API客户端
from shared.api.errors import ChirenApiError  # 导入API错误基类
from shared.api.openai_client import OpenAICompatibleClient  # 导入OpenAI兼容客户端
from shared.api.usage import UsageSnapshot  # 导入使用量快照

# 模块公开接口，定义使用 "from shared.api import *" 时会导入哪些名称
__all__ = [
    "AnthropicApiClient",  # Anthropic API客户端
    "OpenAICompatibleClient",  # OpenAI兼容客户端
    "ChirenApiError",  # API错误基类
    "UsageSnapshot",  # 使用量快照
    "get_client",  # 客户端工厂函数
]

from typing import Literal  # 导入Literal类型

from shared.api.client import SupportsStreamingMessages  # 导入流式消息支持协议


def get_client(
    type: Literal["anthropic", "openai"],  # 客户端类型
    api_key: str,  # API密钥
    base_url: str,  # API基础URL
) -> SupportsStreamingMessages:
    """根据类型创建并返回流式API客户端。

    Args:
        type: 提供商类型（"anthropic"或"openai"）。
        api_key: API密钥。
        base_url: API端点的基础URL。

    Returns:
        实现SupportsStreamingMessages协议的客户端实例。
    """
    if type == "openai":  # 如果用户选择的是OpenAI兼容类型
        return OpenAICompatibleClient(  # 创建OpenAI兼容客户端实例
            api_key=api_key,  # 传入API密钥
            base_url=base_url,  # 传入API基础URL
        )
    elif type == "anthropic":  # 如果用户选择的是Anthropic类型
        return AnthropicApiClient(  # 创建Anthropic客户端实例
            api_key=api_key,  # 传入API密钥
            base_url=base_url,  # 传入API基础URL
        )
