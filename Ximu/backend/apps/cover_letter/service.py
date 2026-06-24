"""Service layer for cover letter generation.

This module provides helper utilities and coroutines to generate a cover
letter via a streaming API. It is intentionally side-effect free with respect to
persisting data.
"""  # 模块文档字符串，说明这个文件是做什么的

import json  # 导入JSON模块，用于处理JSON格式的数据

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)  # 导入异步数据库会话，用于异步操作数据库
from sse_starlette import EventSourceResponse  # 导入SSE响应类，用于实现服务器推送事件

from apps.cover_letter.prompt import (  # 导入提示词构建函数
    build_cover_letter_system_prompt,  # 构建系统提示词的函数
    build_cover_letter_user_prompt,  # 构建用户提示词的函数
)
from apps.cover_letter.schemas import CoverLetterRequest  # 导入求职信请求数据模型
from shared.api import get_client  # 导入获取API客户端的函数
from shared.api.client import (
    ApiMessageRequest,
    ApiTextDeltaEvent,
)  # 导入API请求和事件类型
from shared.types.messages import ConversationMessage  # 导入对话消息类型
from shared.types.resume import ResumeSectionSchema  # 导入简历板块数据模型


def make_see_event(event: str, data: dict[str, any]) -> dict[str, str]:
    """Create a server-sent event payload.

    Args:
        event: Event name to send to the client.
        data: Payload data to serialize as JSON.

    Returns:
        A dictionary representing a SSE event with the given name and payload.
    """
    # 创建SSE事件负载
    # event是事件名称，data是事件数据
    # json.dumps将数据转换为JSON字符串，ensure_ascii=False确保中文正常显示
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


def extract_personal_info(
    sections: list[ResumeSectionSchema],
) -> tuple[str, str, str]:
    """Extract personal information from resume sections.

    This helper scans the resume sections for a personal_info block and returns
    the name, email, and phone number if present.

    Returns:
        A tuple containing (full_name, email, phone).
    """
    # 初始化个人信息变量
    full_name = ""  # 姓名
    email = ""  # 邮箱
    phone = ""  # 电话

    # 遍历所有简历板块
    for section in sections:
        # 如果是个人信息板块且内容不为空
        if section.type == "personal_info" and section.content:
            # 如果内容是字典类型，直接使用
            if isinstance(section.content, dict):
                content_data = section.content
            else:
                # 如果内容是Pydantic模型，转换为字典
                content_data = (
                    section.content.model_dump()
                    if hasattr(section.content, "model_dump")
                    else {}
                )

            # 兼容前端驼峰命名和后端下划线命名
            # 前端使用fullName，后端使用full_name
            personal_info = content_data.get("personal_info") or content_data
            # 前端: fullName, email, phone; 后端: full_name, email, phone
            full_name = (
                personal_info.get("full_name") or personal_info.get("fullName") or ""
            )
            email = personal_info.get("email") or ""  # 获取邮箱
            phone = personal_info.get("phone") or ""  # 获取电话

    return full_name, email, phone  # 返回提取的个人信息


async def cover_letter_service(
    request: CoverLetterRequest,
    sections: list[ResumeSectionSchema],
    db: AsyncSession,
) -> EventSourceResponse:
    """Public entry point to generate a cover letter as an SSE stream."""
    # 返回SSE流式响应
    # generetor_cover_letter是生成求职信的异步生成器
    return EventSourceResponse(generetor_cover_letter(request, sections, db))


async def generetor_cover_letter(
    request: CoverLetterRequest,
    sections: list[ResumeSectionSchema],
    db: AsyncSession,
):
    """Generate a cover letter with streaming output. Do not persist results.

    This coroutine streams chunks of the generated letter to the client via
    Server-Sent Events. It handles API key validation and error reporting back
    to the client.
    """
    # 延迟导入以避免循环依赖
    from apps.config.router import _get_provider_config_from_db

    # 提取个人信息
    full_name, email, phone = extract_personal_info(sections)

    # 获取AI供应商配置
    config = await _get_provider_config_from_db(db)
    # 获取当前激活的供应商
    provider = config.providers.get(config.active)
    # 如果没有配置供应商或API密钥，返回错误
    if not provider or not provider.api_key:
        yield make_see_event(
            "error", {"message": "请先在设置中配置 AI 供应商和 API Key"}
        )
        return

    # 获取API客户端
    client = get_client(config.active, provider.api_key, provider.base_url)
    # 构建对话消息
    message = [
        ConversationMessage.from_user_text(
            build_cover_letter_user_prompt(
                sections, request.jd_description, full_name, email, phone
            )
        )
    ]

    # 构建系统提示词
    system_prompt = build_cover_letter_system_prompt(request.type, request.language)
    # 标记是否已发送文本
    sended_text = False

    try:
        # 流式调用AI生成求职信
        async for event in client.stream_message(
            ApiMessageRequest(
                model=provider.model,  # 使用的AI模型
                messages=message,  # 对话消息
                system_prompt=system_prompt,  # 系统提示词
                temperature=0.5,  # 温度参数，控制生成的随机性
            )
        ):
            # 如果是文本增量事件
            if isinstance(event, ApiTextDeltaEvent):
                # 如果是思考内容，跳过
                if event.is_think:
                    continue
                # 如果还没发送过文本，先发送text_start事件
                if not sended_text:
                    sended_text = True
                    yield make_see_event("text_start", {})
                # 发送文本增量
                yield make_see_event("text_delta", {"text": event.text})

        # 发送完成事件
        yield make_see_event("done", {})

    except Exception as e:
        # 如果发生错误，发送错误事件
        yield make_see_event("error", {"message": str(e)})
