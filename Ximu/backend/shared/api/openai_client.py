"""OpenAI兼容API客户端模块。

本模块提供OpenAI兼容API的流式客户端：
用于阿里巴巴DashScope、GitHub Models等OpenAI兼容提供商。
"""  # 模块文档字符串

from __future__ import annotations  # 支持延迟注解求值

import asyncio  # 异步IO模块
import json  # JSON模块
import logging  # 日志模块
from collections.abc import AsyncIterator  # 异步迭代器类型
from typing import Any  # 任意类型

from openai import AsyncOpenAI  # OpenAI SDK异步客户端

from shared.api.client import (  # API事件类型
    ApiMessageCompleteEvent,
    ApiMessageRequest,
    ApiStreamEvent,
    ApiTextDeltaEvent,
)
from shared.api.errors import (  # 自定义错误类型
    AuthenticationFailure,
    ChirenApiError,
    RateLimitFailure,
    RequestFailure,
)
from shared.api.usage import UsageSnapshot  # 使用量快照
from shared.types.messages import (  # 消息类型
    ContentBlock,
    ConversationMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)

log = logging.getLogger(__name__)  # 日志记录器

# 重试配置
MAX_RETRIES = 3
BASE_DELAY = 1.0
MAX_DELAY = 30.0


def _convert_tools_to_openai(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """将Anthropic工具格式转换为OpenAI函数调用格式。"""
    result = []  # 用于存放转换后的工具列表
    for tool in tools:  # 遍历每个工具
        result.append(
            {
                "type": "function",  # 固定为"function"类型
                "function": {
                    "name": tool["name"],  # 工具名称
                    "description": tool.get(
                        "description", ""
                    ),  # 工具描述，默认为空字符串
                    "parameters": tool.get("input_schema", {}),  # 输入参数的JSON Schema
                },
            }
        )
    return result  # 返回转换后的工具列表，后续传给OpenAI API


def _convert_messages_to_openai(
    messages: list[ConversationMessage],  # 内部格式的消息列表
    system_prompt: str | None,  # 系统提示词
) -> list[dict[str, Any]]:
    """将消息转换为OpenAI聊天格式。"""
    openai_messages: list[dict[str, Any]] = []  # 用于存放转换后的OpenAI格式消息

    if system_prompt:  # 如果有系统提示词
        openai_messages.append(
            {"role": "system", "content": system_prompt}
        )  # 添加系统消息

    for msg in messages:  # 遍历每条消息
        if msg.role == "assistant":  # 如果是助手消息
            openai_msg = _convert_assistant_message(msg)  # 转换助手消息格式
            openai_messages.append(openai_msg)  # 添加到列表
        elif msg.role == "user":  # 如果是用户消息
            tool_results = [
                b for b in msg.content if isinstance(b, ToolResultBlock)
            ]  # 提取工具结果块
            text_blocks = [
                b for b in msg.content if isinstance(b, TextBlock)
            ]  # 提取文本块

            if tool_results:  # 如果有工具结果
                for tr in tool_results:  # 遍历每个工具结果
                    openai_messages.append(
                        {
                            "role": "tool",  # OpenAI中工具结果的角色是"tool"
                            "tool_call_id": tr.tool_use_id,  # 关联的工具调用ID
                            "content": tr.content,  # 工具返回的内容
                        }
                    )
            if text_blocks:  # 如果有文本块
                text = "".join(b.text for b in text_blocks)  # 把所有文本块拼接
                if text.strip():  # 如果文本不为空
                    openai_messages.append(
                        {"role": "user", "content": text}
                    )  # 添加用户消息
            if not tool_results and not text_blocks:  # 如果既没有工具结果也没有文本
                openai_messages.append(
                    {"role": "user", "content": ""}
                )  # 添加空用户消息（保持消息链完整）

    return openai_messages  # 返回转换后的消息列表，后续传给OpenAI API


def _convert_assistant_message(msg: ConversationMessage) -> dict[str, Any]:
    """将助手消息转换为OpenAI格式。"""
    text_parts = [
        b.text for b in msg.content if isinstance(b, TextBlock)
    ]  # 提取所有文本块的文本
    tool_uses = [
        b for b in msg.content if isinstance(b, ToolUseBlock)
    ]  # 提取所有工具调用块

    openai_msg: dict[str, Any] = {"role": "assistant"}  # 创建助手消息，角色为assistant
    content = "".join(text_parts)  # 把所有文本拼接成一个字符串
    openai_msg["content"] = (
        content if content else None
    )  # 设置内容（如果为空则设为None）

    if tool_uses:  # 如果有工具调用
        openai_msg["tool_calls"] = [  # 添加tool_calls字段
            {
                "id": tu.id,  # 工具调用ID
                "type": "function",  # 固定为"function"类型
                "function": {
                    "name": tu.name,  # 工具名称
                    "arguments": json.dumps(
                        tu.input, ensure_ascii=False
                    ),  # 工具输入参数转成JSON字符串
                },
            }
            for tu in tool_uses  # 遍历每个工具调用
        ]
    return openai_msg  # 返回转换后的助手消息，后续传给OpenAI API


class OpenAICompatibleClient:
    """OpenAI兼容API客户端。

    实现与AnthropicApiClient相同的SupportsStreamingMessages协议，
    可以作为Drop-in替换使用。
    """

    def __init__(self, api_key: str, *, base_url: str | None = None) -> None:
        kwargs: dict[str, Any] = {"api_key": api_key}  # 构建初始化参数，必传API密钥
        if base_url:  # 如果指定了自定义API地址
            kwargs["base_url"] = base_url  # 添加到参数中（用于代理或私有部署）
        self._client = AsyncOpenAI(**kwargs)  # 创建OpenAI异步客户端实例

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
                if attempt >= MAX_RETRIES or not self._is_retryable(
                    exc
                ):  # 如果超过最大重试次数或错误不可重试
                    raise self._translate_error(exc) from exc  # 转换为自定义错误后抛出

                delay = min(
                    BASE_DELAY * (2**attempt), MAX_DELAY
                )  # 计算重试延迟（指数退避）
                log.warning(
                    "OpenAI API请求失败 (尝试 %d/%d), %.1f秒后重试: %s",
                    attempt + 1,  # 当前尝试次数
                    MAX_RETRIES + 1,  # 总尝试次数
                    delay,  # 延迟时间
                    exc,  # 错误信息
                )
                await asyncio.sleep(delay)  # 等待一段时间后重试

        if last_error is not None:  # 如果所有重试都失败了
            raise self._translate_error(
                last_error
            ) from last_error  # 转换为自定义错误后抛出

    async def _stream_once(
        self, request: ApiMessageRequest
    ) -> AsyncIterator[ApiStreamEvent]:
        """单次流式请求。"""
        openai_messages = _convert_messages_to_openai(  # 把内部消息格式转成OpenAI格式
            request.messages,
            request.system_prompt,  # 传入消息列表和系统提示词
        )
        openai_tools = (
            _convert_tools_to_openai(request.tools)
            if request.tools
            else None  # 把工具定义转成OpenAI格式（如果有）
        )

        params: dict[str, Any] = {  # 构建API请求参数
            "model": request.model,  # 模型名称
            "messages": openai_messages,  # 转换后的消息列表
            "max_tokens": request.max_tokens,  # 最大输出token数
            "stream": True,  # 启用流式输出
            "stream_options": {"include_usage": True},  # 在流式响应中包含token使用量
        }
        if openai_tools:  # 如果有工具定义
            params["tools"] = openai_tools  # 添加到参数中
            params.pop(
                "stream_options", None
            )  # 有工具时移除stream_options，避免触发思考模式
        if request.temperature:  # 如果设置了温度参数
            params["temperature"] = request.temperature  # 添加到参数中

        # 收集流式响应的各个部分
        collected_content = ""  # 收集文本内容
        collected_reasoning = ""  # 收集思考/推理内容
        collected_tool_calls: dict[
            int, dict[str, Any]
        ] = {}  # 收集工具调用（按索引分组）
        finish_reason: str | None = None  # 停止原因
        usage_data: dict[str, int] = {}  # token使用量数据

        stream = await self._client.chat.completions.create(**params)  # 创建流式请求
        async for chunk in stream:  # 遍历每个响应块
            if not chunk.choices:  # 如果没有选择（通常是usage数据块）
                if chunk.usage:  # 如果有使用量数据
                    usage_data = {  # 记录使用量
                        "input_tokens": chunk.usage.prompt_tokens or 0,  # 输入token数
                        "output_tokens": chunk.usage.completion_tokens
                        or 0,  # 输出token数
                    }
                continue  # 跳过这个块

            delta = chunk.choices[0].delta  # 获取增量内容
            chunk_finish = chunk.choices[0].finish_reason  # 获取停止原因

            if chunk_finish:  # 如果有停止原因
                finish_reason = chunk_finish  # 记录停止原因
# # OpenAI SDK 内部相当于做了
# class ChoiceDelta(BaseModel):
#     content: str | None = None        # ← 定义了，实例化时自动生成这字段
#     # reasoning_content 没有这一行    # ← 没定义，字段不存在
# 效果：
# # content — 有定义
# delta.content            # ✅ 总是可以访问，值可能是 None 或 "你好"
# if delta.content:        # ✅ 安全
# # reasoning_content — 没定义
# delta.reasoning_content  # ❌ 可能报 AttributeError
# 而 getattr(delta, "reasoning_content", None) 就是自己手工模拟了 = None 的默认声明：
# # Python 等价关系
# # 这一行代码：
# getattr(delta, "reasoning_content", None) or ""
# # 相当于在类里写了这一行：
# reasoning_content: str | None = None
            # 收集思考内容
            reasoning_piece = (
                getattr(delta, "reasoning_content", None) or ""
            )  # 获取推理内容（某些模型支持）
            if reasoning_piece:  # 如果有推理内容
                collected_reasoning += reasoning_piece  # 累积推理内容
                yield ApiTextDeltaEvent(
                    text=reasoning_piece, is_think=True
                )  # 产出思考增量事件

            # 收集文本内容
            if delta.content:  # 如果有文本内容
                collected_content += delta.content  # 累积文本内容
                yield ApiTextDeltaEvent(text=delta.content)  # 产出文本增量事件
# 不需要。这个判断只检查当前 chunk 里有没有 tool_calls 这个字段，不管里面信息完整不完整：
# if delta.tool_calls:   # ← 只要 delta.tool_calls 存在且不为空/None，就进入
# 看前面的例子，第一个 chunk 里的 tool_calls 就已经不完全了：
# # chunk 1 — 最"完整"的一个
# delta.tool_calls = [{
#     "index": 0,
#     "id": "call_abc123",        # ✅ 有 id
#     "function": {
#         "name": "update_section",  # ✅ 有 name
#         "arguments": ""            # ❌ 空的！但 if 仍然为 True
#     }
# }]
# # if delta.tool_calls: → ✅ True，进入循环
# 实际上整个流式过程中，每个携带 tool_calls 的 chunk 都是不完整的，因为 OpenAI 的设计就是"有信息就发，不分完整不完整"：
# chunk     id      name    arguments     if delta.tool_calls
# ─────────────────────────────────────────────────────────────
# chunk 1   ✅      ✅      ""(空的)      ✅ 通过
# chunk 2   null    null    "{\"id\":"    ✅ 通过
# chunk 3   null    null    "1}"          ✅ 通过
# 那 if 进去之后怎么处理不完整的信息？
# for tc_delta in delta.tool_calls:
#     if tc_delta.id:                # 有就更新，没有就跳过
#         entry["id"] = tc_delta.id
#     if tc_delta.function:
#         if tc_delta.function.name:
#             entry["name"] = tc_delta.function.name
#         if tc_delta.function.arguments:
#             entry["arguments"] += tc_delta.function.arguments   # 累加
# 内部也有空值检查，所以不存在"因为信息不完整就报错"的问题。判断仅仅回答"这个 chunk 有没有工具调用相关信息？"这一个问题。
            # 收集工具调用
            if delta.tool_calls:  # 如果有工具调用增量
#                 tool_use 这个字段名是 Anthropic API 团队选的，不是模型起的。模型输出的是原始 token 流，API 层解析这些 token、赋予结构、取名字、包装成 JSON 再返回给你。
# 就像 OpenAI API 选了 tool_calls、function.arguments 这些名字一样——都是 API 层的协议设计。
# 不是 AI 自己定义的，是 OpenAI API 的协议设计者规定的格式。
# 完整链路
# AI 模型内部输出：
#   "我想调用工具 update_section，参数是 {\"id\": 1}"
#            │
#            ▼
# OpenAI API 服务器收到这个输出，决定：
#   1. 这是工具调用，不是文本
#   2. 按 streaming 格式切成多个 chunk
#   3. 每个 chunk 的 delta 里放 tool_calls 字段
#            │
#            ▼
# chunk 1: delta.tool_calls = [{index: 0, id: "call_abc", function: {name: "update", arguments: ""}}]
# chunk 2: delta.tool_calls = [{index: 0, function: {arguments: "{\"id\":"}}]
# chunk 3: delta.tool_calls = [{index: 0, function: {arguments: "1}"}}]
# AI 模型本身不知道 delta.tool_calls 是什么。 模型内部只产生"我想调用函数 X，参数是 Y"这个高层决策。把这个决策序列化成什么格式返回给你，是 OpenAI API 层决定的。
# 所以 delta.tool_calls 是...
# OpenAI API 协议的一部分，写在他们公开的文档里：
# Streaming Chat Completions API
#   ↓
# 每个 chunk 结构：
#   choices[0].delta
#     ├── content: str | null         ← 文本增量
#     ├── tool_calls: [               ← 工具调用增量
#     │     { index, id, function: { name, arguments } }
#     │   ]
#     └── ...
# 这不是模型的输出格式，是API 传输格式。同样的模型决策，如果换成 Anthropic API，返回的就是：
# content_block_start(type=tool_use, id=..., name=...)
# content_block_delta(type=input_json_delta, partial_json='{"id":')
# content_block_delta(type=input_json_delta, partial_json='1}')
# 或者用非流式 API，就直接返回完整的 message.tool_calls（OpenAI）或 content[].type=tool_use（Anthropic）。
                for tc_delta in delta.tool_calls:  # 遍历每个工具调用增量
                    idx = tc_delta.index  # 工具调用的索引位置
                    if idx not in collected_tool_calls:  # 如果这个索引还没初始化
                        collected_tool_calls[idx] = {  # 初始化这个工具调用的数据
                            "id": tc_delta.id or "",  # 工具调用ID
                            "name": "",  # 工具名称（后续会补充）
                            "arguments": "",  # 工具参数（后续会累积）
                        }
                    entry = collected_tool_calls[idx]  # 获取这个工具调用的数据
                    if tc_delta.id:  # 如果有ID
                        entry["id"] = tc_delta.id  # 更新ID
                    if tc_delta.function:  # 如果有函数信息
                        if tc_delta.function.name:  # 如果有函数名
                            entry["name"] = tc_delta.function.name  # 更新函数名
                        if tc_delta.function.arguments:  # 如果有参数增量
                            entry["arguments"] += (
                                tc_delta.function.arguments
                            )  # 累积参数字符串
# 因为 OpenAI 的流式格式对这三个字段的处理方式不同：
# 第一个 chunk（引入新工具调用时）      后续 chunk
# ─────────────────────                ────────────────────
# {                                   {
#   index: 0,                           index: 0,
#   id: "call_abc123",      ← ✅ 完整   id: null,           ← 没有
#   function: {                         function: {
#     name: "update_section", ← ✅ 完整   name: null,         ← 没有
#     arguments: ""                      arguments: "{\"id\":"  ← 碎片！
#   }                                   }
# }                                   }
# id 和 name — 只在第一个 chunk 里出现一次，后面全是 null。所以：
# if tc_delta.id:          # 第一个 chunk: True → 赋值
#     entry["id"] = "..."
#                           # 后续 chunk: id 为 null，if 不通过 → 跳过（不覆盖）
# 实际上不存在"累加"的场景，因为根本不会收到第二次非空的 id。
# arguments — 每个 chunk 都带一小段字符，需要拼起来：
#         arguments: ""                  # chunk 1: 空的
#         arguments: "{\"id\":"          # chunk 2: 第一片
#         arguments: "1}"                # chunk 3: 第二片 → 拼接成完整的 '{"id":1}'
# 所以不是设计上"一个用 = 一个用 +="，而是数据本身的特征决定的：
# 字段	出现方式	操作
# id	只在首 chunk 出现一次，后续 null	= 覆盖一次就够了
# name	只在首 chunk 出现一次，后续 null	= 覆盖一次就够了
# arguments	跨多个 chunk 分片到达	+= 必须累加
            if chunk.usage:  # 如果这个块有使用量数据
                usage_data = {  # 更新使用量
                    "input_tokens": chunk.usage.prompt_tokens or 0,  # 输入token数
                    "output_tokens": chunk.usage.completion_tokens or 0,  # 输出token数
                }

        # 构建最终消息
        content: list[ContentBlock] = []  # 用于存放最终的消息内容块
        if collected_content:  # 如果有文本内容
            content.append(TextBlock(text=collected_content))  # 添加文本块

        for _idx in sorted(collected_tool_calls.keys()):  # 按索引顺序遍历工具调用
            tc = collected_tool_calls[_idx]  # 获取工具调用数据
            if not tc["name"]:  # 如果没有工具名（可能是不完整的调用）
                continue  # 跳过
            try:
                args = json.loads(tc["arguments"])  # 解析工具参数JSON
            except (json.JSONDecodeError, TypeError):  # 如果JSON解析失败
                args = {}  # 使用空字典
            content.append(
                ToolUseBlock(id=tc["id"], name=tc["name"], input=args)
            )  # 添加工具调用块

        final_message = ConversationMessage(
            role="assistant", content=content
        )  # 创建最终的助手消息
        if collected_reasoning:  # 如果有推理内容
            final_message._reasoning = (
                collected_reasoning  # 保存推理内容（用于调试或展示）
            )

        yield ApiMessageCompleteEvent(  # 产出消息完成事件
            message=final_message,  # 完整的助手消息
            usage=UsageSnapshot(  # 使用量快照
                input_tokens=usage_data.get("input_tokens", 0),  # 输入token数
                output_tokens=usage_data.get("output_tokens", 0),  # 输出token数
            ),
            stop_reason=finish_reason,  # 停止原因
        )

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        """检查是否可重试。"""
        status = getattr(exc, "status_code", None)  # 获取HTTP状态码
        if status and status in {429, 500, 502, 503}:  # 如果是可重试的状态码
            return True  # 可以重试
        if isinstance(
            exc, (ConnectionError, TimeoutError, OSError)
        ):  # 如果是网络连接类错误
            return True  # 可以重试
        return False  # 其他错误不重试

    @staticmethod
    def _translate_error(exc: Exception) -> ChirenApiError:
        """转换错误为自定义错误。"""
        status = getattr(exc, "status_code", None)  # 获取HTTP状态码
        msg = str(exc)  # 获取错误消息
        if status == 401 or status == 403:  # 如果是认证错误（未授权或禁止访问）
            return AuthenticationFailure(msg)  # 转换为认证失败错误
        if status == 429:  # 如果是速率限制错误
            return RateLimitFailure(msg)  # 转换为速率限制错误
        return RequestFailure(msg)  # 其他错误转为通用请求失败错误
