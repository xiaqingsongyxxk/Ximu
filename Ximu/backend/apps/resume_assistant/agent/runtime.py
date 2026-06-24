"""Agent运行时模块。

本模块定义了AgentRuntime类，负责执行AI Agent的核心逻辑：
1. 创建工具执行器
2. 初始化Agent核心
3. 执行对话循环
4. 处理内部事件（持久化消息）
5. 转换为SSE事件返回给前端
"""  # 模块文档字符串

import json  # 导入JSON模块
import logging  # 导入日志模块
from collections.abc import AsyncIterator  # 导入异步迭代器类型
from typing import Any  # 导入Any类型

from pydantic import ValidationError  # 导入验证错误类
from sqlalchemy import select  # SQL查询构建器
from sqlalchemy.ext.asyncio import AsyncSession  # 异步数据库会话

from apps.resume_assistant.agent.context import QueryContext  # 查询上下文
from apps.resume_assistant.agent.core import (  # Agent核心
    AgentCore,  # Agent核心类
    BuildSectionsPromptFn,  # 构建板块提示词的函数类型
    InternalEvent,  # 内部事件类型
    ToolExecutor,  # 工具执行器类型
)
from apps.resume_assistant.agent.events import (  # Agent事件
    AgentEvent,  # Agent事件联合类型
    AssistantMessageEvent,  # 助手消息事件
    MessagesCompactedEvent,  # 消息压缩事件
    ToolResultEvent,  # 工具结果事件
    ToolResultMessageEvent,  # 工具结果消息事件
)
from apps.resume_assistant.agent.formatters import to_sse_event  # SSE事件转换函数
from apps.resume_assistant.agent.state import IterationState  # 迭代状态
from apps.resume_assistant.conversation_store import ConversationStore  # 对话存储
from apps.resume_assistant.prompt import build_jd_prompt  # JD提示词构建函数
from apps.resume_assistant.schemas import ResumeAssistantRequest  # 请求数据模型
from shared.api.client import SupportsStreamingMessages  # LLM客户端接口
from shared.models import (  # 数据库模型
    ConversationMessageRecord,  # 对话消息记录
    JobDescriptionAnalysis,  # JD分析记录
    Resume,  # 简历模型
)
from shared.types.base_tool import (  # 工具相关类型
    ToolExecutionContext,  # 工具执行上下文
    ToolRegistry,  # 工具注册表
)
from shared.types.messages import (  # 消息类型
    ConversationMessage,  # 对话消息
    ToolResultBlock,  # 工具结果块
    ToolUseBlock,  # 工具调用块
)

log = logging.getLogger(__name__)  # 创建日志记录器


def create_tool_executor(
    tool_registry: ToolRegistry,
    id_to_type: dict[str, str],
) -> ToolExecutor:
    """创建工具执行器函数。

    Args:
        tool_registry: 工具注册表。
        id_to_type: 板块ID到类型的映射。

    Returns:
        工具执行器函数。
    """

    async def tool_executor(
        tool_use: ToolUseBlock,
        sections: list[dict[str, Any]],
        context: QueryContext,
    ) -> tuple[ToolResultEvent, ToolResultBlock, dict | None]:
        """执行工具调用。

        Args:
            tool_use: 工具调用块。
            sections: 板块列表。
            context: 查询上下文。

        Returns:
            (工具结果事件, 工具结果块, 板块内容)。
        """
        tool_id = tool_use.id  # 工具调用ID
        handler = tool_registry.get(tool_use.name)  # 获取工具处理器
#         handler = tool_registry.get(tool_use.name)
# # handler = UpdateSectionTool()
        if handler is None:  # 工具不存在
            result_content = f"Unknown tool: {tool_use.name}"
            return (
                ToolResultEvent(
                    is_error=True, tool_use_id=tool_id, content=result_content
                ),
                ToolResultBlock(
                    tool_use_id=tool_id, content=result_content, is_error=True
                ),
                None,
            )

        try:
            arguments = handler.input_model.model_validate(
                tool_use.input
            )  # 用Pydantic验证工具输入参数是否符合预期格式
            # arguments	UpdateSectionToolInput(section_id="xxx", value={...})
            # tool_use.input 是 AI 返回的工具调用参数。
# 内容示例
# # AI 调用 update_section 工具时
# tool_use.input = {
#     "section_id": "xxx-0001",
#     "value": {
#         "full_name": "李四",
#         "email": "lisi@example.com"
#     }
# }	告诉工具做什么
        except ValidationError as e:  # 如果验证失败（参数格式不对）
            errors = []  # 用于存放所有验证错误
            for err in e.errors():  # 遍历每个验证错误
                field = ".".join(
                    str(loc) for loc in err["loc"]
                )  # 把错误位置拼接成字段路径
                errors.append(f"  - {field}: {err['msg']}")  # 格式化错误信息
            error_msg = "Validation failed:\n" + "\n".join(
                errors
            )  # 把所有错误拼接成一条消息
            return (
                ToolResultEvent(
                    is_error=True, tool_use_id=tool_id, content=error_msg
                ),  # 返回错误事件
                ToolResultBlock(
                    tool_use_id=tool_id, content=error_msg, is_error=True
                ),  # 返回错误块
                None,  # 没有板块内容
            )

        client = (
            context.api_client
        )  # 从上下文获取LLM客户端，后续可能用于需要LLM辅助的工具
        model_name = context.model  # 从上下文获取模型名称
# 没有直接调用 TranslateResumeTool.execute() 这个名字。
# 它在 runtime.py 里通过通用分发机制被调用：
# L88:  handler = tool_registry.get(tool_use.name)        # 按名字拿到 TranslateResumeTool 实例
# L143: tool_result = await handler.execute(arguments, ...)  # 统一调用 execute()
# 当 AI 决定调用 "translate_resume" 工具时，tool_registry.get("translate_resume") 返回注册好的 TranslateResumeTool 实例，然后走同一个 handler.execute() 入口。
# 所有工具都走这条路径，没有单独为 translate_resume 写特殊调用代码。
# 工具名
# "update_section"
# "add_section"
# "translate_resume"
# "section_info"
# L143 那一行就是所有工具的统一调用入口
        tool_result = await handler.execute(  # 调用工具的execute方法执行工具
            arguments,  # 验证后的输入参数
            ToolExecutionContext(
                sections=sections,  # 当前的板块列表
                metadata={
                    "tool_use_id": tool_use.id,  # 工具调用ID
                    "id_to_type": id_to_type,  # 板块ID到类型的映射
                    "client": client,  # LLM客户端
                    "model": model_name,  # 模型名称
                },
            ),
        )

# ---
# 抽象方法（BaseTool）
# class BaseTool(ABC):
#     @abstractmethod
#     async def execute(self, arguments, context) -> ToolResult:
#         ...  # ← 只定义接口，不实现
# 作用：强制子类必须实现 execute 方法。
# ---
# 具体实现（UpdateSectionTool）
# class UpdateSectionTool(BaseTool):
#     async def execute(self, arguments, context) -> ToolResult:
#         # 1. 验证 section_id
#         section_type = id_to_type.get(arguments.section_id)
        
#         # 2. 验证数据格式
#         model.model_validate(arguments.value)
        
#         # 3. 更新板块内容
#         content.update(arguments.value)
        
#         # 4. 保存到数据库
#         await db.commit()
        
#         # 5. 返回结果
#         return ToolResult(output="Successfully updated section xxx.")
# ---
# 为什么这样设计
# BaseTool (抽象基类)
#     ├── name
#     ├── description
#     ├── input_model
#     └── execute()  ← 只定义接口
#          ↓
#     UpdateSectionTool (具体工具)
#         └── execute()  ← 实际实现
# 目的：
# 1. 统一所有工具的接口
# 2. 强制子类实现 execute 方法
# 3. 运行时通过 handler.execute() 调用具体实现
# ---
# 总结
# BaseTool 中的 ... 不是"什么都没有"，而是抽象方法，表示"这个方法必须由子类实现"。真正执行逻辑在 UpdateSectionTool.execute() 中。
        # 获取板块内容（用于前端更新UI）
        section_content = None  # 默认没有板块内容
        if tool_use.name == "update_section":  # 如果是更新板块工具
#             核心原则
# Python 永远传引用，但效果取决于对象是否可变。
# ---
# 两种情况
# 类型	例子
# 不可变	int, str, tuple, frozenset
# 可变	list, dict, set
# ---
# 例子
# 不可变类型（str）
# name = "张三"
# def change(s):
#     s = "李四"  # 创建新对象，不影响外部
# change(name)
# print(name)  # "张三" ← 没变
# 可变类型（list）
# sections = [{"id": "abc"}]
# def change(lst):
#     lst.append({"id": "xyz"})  # 修改原对象
# change(sections)
# print(sections)  # [{"id": "abc"}, {"id": "xyz"}] ← 变了！
# 可变类型（dict）
# data = {"name": "张三"}
# def change(d):
#     d["name"] = "李四"  # 修改原对象
# change(data)
# print(data)  # {"name": "李四"} ← 变了！
# ---
# 如何判断
# 对象是否可变？
#     ├── 不可变（int, str, tuple）→ 修改不影响外部
#     └── 可变（list, dict, set）→ 修改会影响外部
# ---
# 代码中的例子
# # sections 是 list（可变）
# sections = [{"id": "abc", "content": {"姓名": "张三"}}]
# # 传给 ToolExecutionContext
# ToolExecutionContext(sections=sections)
# # handler.execute() 内部修改 sections
# content.update(arguments.value)
# # 外部 sections 也变了
# print(sections[0]["content"])  # {"姓名": "李四"} ← 受影响
            for section in sections:  # 遍历所有板块
#                 执行顺序
# # 1. 先执行工具（更新数据）
# tool_result = await handler.execute(arguments, context)
# #    ↓
# #    update_section.py: content.update(arguments.value)
# #    ↓
# #    sections 里的数据已经变了！
# # 2. 再提取板块内容（用于前端更新UI）
                if section["id"] == tool_use.input["section_id"]:  # 找到被更新的板块
                    section_content = {
                        "data": section["content"],
                        "id": section["id"],
                    }  # 提取板块内容和ID
                    break  # 找到后退出循环
        elif tool_use.name == "add_section":  # 如果是添加板块工具
            for section in sections:  # 遍历所有板块
                if (
                    section["type"] == tool_use.input["type"]
                    and section["title"] == tool_use.input["title"]
                ):  # 找到新添加的板块
                    section_content = {**section}  # 复制整个板块数据
                    break  # 找到后退出循环

        result_event = ToolResultEvent(  # 创建工具结果事件
            is_error=tool_result.is_error,  # 是否出错
            tool_use_id=tool_id,  # 工具调用ID
            content=tool_result.output,  # 工具输出内容
            section_content=section_content,  # 板块内容（用于前端更新）
        )
        result_block = ToolResultBlock(  # 创建工具结果块（用于消息历史）
            tool_use_id=tool_id,  # 工具调用ID
            content=tool_result.output,  # 工具输出内容
            is_error=tool_result.is_error,  # 是否出错
        )
# 两者的区别
# ToolResultEvent - 发送给前端的事件
# @dataclass
# class ToolResultEvent:
#     is_error: bool           # 是否出错
#     tool_use_id: str         # 工具调用 ID
#     content: str             # 结果内容
#     section_content: dict | None  # 板块内容（用于前端更新 UI）← 额外信息
# 用途：通过 SSE 发送给前端，让前端知道工具执行结果并更新 UI。
# ---
# ToolResultBlock - 保存到消息历史的数据
# class ToolResultBlock(BaseModel):
#     type: Literal["tool_result"] = "tool_result"  # 类型标识
#     tool_use_id: str     # 对应的工具调用 ID
#     content: str         # 结果内容
#     is_error: bool       # 是否出错
# 用途：添加到 state.messages，作为对话历史的一部分，供 LLM 下次读取。
        return (result_event, result_block, section_content)  # 返回事件、块和板块内容

    return tool_executor


class AgentRuntime:
    """Agent运行时类。

    负责执行AI Agent的核心逻辑。
    """

    def __init__(
        self,
        db: AsyncSession,
        store: ConversationStore,
        api_client: SupportsStreamingMessages,
        tool_registry: ToolRegistry,
        model: str,
        max_tokens: int | None = None,
        temperature: float = 1.0,
        max_iterations: int = 30,
        stop_reasons: set[str] | None = None,
    ):
        """初始化Agent运行时。

        Args:
            db: 数据库会话。
            store: 对话存储。
            api_client: LLM客户端。
            tool_registry: 工具注册表。
            model: 模型名称。
            max_tokens: 最大token数。
            temperature: 温度参数。
            max_iterations: 最大迭代次数。
            stop_reasons: 停止原因集合。
        """
        self.db = db  # 数据库会话，后续用于持久化对话消息
        self.store = store  # 对话存储，后续用于读写JSONL格式的对话历史
        self.api_client = api_client  # LLM客户端，后续用于调用AI模型
        self.tool_registry = tool_registry  # 工具注册表，后续用于查找和执行工具
        self.model = model  # 模型名称，后续用于指定调用哪个AI模型
        self.max_tokens = max_tokens  # 最大token数，控制LLM输出长度
        self.temperature = temperature  # 温度参数，控制生成的随机性（0=确定性，1=随机）
        self.max_iterations = max_iterations  # 最大迭代次数，防止Agent无限循环
        self.stop_reasons = stop_reasons or {
            "end_turn",
            "stop",
        }  # 停止原因集合，LLM返回这些原因时停止循环

    async def execute(
        self,
        request: ResumeAssistantRequest,
        initial_state: IterationState,
        sections: list[dict[str, Any]],
        system_template: str,
        sub_system_template: str | None,
        build_sections_prompt_fn: BuildSectionsPromptFn,
        id_to_type: dict[str, str],
        resume: Resume | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        """执行Agent循环。

        Args:
            request: 请求参数。
            initial_state: 初始状态。
            sections: 板块列表。
            system_template: 系统提示词模板。
            sub_system_template: 子系统提示词模板。
            build_sections_prompt_fn: 构建板块提示词的函数。
            id_to_type: 板块ID到类型的映射。
            resume: 简历对象。

        Yields:
            SSE事件字典。
        """
        # 构建系统提示词后缀（包含JD信息）
        system_suffix: str | None = None  # 初始化为空，后续如果有JD信息会填充
        if resume is not None and resume.meta_info:  # 如果简历存在且有元数据
            job_description = resume.meta_info.get(
                "job_description"
            )  # 从元数据中获取职位描述
            if job_description:  # 如果有职位描述
                parts: list[str] = [
                    sub_system_template.format(job_description=job_description)
                ]  # 用职位描述填充子系统模板
            else:  # 如果没有职位描述
                parts = []  # 空列表

            # 查询最新的JD分析结果
            result = await self.db.execute(
                select(JobDescriptionAnalysis)  # 查询JD分析表
                .where(
                    JobDescriptionAnalysis.resume_id == resume.id
                )  # 条件：属于这个简历
                .order_by(JobDescriptionAnalysis.created_at.desc())  # 按创建时间降序
                .limit(1)  # 只取最新的一条
            )
            jd_analysis = result.scalars().first()  # 获取第一条结果
            if jd_analysis is not None:  # 如果有JD分析结果
                parts.append(
                    build_jd_prompt(jd_analysis.to_pydantic(), sections)
                )  # 构建JD分析提示词并添加到parts
# 提前准备 JD 分析结果（以防需要）
#     ↓
# 发给 AI 作为上下文
#     ↓
# AI 根据用户的问题决定是否使用：
#     - 用户说"针对这个职位优化" → AI 使用 JD 分析
#     - 用户说"帮我改个错别字" → AI 不用 JD 分析
            if parts:  # 如果有内容
                system_suffix = "\n\n" + "\n\n".join(parts)  # 用双换行符拼接所有部分

        # 创建查询上下文，包含Agent运行所需的所有配置
        context = QueryContext(
            api_client=self.api_client,  # LLM客户端
            tool_registry=self.tool_registry,  # 工具注册表
            model=self.model,  # 模型名称
            max_tokens=self.max_tokens,  # 最大token数
            temperature=self.temperature,  # 温度参数
            max_iterations=self.max_iterations,  # 最大迭代次数
            stop_reasons=self.stop_reasons,  # 停止原因
            metadata={},  # 额外元数据（暂为空）
        )

        # 创建工具执行器
        tool_executor_fn = create_tool_executor(
            tool_registry=self.tool_registry,  # 传入工具注册表
            id_to_type=id_to_type,  # 传入板块ID到类型的映射
        )

        # 创建Agent核心
        core = AgentCore(
            context=context,  # 查询上下文
            tool_executor=tool_executor_fn,  # 工具执行器
        )
        pending: list[ConversationMessage] = []  # 待持久化的消息列表

        if initial_state.messages[-1].role == "user":  # 如果最后一条是用户消息
            pending.append(initial_state.messages[-1])  # 添加到待持久化列表

        try:
            async for event in core.run(  # 执行Agent核心循环
                initial_state=initial_state,  # 初始状态
                sections=sections,  # 板块列表
                system_template=system_template,  # 系统提示词模板
                system_suffix=system_suffix,  # 系统提示词后缀
                build_sections_prompt_fn=build_sections_prompt_fn,  # 构建板块提示词的函数
            ):
                if isinstance(event, InternalEvent):  # 如果是内部事件（需要持久化）
                    if isinstance(event, MessagesCompactedEvent):  # 如果是消息压缩事件
                        pending = pending[-6:]  # 只保留最近6条待持久化消息
                        self.store.write(
                            request.resume_id, initial_state.messages[:1]
                        )  # 覆盖写入对话历史（只保留第一条）
                    else:  # 其他内部事件
                        self._handle_internal_event(
                            event, request.resume_id, pending
                        )  # 处理内部事件
                elif isinstance(event, AgentEvent):  # 如果是Agent事件（需要返回给前端）
                    yield to_sse_event(event)  # 转为SSE事件格式返回

        finally:
            self.store.extend(
                request.resume_id, pending
            )  # 持久化所有待处理消息到JSONL文件
            await self.db.commit()  # 提交数据库事务，保存对话消息记录
# 完整流程
# 1. 用户打开简历编辑器
# 前端界面加载
#     ↓
# 显示简历内容（板块列表）
#     ↓
# 显示对话界面（侧边栏）
# ---
# 2. 前端加载对话历史
# // 前端代码（示例）
# const response = await fetch(`/conversation-message/list/${resumeId}`);
# const messages = await response.json();
# // messages = [
# //   { role: "user", content: "..." },
# //   { role: "assistant", content: "..." },
# //   ...
# // ]
# ---
# 3. 后端处理请求
# # conversation_message/router.py:43-56
# @router.get("/list/{conversation_id}")
# async def get_message_list(conversation_id, db):
#     stmt = (
#         select(ConversationMessageRecord)
#         .where(ConversationMessageRecord.conversation_id == conversation_id)
#         .order_by(ConversationMessageRecord.created_at)
#     )
#     result = await db.execute(stmt)
#     record_list = result.scalars().all()
#     return [record.to_pydantic() for record in record_list]
# ---
# 4. 前端渲染对话
# ┌─────────────────────────────────────────┐
# │ 简历编辑器                               │
# ├─────────────────────────────────────────┤
# │ 板块列表:                                │
# │   - 个人信息: 张三, 138xxxx              │
# │   - 教育背景: 清华大学, 硕士             │
# ├─────────────────────────────────────────┤
# │ 对话界面:                                │
# │   用户: 帮我修改姓名                     │
# │   助手: 好的，已修改为李四               │
# │   用户: 把邮箱改成 xxx@example.com       │
# │   助手: 已修改邮箱                       │
# └─────────────────────────────────────────┘
# ---
# 5. 用户发送新消息
# 用户输入: "把手机号改成 139xxxx"
#     ↓
# 前端发送 SSE 请求到后端
#     ↓
# 后端执行 Agent 循环
#     ↓
# 返回结果
#     ↓
# 前端更新对话界面
#     ↓
# 同时更新简历板块（如果工具调用成功）
# ---
# 完整流程图
# ┌─────────────────────────────────────────────────────┐
# │ 前端                                                │
# ├─────────────────────────────────────────────────────┤
# │ 1. 加载简历编辑器                                    │
# │    ↓                                                │
# │ 2. GET /conversation-message/list/{resume_id}       │
# │    ↓                                                │
# │ 3. 渲染对话历史                                     │
# │    ↓                                                │
# │ 4. 用户输入新消息                                   │
# │    ↓                                                │
# │ 5. POST /resume-assistant/query (SSE)               │
# │    ↓                                                │
# │ 6. 接收流式响应                                      │
# │    ├── TextDeltaEvent → 显示文本                    │
# │    ├── ToolUseEvent → 显示工具调用                  │
# │    ├── ToolResultEvent → 显示工具结果               │
# │    └── DoneEvent → 完成                            │
# │    ↓                                                │
# │ 7. 更新简历板块（如果有工具调用）                    │
# └─────────────────────────────────────────────────────┘
# ---
# 数据流向
# 数据库 (ConversationMessageRecord)
#     ↓ GET 请求
# 前端渲染对话历史
# 用户输入
#     ↓ POST 请求
# 后端 Agent 循环
#     ↓ SSE 响应
# 前端显示结果
#     ↓ 工具调用
# 更新简历板块
#     ↓ 保存
# 数据库 + JSONL 文件
# ---
# 总结
# 阶段	操作
# 打开编辑器	从数据库加载对话历史
# 显示对话	渲染之前的对话记录
# 发送消息	调用后端 API 执行 Agent
# 接收响应	流式显示 LLM 输出
# 工具调用	更新简历板块
# 保存结果	写入数据库 + JSONL 文件
    def _handle_internal_event(
        self,
        event: InternalEvent,  # 内部事件
        resume_id: str,  # 简历ID
        pending: list[ConversationMessage],  # 待持久化的消息列表
    ) -> None:
        """处理内部事件（持久化消息到数据库）。"""
        if isinstance(
            event, (AssistantMessageEvent, ToolResultMessageEvent)
        ):  # 如果是助手消息或工具结果消息事件
            self.db.add(  # 添加到数据库会话
                ConversationMessageRecord(
                    conversation_id=resume_id,  # 对话ID（使用简历ID）
                    role=event.message.role,  # 消息角色（assistant或user）
                    content=json.dumps(  # 消息内容转成JSON字符串
                        [
                            block.model_dump() for block in event.message.content
                        ],  # 把每个消息块转成字典
                        ensure_ascii=False,  # 确保中文正常显示
                    ),
                    reasoning=event.message._reasoning
                    if hasattr(event.message, "_reasoning")
                    else None,  # 如果有推理内容则保存
                )
            )
            # 这是为了之后用户到开==打开页面看的,不是这一次给的前端
            pending.append(event.message)  # 添加到待持久化列表，后续写入JSONL文件
