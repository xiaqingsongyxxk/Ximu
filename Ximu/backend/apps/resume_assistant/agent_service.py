"""简历助手的Agent服务模块。

本模块是AI简历助手的核心服务层：
1. 初始化工具注册表（UpdateSectionTool、AddSectionTool、SectionInfoTool）
2. 创建Agent运行时
3. 执行Agent循环（LLM调用工具 → 更新简历 → 继续对话）
4. 通过SSE流式返回结果

Agent模式：LLM作为大脑，通过工具操作简历数据。
"""  # 模块文档字符串

import logging  # 导入日志模块
from typing import Any  # 导入Any类型

from sqlalchemy.ext.asyncio import AsyncSession  # 异步数据库会话
from sse_starlette import EventSourceResponse  # SSE响应类

from apps.resume_assistant.agent.runtime import AgentRuntime  # Agent运行时
from apps.resume_assistant.agent.state import IterationState  # 迭代状态
from apps.resume_assistant.conversation_store import ConversationStore  # 对话存储
from apps.resume_assistant.prompt import (  # 提示词
    SUB_SYSTEM,  # 子系统提示词
    SYSTEM,  # 系统提示词
    build_sections_prompt,  # 构建板块提示词的函数
)
from apps.resume_assistant.schemas import ResumeAssistantRequest  # 请求数据模型
from apps.resume_assistant.tools import (  # 工具类
    AddSectionTool,  # 添加板块工具
    SectionInfoTool,  # 查询板块信息工具
    UpdateSectionTool,  # 更新板块工具
)
from shared.api import get_client  # 获取LLM客户端
from shared.models import Resume  # 简历ORM模型
from shared.types.base_tool import ToolRegistry  # 工具注册表
from shared.types.messages import ConversationMessage  # 对话消息类型
from shared.types.resume import ResumeSectionSchema  # 简历板块类型

log = logging.getLogger(__name__)  # 创建日志记录器


async def resume_assistant_service(
    request: ResumeAssistantRequest,  # 请求参数
    resume: Resume,  # 简历ORM对象
    sections: list[ResumeSectionSchema],  # 板块列表
    db: AsyncSession,  # 数据库会话
) -> EventSourceResponse:
    """AI简历助手的核心服务函数。

    初始化Agent环境，执行对话循环，返回SSE事件流。

    Args:
        request: 请求参数（包含简历ID、用户消息、LLM配置）。
        resume: 简历ORM对象。
        sections: 简历板块列表。
        db: 数据库会话。

    Returns:
        SSE事件流响应。
    """
    # 构建板块数据
    sections_list: list[dict[str, Any]] = []  # 板块字典列表
    id_to_type: dict[str, str] = {}  # 板块ID到类型的映射

    for section in sections:  # 遍历板块
        id_to_type[section.id] = section.type  # 记录ID到类型的映射
        sections_list.append(section.model_dump())  # 转为字典

    return EventSourceResponse(
        generate_content(request, resume, sections_list, id_to_type, db)
    )


async def generate_content(
    request: ResumeAssistantRequest,
    resume: Resume,
    sections: list[dict[str, Any]],
    id_to_type: dict[str, str],
    db: AsyncSession,
):
    """生成AI响应的内容生成器。

    读取对话历史 → 注册工具 → 创建Agent运行时 → 执行对话循环。
    """
    # 读取对话历史
    store = ConversationStore()  # 创建对话存储实例
    messages: list[ConversationMessage] = store.read(request.resume_id)  # 读取历史
    messages.append(ConversationMessage.from_user_text(request.input))  # 添加用户消息

    # 创建初始状态
    initial_state = IterationState(messages=messages)

    # 注册工具
    tool_registry = ToolRegistry()  # 创建工具注册表
    for tool in (UpdateSectionTool(), AddSectionTool(), SectionInfoTool()):
        tool_registry.register(tool)  # 注册每个工具

    # 创建Agent运行时
    runtime = AgentRuntime(
        db=db,  # 数据库会话
        store=store,  # 对话存储
        api_client=get_client(
            request.type, request.api_key, request.base_url
        ),  # LLM客户端
        tool_registry=tool_registry,  # 工具注册表
        model=request.model,  # 模型名称
    )

    # 执行Agent循环
    async for event in runtime.execute(  # 调用Agent运行时的execute方法，流式获取事件
        request=request,  # 请求参数（包含简历ID、用户消息等）
        initial_state=initial_state,  # 初始迭代状态（包含对话历史）
        sections=sections,  # 简历板块列表
        system_template=SYSTEM,  # 系统提示词模板
        sub_system_template=SUB_SYSTEM,  # 子系统提示词模板（包含JD信息）
        build_sections_prompt_fn=build_sections_prompt,  # 构建板块提示词的函数
        id_to_type=id_to_type,  # 板块ID到类型的映射
        resume=resume,  # 简历对象（用于获取JD等元数据）
    ):
        yield event  # 把每个事件产出给SSE客户端，前端会实时接收到这些事件
