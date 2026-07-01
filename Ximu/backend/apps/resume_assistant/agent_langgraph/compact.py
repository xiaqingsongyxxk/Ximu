# 对话历史压缩模块（LangGraph 版）。

# 对应手写版: agent/compact.py

# 功能完全相同：估算 token 数 → 超阈值 → 压缩 → 返回摘要 + 保留最近消息。
# 不同点：
# - 手写版: 自己估算 token，手动调用 LLM 生成摘要
# - LangGraph 版: 用 langchain_core.messages.trim_messages + LangChain 的 LLM 调用

# 但注入给 LLM 的提示词、保留策略、返回格式与手写版保持一致。


# 导入 logging，记录压缩过程的日志（方便排查压缩相关的问题）
import logging  # 导入 logging 模块

# 导入 re，用正则表达式从 LLM 返回的摘要文本中提取 <summary> 标签内容
import re  # 导入 re 模块
from typing import Any  # 导入 Any 类型，用于 LLM 参数类型标注

# LangChain 的消息类型，用于直接调用 LLM（替代手写版 SupportsStreamingMessages）
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)  # 导入 LangChain 消息类型（替代手写的 ApiMessageRequest）

# ConversationMessage：手写版定义的消息类型，LangGraph 版复用
from shared.types.messages import (
    ConversationMessage,
    TextBlock,
)  # 从 shared.types.messages 导入 ConversationMessage

# log 记录压缩日志
log = logging.getLogger(__name__)  # 将 logging.getLogger(__name__) 赋值给 log

# TOKEN_ESTIMATION_PADDING：估算 token 时的膨胀系数
# 中文占的 token 估算不太准，乘 4/3 留一些余量
TOKEN_ESTIMATION_PADDING = 4 / 3  # 将 4 / 3 赋值给 TOKEN_ESTIMATION_PADDING
# MAX_OUTPUT_TOKENS_FOR_SUMMARY：压缩时允许 LLM 输出的最大 token 数
# 摘要最多用 20000 个 token 来写
MAX_OUTPUT_TOKENS_FOR_SUMMARY = 20_000  # 将 20_000 赋值给 MAX_OUTPUT_TOKENS_FOR_SUMMARY
# AUTOCOMPACT_BUFFER_TOKENS：自动压缩的缓冲余量
# 如果对话接近上下文窗口上限，提前 13000 个 token 就触发压缩
AUTOCOMPACT_BUFFER_TOKENS = 13_000  # 将 13_000 赋值给 AUTOCOMPACT_BUFFER_TOKENS


def estimate_tokens(text: str) -> int:  # 定义函数 estimate_tokens
    # 根据字符长度估算 token 数。

    # 这个估算结果用于 should_autocompact() 判断是否需要压缩。
    # 手写版和 LangGraph 版用同样的估算方法。

    if not text:  # 如果传入的文本是空的（比如 None 或 ""）
        return 0  # 直接返回 0 个 token，因为空文本不占空间
    return max(
        1, (len(text) + 3) // 4
    )  # 粗略估算：每 4 个字符 ≈ 1 个 token，最少算 1 个


def estimate_message_tokens(
    messages: list[ConversationMessage],
) -> int:  # 定义函数 estimate_message_tokens
    # 估算对话消息的总 token 数。

    # 遍历每条消息的每个内容块，累加 token 估算值。
    # 返回值给 should_autocompact() 用，告诉它"对话有多长了，需不需要压缩"。
    # 手写版和 LangGraph 版用同样的方法。

    total = 0  # 初始化总数，从 0 开始累加
    for msg in messages:  # 遍历每条消息
        for block in (
            msg.content
        ):  # 遍历每条消息里的每个内容块（一条消息可能同时有文字和工具调用）
            from shared.types.messages import TextBlock, ToolResultBlock, ToolUseBlock

            if isinstance(block, TextBlock):  # 如果当前块是"文本块"（纯文字）
                total += estimate_tokens(block.text)  # 累加文本的 token 估算值
            elif isinstance(
                block, ToolResultBlock
            ):  # 如果是"工具结果块"（比如 update_section 返回的结果）
                total += estimate_tokens(block.content)  # 累加工具返回结果的 token 数
            elif isinstance(
                block, ToolUseBlock
            ):  # 如果是"工具调用块"（AI 决定调什么工具）
                total += estimate_tokens(  # 将 estimate_tokens( 赋值给 total +
                    block.name
                )  # 累加工具名称的 token（比如 "update_section"）
                total += estimate_tokens(  # 将 estimate_tokens( 赋值给 total +
                    str(block.input)
                )  # 累加工具参数的 token（传给工具的 JSON 参数）
    return int(
        total * TOKEN_ESTIMATION_PADDING
    )  # 乘 4/3 膨胀系数（中文估算不准，留余量）+ 取整为整数


def get_autocompact_threshold() -> int:  # 定义函数 get_autocompact_threshold
    # 计算自动压缩的 token 阈值。

    # 计算公式：上下文窗口 - 保留给输出的空间 - 缓冲余量
    # 这个阈值传给 should_autocompact()，用来判断"现在对话够不够长，需不需要压缩"。

    context_window = 128_000  # 模型的上下文窗口大小（Claude 默认 128K，类似"脑子能记住的最大信息量"）
    reserved = min(  # 将 min( 赋值给 reserved
        MAX_OUTPUT_TOKENS_FOR_SUMMARY, 20_000
    )  # 预留 20000 个 token 给 LLM 写摘要用（不能把窗口全占满）
    effective = context_window - reserved  # 实际可用空间 = 总窗口 - 摘要预留
    return (
        effective - AUTOCOMPACT_BUFFER_TOKENS
    )  # 再减 13000 缓冲 = 真正的压缩触发线（到了这条线就开始压缩）


def should_autocompact(
    messages: list[ConversationMessage],
) -> bool:  # 定义函数 should_autocompact
    # 判断对话是否需要自动压缩。

    # 由 prepare 节点调用。如果超过阈值 → 执行压缩。
    # 手写版和 LangGraph 版用同样的判断逻辑。
    # 这就好比"房间东西太多了，该收拾了"的判断。

    token_count = (
        estimate_message_tokens(  # 将 estimate_message_tokens( 赋值给 token_count
            messages
        )
    )  # 算一下当前对话有多少 token（类似"量一下房间满了多少"）
    threshold = get_autocompact_threshold()  # 获取阈值（类似"房间的容量上限"）
    return token_count >= threshold  # 如果当前量 >= 上限 → 需要压缩（返回 True）


def get_compact_prompt(
    custom_instructions: str | None = None,
) -> str:  # 定义函数 get_compact_prompt
    # 构建发送给模型的完整压缩提示词。

    # 这个提示词告诉 LLM："把前面的对话浓缩成一段摘要，保留所有重要信息"。
    # 返回值传给 compact_conversation() 中的 LLM 调用，LLM 根据这个提示词来写摘要。

    prompt = (  # 将 ( 赋值给 prompt
        NO_TOOLS_PREAMBLE + BASE_COMPACT_PROMPT
    )  # 把"不要调用工具"的开头 + "请写摘要"的正文拼在一起
    if (
        custom_instructions and custom_instructions.strip()
    ):  # 如果调用方传了额外的自定义指令（比如"重点关注技术细节"）
        prompt += f"\n\nAdditional Instructions:\n{custom_instructions}"  # 把自定义指令附加到提示词末尾
    prompt += NO_TOOLS_TRAILER  # 再追加一句"最后提醒：别调用工具"的结尾
    return prompt  # 返回拼好的完整压缩提示词，后面发给 LLM


def format_compact_summary(raw_summary: str) -> str:  # 定义函数 format_compact_summary
    # 提取摘要内容（去除分析草稿）。

    # LLM 返回的文本通常包含 <analysis>（分析过程）和 <summary>（最终摘要）。
    # 这个函数只提取 <summary> 标签里的内容，把 LLM 的思考过程扔掉。
    # 返回值给 build_compact_summary_message() 用，最终插入到对话中。

    text = re.sub(  # 将 re.sub( 赋值给 text
        r"<analysis>[\s\S]*?</analysis>", "", raw_summary
    )  # 用正则删掉 <analysis>...</analysis> 之间的所有内容（LLM 的分析草稿，不需要保留）
    m = re.search(  # 将 re.search( 赋值给 m
        r"<summary>([\s\S]*?)</summary>", text
    )  # 在剩下的文本中找 <summary>...</summary> 标签，提取里面的摘要内容
    if m:  # 如果找到了 <summary> 标签
        text = text.replace(  # 将 text.replace( 赋值给 text
            m.group(0), f"Summary:\n{m.group(1).strip()}"
        )  # 把 <summary>...</summary> 替换成 "Summary:\n摘要内容" 的格式
    text = re.sub(  # 将 re.sub( 赋值给 text
        r"\n\n+", "\n\n", text
    )  # 把连续多个空行替换成两个空行（让排版更整洁）
    return text.strip()  # 去掉开头和结尾的空格/空行，返回干净的摘要文本


def build_compact_summary_message(  # 定义函数 build_compact_summary_message
    summary: str,  # LLM 生成的原始摘要文本（可能带 <analysis> 标签）
    *,  # 星号表示后面的参数只能通过名字传（禁止按位置传），防止传错
    suppress_follow_up: bool = False,  # 是否禁止 AI 追问（True = 让 AI 直接继续干活，别问用户问题）
    recent_preserved: bool = False,  # 是否保留了最近的 N 条消息（True = 有些消息没被压缩，原样保留着）
) -> str:
    # 构建用于替换压缩历史的用户消息。

    # 压缩后的摘要包装成一条"用户消息"的形式，插入到对话中。
    # 这样 AI 看到这条消息就会知道"之前的对话已经被压缩成摘要了"。
    # 返回值作为一个 ConversationMessage 的文本内容，塞回 messages 列表里。

    formatted = format_compact_summary(  # 将 format_compact_summary( 赋值给 formatted
        summary
    )  # 调用上面的格式化函数，把原始摘要中的 <analysis> 去掉，只留 <summary> 里的内容
    text = (  # 拼接完整的提示文本
        "This session is being continued from a previous conversation that ran "  # "这个会话是从之前一段对话继续的"
        "out of context. The summary below covers the earlier portion of the "  # "之前的对话超长了，下面是前面部分的摘要"
        "conversation.\n\n"  # 空一行，再接摘要内容
        f"{formatted}"  # 把格式化后的摘要内容拼进来
    )
    if recent_preserved:  # 如果最近的消息保留了一部分没压缩
        text += "\n\nRecent messages are preserved verbatim."  # 加一句"最近的消息原样保留了"
    if suppress_follow_up:  # 如果设置了"禁止 AI 追问"
        text += (  # 追加一段"别废话"的指令
            "\nContinue the conversation from where it left off without asking "  # "从刚才停下的地方继续，别问用户问题"
            "the user any further questions. Resume directly — do not acknowledge "  # "直接继续，不要提'我继续了'"
            "the summary, do not recap what was happening, do not preface with "
            '"I\'ll continue" or similar. Pick up the last task as if the break '
            "never happened."  # 告诉 AI 不要废话，直接继续干活
        )
    return text  # 返回拼好的完整文本，后面包装成 ConversationMessage 插入对话


async def compact_conversation(  # 定义异步函数 compact_conversation
    messages: list[ConversationMessage],
    *,
    llm: Any,  # LangChain LLM 实例
    system_prompt: str = "",  # 系统提示词
    preserve_recent: int = 6,  # 保留最近的多少条消息
    custom_instructions: str | None = None,  # 自定义压缩指令
    suppress_follow_up: bool = True,  # 禁止 AI 追问
) -> list[ConversationMessage]:
    # 压缩对话历史，生成摘要并保留最近消息。

    # 与手写版 agent/compact.py compact_conversation() 完全相同的行为。
    # 返回值是压缩后的消息列表（摘要 + 最近 N 条），传给 prepare 节点继续用。

    # 如果消息数量不超过保留数量，不需要压缩
    if (
        len(messages) <= preserve_recent
    ):  # 如果总消息数 <= 要保留的条数（比如总共才 5 条，要保留 6 条）
        return list(messages)  # 直接返回原始消息的副本，不用压缩

    # 记录压缩前的 token 数（用于日志对比）
    pre_compact_tokens = estimate_message_tokens(  # 将 estimate_message_tokens( 赋值给 pre_compact_tokens
        messages
    )  # 算一下压缩前有多少 token，后面和压缩后对比
    log.info(  # 打印一条日志，记录"开始压缩"
        "Compacting conversation: %d messages, ~%d tokens",  # 日志格式："正在压缩：X 条消息，约 Y 个 token"
        len(messages),
        pre_compact_tokens,
    )

    # 分成两部分：older（要压缩的）+ newer（保留的）
    older = messages[:-preserve_recent]  # 从开头到倒数第 N 条 → 这些旧消息要压缩成摘要
    newer = messages[-preserve_recent:]  # 倒数 N 条到末尾 → 这些新消息原样保留

    # 构建压缩用的提示词和消息列表
    compact_prompt = get_compact_prompt(custom_instructions)  # 生成"请压缩"的提示词
    compact_messages = list(older) + [  # 把旧消息 + 压缩指令拼在一起
        ConversationMessage.from_user_text(
            compact_prompt
        )  # 把"请压缩"的指令包装成一条用户消息，追加到旧消息后面
    ]  # 这个组合发给 LLM，LLM 看了旧消息后按指令写摘要

    # 将 ConversationMessage 转为 LangChain 消息，调用 LLM 生成摘要
    lc_messages: list = [  # 构建 LangChain 消息列表
        SystemMessage(
            content=system_prompt or "You are a conversation summarizer."
        )  # 系统提示词，没传就用默认的"你是一个对话摘要师"
    ]
    for msg in compact_messages:  # 遍历要压缩的消息
        text = "".join(  # 提取所有文本块拼接成纯文本
            b.text for b in msg.content if isinstance(b, TextBlock)
        )
        if msg.role == "user":  # 用户消息
            lc_messages.append(HumanMessage(content=text))
        elif msg.role == "assistant":  # AI 消息
            lc_messages.append(AIMessage(content=text))

    summary_text = ""  # 初始化摘要文本为空字符串
    try:  # 尝试调用 LLM
        response = await llm.ainvoke(lc_messages)  # 用 LangChain LLM 一次调用生成摘要
        summary_text = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )  # 从响应中提取文本内容
    except Exception as e:  # 如果 LLM 调用失败
        log.error("Compact LLM call failed: %s", e)  # 记一条错误日志

    # 如果 LLM 没返回摘要，用原始消息（虽然超长了但总比丢了强）
    if not summary_text:  # 检查 LLM 是不是啥也没返回
        log.warning(
            "Compact summary was empty — returning original messages"
        )  # 记一条警告日志
        return messages  # 保底策略：返回原始消息，虽然可能超长但总比丢了好

    # 把摘要包装成一条"用户消息"，插在保留消息前面
    summary_content = build_compact_summary_message(  # 调用组装函数，把原始摘要处理成一条"用户消息"的形式
        summary_text,  # LLM 返回的原始摘要
        suppress_follow_up=suppress_follow_up,  # 按调用方的要求：是否禁止 AI 追问
        recent_preserved=len(newer)  # 将 len(newer) 赋值给 recent_preserved
        > 0,  # 如果有保留的消息，告诉组装函数"有些消息原样保留了"
    )
    summary_msg = ConversationMessage.from_user_text(  # 将 ConversationMessage.from_user_ 赋值给 summary_msg
        summary_content
    )  # 把处理好的摘要文本包装成一条正式的 ConversationMessage

    result = [summary_msg, *newer]  # 新的消息列表 = [摘要消息, ...保留的最新消息]
    post_compact_tokens = estimate_message_tokens(result)  # 算一下压缩后有多少 token
    log.info(  # 打印压缩结果的日志
        "Compaction done: %d -> %d messages, ~%d -> ~%d tokens (saved ~%d)",  # "压缩完成：X->Y 条消息，~A->~B token（省了 ~C）"
        len(messages),
        len(result),
        pre_compact_tokens,
        post_compact_tokens,
        pre_compact_tokens - post_compact_tokens,
    )
    return result  # 返回压缩后的消息列表（[摘要, 最近消息...]），给 prepare 节点继续用


async def auto_compact_if_needed(  # 定义异步函数 auto_compact_if_needed
    messages: list[ConversationMessage],
    *,
    llm: Any,  # LangChain LLM 实例
    system_prompt: str = "",  # 系统提示词
    preserve_recent: int = 6,  # 保留最近消息数
) -> tuple[list[ConversationMessage], bool]:
    # 自动压缩对话（如果需要）。

    # 与手写版完全相同的行为和签名。
    # 在 prepare 节点中调用。
    # 返回值：(压缩后的消息, 是否执行了压缩)。

    if not should_autocompact(
        messages
    ):  # 先调用判断函数，看看当前对话 token 数是否超过阈值
        return (
            messages,
            False,
        )  # 没超过阈值 → 不需要压缩，直接返回原始消息 + 标记"没压缩"

    try:  # 尝试执行压缩（可能会出错，所以要 try）
        # 执行压缩
        result = await compact_conversation(  # 将 await compact_conversation( 赋值给 result
            messages,
            llm=llm,  # 将 llm, 赋值给 llm
            system_prompt=system_prompt,  # 将 system_prompt, 赋值给 system_prompt
            preserve_recent=preserve_recent,  # 将 preserve_recent, 赋值给 preserve_recent
            suppress_follow_up=True,  # 禁止 AI 在摘要后追问（直接继续干活）
        )
        return result, True  # 返回压缩后的消息列表 + True（标记"已执行压缩"）
    except Exception as exc:  # 万一压缩过程出了啥错（比如 LLM 调用超时）
        log.error("Auto-compact failed: %s", exc)  # 记一条错误日志
        return messages, False  # 保底：返回原始消息 + False（标记"没压缩成功"）

        # ─────────────────────────────────────────────
        # 下面这些是压缩提示词的模板字符串，不逐行注释
        # 它们是发给 LLM 的指令，告诉 LLM 如何写摘要
        # ─────────────────────────────────────────────


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

NO_TOOLS_TRAILER = """\
REMINDER: Do NOT call any tools. Respond with plain text only — an <analysis> block followed by a <summary> block. Tool calls will be rejected and you will fail the task.
"""


# ---- LangChain 版本的 trim_messages 包装 ----
# 手写版压缩用 LLM 生成摘要，LangGraph 版也可以用 LangChain 的 trim_messages 直接裁剪


async def auto_compact_langchain(  # 定义异步函数 auto_compact_langchain
    messages: list,
    *,
    max_tokens: int = 100_000,  # 保留的最大 token 数
    preserve_recent: int = 6,  # 保留最近 N 条
) -> tuple[list, bool]:
    # 用 LangChain trim_messages 实现消息压缩。

    # 这是手写版 auto_compact_if_needed 的 LangGraph 替代实现。
    # 两者行为等价，但实现机制不同：
    # - 手写版: 调用 LLM 生成摘要（保留语义）
    # - LangGraph: 按 token 数截断，保留最近消息 + 系统消息（直接裁剪，更快但会丢信息）

    # 返回值：(压缩后的消息, 是否执行了压缩)。

    # 低于阈值的口算（快速判断，避免不必要的导入）
    total = sum(  # 累加所有消息的 token 数
        estimate_tokens(  # 逐条估算每条消息的 token
            m.content  # 如果是字符串，直接取内容
            if hasattr(m, "content") and isinstance(m.content, str)
            else str(m.content or "")  # 否则转成字符串再估算
        )
        for m in messages  # 遍历所有消息
    )
    threshold = max_tokens - 5000  # 阈值 = 最大上限 - 5000 的余量（提前 5000 就触发）
    if total < threshold:  # 如果当前消息总 token 还没到阈值
        return messages, False  # 不需要压缩，直接返回原始消息

    from langchain_core.messages import (
        trim_messages as lc_trim,
    )  # 导入 LangChain 的裁剪函数（延迟导入，不用就不加载）

    try:
        # LangChain 的 trim_messages 按策略裁剪消息
        trimmed = lc_trim(  # 调用 LangChain 的裁剪函数
            messages,  # 要裁剪的消息列表
            strategy="last",  # 策略："last" = 保留最靠后的（最新的）消息
            token_counter=estimate_tokens,  # 用我们自己的估算函数来算 token 数
            max_tokens=max_tokens,  # 最多保留多少 token
            start_on="human",  # 从用户消息开始保留（确保第一条是用户消息）
            end_on=("human", "tool"),  # 到用户消息或工具结果消息结束（不要断在中间）
            include_system=True,  # 保留系统提示词（system prompt 不能丢）
        )
        log.info(
            "LangChain trim: %d -> %d messages", len(messages), len(trimmed)
        )  # 记录"裁剪了多少条"
        return trimmed, True  # 返回裁剪后的消息 + 标记"已压缩"
    except Exception as exc:  # 如果裁剪过程中出了异常
        log.error("LangChain trim failed: %s", exc)  # 记一条错误日志
        return messages, False  # 保底：返回原始消息 + 标记"没压缩"
