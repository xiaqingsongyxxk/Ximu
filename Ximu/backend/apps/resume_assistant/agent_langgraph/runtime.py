# Agent 运行时模块（LangGraph 版）。

# 对应手写版: agent/runtime.py (AgentRuntime)

# 手写版 AgentRuntime.execute() 负责：
# 1. 构建系统提示词（含 JD 信息）
# 2. 创建 QueryContext
# 3. 创建工具执行器
# 4. 运行 Agent 核心循环
# 5. 将内部事件持久化到 DB + JSONL
# 6. 将 Agent 事件转为 SSE

# LangGraph 版 AgentRuntime 保持完全相同的外部行为：
# - execute() 签名不变
# - 产生相同的 SSE 事件
# - 相同的 DB 持久化逻辑

# 但内部使用 StateGraph（通过 run_langgraph_stream）替代 while 循环。


import json  # 导入 json，把对话消息转成 JSON 格式存入数据库
import logging  # 导入 logging，记录运行时日志
from collections.abc import (
    AsyncIterator,
)  # 导入 AsyncIterator，execute 方法会一个一个地产出事件
from typing import Any  # 导入 Any 类型，用于不确定类型的参数

from sqlalchemy.ext.asyncio import AsyncSession  # 导入异步数据库会话

from apps.resume_assistant.agent_langgraph.core import (
    run_langgraph_stream,
)  # 导入 StateGraph 驱动的核心函数
from apps.resume_assistant.agent_langgraph.events import (  # 导入事件类型
    AgentEvent,  # 联合类型：所有 Agent 事件
    AssistantMessageEvent,  # AI 完整消息事件
    InternalEvent,  # 内部事件
    ToolResultMessageEvent,  # 工具结果消息事件
)
from apps.resume_assistant.agent_langgraph.formatters import (
    to_sse_event,
)  # 导入 SSE 转换函数
from apps.resume_assistant.conversation_store import (
    ConversationStore,
)  # 导入对话历史存储（和手写版是同一个类）
from apps.resume_assistant.prompt import build_jd_prompt  # 导入构建岗位描述提示词的函数
from apps.resume_assistant.schemas import (
    ResumeAssistantRequest,
)  # 导入请求和数据的 schema 定义
from shared.models import (
    ConversationMessageRecord,
    Resume,
)  # 导入数据库模型
from shared.types.messages import ConversationMessage  # 导入消息类型（手写版定义）

log = logging.getLogger(__name__)  # 创建日志记录器，输出时自动标明模块名


class AgentRuntime:  # Agent 运行时类（LangGraph 版）
    # Agent 运行时类（LangGraph 版）。

    # 与手写版 agent/runtime.py AgentRuntime 接口完全一致。
    # 内部使用 StateGraph（通过 run_langgraph_stream），但对外行为完全相同。

    def __init__(  # 初始化 AgentRuntime
        self,  # 实例自身
        db: AsyncSession,  # 数据库会话（SQLAlchemy 异步会话，用来读写 SQLite）
        store: ConversationStore,  # 对话历史 JSONL 存储（同时读写 JSONL 文件）
        model: str,  # AI 模型名称（比如 "claude-sonnet-4-20250514"）
        max_tokens: int | None = None,  # 最大输出 token 数（None = 不限制）
        temperature: float = 1.0,  # 温度参数（0=稳定保守，1=有创意，2=放飞）
        max_iterations: int = 30,  # 最大迭代轮数（防止 AI 无限循环调用工具）
        stop_reasons: set[str]  # 停止原因集合
        | None = None,  # 停止原因集合（LLM 返回这些原因时就结束本轮）
    ):  # 初始化方法结束
        self.db = db  # 保存数据库会话，后面存对话记录到 ConversationMessageRecord 表
        self.store = store  # 保存 JSONL 对话存储，后面写对话历史到 .jsonl 文件
        self.model = model  # 保存模型名，后面传给 LLM
        self.max_tokens = max_tokens  # 保存最大 token 数，后面构建 LLM 请求时用
        self.temperature = temperature  # 保存温度参数，后面构建 LLM 请求时用
        self.max_iterations = max_iterations  # 保存最大迭代次数
        self.stop_reasons = stop_reasons or {  # 设置停止原因集合
            "end_turn",  # OpenAI/Anthropic 的"结束本轮"信号
            "stop",  # 另一种停止信号
        }

    async def execute(  # 执行 Agent 循环，产生 SSE 事件（异步方法）
        self,  # 实例自身
        request: ResumeAssistantRequest,  # 前端发来的请求
        initial_state: Any,  # 初始状态（包含对话历史）
        sections: list[dict[str, Any]],  # 简历板块数据列表（工具函数直接修改）
        system_template: str,  # 系统提示词模板（定义 AI 的角色和行为）
        sub_system_template: str | None,  # 岗位描述子模板（如果有 JD 就拼进来）
        build_sections_prompt_fn: Any,  # 构建板块提示词的函数
        id_to_type: dict[str, str],  # 板块 ID → 类型映射表
        resume: Resume | None = None,  # 简历数据（用来获取 JD 信息）
    ) -> AsyncIterator[dict[str, str]]:  # 返回值：异步迭代器，逐条产出 SSE 事件字典
        # 执行 Agent 循环，产生 SSE 事件。

        # 内部使用 run_langgraph_stream（StateGraph），事件流与手写版完全一致。
        # execute 方法的返回值是一个异步迭代器，逐条 yield SSE 事件给前端。
        # 前端通过 EventSource 对象一条一条接收这些事件。

        system_suffix: str | None = None  # 初始化后缀为 None（后面可能拼上 JD 信息）
        if (  # 如果简历存在而且有元数据
            resume is not None
            and resume.meta_info  # 检查 resume 对象及其 meta_info 字段
        ):  # 简历的 meta_info 中有岗位描述数据
            job_description = resume.meta_info.get(  # 从 meta_info 里取出 JD 文本
                "job_description"  # meta_info 是 JSON 字段，"job_description" 是 JD 的键名
            )
            if job_description:  # 如果有 JD 文本
                parts = [  # 构建后缀的各部分
                    build_jd_prompt(job_description)  # 调用构建 JD 提示词的函数
                ]
                system_suffix = "\n\n".join(
                    parts
                )  # 用空行连接各部分，拼成完整的系统提示词后缀

        # 获取历史对话消息
        messages = list(  # 把元组转成列表
            getattr(initial_state, "messages", [])  # 从初始状态中取 messages 字段
        )  # 得到对话历史消息列表

        # 将历史消息写入 JSONL 文件（持久化备份）
        self.store.extend(  # 调用存储对象的批量追加方法
            request.resume_id,  # 简历 ID，用来定位对应的 JSONL 文件
            messages,  # 要写入的消息列表
        )

        async for (
            sse_event
        ) in run_langgraph_stream(  # 遍历 LangGraph 流式执行产生的事件
            initial_messages=messages,  # 初始消息列表
            sections=sections,  # 简历板块数据
            section_id_to_type=id_to_type,  # 板块 ID → 类型映射
            system_template=system_template,  # 系统提示词模板
            system_suffix=system_suffix,  # 系统提示词后缀（含 JD 信息）
            build_sections_prompt_fn=build_sections_prompt_fn,  # 构建板块提示词的函数
            model=self.model,  # 模型名称（llm 为 None 时自动创建）
            max_iterations=self.max_iterations,  # 最大迭代次数
            stop_reasons=self.stop_reasons,  # 停止原因集合
        ):  # 开始处理每个事件
            sse_dict = to_sse_event(sse_event)  # 把 Agent 事件转成 SSE 字典格式
            yield sse_dict  # 向外层 yield 给前端

            # 处理内部事件（持久化到数据库）
            await self._handle_internal_event(  # 调用内部事件处理器
                sse_event,
                request.resume_id,
                self.db,  # 传入事件、简历 ID、数据库会话
            )

    async def _handle_internal_event(  # 处理需要持久化的内部事件
        self,  # 实例自身
        event: AgentEvent | InternalEvent,  # 当前事件
        resume_id: str,  # 简历 ID
        db: AsyncSession,  # 数据库会话
    ):  # 返回值：无
        # 处理需要持久化的内部事件。

        # 与手写版 _handle_internal_event 完全相同。
        # AssistantMessageEvent 和 ToolResultMessageEvent 都包含 AI 生成的对话消息，
        # 这些消息需要存到 SQLite 数据库，这样下次用户继续对话时能读到历史。

        pending: list[ConversationMessage] = []  # 创建一个空列表，存放待处理的消息

        if isinstance(
            event, (AssistantMessageEvent, ToolResultMessageEvent)
        ):  # 如果是需要持久化的事件
            db.add(  # 把消息加入数据库会话
                ConversationMessageRecord(  # 创建数据库记录对象
                    resume_id=resume_id,  # 关联的简历 ID
                    role=event.message.role,  # 消息角色（user / assistant / tool）
                    content=json.dumps(  # 消息内容转 JSON 字符串
                        [
                            block.model_dump() for block in event.message.content
                        ],  # 把每个内容块转成字典
                        ensure_ascii=False,  # 保留 Unicode 字符（中文）
                    ),
                    reasoning=json.dumps(
                        getattr(event.message, "_reasoning", None)
                    )  # 推理内容转 JSON
                    if hasattr(event.message, "_reasoning")  # 如果消息有推理内容
                    else None,  # 没有推理内容就存 None
                )
            )
            pending.append(event.message)  # 把消息追加到待持久化列表

        if pending:  # 如果有待持久化的消息
            self.store.extend(resume_id, pending)  # 批量写入 JSONL 文件
            await db.flush()  # 刷新到数据库（提交但保持事务打开）
