"""更新板块内容的工具模块。

本模块定义了UpdateSectionTool，用于AI Agent更新简历板块的内容。
支持部分更新（只修改传入的字段）和完整更新（替换整个内容）。
"""  # 模块文档字符串，说明这个文件是做什么的

import json  # 导入JSON模块，用于处理JSON格式的数据
import re  # 导入正则表达式模块，用于文本匹配和验证
import secrets  # 导入安全随机数模块，用于生成安全的随机数
from typing import Any  # 导入Any类型，表示可以是任何类型的数据

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
)  # 导入Pydantic组件，用于定义数据模型和字段验证
from sqlalchemy import select  # 导入SQL查询构建器，用于构建数据库查询语句

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
from shared.types.resume import (
    SECTION_TYPE_TO_MODEL,
)  # 导入板块类型到模型的映射，用于验证板块数据

# ID格式正则：8位十六进制-4位数字
# 这个正则表达式用于验证板块ID的格式是否正确
_ID_FORMAT = re.compile(r"^[0-9a-f]{8}-\d{4}$")

# 各板块类型的字段结构和示例（供LLM理解）
# 这个字典定义了每个板块类型的字段结构和示例，用于帮助AI Agent理解每个板块应该包含什么数据
_SECTION_CONTENT_SCHEMAS = {
    "personal_info": {
        "fields": "full_name, job_title, email, phone, location, salary, age, gender, political_status, education_level, ethnicity, hometown, marital_status, years_of_experience, wechat, website, linkedin",
        "example": '{ "full_name": "张三", "email": "zhangsan@example.com" }',
    },  # 个人信息板块的字段结构和示例
    "summary": {
        "fields": "text",
        "example": '{ "text": "3年前端开发经验..." }',
    },  # 个人总结板块的字段结构和示例
    "work_experience": {
        "fields": "items: [{ id, company, position, location, start_date, end_date, current, description, technologies: string[], highlights: string[] }]",
        "example": '{ "items": [{ "company": "ABC公司", "position": "前端工程师", "start_date": "2020-01", "end_date": "2023-12", "description": "...", "technologies": ["React", "TypeScript"] }] }',
    },  # 工作经历板块的字段结构和示例
    "education": {
        "fields": "items: [{ id, institution, degree, field, location, start_date, end_date, gpa, highlights: string[] }]",
        "example": '{ "items": [{ "institution": "XX大学", "degree": "本科", "field": "计算机科学", "start_date": "2018", "end_date": "2022" }] }',
    },  # 教育背景板块的字段结构和示例
    "projects": {
        "fields": "items: [{ id, name, url, description, technologies: string[], highlights: string[], start_date, end_date }]",
        "example": '{ "items": [{ "name": "AI项目", "description": "...", "technologies": ["Python", "PyTorch"] }] }',
    },  # 项目经验板块的字段结构和示例
    "certifications": {
        "fields": "items: [{ id, name, issuer, date, description }]",
        "example": '{ "items": [{ "name": "AWS认证", "issuer": "Amazon", "date": "2023-01", "description": "..." }] }',
    },  # 证书板块的字段结构和示例
    "languages": {
        "fields": "items: [{ id, language, proficiency, description }]",
        "example": '{ "items": [{ "language": "英语", "proficiency": "CET-6" }] }',
    },  # 语言能力板块的字段结构和示例
    "github": {
        "fields": "items: [{ id, repo_url, name, stars, language, description }] — repo_url/name/stars/language只读，只修改description",
        "example": '{ "items": [{ "name": "my-repo", "description": "一个很棒的项目" }] }',
    },  # GitHub项目板块的字段结构和示例
    "custom": {
        "fields": "items: [{ id, title, date, description }]",
        "example": '{ "items": [{ "title": "获奖", "description": "..." }] }',
    },  # 自定义板块的字段结构和示例
    "skills": {
        "fields": "categories: [{ id, name, skills: string[] }]",
        "example": '{ "categories": [{ "name": "编程语言", "skills": ["Python", "Java"] }] }',
    },  # 技能板块的字段结构和示例
}


def build_tool_description(sections: list[dict]) -> str:
    """根据激活的板块构建工具描述中的字段结构说明。

    Args:
        sections: 已排序的可见板块列表。

    Returns:
        动态生成的字段结构说明字符串。
    """
    lines = []  # 用于存储生成的说明行
    for section in sections:  # 遍历所有板块
        section_type = section.get("type")  # 获取板块类型
        if section_type in _SECTION_CONTENT_SCHEMAS:  # 如果该类型有定义
            schema = _SECTION_CONTENT_SCHEMAS[section_type]  # 获取该类型的字段结构
            lines.append(f"- {section_type}: {schema['fields']}")  # 添加字段说明
            lines.append(f"  → e.g. {schema['example']}")  # 添加示例
    return "\n".join(lines)  # 将所有行合并成一个字符串


def _generate_prefix() -> str:
    """生成8位随机十六进制前缀。"""
    return secrets.token_hex(4)  # 生成4字节的随机十六进制字符串（8个字符）


def _generate_id(prefix: str, index: int) -> str:
    """生成格式化的ID。"""
    return f"{prefix}-{index:04d}"  # 将前缀和序号组合成格式化的ID


def _assign_ids(submitted_items: list, existing_items: list) -> list:
    """为新条目分配ID，保留现有条目的ID。"""
    if existing_items:  # 如果已有条目
        last_id = (
            existing_items[-1].get("id", "")  # 获取最后一个条目的ID
            if isinstance(existing_items[-1], dict)  # 如果是字典类型
            else ""  # 否则为空字符串
        )
        prefix = last_id.split("-")[0]  # 提取ID的前缀部分
        last_index = int(last_id.split("-")[1])  # 提取ID的序号部分
    else:  # 如果没有已有条目
        prefix = _generate_prefix()  # 生成新的前缀
        last_index = 0  # 从0开始
# 这种情况发生在新创建的板块还没有任何条目时。
# 场景
# # 创建主简历时，默认板块内容是空的
# content = WorkExperienceContent()  # → {"items": []}
# content = EducationContent()       # → {"items": []}
# 数据库里的内容
# # 新简历的"工作经历"板块
# section.content = '{"items": []}'  # 空的，没有条目
# 用户想往空板块里添加内容时就会用到。
# 场景
# 用户创建了新简历
#     ↓
# 板块是空的：{"items": []}
#     ↓
# 用户说："帮我添加工作经历"
#     ↓
# AI 调用 update_section 工具
#     ↓
# 代码处理：没有条目 → 用 else 分支
# 代码流程
# # 用户："帮我添加一份工作经历"
# # AI 调用工具：
    next_index = last_index + 1  # 计算下一个序号
    result = []  # 用于存储处理后的条目
    for item in submitted_items:  # 遍历提交的条目
        if isinstance(item, dict):  # 如果是字典类型
            if "id" not in item or not item["id"]:  # 如果没有ID字段或ID为空
                item["id"] = _generate_id(prefix, next_index)  # 自动生成ID
                next_index += 1  # 序号递增
            result.append(item)  # 添加到结果列表
        else:  # 如果不是字典类型
            result.append(item)  # 直接添加到结果列表
    return result  # 返回处理后的条目列表


def _collect_existing_ids(items: list[dict]) -> set[str]:
    """收集已存在条目的ID集合。"""
    return {
        item["id"] for item in items if isinstance(item, dict) and item.get("id")
    }  # 提取所有有效ID


def _validate_item_id(item: dict, field_path: str, existing_ids: set[str]) -> list[str]:
    """验证单个条目的ID。"""
    errors = []  # 用于存储错误信息
    item_id = item.get("id")  # 获取条目的ID
    if not item_id:  # 如果没有ID
        return errors  # 直接返回（新条目可以没有ID）

    if (
        not _ID_FORMAT.match(item_id) or item_id not in existing_ids
    ):  # 如果ID格式不正确或不存在于原始内容
        errors.append(
            f"  - {field_path}.id: '{item_id}' is invalid. Omit the id field for new items; preserve the original id for existing items."
        )  # 添加错误信息
    return errors  # 返回错误列表


def _validate_items(
    submitted_items: list, existing_items: list, item_type: str
) -> list[str]:
    """验证提交的条目的ID。"""
    errors = []  # 用于存储错误信息
    existing_ids = _collect_existing_ids(existing_items)  # 收集已存在条目的ID
    for i, item in enumerate(submitted_items):  # 遍历提交的条目
        if not isinstance(item, dict):  # 如果不是字典类型
            continue  # 跳过
        field_path = f"{item_type}[{i}]"  # 构建字段路径
        errors.extend(
            _validate_item_id(item, field_path, existing_ids)
        )  # 验证ID并收集错误
    return errors  # 返回所有错误


class UpdateSectionToolInput(BaseModel):
    """更新板块工具的输入数据模型。"""

    section_id: str = Field(
        description="要更新的板块ID"
    )  # 板块ID字段，用于指定要更新哪个板块
    value: dict = Field(
        description="部分更新对象。标量板块（personal_info, summary）只包含要修改的字段。数组板块传入完整的items/categories数组。"
    )  # 更新内容字段，包含要更新的数据


class UpdateSectionTool(BaseTool):
    """更新板块内容的工具类。

    AI Agent调用此工具来修改简历板块的内容。
    支持部分更新和完整更新。
    """

    name = "update_section"  # 工具名称，用于标识这个工具
    description = (
        "Update the content of a specific resume section using a partial update object.\n\n"
        "Pass only the fields you want to update. Unmentioned fields remain unchanged.\n\n"
        "Section content structures and update examples:\n"
        "{content_structures}\n\n"
        "For all array sections, pass the COMPLETE items/categories array.\n\n"
        "Item ID rules:\n"
        "- Existing items: preserve their id field exactly as-is\n"
        "- New items: omit the id field entirely — it will be generated automatically"
    )  # 工具描述，告诉AI Agent这个工具的作用和使用方法
    input_model = UpdateSectionToolInput  # 指定输入数据模型

    async def execute(
        self, arguments: UpdateSectionToolInput, context: ToolExecutionContext
    ) -> ToolResult:
        """执行更新板块操作。

        Args:
            arguments: 输入参数（板块ID和更新内容）。
            context: 工具执行上下文。

        Returns:
            操作结果。
        """
        # 从上下文中获取ID到类型的映射
        id_to_type: dict[str, str] = context.metadata.get("id_to_type", {})
        # 根据板块ID获取板块类型
        section_type = id_to_type.get(arguments.section_id)

        # 验证section_id是否有效
        if section_type is None:  # 如果找不到对应的板块类型
            return ToolResult(
                is_error=True, output=f"Unknown Section ID: {arguments.section_id}"
            )  # 返回错误结果

        # 获取对应的Pydantic模型，用于验证数据
        model = SECTION_TYPE_TO_MODEL.get(section_type)

        # 验证value是否符合板块的数据结构
        try:
            if section_type in ("personal_info", "summary", "custom"):  # 标量板块
                model.model_validate(arguments.value)  # 直接验证整个value对象
            elif section_type in (
                "work_experience",
                "education",
                "projects",
                "certifications",
                "languages",
                "github",
            ):  # 数组板块
                for item_data in arguments.value.get("items", []):  # 遍历items数组
                    model.model_validate(item_data)  # 验证每个条目
            elif section_type == "skills":  # 技能板块
                for category_data in arguments.value.get(
                    "categories", []
                ):  # 遍历categories数组
                    model.model_validate(category_data)  # 验证每个分类
        except ValidationError as e:  # 如果验证失败
            errors = []  # 用于存储错误信息
            for err in e.errors():  # 遍历所有验证错误
                field = ".".join(str(loc) for loc in err["loc"])  # 构建字段路径
                errors.append(f"  - {field}: {err['msg']}")  # 添加错误信息
            error_msg = f"[{section_type}] Validation failed:\n" + "\n".join(
                errors
            )  # 构建错误消息
            return ToolResult(is_error=True, output=error_msg)  # 返回错误结果

        # 验证并执行更新
        for section in context.sections:  # 遍历所有板块
            if section["id"] != arguments.section_id:  # 如果不是目标板块
                continue  # 跳过

            content = section.get("content", {})  # 获取板块内容

            # 验证并分配ID
            if section_type in (
                "work_experience",
                "education",
                "projects",
                "certifications",
                "languages",
                "github",
            ):  # 数组板块
                id_errors = _validate_items(
                    arguments.value.get("items", []), content.get("items", []), "items"
                )  # 验证ID
                if id_errors:  # 如果有ID错误
                    error_msg = (
                        f"[{section_type}] Item ID validation failed:\n"
                        + "\n".join(id_errors)
                    )  # 构建错误消息
                    return ToolResult(is_error=True, output=error_msg)  # 返回错误结果
                content["items"] = _assign_ids(
                    arguments.value.get("items", []), content.get("items", [])
                )  # 分配ID
            elif section_type == "skills":  # 技能板块
                id_errors = _validate_items(
                    arguments.value.get("categories", []),
                    content.get("categories", []),
                    "categories",
                )  # 验证ID
                if id_errors:  # 如果有ID错误
                    error_msg = (
                        f"[{section_type}] Item ID validation failed:\n"
                        + "\n".join(id_errors)
                    )  # 构建错误消息
                    return ToolResult(is_error=True, output=error_msg)  # 返回错误结果
                content["categories"] = _assign_ids(
                    arguments.value.get("categories", []), content.get("categories", [])
                )  # 分配ID
            elif section_type in ("personal_info", "summary"):  # 标量板块
                content.update(arguments.value)  # 更新内容
            break  # 找到目标板块后退出循环

        # 同步更新到数据库
        resume_id = context.sections[0]["resume_id"]  # 获取简历ID
        async with async_session() as db:  # 创建数据库会话
            result = await db.execute(
                select(ResumeSection).where(
                    ResumeSection.id == arguments.section_id,  # 板块ID匹配
                    ResumeSection.resume_id == resume_id,  # 简历ID匹配
                )
            )  # 查询数据库中的板块
            db_section = result.scalar_one_or_none()  # 获取查询结果
            if db_section is not None:  # 如果找到了板块
                for section in context.sections:  # 遍历上下文中的板块
                    if section["id"] == arguments.section_id:  # 如果是目标板块
                        db_section.content = json.dumps(
                            section.get("content", {}), ensure_ascii=False
                        )  # 更新板块内容为JSON格式
                        break  # 找到后退出循环
                db_section.updated_at = utc_now()  # 更新修改时间
                db.add(db_section)  # 将板块添加到数据库
            await db.commit()  # 提交数据库事务

        return ToolResult(
            output=f"Successfully updated section {arguments.section_id}."
        )  # 返回成功结果
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
    def to_api_schema_v2(self, sections: list[dict[str, Any]]) -> dict[str, Any]:
        """生成API Schema v2格式的工具定义。"""
        return {
            "name": self.name,  # 工具名称
            "description": self.description.format(
                content_structures=build_tool_description(sections)
            ),  # 格式化后的工具描述
            "input_schema": self.input_model.model_json_schema(),  # 输入数据的JSON Schema
        }
# 这是工具参数的 JSON Schema 定义，告诉 AI 需要传什么参数。
# 实际内容
# self.input_model.model_json_schema()
# # → 生成这样的 JSON：
# {
#     "type": "object",
#     "properties": {
#         "section_id": {
#             "type": "string",
#             "description": "要更新的板块ID"
#         },
#         "value": {
#             "type": "object",
#             "description": "部分更新对象。标量板块只包含要修改的字段。数组板块传入完整的items/categories数组。"
#         }
#     },
#     "required": ["section_id", "value"]
# }
# AI 看到后知道
# 信息	AI 理解
# section_id	必填，字符串，要传板块 ID
# value	必填，对象，要传更新内容
# 简单说
# model_json_schema() 把 Pydantic 模型转成 JSON 格式，让 AI 知道调用工具时需要传什么参数、参数是什么类型。