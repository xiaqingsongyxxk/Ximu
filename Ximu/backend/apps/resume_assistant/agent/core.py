"""Agent核心循环控制模块。

本模块定义了AgentCore类，负责AI Agent的核心循环逻辑：
1. 调用LLM获取响应
2. 处理工具调用
3. 管理迭代状态
4. 生成各种事件

这是纯函数循环控制，不直接进行I/O操作。
"""  # 模块文档字符串

import json  # 导入JSON模块
import logging  # 导入日志模块
from collections.abc import (  # 导入异步迭代器和可调用类型
    AsyncIterator,
    Awaitable,
    Callable,
)
from typing import Any  # 导入Any类型

from apps.resume_assistant.agent.compact import (  # 导入消息压缩函数
    auto_compact_if_needed,
)
from apps.resume_assistant.agent.context import QueryContext  # 查询上下文
from apps.resume_assistant.agent.events import (  # Agent事件类型
    AgentEvent,
    AssistantMessageEvent,
    DoneEvent,
    ErrorEvent,
    InternalEvent,
    MessagesCompactedEvent,
    NextEvent,
    ToolResultEvent,
    ToolResultMessageEvent,
    ToolUseEvent,
)
from apps.resume_assistant.agent.formatters import (  # 流式格式化器
    StreamingFormatter,
)
from apps.resume_assistant.agent.state import IterationState  # 迭代状态
from shared.api.client import (  # LLM客户端事件类型
    ApiMessageCompleteEvent,
    ApiMessageRequest,
    ApiTextDeltaEvent,
)
from shared.types.messages import (  # 消息类型
    ToolResultBlock,
    ToolUseBlock,
)

log = logging.getLogger(__name__)  # 创建日志记录器

# 工具执行器类型定义
ToolExecutor = Callable[
    [ToolUseBlock, list[dict[str, Any]], QueryContext],
    Awaitable[tuple[ToolResultEvent, ToolResultBlock, dict | None]],
]


async def make_current_resume_info(sections: list[dict[str, Any]]) -> str:
    """生成当前简历信息的JSON字符串（用于缓存键）。"""

    def json_serializer(obj: Any) -> Any:  # 自定义JSON序列化器，处理特殊类型
        if hasattr(obj, "isoformat"):  # 如果是日期时间对象
            return obj.isoformat()  # 转成ISO格式字符串
        if hasattr(obj, "model_dump"):  # 如果是Pydantic模型
            return obj.model_dump()  # 转成字典
        if hasattr(obj, "__dict__"):  # 如果是普通对象
            return obj.__dict__  # 转成字典
# Event	                              __dict__
# ToolUseEvent(name="update", ...)	{"name":"update", "id":"xxx", "input":{...}}
# TextDeltaEvent(text="你好")	{"text":"你好"}
# NextEvent()	{}
# DoneEvent()	{}
        # 如果有一个对象 user.name = "Alice", user.age = 25，那么 user.__dict__ 就是 {"name": "Alice", "age": 25}
        raise TypeError(
            f"Object of type {type(obj)} is not JSON serializable"
        )  # 无法序列化，抛出错误

    return json.dumps(
        sections, ensure_ascii=False, default=json_serializer
    )  # 把板块列表转成JSON字符串


async def insert_resume_info(messages: list, resume_info: str, count: int) -> list:
    """在最后一条用户消息中注入简历信息。"""
    from shared.types.messages import ConversationMessage, ToolResultBlock

    if not messages:  # 如果消息列表为空
        return messages  # 直接返回

    last_msg = messages[-1]  # 获取最后一条消息

    if count == 1 and last_msg.role == "user":  # 第一轮对话：在用户消息前插入简历信息
        return [
            *messages[:-1],  # 保留除最后一条外的所有消息
            ConversationMessage.from_user_text(
                f"Current Resume Information: \n---\n{resume_info}\n---"
            ),  # 插入简历信息
            messages[-1],  # 最后一条用户消息
        ]
    elif (
        count != 1
        and last_msg.role == "user"
        and last_msg.content
        and isinstance(last_msg.content[-1], ToolResultBlock)
    ):
        # 后续轮次：更新工具结果中的简历信息
        last_block = last_msg.content[-1]  # 获取最后一个消息块（工具结果）
        new_block = last_block.model_copy(
            update={
                "content": json.dumps(
                    {"content": last_block.content, "resume_info": resume_info},
                    ensure_ascii=False,
                )
            }  # 把工具结果和简历信息合并
        )
        new_last = last_msg.model_copy(
            update={"content": [*last_msg.content[:-1], new_block]}
        )  # 替换最后一个消息块
        return [*messages[:-1], new_last]  # 返回更新后的消息列表

    return messages  # 其他情况直接返回
# 1. 第一轮对话（count == 1）
# if count == 1 and last_msg.role == "user":
#     # 在用户消息前插入简历信息
#     return [
#         *messages[:-1],
#         ConversationMessage.from_user_text(
#             f"Current Resume Information: \n---\n{resume_info}\n---"
#         ),
#         messages[-1],
#     ]
# 为什么？ 让 LLM 知道当前简历的内容，才能根据用户的要求修改。
# ┌─────────────────────────────────────┐
# │ system prompt                       │
# │ ...                                 │
# ├─────────────────────────────────────┤
# │ user: "Current Resume Information:  │
# │   ---                               │
# │   {简历JSON}                        │
# │   ---"                              │
# │                                     │
# │ user: "帮我修改姓名"                 │  ← 用户实际请求
# ├─────────────────────────────────────┤
# │ assistant: 使用 update_section 工具  │
# └─────────────────────────────────────┘
# ---
# 2. 后续轮次（count != 1）
# # 工具结果中注入简历信息
# new_block = last_block.model_copy(
#     update={
#         "content": json.dumps(
#             {"content": last_block.content, "resume_info": resume_info}
#         )
#     }
# )
# 为什么？ 工具执行后，简历内容可能已经变化。LLM 需要看到最新的简历才能决定下一步操作。
# ┌─────────────────────────────────────┐
# │ assistant: "使用 update_section..." │
# ├─────────────────────────────────────┤
# │ user (tool_result):                 │
# │   content: "Successfully updated"   │
# │   resume_info: {最新的简历JSON}      │  ← 包含更新后的简历
# ├─────────────────────────────────────┤
# │ assistant: 知道下一步该做什么        │
# └─────────────────────────────────────┘
# ---
# 本质
# LLM 没有持久记忆，每次调用都是无状态的。所以必须：
# 注入内容
# 简历信息 + 用户请求
# 最新简历信息
# 核心：让 LLM 始终看到简历的最新状态，才能做出正确的决策。

BuildSectionsPromptFn = Callable[
    [list[dict[str, Any]]], str
]  # 构建板块提示词的函数类型


class AgentCore:
    """Agent核心循环控制类。

    负责执行AI Agent的主循环：调用LLM → 处理工具调用 → 继续循环。
    """

    def __init__(self, context: QueryContext, tool_executor: ToolExecutor):
        """初始化Agent核心。

        Args:
            context: 查询上下文。
            tool_executor: 工具执行器函数。
        """
        self.context = context  # 查询上下文，包含LLM客户端、工具注册表等配置
        self.tool_executor = tool_executor  # 工具执行器函数，后续用于执行工具调用

    async def run(
        self,
        initial_state: IterationState,  # 初始迭代状态
        sections: list[dict[str, Any]],  # 简历板块列表
        system_template: str,  # 系统提示词模板
        system_suffix: str | None,  # 系统提示词后缀（包含JD信息）
        build_sections_prompt_fn: BuildSectionsPromptFn,  # 构建板块提示词的函数
    ) -> AsyncIterator[AgentEvent | InternalEvent]:
        """运行Agent主循环。

        Args:
            initial_state: 初始迭代状态。
            sections: 简历板块列表。
            system_template: 系统提示词模板。
            system_suffix: 系统提示词后缀（包含JD信息）。
            build_sections_prompt_fn: 构建板块提示词的函数。

        Yields:
            各类事件（NextEvent、TextDeltaEvent、ToolUseEvent等）。
        """
        state = initial_state  # 当前迭代状态
        formatter = StreamingFormatter()  # 创建流式格式化器，用于把LLM输出转成事件

        while (
            state.count < self.context.max_iterations
        ):  # 主循环，最多执行max_iterations次
            state.count += 1  # 迭代次数加1
            formatter.reset()  # 重置格式化器状态

            resume_info = await make_current_resume_info(
                sections
            )  # 生成当前简历的JSON信息
# 是的，改了。而且不需要等到"下一轮"，工具执行完回到 while 循环时，sections 已经变了。
# 看完整链路：
# # core.py:368-372
# if complete_event.message.tool_uses:
#     async for event in self._handle_tool_calls(
#         complete_event.message.tool_uses, state, sections
#     ):
#         yield event
# _handle_tool_calls 里：
# # core.py:404-421
# for tool_use in tool_use_blocks:
#     (tool_result_event, tool_result_block, _) = await self.tool_executor(
#         tool_use,
#         sections,    # ← 传进去
#         self.context,
#     )
#     # ↑ tool_executor 内部调用了 UpdateSectionTool.execute()
#     #   UpdateSectionTool.execute() 里改了 content["items"] = ...
#     #   这个 content 是 sections[i]["content"]，same reference
    
#     yield tool_result_event
#     tool_results.append(tool_result_block)
# 回到 run() 的 while 循环头：
# # core.py:220
# while state.count < self.context.max_iterations:
#     # ★ 下一轮循环，直接读 sections
#     resume_info = await make_current_resume_info(sections)
#     #                              ↑ sections 已经包含了刚才改的内容
#     if resume_info != state._cached_resume_info:
#         # 发现变化了 → 重建 system 和 tools_schema
#         sections_prompt = build_sections_prompt_fn(sections)
#         state.system = system_template.format(sections=sections_prompt)
#         state.tools_schema = self.context.tool_registry.to_api_schema_v2(sections)
# 改动路径
# core.run() 里 sections 变量 (list[dict])
#     │
#     ├──→ _handle_tool_calls(sections)
#     │       │
#     │       └──→ tool_executor(tool_use, sections, context)
#     │               │
#     │               └──→ ToolExecutionContext(sections=sections)
#     │                       │
#     │                       └──→ UpdateSectionTool.execute(arguments, context)
#     │                               │
#     │                               └── content["items"] = _assign_ids(...)
#     │                                   ↑ 改的就是 sections[i]["content"]
#     │
#     ├──→ resume_info = make_current_resume_info(sections)  ← 已变了
#     │
#     └──→ build_sections_prompt_fn(sections)                ← 已变了
# 从头到尾只有一个 sections 列表。 工具执行时通过 ToolExecutionContext.sections 拿到它，修改它。回到 while 循环头时，sections 已经被改了，make_current_resume_info 读到的是最新数据。
            if resume_info != state._cached_resume_info:  # 如果简历内容有变化
                state._cached_resume_info = resume_info  # 更新缓存
# 因为这两样东西里都硬编码了当前简历的快照，简历变了它们就过期了。
# 1. system（系统提示词）里包含板块列表
# # prompt.py:31-38
# build_sections_prompt(sections) → 
#   - [personal_info] "个人信息" (section_id: xxx-0001)
#   - [work_experience] "工作经历" (section_id: xxx-0002)
# 然后拼进系统提示词：
# # SYSTEM 模板 (prompt.py:188)
# # The resume currently contains the following sections
# {sections}
# 如果新加了一个 skills 板块但不更新 system，LLM 还以为只有两个板块，后续让它操作"技能板块"它都不知道在说谁。
# 2. tools_schema（工具定义）里依赖板块状态
# - update_section 的描述需要知道当前有哪些板块、每个板块有哪些字段
# - add_section 的描述需要排除已存在的类型，否则 LLM 会重复添加
# 举例：不加这个 check 会怎样
# 步骤	LLM 看到的 system	LLM 看到的 tools	结果
# 用户说"加个技能板块"	有 [personal_info, work_experience]	add_section 可用: [skills, ...]	✅ 正确调用 add_section
# → 工具执行完，sections 已变更	还显示旧的	还显示skills可用	❌ LLM 不知道skills已存在，可能再调一次
# 这个 if 就是为了保证每次给 LLM 发送请求前，它看到的简历状态和工具描述都是最新的。
                sections_prompt = build_sections_prompt_fn(
                    sections
                )  # 构建板块列表的提示词文本
                system = system_template.format(
                    sections=sections_prompt
                )  # 把板块信息填入系统提示词模板
                if system_suffix:  # 如果有后缀（JD信息）
                    system += system_suffix  # 追加到系统提示词末尾

                state.system = system  # 更新系统提示词
                state.tools_schema = self.context.tool_registry.to_api_schema_v2(
                    sections
                )  # 更新工具定义（包含板块信息）
#   简历数据 (sections)
#     ↓
# # to_api_schema_v2(sections)  ← 用 sections 生成工具描述
# #     ↓
# # 工具描述中包含：
# #   - 个人信息: 姓名, 手机, 邮箱
# #   - 教育背景: 学校, 学历, 时间
# #   - 项目经验: 项目名, 角色, 描述
# #     ↓
# # LLM 知道可以操作哪些字段
# # 本质：把"简历有什么板块"的信息，注入到"工具的说明"里，让 LLM 知道怎么用工具修改简历。

#             # 自动压缩消息（如果token数接近上下文窗口限制）
# 简单对比
# 1. tool_registry（原始工具）
# → 里面保存着工具的"代码"（能执行操作）
# tool_registry = {
#     "update_section": UpdateSectionTool(),  # 可以更新数据库
#     "add_section": AddSectionTool(),        # 可以添加板块
# }
# # 2. to_api_schema_v2(sections)（给 AI 看的说明书）
# # → 把工具变成"文字描述"，告诉 AI 这个工具怎么用
# {
#     "name": "update_section",
#     "description": "更新板块内容，需要 section_id",
#     "input_schema": {...}
# }
# 本质区别
#  	tool_registry
# 给谁看	后端代码
# 形式	可执行的代码
# 作用	真正执行操作
# 为什么要转换
# AI 只能读文字，不能执行代码。
# # AI 看到的：
# "你可以用 update_section 工具，它需要 section_id 参数"
# # AI 没看到的（后端悄悄做）：
# tool_registry.get("update_section").execute(...)  # 实际修改数据库
# 转换过程：把"能执行代码的工具" → "AI 能看懂的文字描述"
# 为什么要传入 sections
# # 告诉 AI：这篇简历有哪些板块可以修改
# to_api_schema_v2(sections)
# # AI 就知道：只能修改这 3 个板块，别的不行
# 简单说：sections 参数让 AI 知道"哪些板块可以操作"。
            state.messages, was_compacted = await auto_compact_if_needed(
                state.messages,  # 当前消息列表
                api_client=self.context.api_client,  # LLM客户端
                model=self.context.model,  # 模型名称
                system_prompt=state.system,  # 系统提示词
            )
            if was_compacted:  # 如果执行了压缩
                yield MessagesCompactedEvent()  # 通知前端消息被压缩了
# 3. 这个设计的假设
# 压缩前: [A1, A2, A3, ..., A50, B1, B2, B3, B4, B5, B6, C1, C2, ...]
#          ↑_________________↑  ↑_________________↑  ↑________↑
#           被压缩成摘要          保留的最近6条        压缩后继续产生的消息
# 系统假设：
# - 最近的上下文最重要 → 保留最近 6 条 + 所有后续消息
# - 旧的上下文如果真需要 → 用户会重新提及，LLM 能从保留的消息中推断
# - 极端情况 → 用户说"之前我让你改的那个公司名还记得吗" → LLM 可能不记得了，用户需要再说一次
# 这是一个工程上的取舍： 为了在当前会话中不中断对话，牺牲了跨会话的长期记忆。如果你需要跨会话保留压缩摘要，那需要把 summary_msg 也写到 JSONL 里——但当前代码没做这件事。
            # 注入简历信息到消息中
            state.messages = await insert_resume_info(
                state.messages, resume_info, state.count
            )

            # 构建API请求
            api_request = ApiMessageRequest(
                model=self.context.model,  # 模型名称
                messages=state.messages,  # 消息列表
                system_prompt=state.system,  # 系统提示词
                tools=state.tools_schema,  # 工具定义
                max_tokens=self.context.max_tokens,  # 最大token数
                temperature=self.context.temperature,  # 温度参数
            )

            yield NextEvent()  # 通知前端开始新轮次

            # 流式调用LLM
            complete_event = None  # 用于保存LLM的完成事件
            try:
                async for api_event in self.context.api_client.stream_megssage(
                    api_request
                ):  # 流式接收LLM输出
                    if isinstance(api_event, ApiTextDeltaEvent):  # 如果是文本增量事件
                        for agent_event in formatter.format(
                            api_event
                        ):  # 用格式化器把增量转成事件
                            yield agent_event  # 产出事件给调用方
                    elif isinstance(
                        api_event, ApiMessageCompleteEvent
                    ):  # 如果是消息完成事件
                        complete_event = api_event  # 保存完成事件
            except Exception as e:  # 如果调用出错
                log.error(f"Agent loop error: {e}")  # 记录错误日志
                yield ErrorEvent(message=str(e))  # 产出错误事件
                break  # 退出循环

            if complete_event is None:  # 如果API未返回有效响应
                yield DoneEvent()  # 产出完成事件
                break  # 退出循环

            state.messages.append(
                complete_event.message
            )  # 把LLM的完整回复添加到消息历史
            yield AssistantMessageEvent(
                message=complete_event.message
            )  # 产出助手消息事件

            # 处理工具调用
            if complete_event.message.tool_uses:  # 如果LLM回复中包含工具调用
#                 没有 @property → 报错：
# # 如果 @property 去掉
# complete_event.message.tool_uses       # → <bound method>（方法对象，不是列表）
# if complete_event.message.tool_uses:   # → True（方法对象永远 truthy）
#     # 永远进入，逻辑错了
# 有 @property → 正常工作：
# # @property 在，. 触发方法执行
# complete_event.message.tool_uses       # → [ToolUseBlock, ToolUseBlock] 或 []
#                                        #    执行了 tool_uses() 里的 return 逻辑
# if complete_event.message.tool_uses:   # → bool([]) = False
#                                        # → bool([ToolUseBlock]) = True
# 完整链路：
# Python 执行到 if complete_event.message.tool_uses:
# 1. 读取 complete_event
#    → ConversationMessage 实例
# 2. 读取 .message
#    → ConversationMessage 实例
# 3. 读取 .tool_uses
#    → Python 发现 tool_uses 上有 @property
#    → 自动调用 tool_uses() 方法
#    → 执行 return [x for x in self.content if isinstance(x, ToolUseBlock)]
#    → 返回 [] 或 [ToolUseBlock, ...]
# 4. if 判断
#    → [] → falsy → 不进入
#    → [ToolUseBlock, ...] → truthy → 进入
# 普通方法 vs property：
# # 普通方法
# def tool_uses(self): ...
# complete_event.message.tool_uses()    # 要加 ()
# # @property
# @property
# def tool_uses(self): ...
# complete_event.message.tool_uses      # 不加 ()，但背后还是执行了方法
# 这行代码本质上就是在调方法，只是用了 @property 把括号藏起来了。
                async for event in self._handle_tool_calls(
                    complete_event.message.tool_uses, state, sections
                ):  # 处理所有工具调用
                    yield event  # 产出工具相关事件
                yield ToolResultMessageEvent(
                    message=state.messages[-1]
                )  # 产出工具结果消息事件

            # 检查停止条件
            if (
                complete_event.stop_reason in self.context.stop_reasons
            ):  # 如果LLM的停止原因在允许的停止原因中
                yield DoneEvent()  # 产出完成事件
                break  # 退出循环

    async def _handle_tool_calls(
        self,
        tool_use_blocks: list[ToolUseBlock],
        state: IterationState,
        sections: list[dict[str, Any]],
    ) -> AsyncIterator[AgentEvent]:
        """处理工具调用。

        Args:
            tool_use_blocks: 工具调用列表。
            state: 当前迭代状态。
            sections: 简历板块列表。

        Yields:
            工具相关事件（ToolUseEvent、ToolResultEvent）。
        """
        from shared.types.messages import ConversationMessage, ToolResultBlock

        tool_results: list[ToolResultBlock] = []  # 用于存放所有工具结果块

        for tool_use in tool_use_blocks:  # 遍历每个工具调用
            tool_id = tool_use.id  # 获取工具调用ID

            yield ToolUseEvent(
                name=tool_use.name, id=tool_id, input=tool_use.input
            )  # 通知前端：工具开始调用

            (
                tool_result_event,
                tool_result_block,
                _,
            ) = await self.tool_executor(  # 执行工具
                tool_use,
                sections,
                self.context,  # 传入工具调用、板块列表和上下文
            )

            yield tool_result_event  # 通知前端：工具执行结果
            tool_results.append(tool_result_block)  # 把工具结果块添加到列表

        if tool_results:  # 如果有工具结果
            tool_result_msg = ConversationMessage(
                role="user", content=tool_results
            )  # 把工具结果包装成用户消息（这是LLM API的要求）
            state.messages.append(
                tool_result_msg
            )  # 添加到消息历史，下一轮LLM会看到这些结果
# state.messages 是整个 Agent 循环的消息历史，每次迭代都发给 LLM。
# 看循环里的完整流程：
# while state.count < max_iterations:          # L214 每次循环
#     # 1. 压缩消息（如果太长）
#     state.messages = auto_compact_if_needed(state.messages)   # L284
#     # 2. 注入当前简历信息
#     state.messages = insert_resume_info(state.messages, ...)  # L294
#     # 3. ★★★ 发给 LLM ★★★
#     api_request = ApiMessageRequest(
#         messages=state.messages,      # ← L301：当前完整对话历史
#         system_prompt=state.system,
#         tools=state.tools_schema,
#     )
#     async for api_event in api_client.stream_megssage(api_request):  # L313
#     # 4. LLM 回复来了，添加到历史
#     state.messages.append(llm_response)                    # L334
#     # 5. 如果有工具调用，执行工具，结果也追加到历史
#     state.messages.append(tool_result_msg)                 # L402
#     # 6. 回到 while 开头 → 下一轮迭代，把更新后的 state.messages 再次发给 LLM
# 所以 state.messages 就是LLM 看到的完整对话上下文：
# state.messages = [
#   用户消息: "帮我改一下手机号",
#   LLM回复: "好的，我来...",                 ← 第1轮
#   工具结果: "已成功更新 section xxx-0001",   ← 工具执行结果
#   LLM回复: "已经帮您更新了手机号",            ← 第2轮（看到工具结果后）
#   工具结果: ...                             ← 如果有更多工具
# ]
#                 ↓
#          下一次循环 → 全部发给 LLM → LLM 知道之前发生了什么
# 没有 state.messages，LLM 就是个"健忘症"——每次调用都不知道之前说过什么。