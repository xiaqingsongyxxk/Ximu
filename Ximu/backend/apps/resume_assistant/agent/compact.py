"""对话历史压缩模块。

本模块提供对话历史的自动压缩功能：
当对话token数接近上下文窗口限制时，自动压缩历史消息为摘要。
保留最近的消息，将较早的消息压缩为摘要。

主要函数：
- auto_compact_if_needed: 自动压缩（如果需要）
- compact_conversation: 执行压缩
- estimate_message_tokens: 估算token数
"""  # 模块文档字符串

import logging  # 导入日志模块
import re  # 导入正则表达式模块

from shared.api.client import (  # LLM客户端相关类型
    ApiMessageCompleteEvent,
    ApiMessageRequest,
    SupportsStreamingMessages,
)
from shared.types.messages import (  # 消息类型
    ConversationMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)

log = logging.getLogger(__name__)  # 创建日志记录器

TOKEN_ESTIMATION_PADDING = 4 / 3  # token估算填充系数（实际token约为字符数的4/3倍）
MAX_OUTPUT_TOKENS_FOR_SUMMARY = 20_000  # 摘要生成的最大输出token数
AUTOCOMPACT_BUFFER_TOKENS = 13_000  # 自动压缩的缓冲token数


def estimate_message_tokens(messages: list[ConversationMessage]) -> int:
    """估算对话消息的总token数。

    Args:
        messages: 对话消息列表。

    Returns:
        估算的token总数（包含填充系数）。
    """
    total = 0  # 总token数
    for msg in messages:  # 遍历每条消息
        for block in msg.content:  # 遍历消息中的每个块
            if isinstance(block, TextBlock):  # 如果是文本块
                total += estimate_tokens(block.text)  # 估算文本的token数
            elif isinstance(block, ToolResultBlock):  # 如果是工具结果块
                total += estimate_tokens(block.content)  # 估算工具结果内容的token数
            elif isinstance(block, ToolUseBlock):  # 如果是工具调用块
                total += estimate_tokens(block.name)  # 估算工具名称的token数
                total += estimate_tokens(str(block.input))  # 估算工具输入参数的token数
    return int(
        total * TOKEN_ESTIMATION_PADDING
    )  # 乘以填充系数返回（实际token通常比字符估算多一些）


def estimate_tokens(text: str) -> int:
    """根据字符长度估算token数（约4字符=1 token）。"""
    if not text:  # 如果文本为空
        return 0  # 返回0
    return max(1, (len(text) + 3) // 4)  # 按4字符1 token估算，至少返回1


def get_autocompact_threshold() -> int:
    """计算自动压缩的token阈值。"""
    context_window = 128_000  # 上下文窗口大小
    reserved = min(MAX_OUTPUT_TOKENS_FOR_SUMMARY, 20_000)  # 预留的输出token
    effective = context_window - reserved  # 有效上下文大小
    return effective - AUTOCOMPACT_BUFFER_TOKENS  # 返回阈值


def should_autocompact(messages: list[ConversationMessage]) -> bool:
    """判断对话是否需要自动压缩。"""
    token_count = estimate_message_tokens(messages)  # 估算当前消息的总token数
    threshold = get_autocompact_threshold()  # 获取自动压缩的阈值
    return token_count >= threshold  # 如果token数超过阈值，返回True


async def compact_conversation(
    messages: list[ConversationMessage],
    *,
    api_client: SupportsStreamingMessages,
    model: str,
    system_prompt: str = "",
    preserve_recent: int = 6,
    custom_instructions: str | None = None,
    suppress_follow_up: bool = True,
) -> list[ConversationMessage]:
    """压缩对话历史，生成摘要并保留最近消息。

    Args:
        messages: 对话消息列表。
        api_client: LLM客户端。
        model: 模型名称。
        system_prompt: 系统提示词。
        preserve_recent: 保留的最近消息数量。
        custom_instructions: 自定义指令。
        suppress_follow_up: 是否抑制后续问题。

    Returns:
        压缩后的消息列表。
    """
    if len(messages) <= preserve_recent:  # 如果消息数量不超过要保留的数量
        return list(messages)  # 直接返回原消息列表的副本

    pre_compact_tokens = estimate_message_tokens(messages)  # 压缩前的token数
    log.info(
        "Compacting conversation: %d messages, ~%d tokens",
        len(messages),
        pre_compact_tokens,
    )  # 记录日志

    older = messages[:-preserve_recent]  # 较早的消息（需要压缩的部分）
    newer = messages[-preserve_recent:]  # 较近的消息（保留原样）

    compact_prompt = get_compact_prompt(custom_instructions)  # 获取压缩提示词
    compact_messages = list(older) + [
        ConversationMessage.from_user_text(compact_prompt)
    ]  # 把较早的消息和压缩提示词组合

    # 调用LLM生成摘要
    summary_text = ""  # 用于存放生成的摘要
    async for event in api_client.stream_message(  # 流式调用LLM
        ApiMessageRequest(
            model=model,  # 模型名称
            messages=compact_messages,  # 消息列表
            system_prompt=system_prompt
            or "You are a conversation summarizer.",  # 系统提示词
            max_tokens=MAX_OUTPUT_TOKENS_FOR_SUMMARY,  # 最大输出token数
            tools=[],  # 不使用工具
        )
    ):
        if isinstance(event, ApiMessageCompleteEvent):  # 如果是消息完成事件
            summary_text = event.message.text  # 获取摘要文本

    if not summary_text:  # 如果摘要为空
        log.warning(
            "Compact summary was empty — returning original messages"
        )  # 记录警告日志
        return messages  # 返回原始消息

    # 构建摘要消息
    summary_content = build_compact_summary_message(
        summary_text,  # 摘要文本
        suppress_follow_up=suppress_follow_up,  # 是否抑制后续问题
        recent_preserved=len(newer) > 0,  # 是否保留了最近消息
    )
    summary_msg = ConversationMessage.from_user_text(
        summary_content
    )  # 把摘要包装成用户消息
    # 所以：摘要作为 user 消息，让 LLM 知道这是"之前发生了什么"，而不是"我之前说了什么"。

    result = [summary_msg, *newer]  # 摘要 + 最近消息
    post_compact_tokens = estimate_message_tokens(result)  # 压缩后的token数
    log.info(
        "Compaction done: %d -> %d messages, ~%d -> ~%d tokens (saved ~%d)",
        len(messages),
        len(result),
        pre_compact_tokens,
        post_compact_tokens,
        pre_compact_tokens - post_compact_tokens,  # 节省的token数
    )
    return result  # 返回压缩后的消息列表


async def auto_compact_if_needed(
    messages: list[ConversationMessage],
    *,
    api_client: SupportsStreamingMessages,
    model: str,
    system_prompt: str = "",
    preserve_recent: int = 6,
) -> tuple[list[ConversationMessage], bool]:
    """自动压缩对话（如果需要）。

    Args:
        messages: 对话消息列表。
        api_client: LLM客户端。
        model: 模型名称。
        system_prompt: 系统提示词。
        preserve_recent: 保留的最近消息数量。

    Returns:
        (压缩后的消息列表, 是否执行了压缩)。
    """
    if not should_autocompact(messages):  # 如果不需要压缩
        return messages, False  # 返回原消息和False（未压缩）

    try:
        result = await compact_conversation(  # 执行压缩
            messages,  # 消息列表
            api_client=api_client,  # LLM客户端
            model=model,  # 模型名称
            system_prompt=system_prompt,  # 系统提示词
            preserve_recent=preserve_recent,  # 保留的最近消息数
            suppress_follow_up=True,  # 抑制后续问题
        )
        return result, True  # 返回压缩后的消息和True（已压缩）
    except Exception as exc:  # 如果压缩失败
        log.error("Auto-compact failed: %s", exc)  # 记录错误日志
        return messages, False  # 返回原消息和False（未压缩）


def get_compact_prompt(custom_instructions: str | None = None) -> str:
    """构建发送给模型的完整压缩提示词。"""
    prompt = NO_TOOLS_PREAMBLE + BASE_COMPACT_PROMPT  # 拼接前缀和基础提示词
    if custom_instructions and custom_instructions.strip():  # 如果有自定义指令
        prompt += (
            f"\n\nAdditional Instructions:\n{custom_instructions}"  # 追加自定义指令
        )
    prompt += NO_TOOLS_TRAILER  # 追加后缀
    return prompt  # 返回完整的压缩提示词


def format_compact_summary(raw_summary: str) -> str:
    """提取摘要内容（去除分析草稿）。"""
    text = re.sub(
        r"<analysis>[\s\S]*?</analysis>", "", raw_summary
    )  # 用正则去除<analysis>标签及其内容
    m = re.search(r"<summary>([\s\S]*?)</summary>", text)  # 查找<summary>标签
    if m:  # 如果找到了
        text = text.replace(
            m.group(0), f"Summary:\n{m.group(1).strip()}"
        )  # 替换成格式化的摘要
    text = re.sub(r"\n\n+", "\n\n", text)  # 把多个连续空行合并成一个
    return text.strip()  # 去除首尾空白后返回


def build_compact_summary_message(
    summary: str,  # 摘要文本
    *,
    suppress_follow_up: bool = False,  # 是否抑制后续问题
    recent_preserved: bool = False,  # 是否保留了最近消息
) -> str:
    """构建用于替换压缩历史的用户消息。"""
    formatted = format_compact_summary(summary)  # 格式化摘要（去除分析草稿）
    text = (
        "This session is being continued from a previous conversation that ran "
        "out of context. The summary below covers the earlier portion of the "
        "conversation.\n\n"
        f"{formatted}"  # 拼接说明文本和格式化后的摘要
    )
    if recent_preserved:  # 如果保留了最近消息
        text += "\n\nRecent messages are preserved verbatim."  # 添加说明
    if suppress_follow_up:  # 如果需要抑制后续问题
        text += (
            "\nContinue the conversation from where it left off without asking "
            "the user any further questions. Resume directly — do not acknowledge "
            "the summary, do not recap what was happening, do not preface with "
            '"I\'ll continue" or similar. Pick up the last task as if the break '
            "never happened."  # 添加抑制后续问题的指令
        )
    return text  # 返回构建好的消息


# 压缩提示词模板
NO_TOOLS_PREAMBLE = """\
CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.

- Do NOT use read_file, bash, grep, glob, edit_file, write_file, or ANY other tool.
- You already have all the context you need in the conversation above.
- Tool calls will be REJECTED and will waste your only turn — you will fail the task.
- Your entire response must be plain text: an <analysis> block followed by a <summary> block.

"""

BASE_COMPACT_PROMPT = """\
Your task is to create a detailed summary of the conversation so far. This summary will replace the earlier messages, so it must capture all important information.

First, draft your analysis inside <analysis> tags. Walk through the conversation chronologically and extract:
- Every user request and intent (explicit and implicit)
- The approach taken and technical decisions made
- Specific code, files, and configurations discussed (with paths and line numbers where available)
- All errors encountered and how they were fixed
- Any user feedback or corrections

Then, produce a structured summary inside <summary> tags with these sections:

1. **Primary Request and Intent**: All user requests in full detail, including nuances and constraints.
2. **Key Technical Concepts**: Technologies, frameworks, patterns, and conventions discussed.
3. **Files and Code Sections**: Every file examined or modified, with specific code snippets and line numbers.
4. **Errors and Fixes**: Every error encountered, its cause, and how it was resolved.
5. **Problem Solving**: Problems solved and approaches that worked vs. didn't work.
6. **All User Messages**: Non-tool-result user messages (preserve exact wording for context).
7. **Pending Tasks**: Explicitly requested work that hasn't been completed yet.
8. **Current Work**: Detailed description of the last task being worked on before compaction.
9. **Optional Next Step**: The single most logical next step, directly aligned with the user's recent request.
"""

NO_TOOLS_TRAILER = """
REMINDER: Do NOT call any tools. Respond with plain text only — an <analysis> block followed by a <summary> block. Tool calls will be rejected and you will fail the task."""
