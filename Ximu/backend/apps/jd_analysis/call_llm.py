"""LLM调用封装模块。

本模块负责与大语言模型（LLM）通信，执行简历与职位的匹配分析。
主要功能：
1. 构建提示词（system prompt + user prompt）
2. 流式调用LLM获取结果
3. 解析和验证LLM返回的JSON数据
4. 处理错误和重试逻辑
"""  # 模块文档字符串

import json  # 导入JSON模块，用于处理JSON数据

import json_repair  # 导入json_repair模块，用于修复LLM返回的不完整JSON（LLM有时会截断JSON）
from pydantic import ValidationError  # 从Pydantic导入验证错误类，用于捕获数据验证失败

from apps.jd_analysis.prompt import (  # 从apps/jd_analysis/prompt.py导入提示词相关
    SYSTEM,  # 系统提示词模板，告诉LLM它的角色和输出格式
    build_user_prompt,  # 构建用户提示词的函数，将简历内容和职位描述组合成文本
)
from apps.jd_analysis.schemas import (
    MatchResult,
)  # 从apps/jd_analysis/schemas.py导入匹配结果数据模型
from shared.api.client import (  # 从shared/api/client.py导入API客户端相关类型
    ApiMessageCompleteEvent,  # API消息完成事件类（LLM回复完成时触发）
    ApiMessageRequest,  # API消息请求类（发送给LLM的请求）
    ApiTextDeltaEvent,  # API文本增量事件类（LLM流式输出的每个token）
    SupportsStreamingMessages,  # 支持流式消息的接口（LLM客户端必须实现此接口）
)
from shared.types.messages import (
    ConversationMessage,
)  # 从shared/types/messages.py导入对话消息类型
from shared.types.resume import (
    ResumeSectionSchema,
)  # 从shared/types/resume.py导入简历板块类型

MAX_RETRIES = 3  # 最大重试次数：如果LLM返回的结果验证失败，最多重试3次


async def executor_llm(  # 定义执行LLM分析的异步函数
    client: SupportsStreamingMessages,  # 参数：LLM客户端（支持流式消息）
    model: str,  # 参数：模型名称（如"gpt-4"、"claude-3"）
    sections: list[ResumeSectionSchema],  # 参数：简历板块列表
    job_description: str,  # 参数：职位描述文本
    job_title: str | None = None,  # 参数：职位名称（可选）
) -> MatchResult:  # 返回值类型：匹配结果
    """执行流式LLM调用，生成JD匹配分析结果。

    流程：
    1. 构建系统提示词（包含JSON Schema）和用户提示词
    2. 流式调用LLM，逐步收集输出
    3. 修复并解析LLM返回的JSON
    4. 验证结果是否符合MatchResult格式
    5. 如果验证失败，将错误信息反馈给LLM重试

    Args:
        client: LLM客户端实例。
        model: 要使用的模型名称。
        sections: 简历板块列表。
        job_description: 目标职位描述。
        job_title: 目标职位名称（可选）。

    Returns:
        验证通过的MatchResult对象。
    """  # 文档字符串
    accumulated_content = ""  # 初始化累积内容为空字符串，用于收集LLM的流式输出
    messages = [  # 创建对话消息列表
        ConversationMessage.from_user_text(  # 创建用户消息
            build_user_prompt(sections, job_description, job_title)  # 构建用户提示词
        )
    ]
    system_prompt = SYSTEM.format(  # 格式化系统提示词模板
        json_schema=json.dumps(  # 将MatchResult的JSON Schema转为格式化字符串
            MatchResult.model_json_schema(),  # 获取MatchResult模型的JSON Schema定义
            indent=2,  # 缩进2个空格，便于阅读
            ensure_ascii=False,  # 允许中文直接显示
        )
    )

    # 重试循环：最多尝试MAX_RETRIES次
    for i in range(MAX_RETRIES):  # 遍历重试次数
        complete_event: ApiMessageCompleteEvent | None = None  # 初始化完成事件为None
        async for event in client.stream_message(  # 异步遍历LLM的流式输出事件
            ApiMessageRequest(  # 创建API请求
                model=model,  # 模型名称
                messages=messages,  # 对话消息列表
                system_prompt=system_prompt,  # 系统提示词
                temperature=0.0,  # 温度设为0，确保输出确定性（相同输入产生相同输出）
            )
        ):
            if isinstance(
                event, ApiTextDeltaEvent
            ):  # 如果是文本增量事件（LLM输出的每个token）
                if event.is_think:  # 如果是思考内容（某些模型有思考过程）
                    continue  # 跳过思考内容，不累积
                accumulated_content += event.text  # 将token追加到累积内容
            elif isinstance(event, ApiMessageCompleteEvent):  # 如果是消息完成事件
                complete_event = event  # 保存完成事件

        # 修复并解析LLM返回的JSON（json_repair能修复不完整的JSON）
        parser_content = json_repair.loads(
            accumulated_content  # 将累积的文本解析为Python对象
        )

        try:  # 尝试验证
            result = MatchResult.model_validate(  # 使用Pydantic验证解析结果
                parser_content  # 验证数据是否符合MatchResult格式
            )
        except ValidationError as e:  # 如果验证失败
            if i == MAX_RETRIES - 1:  # 如果是最后一次重试
                raise e  # 抛出验证错误

            # 构建错误信息，告诉LLM哪里出错了
            errors = []  # 初始化错误列表
            for err in e.errors():  # 遍历所有验证错误
                field = ".".join(
                    str(loc) for loc in err["loc"]
                )  # 构建字段路径（如"suggestions.0.section_id"）
                errors.append(f"  - {field}: {err['msg']}")  # 添加错误描述
            error_msg = f"Validation failed:\n" + "\n".join(errors)  # 构建完整错误消息

            messages.append(complete_event.message)  # 添加LLM的完整回复到对话历史
            messages.append(
                ConversationMessage.from_user_text(error_msg)  # 添加错误反馈消息
            )
            continue  # 继续下一次重试
        except Exception as e:  # 如果是其他异常
            raise e  # 直接抛出

        # 验证建议中的section_id引用是否存在于提供的板块中
        valid_section_ids = {s.id for s in sections}  # 获取所有有效板块ID的集合
        invalid_section_ids = [  # 获取无效的section_id列表
            s.section_id  # 建议中的板块ID
            for s in result.suggestions  # 遍历所有建议
            if s.section_id not in valid_section_ids  # 如果板块ID不在有效集合中
        ]
        if invalid_section_ids:  # 如果存在无效的板块ID
            if i == MAX_RETRIES - 1:  # 如果是最后一次重试
                raise ValueError(  # 抛出值错误
                    f"Invalid section_id: {invalid_section_ids}, "
                    f"these IDs do not exist in the provided sections"
                )
            # 构建错误信息
            error_msg = (  # 构建错误消息
                "Validation failed:\n"
                f"  - suggestions: invalid section_id {invalid_section_ids}, "
                f"valid section_id are: {list(valid_section_ids)}"
            )
            messages.append(complete_event.message)  # 添加LLM的回复
            messages.append(
                ConversationMessage.from_user_text(error_msg)  # 添加错误反馈
            )
            continue  # 继续下一次重试

        return result  # 验证通过，返回结果

    raise Exception("Max retries exceeded")  # 超过最大重试次数，抛出异常
