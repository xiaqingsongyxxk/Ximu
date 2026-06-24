"""翻译简历的工具模块。

本模块定义了TranslateResumeTool，用于AI Agent将简历翻译成目标语言。
支持翻译整个简历或单个板块。
"""  # 模块文档字符串，说明这个文件是做什么的

import asyncio  # 导入异步IO库，用于实现异步操作和延迟
import json  # 导入JSON模块，用于处理JSON格式的数据
import re  # 导入正则表达式模块，用于文本匹配和验证
from collections import Counter  # 导入计数器，用于统计元素出现次数

import json_repair  # 导入JSON修复模块，用于修复不完整的JSON
from pydantic import (
    BaseModel,
    Field,
    ValidationError,
)  # 导入Pydantic组件，用于定义数据模型和字段验证
from sqlalchemy import select  # 导入SQL查询构建器，用于构建数据库查询语句

from shared.api.client import (  # 导入LLM客户端相关类型
    ApiMessageCompleteEvent,  # API消息完成事件
    ApiMessageRequest,  # API消息请求
    ApiTextDeltaEvent,  # API文本增量事件
    SupportsStreamingMessages,  # 支持流式消息的接口
)
from shared.database import async_session  # 导入异步会话生成器，用于创建数据库连接
from shared.models import (
    ResumeSection,
    utc_now,
)  # 导入板块ORM模型和时间函数，用于操作数据库中的板块数据
from shared.types.base_tool import (
    BaseTool,
    ToolExecutionContext,
    ToolResult,
)  # 导入工具基类，所有工具都需要继承这些基类
from shared.types.messages import (
    ConversationMessage,
    TextBlock,
)  # 导入对话消息类型，用于构建LLM对话
from shared.types.resume import (
    SECTION_TYPE_TO_MODEL,
)  # 导入板块类型到模型的映射，用于验证板块数据

# ID格式正则：8位十六进制-4位数字
# 这个正则表达式用于验证板块ID的格式是否正确
_ID_FORMAT = re.compile(r"^[0-9a-f]{8}-\d{4}$")
_MAX_RETRIES = 5  # 最大重试次数，当翻译失败时最多重试5次


def _collect_existing_ids(content: dict, section_type: str) -> set[str]:
    """收集现有内容中的ID集合。"""
    if section_type in (
        "work_experience",
        "education",
        "projects",
        "certifications",
        "languages",
        "github",
        "custom",
    ):  # 如果是数组类型的板块
        items = content.get("items", [])  # 获取items数组
        return {
            item["id"] for item in items if isinstance(item, dict) and item.get("id")
        }  # 提取所有有效ID
    if section_type == "skills":  # 如果是技能板块
        categories = content.get("categories", [])  # 获取categories数组
        return {
            cat["id"] for cat in categories if isinstance(cat, dict) and cat.get("id")
        }  # 提取所有有效ID
    return set()  # 其他类型返回空集合


def _validate_item_ids(
    submitted_items: list[dict], existing_ids: set[str], item_type: str
) -> list[str]:
    """验证提交的条目ID是否有效。

    Args:
        submitted_items: 提交的条目列表。
        existing_ids: 原始内容中的ID集合。
        item_type: 条目类型（items或categories）。

    Returns:
        错误消息列表（空表示有效）。
    """
    errors = []  # 用于存储错误信息
    submitted_ids = []  # 用于存储已提交的ID

    for i, item in enumerate(submitted_items):  # 遍历提交的条目
        if not isinstance(item, dict):  # 如果不是字典类型
            continue  # 跳过

        item_id = item.get("id")  # 获取条目的ID
        field_path = f"{item_type}[{i}]"  # 构建字段路径

        if not item_id:  # 如果缺少ID
            errors.append(f"  - {field_path}: missing 'id' field.")  # 添加错误信息
            continue  # 继续下一个条目

        if not _ID_FORMAT.match(item_id):  # 如果ID格式错误
            errors.append(
                f"  - {field_path}.id '{item_id}': invalid format."
            )  # 添加错误信息
            continue  # 继续下一个条目

        if item_id not in existing_ids:  # 如果ID不存在于原始内容
            errors.append(
                f"  - {field_path}.id '{item_id}': not found in original content."
            )  # 添加错误信息
            continue  # 继续下一个条目

        submitted_ids.append(item_id)  # 记录有效的ID

    # 检查重复ID
    duplicates = [
        id_ for id_, count in Counter(submitted_ids).items() if count > 1
    ]  # 找出重复的ID
    if duplicates:  # 如果有重复ID
        errors.append(f"  - Duplicate IDs found: {duplicates}.")  # 添加错误信息

    return errors  # 返回所有错误


def validate_translated_content(
    content: dict, section_type: str, original_content: dict
) -> tuple[bool, str | None]:
    """验证翻译后的内容。

    Args:
        content: 翻译后的内容。
        section_type: 板块类型。
        original_content: 原始内容。

    Returns:
        (是否有效, 错误消息)。
    """
    model = SECTION_TYPE_TO_MODEL.get(section_type)  # 获取对应的Pydantic模型
    if model is None:  # 如果找不到模型
        return False, f"Unknown section type: {section_type}"  # 返回错误

    # Schema验证：根据板块类型验证翻译后的内容结构
    try:
        if section_type in ("personal_info", "summary", "custom"):  # 标量板块
            # 直接验证整个content对象
            model.model_validate(content)
        elif section_type in (
            "work_experience",
            "education",
            "projects",
            "certifications",
            "languages",
            "github",
        ):  # 数组板块
            # 逐个验证items数组中的每个条目
            for item_data in content.get("items", []):
                model.model_validate(item_data)
        elif section_type == "skills":  # 技能板块
            # 逐个验证categories数组中的每个分类
            for category_data in content.get("categories", []):
                model.model_validate(category_data)
    except ValidationError as e:  # 验证失败
        # 收集所有错误信息并返回
        errors = []
        for err in e.errors():
            # 构建字段路径（如 "items.0.company"）
            field = ".".join(str(loc) for loc in err["loc"])
            errors.append(f"  - {field}: {err['msg']}")
        return False, f"[{section_type}] Schema validation failed:\n" + "\n".join(
            errors
        )

    # ID验证：确保翻译后的条目ID与原始内容一致
    existing_ids = _collect_existing_ids(
        original_content, section_type
    )  # 收集原始内容中的所有ID
    if section_type in (
        "work_experience",
        "education",
        "projects",
        "certifications",
        "languages",
        "github",
    ):  # 数组板块
        # 验证items数组中每个条目的ID
        id_errors = _validate_item_ids(content.get("items", []), existing_ids, "items")
        if id_errors:  # 如果有ID错误
            return False, f"[{section_type}] ID validation failed:\n" + "\n".join(
                id_errors
            )
    elif section_type == "skills":  # 技能板块
        # 验证categories数组中每个分类的ID
        id_errors = _validate_item_ids(
            content.get("categories", []), existing_ids, "categories"
        )
        if id_errors:  # 如果有ID错误
            return False, f"[{section_type}] ID validation failed:\n" + "\n".join(
                id_errors
            )

    return True, None  # 验证通过


def _is_content_empty(content: dict, section_type: str) -> bool:
    """检查板块内容是否为空。"""
    if not content:  # 如果内容为空
        return True  # 直接返回True
    if section_type in ("personal_info", "summary", "custom"):  # 标量板块
        # 检查所有字段是否都为空
        return not any(content.values())
    if section_type in (
        "work_experience",
        "education",
        "projects",
        "certifications",
        "languages",
        "github",
    ):  # 数组板块
        # 检查items数组是否为空
        return not content.get("items")
    if section_type == "skills":  # 技能板块
        # 检查categories数组是否为空
        return not content.get("categories")
    return False  # 未知板块类型默认不为空


def build_system_prompt(target_language: str) -> str:
    """构建系统提示词。"""
    # 系统提示词：告诉LLM它的任务是翻译简历内容
    return f"""\
You will receive a JSON array of resume sections.
Your task is to translate the resume content to {target_language}.
Return a JSON array only, no explanation.
Keep the original JSON array structure and order.
"""


def build_sections_user_prompt(sections: list[dict]) -> str:
    """构建用户提示词。"""
    # 过滤掉时间戳字段，只保留内容相关字段
    filtered = [
        {k: v for k, v in s.items() if k not in ("updated_at", "created_at")}
        for s in sections
    ]
    # 用户提示词：包含待翻译的JSON简历内容
#     # filtered 是一个 Python list，不是消息结构的一部分
# filtered = [{"type": "personal_info", "content": {"full_name": "张三"}}]
# # 它必须被嵌入到一个 text 块的消息里
# ConversationMessage.from_user_text(
#     f"Here is the JSON resume content:\n---\n{json.dumps(filtered, ...)}\n---"
# )
# # 生成 → TextBlock(text="Here is...\n---\n[{\"type\": \"personal_info\", ...}]\n---")
    return f"""\
Here is the JSON resume content:

---
{json.dumps(filtered, indent=2, ensure_ascii=False)}
---
"""
# 不一定必须，但不给 JSON 会出问题。
# 看如果不给 JSON 会怎么做：
# # 假设用自然语言描述
# "请翻译以下简历内容：\n姓名：张三\n邮箱：zhangsan@example.com\n公司：ABC科技有限公司\n职位：高级工程师"
# LLM 要输出：
# {
#   "full_name": "Zhang San",
#   "email": "zhangsan@example.com",
#   "company": "ABC Technology Co., Ltd.",
#   "position": "Senior Engineer"
# }
# 问题是 LLM 可能搞错字段名：
# LLM 输出:
# {
#   "name": "Zhang San",        ← 字段名和原始架构里的 full_name 不一致
#   "mail": "zhangsan@example.com",  ← email 变成了 mail
#   ...
# }
# 后端解析 content["full_name"] 时直接报错。
# 给 JSON 输入的好处
# // 输入 JSON
# {
#   "full_name": "张三",
#   "email": "zhangsan@example.com"
# }
# // LLM 看到结构，输出自然用同样的键
# {
#   "full_name": "Zhang San",
#   "email": "zhangsan@example.com"
# }
# 输入格式	LLM 的行为	风险
# JSON	看到键名 full_name，输出也用 full_name	✅ 低
# 自然语言 "姓名：张三"	LLM 自己猜键名，可能用 name、user_name、姓名	❌ 高
# 核心原因就一句：Keep the original JSON array structure——要 LLM 保持原结构，就得让它先看到原结构长什么样。 JSON 是最精确的"结构展示"方式，自然语言描述结构总有歧义。




# 。filtered 是发给 LLM 做翻译的，LLM 需要看到完整的结构才能原样保留。
# 如果 filtered 是 list[str]
# 假设强行把每个 section 转成字符串：
# filtered = [
#     "work_experience: ABC公司/工程师/2020-2023 ...",
#     "personal_info: 张三/zhang@example.com ...",
# ]
# LLM 翻译后返回：
# [
#     "work_experience: ABC Company/Engineer/2020-2023 ...",
#     "personal_info: Zhang San/zhang@example.com ...",
# ]
# 然后代码要解析这个字符串，反解回 {"type": "work_experience", "content": {"items": [...]}} — 怎么做？正则硬拆？字段名（company、position）全丢了，根本拼不回原来的结构。
# 为什么要保持 list[dict]
# 翻译工具的预期是：LLM 返回跟输入结构一致的 JSON，字段名不变，只把值翻译成目标语言。
# // 输入
# {"company": "ABC公司", "position": "前端工程师"}
# // 输出（只改值）
# {"company": "ABC Company", "position": "Frontend Engineer"}
# 后续代码直接 json.loads() → 按 key 取值覆盖原 content，干净利落。
# 什么时候 list[str] 才合理？
# 只有不需要保留结构的场景才用。比如 missing_keywords：
# # 结构不重要，只是给 LLM 看一眼
# missing_keywords = ["Python", "React", "AWS"]
# ', '.join(missing_keywords)
# # → "Python, React, AWS"  ✓ 够用了
# 因为这里 LLM 不需要返回结构，只是看到了参考一下。而 filtered LLM 必须返回同样结构，所以必须给 JSON。
class TranslateResumeToolInput(BaseModel):
    """翻译简历工具的输入数据模型。"""

    target_language: str = Field(
        description="目标语言代码，如zh, en"
    )  # 目标语言字段，用于指定翻译成什么语言
    section_id: str | None = Field(
        default=None,
        description="要翻译的板块ID。省略则翻译整个简历。",
    )  # 板块ID字段，用于指定要翻译哪个板块（可选）


class TranslateResumeTool(BaseTool):
    """翻译简历的工具类。

    AI Agent调用此工具来翻译简历内容。
    """

    name = "translate_resume"  # 工具名称，用于标识这个工具
    description = "Translate a resume (or a specific section) to the target language."  # 工具描述，告诉AI Agent这个工具的作用
    input_model = TranslateResumeToolInput  # 指定输入数据模型
# TranslateResumeTool 没有定义 to_api_schema_v2，所以走的是 BaseTool 的默认实现：
# # BaseTool 里的默认方法
# def to_api_schema_v2(self, sections):
#     return self.to_api_schema()  # 返回静态定义
# to_api_schema() 返回的就是：
# {
#     "name": "translate_resume",
#     "description": "Translate a resume (or a specific section) to the target language.",
#     "input_schema": {
#         "type": "object",
#         "properties": {
#             "target_language": {
#                 "title": "Target Language",
#                 "type": "string"
#             },
#             "section_id": {
#                 "anyOf": [
#                     {"type": "string"},
#                     {"type": "null"}
#                 ],
#                 "default": None,
#                 "title": "Section Id"
#             }
#         },
#         "required": ["target_language"]
#     }
# }
# 对比其他两个工具，它们 override 后会在 description 里注入动态信息：
# 工具	to_api_schema_v2	LLM 看到的 description
# UpdateSectionTool	override → 注入字段结构	"... 当前板块字段: personal_info有full_name, email..."
# AddSectionTool	override → 注入可用类型	"... 可添加类型: skills, education, ..."
# TranslateResumeTool	不 override → 走默认	"Translate a resume..."（静态，不变）
# 因为翻译工具的输入（目标语言 + 可选板块 ID）不依赖当前简历状态，所以不需要覆写，默认的静态 schema 就够用了。
    async def execute(
        self, arguments: TranslateResumeToolInput, context: ToolExecutionContext
    ) -> ToolResult:
        """执行翻译操作。

        Args:
            arguments: 输入参数（目标语言和可选的板块ID）。
            context: 工具执行上下文。

        Returns:
            操作结果。
        """
        # 验证板块ID是否有效
        id_to_type = context.metadata.get("id_to_type", {})  # 获取ID到类型的映射
        if (
            arguments.section_id is not None and arguments.section_id not in id_to_type
        ):  # 如果指定了ID但无效
            return ToolResult(
                output=f"Invalid section ID: {arguments.section_id}", is_error=True
            )  # 返回错误结果

        # 确定待翻译的板块：如果指定了板块ID就只翻译该板块，否则翻译全部
        if arguments.section_id is not None:  # 如果指定了板块ID
            target_sections = [
                s for s in context.sections if s["id"] == arguments.section_id
            ]  # 只翻译指定的板块
        else:  # 如果没有指定板块ID
            target_sections = list(context.sections)  # 翻译所有板块

        # 过滤空板块：跳过没有内容的板块
        non_empty = []  # 用于存储非空板块
        for section in target_sections:  # 遍历目标板块
            if not _is_content_empty(
                section.get("content", {}), section["type"]
            ):  # 如果内容不为空
                non_empty.append(section)  # 添加到非空板块列表

        skipped = len(target_sections) - len(non_empty)  # 记录跳过的空板块数量

        # 翻译所有非空板块
        section_results = await _translate_all_sections(
            non_empty, arguments.target_language, context.metadata
        )

        # 汇总翻译结果
        success = sum(1 for r in section_results if r["success"])  # 成功数量
        failed = len(section_results) - success  # 失败数量

        # 构建结果报告
        lines = []  # 用于存储结果报告行
        for r in section_results:  # 遍历翻译结果
            if r["success"]:  # 如果成功
                lines.append(
                    f"✓ {r['section_id']} ({r['section_type']})"
                )  # 添加成功标记
            else:  # 如果失败
                lines.append(
                    f"✗ {r['section_id']} ({r['section_type']}): {r['error']}"
                )  # 添加失败标记

        if skipped:  # 如果有跳过的板块
            lines.append(f"Skipped {skipped} empty section(s)")  # 添加跳过信息

        lines.append(
            f"\nTotal: {len(non_empty)} translated, {success} succeeded, {failed} failed"
        )  # 添加总计信息

        # 同步翻译结果到数据库
        if success:  # 如果有成功的翻译
            resume_id = context.sections[0]["resume_id"]  # 获取简历ID
            now = utc_now()  # 获取当前时间
            async with async_session() as db:  # 创建数据库会话
                for r in section_results:  # 遍历翻译结果
                    if not r["success"]:  # 如果失败
                        continue  # 跳过
                    section_id = r["section_id"]  # 获取板块ID
                    # 在context.sections中找到对应的板块并更新数据库
                    for section in context.sections:  # 遍历上下文中的板块
                        if section["id"] == section_id:  # 如果是目标板块
                            result = await db.execute(
                                select(ResumeSection).where(
                                    ResumeSection.id == section_id,  # 板块ID匹配
                                    ResumeSection.resume_id == resume_id,  # 简历ID匹配
                                )
                            )  # 查询数据库中的板块
                            db_section = result.scalar_one_or_none()  # 获取查询结果
                            if db_section is not None:  # 如果找到了板块
                                # 更新板块内容为翻译后的JSON
                                db_section.content = json.dumps(
                                    section.get("content", {}), ensure_ascii=False
                                )
                                db_section.updated_at = now  # 更新修改时间
                                db.add(db_section)  # 将板块添加到数据库
                            break  # 找到后退出循环
                await db.commit()  # 提交事务

        return ToolResult(output="\n".join(lines))  # 返回结果报告


async def _translate_all_sections(
    sections: list[dict], target_language: str, metadata: dict
) -> list[dict]:
    """翻译所有板块。

    单次LLM调用翻译所有板块，验证失败则重试。

    Args:
        sections: 板块列表。
        target_language: 目标语言。
        metadata: 元数据（包含client和model）。

    Returns:
        结果列表。
    """
    # 获取LLM客户端和模型名称
    client: SupportsStreamingMessages = metadata.get("client")  # 获取LLM客户端
    model: str = metadata.get("model")  # 获取模型名称

    # 构建系统提示词和用户提示词
    system_prompt = build_system_prompt(target_language)  # 构建系统提示词
    user_prompt = build_sections_user_prompt(sections)  # 构建用户提示词

    # 建立板块ID到板块数据的映射，方便后续查找
    section_map: dict[str, dict] = {s["id"]: s for s in sections}
    # 初始化对话消息列表
    messages: list[ConversationMessage] = [
        ConversationMessage.from_user_text(user_prompt)
    ]

    # 重试循环：最多尝试_MAX_RETRIES次
    for attempt in range(1, _MAX_RETRIES + 1):
        # 调用LLM进行翻译
        raw_content, call_error = await _call_translation(
            client, model, messages, system_prompt
        )
        if call_error:  # 如果LLM调用失败
            # 返回错误结果
            return [
                {
                    "success": False,
                    "section_id": s["id"],
                    "section_type": s["type"],
                    "error": call_error,
                }
                for s in sections
            ]

        try:
            # 解析LLM返回的JSON（json_repair能修复不完整的JSON）
            translated_list = json_repair.loads(raw_content)
            if not isinstance(translated_list, list):  # 如果返回的不是列表
                raise ValueError(f"Expected list, got {type(translated_list).__name__}")
        except Exception as e:  # 如果JSON解析失败
            # 返回错误结果
            return [
                {
                    "success": False,
                    "section_id": s["id"],
                    "section_type": s["type"],
                    "error": f"JSON parse error: {e}",
                }
                for s in sections
            ]

        # 逐个验证翻译后的板块内容
        results: list[dict] = []  # 用于存储验证结果
        all_valid = True  # 标记是否所有板块都验证通过
        for i, translated_item in enumerate(translated_list):  # 遍历翻译后的板块
            if i >= len(sections):  # 如果索引超出范围
                break  # 防止索引越界
            original = sections[i]  # 获取原始板块
            section_id = original["id"]  # 获取板块ID
            section_type = original["type"]  # 获取板块类型
            original_content = original.get("content", {})  # 获取原始内容
            new_content = translated_item.get("content", {})  # 获取翻译后的内容

            # 验证翻译后的内容是否符合schema和ID要求
            is_valid, error_msg = validate_translated_content(
                new_content, section_type, original_content
            )

            if is_valid:  # 如果验证通过
                # 更新板块内容
                section_map[section_id]["content"] = new_content
                results.append(
                    {
                        "success": True,
                        "section_id": section_id,
                        "section_type": section_type,
                        "error": None,
                    }
                )
            else:  # 如果验证失败
                # 记录错误信息
                all_valid = False
                results.append(
                    {
                        "success": False,
                        "section_id": section_id,
                        "section_type": section_type,
                        "error": error_msg,
                    }
                )

        if all_valid:  # 如果所有板块都验证通过
            return results  # 返回结果

        # 有验证失败：准备重试
        # 将LLM的回复添加到对话历史
        messages.append(
            ConversationMessage(role="assistant", content=[TextBlock(text=raw_content)])
        )
        # 收集所有失败板块的错误信息
        error_summary_parts = []
        for r in results:  # 遍历结果
            if not r["success"]:  # 如果失败
                error_summary_parts.append(
                    f"**Section {r['section_id']} ({r['section_type']}) errors:**\n{r['error']}"
                )  # 添加错误信息

        # 构建重试消息：要求LLM修复所有错误
        retry_msg = (
            "Some sections failed validation. Please fix ALL sections below and return the complete corrected JSON array.\n\n"
            + "\n\n".join(error_summary_parts)
        )
        messages.append(ConversationMessage.from_user_text(retry_msg))  # 添加重试消息

        # 等待一段时间再重试（指数退避）
        if attempt < _MAX_RETRIES:  # 如果不是最后一次尝试
            await asyncio.sleep(0.5 * attempt)  # 等待一段时间

    # 超过最大重试次数，返回失败结果
    return [
        {
            "success": False,
            "section_id": s["id"],
            "section_type": s["type"],
            "error": "Max retries exceeded",
        }
        for s in sections
    ]


async def _call_translation(
    client: SupportsStreamingMessages,
    model: str,
    messages: list[ConversationMessage],
    system_prompt: str | None,
) -> tuple[str, str | None]:
    """执行单次翻译LLM调用。

    Returns:
        (内容, 错误消息)。
    """
    # 构建API请求
    request = ApiMessageRequest(
        model=model, messages=messages, system_prompt=system_prompt
    )

    # 初始化累积内容为空字符串
    accumulated_content = ""
    try:
        # 流式接收LLM的输出
        async for event in client.stream_message(request):
            if isinstance(event, ApiTextDeltaEvent):  # 如果是文本增量事件
                # 跳过思考内容，累积正常文本
                if event.is_think:  # 如果是思考内容
                    continue  # 跳过
                accumulated_content += event.text  # 累积文本
            elif isinstance(event, ApiMessageCompleteEvent):  # 如果是消息完成事件
                pass  # 不需要处理
    except Exception as e:  # 如果流式接收出错
        # 返回错误消息
        return "", f"Stream error: {type(e).__name__}: {e}"

    # 检查是否有内容返回
    if not accumulated_content:  # 如果没有内容
        return "", "No content in response"  # 返回空响应错误

    return accumulated_content, None  # 返回内容，无错误
