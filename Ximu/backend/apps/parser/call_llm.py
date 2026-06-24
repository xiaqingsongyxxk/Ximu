"""简历解析的LLM调用模块。

本模块负责调用大语言模型（LLM）解析简历文本，
将非结构化的PDF文本内容转换为结构化的简历数据。
"""  # 模块文档字符串

import json  # 导入JSON模块

import json_repair  # 导入JSON修复模块（LLM返回的JSON可能不完整）
from pydantic import ValidationError  # 导入Pydantic验证错误类

from apps.parser.prompt import CONTENT, SYSTEM  # 从apps/parser/prompt.py导入提示词模板
from apps.parser.schemas import ParserResult  # 从apps/parser/schemas.py导入解析结果模型
from shared.api.client import (  # 从shared/api/client.py导入LLM客户端相关类型
    ApiMessageCompleteEvent,  # 消息完成事件
    ApiMessageRequest,  # 消息请求
    ApiTextDeltaEvent,  # 文本增量事件
    SupportsStreamingMessages,  # 支持流式消息的接口
)
from shared.types.messages import ConversationMessage  # 对话消息类型

MAX_RETRIES = 3  # 最大重试次数


async def executor_llm(
    client: SupportsStreamingMessages,  # LLM客户端
    model: str,  # 模型名称
    content: str,  # 简历文本内容
) -> ParserResult:
    """调用LLM解析简历文本，返回结构化结果。

    流程：
    1. 构建提示词（系统提示词 + 用户提示词）
    2. 流式调用LLM
    3. 修复并解析JSON
    4. 验证结果格式
    5. 失败则重试（最多3次）

    Args:
        client: LLM客户端实例。
        model: 模型名称（如gpt-4o）。
        content: 简历的纯文本内容。

    Returns:
        验证通过的ParserResult对象。
    """
    accumulated_content = ""  # 初始化累积内容

    # 构建用户消息：将简历文本填入CONTENT模板
    messages = [
        ConversationMessage.from_user_text(CONTENT.format(content=content))
    ]
    # 构建系统提示词：将ParserResult的JSON Schema填入SYSTEM模板
    system_prompt = SYSTEM.format(
        json_schema=json.dumps(
            ParserResult.model_json_schema(),  # 获取JSON Schema
            indent=2,
            ensure_ascii=False,
        )
    )

    # 重试循环
    for i in range(MAX_RETRIES):
        complete_event: ApiMessageCompleteEvent | None = None
        async for event in client.stream_message(  # 流式调用LLM
            ApiMessageRequest(
                model=model,
                messages=messages,
                system_prompt=system_prompt,
            )
        ):
            if isinstance(event, ApiTextDeltaEvent):  # 文本增量事件
                if event.is_think:  # 跳过思考内容
                    continue
                accumulated_content += event.text  # 累积文本
            elif isinstance(event, ApiMessageCompleteEvent):  # 消息完成事件
                complete_event = event

        # 修复并解析JSON
        parser_content = json_repair.loads(accumulated_content)

        try:
            result = ParserResult.model_validate(parser_content)  # 验证解析结果
        except ValidationError as e:  # 验证失败
            if i == MAX_RETRIES - 1:  # 最后一次重试
                raise e
            # 构建错误信息反馈给LLM
            errors = []
            for err in e.errors():
                field = ".".join(str(loc) for loc in err["loc"])
                errors.append(f"  - {field}: {err['msg']}")
            error_msg = f"Validation failed:\n" + "\n".join(errors)

            messages.append(complete_event.message)  # 添加LLM的回复
            messages.append(ConversationMessage.from_user_text(error_msg))  # 添加错误反馈
            continue  # 重试
        except Exception as e:
            raise e
        return result  # 返回验证通过的结果

    raise Exception("Max retries exceeded")  # 超过最大重试次数
