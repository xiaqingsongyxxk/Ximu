"""统一异常定义模块。

本模块定义了应用层的自定义异常类型：
1. AppException - 应用层基础异常
2. ParseError - 文档解析异常
3. ValidationError - 数据校验异常
"""  # 模块文档字符串


class AppException(Exception):
    """应用层基础异常。

    所有应用异常的基类，包含错误消息和错误码。
    """
    def __init__(self, message: str, code: str | None = None):
        self.message = message  # 错误描述信息
        self.code = code or "APP_ERROR"  # 错误码（默认APP_ERROR）
        super().__init__(self.message)
# Exception.__init__ 做的事情很简单：把传进来的位置参数存到 self.args 里。而 str() 和 repr() 就是从 args 取值显示。
# 底层源码大致是这样：
# class Exception(BaseException):
#     def __init__(self, *args):
#         self.args = args  # 就干了这一件事
# 对于 Exception，__str__ 的实现是：
# class Exception:
#     def __str__(self):
#         if len(self.args) == 1:    # 只有一个参数
#             return str(self.args[0])  # 直接返回那个字符串
#         return str(self.args)

class ParseError(AppException):
    """文档解析异常。

    PDF解析失败时抛出。
    """
    def __init__(self, message: str):
        super().__init__(message, code="PARSE_ERROR")
# ↑ 这里的 super() = AppException
# 所以这行等价于调用 AppException.__init__(self, message, code="PARSE_ERROR")

class ValidationError(AppException):
    """数据校验异常。

    数据验证失败时抛出。
    """
    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR")
