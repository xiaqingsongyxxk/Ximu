"""Anthropic API客户端模块。

本模块定义了Anthropic API的流式客户端：
1. ApiMessageRequest - 消息请求参数
2. ApiTextDeltaEvent - 文本增量事件
3. ApiMessageCompleteEvent - 消息完成事件
4. AnthropicApiClient - API客户端类（支持重试）
5. SupportsStreamingMessages - 流式消息协议
"""  # 模块文档字符串

from __future__ import annotations  # 支持延迟注解求值

import asyncio  # 异步IO模块
import logging  # 日志模块
from collections.abc import AsyncIterator  # 异步迭代器类型
from dataclasses import dataclass, field  # 数据类装饰器
from typing import Any, Protocol  # 类型注解工具

from anthropic import (  # Anthropic SDK
    APIError,
    APIStatusError,
    AsyncAnthropic,
)

from shared.api.errors import (  # 自定义错误类型
    AuthenticationFailure,
    ChirenApiError,
    RateLimitFailure,
    RequestFailure,
)
from shared.api.usage import UsageSnapshot  # 使用量快照
from shared.types.messages import (  # 消息类型
    ConversationMessage,
    assistant_message_from_api,
)

log = logging.getLogger(__name__)  # 日志记录器

# 重试配置
MAX_RETRIES = 3  # 最大重试次数
BASE_DELAY = 1.0  # 基础延迟（秒）
MAX_DELAY = 30.0  # 最大延迟（秒）
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 529}  # 可重试的HTTP状态码


@dataclass(frozen=True)
class ApiMessageRequest:
    """模型调用的输入参数。"""

    model: str  # 模型名称
    messages: list[ConversationMessage]  # 对话消息列表
    system_prompt: str | None = None  # 系统提示词
    max_tokens: int = 4096  # 最大token数
    temperature: float | None = None  # 温度参数
    tools: list[dict[str, Any]] = field(default_factory=list)  # 工具列表


@dataclass(frozen=True)
class ApiTextDeltaEvent:
    """模型产生的增量文本。"""

    text: str  # 增量文本
    is_think: bool = False  # 是否为思考内容（前端可特殊显示）


@dataclass(frozen=True)
class ApiMessageCompleteEvent:
    """包含完整助手消息的终止事件。"""

    message: ConversationMessage  # 完整的助手消息
    usage: UsageSnapshot  # token使用量快照
    stop_reason: str | None = None  # 停止原因


# 流事件类型别名
ApiStreamEvent = ApiTextDeltaEvent | ApiMessageCompleteEvent


class SupportsStreamingMessages(Protocol):
    """支持流式消息的协议（接口）。"""

    async def stream_message(
        self, request: ApiMessageRequest
    ) -> AsyncIterator[ApiStreamEvent]:
        """产出流式事件。"""
        ...


def _is_retryable(exc: Exception) -> bool:
    """检查异常是否可重试。"""
    if isinstance(exc, APIStatusError):  # 如果是HTTP状态码错误
        return (
            exc.status_code in RETRYABLE_STATUS_CODES
        )  # 检查状态码是否在可重试列表中（429、500等）
    if isinstance(exc, APIError):  # 如果是通用API错误（通常是网络问题）
        return True  # 网络问题可以重试
    if isinstance(
        exc, (ConnectionError, TimeoutError, OSError)
    ):  # 如果是网络连接类错误
        return True  # 连接问题可以重试
    return False  # 其他错误（如参数错误）不重试
# 和shared/api/openai_client.py里面的def _is_retryable(exc: Exception) -> boo
# 没有什么区别

def _get_retry_delay(attempt: int, exc: Exception | None = None) -> float:
    """计算重试延迟（指数退避 + 抖动）。"""
    import random  # 导入随机数模块，用于添加抖动

    # 检查服务器是否返回了Retry-After响应头
    if isinstance(exc, APIStatusError):  # 如果是HTTP状态码错误
        retry_after = getattr(exc, "headers", {})  # 获取响应头
        if hasattr(retry_after, "get"):  # 如果响应头支持get方法
            val = retry_after.get("retry-after")  # 获取Retry-After的值
            if val:  # 如果有Retry-After值
                try:
                    return min(
                        float(val), MAX_DELAY
                    )  # 使用服务器建议的延迟，但不超过最大延迟
                except (ValueError, TypeError):  # 如果值无法转成数字
                    pass  # 忽略，使用默认的指数退避

    delay = min(
        BASE_DELAY * (2**attempt), MAX_DELAY
    )  # 指数退避：1秒、2秒、4秒...但不超过30秒
    jitter = random.uniform(
        0, delay * 0.25
    )  # 添加0~25%的随机抖动，避免多个客户端同时重试
    return delay + jitter  # 返回延迟时间（含抖动）


class AnthropicApiClient:
    """Anthropic API客户端（支持重试和流式输出）。"""

    def __init__(self, api_key: str, *, base_url: str | None = None) -> None:
        """初始化客户端。"""
        kwargs: dict[str, Any] = {"api_key": api_key}  # 构建初始化参数，必传API密钥
        if base_url:  # 如果指定了自定义API地址
            kwargs["base_url"] = base_url  # 添加到参数中（用于代理或私有部署）
        self._client = AsyncAnthropic(**kwargs)  # 创建Anthropic异步客户端实例

    async def stream_message(
        self, request: ApiMessageRequest
    ) -> AsyncIterator[ApiStreamEvent]:
        """流式获取LLM响应（支持重试）。"""
        last_error: Exception | None = None  # 记录最后一次错误，后续用于抛出

        for attempt in range(MAX_RETRIES + 1):  # 重试循环，从0开始到MAX_RETRIES
            try:
                async for event in self._stream_once(request):  # 尝试单次流式请求
                    yield event  # 产出事件给调用方
                return  # 成功则直接返回，不再重试
            except ChirenApiError:  # 如果是自定义API错误（认证失败等）
                raise  # 直接抛出，不重试
            except Exception as exc:  # 如果是其他异常
                last_error = exc  # 记录错误
                if attempt >= MAX_RETRIES or not _is_retryable(
                    exc
                ):  # 如果超过最大重试次数或错误不可重试
                    if isinstance(exc, APIError):  # 如果是Anthropic SDK的错误
                        raise _translate_api_error(
                            exc
                        ) from exc  # 转换为自定义错误后抛出
                    raise RequestFailure(str(exc)) from exc  # 包装为请求失败错误后抛出

                delay = _get_retry_delay(attempt, exc)  # 计算重试延迟
                status = getattr(exc, "status_code", "?")  # 获取HTTP状态码
                log.warning(
                    "API请求失败 (尝试 %d/%d, 状态=%s), %.1f秒后重试: %s",
                    attempt + 1,
                    MAX_RETRIES + 1,
                    status,
                    delay,
                    exc,
                )  # 记录警告日志
                await asyncio.sleep(delay)  # 等待一段时间后重试
        # 也是有点多余
        if last_error is not None:  # 如果所有重试都失败了
            if isinstance(last_error, APIError):  # 如果是Anthropic SDK的错误
                raise _translate_api_error(
                    last_error
                ) from last_error  # 转换为自定义错误后抛出
            raise RequestFailure(
                str(last_error)
            ) from last_error  # 包装为请求失败错误后抛出

    async def _stream_once(
        self, request: ApiMessageRequest
    ) -> AsyncIterator[ApiStreamEvent]:
        """单次流式请求。"""
        params: dict[str, Any] = {  # 构建API请求参数
            "model": request.model,  # 模型名称
            "messages": [
                message.to_api_param() for message in request.messages
            ],  # 把消息列表转成API格式
            "max_tokens": request.max_tokens,  # 最大输出token数
        }
        if request.system_prompt:  # 如果有系统提示词
            params["system"] = request.system_prompt  # 添加到参数中
        if request.tools:  # 如果有工具定义
            params["tools"] = request.tools  # 添加到参数中
        if request.temperature:  # 如果设置了温度参数
            params["temperature"] = request.temperature  # 添加到参数中

        try:
            async with self._client.messages.stream(**params) as stream:  # 创建流式连接
                async for event in stream:  # 遍历流式事件
                    if (
                        getattr(event, "type", None) != "content_block_delta"
                    ):  # 如果不是内容块增量事件
                        continue  # 跳过
                    delta = getattr(event, "delta", None)  # 获取增量内容
                    if getattr(delta, "type", None) not in (
                        "text_delta",
                        "thinking_delta",
                    ):  # 如果不是文本或思考增量
                        continue  # 跳过
# 因为两个 API 的流式事件结构不一样，OpenAI 不存在"有其他事件类型需要跳过"的情况。
# Anthropic 的流式 — 多种事件类型，需要过滤
# Anthropic 流式事件流（多种 type）：
# ──────────────────────────────────
# event.type = "message_start"                 ← 消息开始
# event.type = "content_block_start"            ← 内容块开始（可能带完整的 tool_use 头部）
# event.type = "content_block_delta"            ← 内容块增量
#   └─ delta.type = "text_delta"               ✅ 要处理
#   └─ delta.type = "input_json_delta"         ❌ 跳过（工具参数增量）
#   └─ delta.type = "thinking_delta"           ✅ 要处理
# event.type = "content_block_stop"             ← 内容块结束
# event.type = "message_delta"                  ← 消息结束
# 所以需要两层过滤：
# if event.type != "content_block_delta":       # ← 只处理 delta 事件
#     continue
# if delta.type not in ("text_delta", "thinking_delta"):  # ← 只处理文本和思考
#     continue
# OpenAI 的流式 — 只有一种事件结构
# OpenAI 流式（每 chunk 结构一样，靠 null/非 null 区分）：
# ──────────────────────────────────────────────────────
# chunk.choices[0].delta
#   ├── content: "你好" | None            ← 文本就走这里
#   ├── tool_calls: [...] | None          ← 工具调用就走这里
#   └── (没有 type 字段，没有其他事件类型)
# OpenAI 不存在 "type == content_block_start 需要跳过"这种事情。每个 chunk 的结构一模一样，只是不同的字段为 null 或非 null：
# skip_usage_only_chunks:  if not chunk.choices: continue  # ← 唯一需要跳过的
# # 然后直接根据字段是否有值来处理：
# if delta.content:           ← 有文本？
#     ...
# if delta.tool_calls:        ← 有工具调用？
#     ...
# OpenAI 不用过滤 type，因为它没有多种事件类型。 每个 chunk 都是 ChoiceDelta 这同一个东西，只是里面字段 null 或非 null。需要过滤的是 Anthropic 那边专有的设计——把流式拆成多种语义不同的事件。                    
                    text = getattr(delta, "text", None)  # 获取文本内容
                    thinking = getattr(delta, "thinking", None)  # 获取思考内容
# 假设模型输出了 "我来帮你" 然后是思维链 "先修改教育经历"，Anthropic 会发两个事件：
# 事件 1: delta = TextDelta(text="我来帮你", type="text_delta")
# 事件 2: delta = ThinkingDelta(thinking="先修改教育经历", type="thinking_delta")
# 现在逐行执行：
# 事件 1（TextDelta）:
#   delta.text       → ✅ "我来帮你"
#   delta.thinking   → ❌ 这个对象上根本没有 thinking 字段！AttributeError
# 事件 2（ThinkingDelta）:
#   delta.thinking   → ✅ "先修改教育经历"
#   delta.text       → ❌ 这个对象上根本没有 text 字段！AttributeError
# 所以如果用 delta.thinking 直接访问：
# # 事件 1 进来时
# delta.thinking  # 💥 AttributeError: 'TextDelta' object has no attribute 'thinking'
# 程序崩了
# 所以必须用 getattr：
# # 不管进来的是 TextDelta 还是 ThinkingDelta，都安全
# text = getattr(delta, "text", None)         # TextDelta → "我来帮你"
#                                               # ThinkingDelta → None（不崩）
# thinking = getattr(delta, "thinking", None)  # TextDelta → None（不崩）
#                                               # ThinkingDelta → "先修改教育经历"
# OpenAI 那边为什么可以直接用 delta.content
# OpenAI 的 delta 就只有一种类型：
# # OpenAI：不管什么情况，delta 永远是 ChoiceDelta 这一个类
# class ChoiceDelta:
#     content: str | None = None      # 这两个字段永远存在
#     tool_calls: list | None = None  # 永远存在
# 不管你怎么跑，永远只有一个 ChoiceDelta，content 永远在：
# # 这是文本
# delta = ChoiceDelta(content="你好", tool_calls=None)
# delta.content   # ✅ "你好"
# # 这是工具调用
# delta = ChoiceDelta(content=None, tool_calls=[...])
# delta.content   # ✅ None（字段存在，不崩）
#  	Anthropic delta	OpenAI delta
# 可能有几种类型	2 种（TextDelta、ThinkingDelta）	1 种（ChoiceDelta）
# 字段是否永远存在	❌ text 只在 TextDelta 有，thinking 只在 ThinkingDelta 有	✅ content 在 ChoiceDelta 上永远存在
# 所以	必须 getattr 兜底，否则崩	可以直接 .content
# 因为 Python 的规则就是：属性不存在就是 AttributeError，不会自动返回 None。
# class TextDelta:
#     def __init__(self, text):
#         self.text = text       # 只定义了 text
#     # 没有 thinking 这个属性
# d = TextDelta(text="你好")
# d.text        # ✅ "你好" — 存在
# d.thinking    # 💥 AttributeError — 不存在，Python 不知道你想要 None
                    if thinking:  # 如果有思考内容
                        yield ApiTextDeltaEvent(
                            text=thinking, is_think=True
                        )  # 产出思考增量事件
                    if text:  # 如果有文本内容
                        yield ApiTextDeltaEvent(text=text)  # 产出文本增量事件

                final_message = await stream.get_final_message()  # 获取完整的最终消息
#         Anthropic SDK 对象（外部格式）
#         ↓ assistant_message_from_api()
# ConversationMessage（内部格式）
#         ↓
# 用于内部处理（保存、比较、工具执行等）
# 本质：外部 API 返回的格式与我们内部使用的格式不同，需要转换。
        except APIError as exc:  # 如果发生API错误
            if (
                isinstance(exc, APIStatusError)
                and exc.status_code in RETRYABLE_STATUS_CODES
            ):  # 如果是可重试的状态码
                raise  # 让重试逻辑处理
            raise _translate_api_error(exc) from exc  # 转换为自定义错误后抛出

        usage = getattr(final_message, "usage", None)  # 获取token使用量
        yield ApiMessageCompleteEvent(  # 产出消息完成事件
            message=assistant_message_from_api(final_message),  # 把API消息转成内部格式
            usage=UsageSnapshot(  # 创建使用量快照
                input_tokens=int(getattr(usage, "input_tokens", 0) or 0),  # 输入token数
                output_tokens=int(
                    getattr(usage, "output_tokens", 0) or 0
                ),  # 输出token数
            ),
            stop_reason=getattr(final_message, "stop_reason", None),  # 停止原因
        )


def _translate_api_error(exc: APIError) -> ChirenApiError:
    """将Anthropic API错误转换为自定义错误。"""
    name = exc.__class__.__name__  # 获取异常类名
    if name in {"AuthenticationError", "PermissionDeniedError"}:  # 如果是认证相关错误
        return AuthenticationFailure(str(exc))  # 转换为认证失败错误
    if name == "RateLimitError":  # 如果是速率限制错误
        return RateLimitFailure(str(exc))  # 转换为速率限制错误
    return RequestFailure(str(exc))  # 其他错误转为通用请求失败错误
# 和shared/api/openai_client.py里面的def _translate_error(exc: Exception) -> ChirenApiError:
# 没有什么区别