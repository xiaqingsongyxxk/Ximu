"""API错误类型定义模块。

本模块定义了API调用相关的自定义错误类型：
1. ChirenApiError - API错误基类
2. AuthenticationFailure - 认证失败
3. RateLimitFailure - 速率限制
4. RequestFailure - 请求失败
"""  # 模块文档字符串

from __future__ import annotations  # 支持延迟注解求值


class ChirenApiError(RuntimeError):
    """API错误基类。

    所有API相关错误的父类。
    """


class AuthenticationFailure(ChirenApiError):
    """认证失败错误。

    当API密钥无效或被拒绝时抛出。
    """


class RateLimitFailure(ChirenApiError):
    """速率限制错误。

    当请求频率超过API限制时抛出。
    """


class RequestFailure(ChirenApiError):
    """请求失败错误。

    当网络请求失败或其他通用错误时抛出。
    """
