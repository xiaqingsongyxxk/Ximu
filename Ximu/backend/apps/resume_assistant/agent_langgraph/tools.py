# 工具定义模块（LangGraph 版）。

# 对应手写版: tools/ 目录（UpdateSectionTool, AddSectionTool, SectionInfoTool, TranslateResumeTool）

# LangChain 用 @tool 装饰器替代了手写的 BaseTool 继承体系：
# - @tool 自动生成 name / description / input_schema
# - 函数类型注解自动转 JSON Schema
# - 运行时参数用 InjectedToolArg 注入

# 与手写版的对应关系：
# ┌──────────────────────┬──────────────────────────────────────────────┐
# │ 手写版 tools/        │ LangGraph 版                               │
# ├──────────────────────┼──────────────────────────────────────────────┤
# │ UpdateSectionTool    │ update_section()                            │
# │ AddSectionTool       │ add_section()                               │
# │ SectionInfoTool      │ section_info()                              │
# │ TranslateResumeTool  │ translate_resume()                          │
# │ BaseTool基类         │ @tool 装饰器                                │
# │ ToolExecutionContext │ InjectedToolArg 注入                        │
# │ ToolResult           │ return str                                  │
# │ input_model          │ 函数参数类型注解                             │
# │ to_api_schema_v2     │ bind_tools 自动生成                          │
# └──────────────────────┴──────────────────────────────────────────────┘

# 功能对齐：所有工具均与手写版行为一致。
# - Pydantic 校验用 SECTION_TYPE_TO_MODEL
# - ID 格式验证用 _ID_FORMAT 正则
# - DB 同步在外部（caller/graph node）处理，工具只改 sections（可变引用）


import asyncio  # 导入异步库，后面翻译功能需要异步调用 LLM
import json  # 导入 JSON 库，后面要序列化和反序列化 JSON 数据
import logging  # 导入日志库，记录运行日志
import re  # 导入正则表达式库，用于验证 ID 格式
import secrets  # 导入 secrets 库，用于生成安全的随机 ID 前缀
import uuid  # 导入 uuid 库，用于生成全局唯一的板块 ID
from collections import Counter  # 导入 Counter 工具，用于统计重复项（检测重复 ID）
from typing import (  # 导入手写版类型注解工具
    Annotated,
    Any,
    Literal,
)  # 手写版在 BaseTool 的 input_model 中用 Pydantic Field，LangGraph 版用 Annotated + Literal

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)  # 导入 LangChain 消息类型（替代手写的 ApiMessageRequest）

# 导入手写版中 ToolExecutionContext 的替代品
# 手写版：ToolExecutionContext(sections=sections, section_id_to_type=id_to_type)
# LangGraph 版：InjectedToolArg 自动注入运行时参数
from langchain_core.tools import (  # 从 langchain_core.tools 导入 (
    InjectedToolArg,
    tool,
)  # InjectedToolArg = "由系统注入的参数，AI 不需要提供"；@tool = "把函数变成 AI 可调用的工具"

from shared.types.messages import (  # 手写版定义的消息类型
    ConversationMessage,
    TextBlock,
)  # LangGraph 版复用，保证两种版本的消息格式一致
from shared.types.resume import (  # 从 shared.types.resume 导入 (
    SECTION_TYPE_TO_MODEL,
)  # 板块类型 → Pydantic 校验模型的映射表，手写版也用这个

log = logging.getLogger(__name__)  # 创建日志记录器，用于记录运行日志（排查问题用）

# ---- ID 生成与验证 ----

_ID_FORMAT_PREFIX_LEN = (  # ID 前缀的长度（4字节）
    4  # 4字节 = 8个十六进制字符（secrets.token_hex(4) 生成 8 位随机字符串）
)
_ID_FORMAT = re.compile(  # 预编译正则表达式
    r"^[0-9a-f]{8}-\d{4}$"
)  # 匹配 "8位十六进制-4位数字" 的 ID 格式，验证 ID 是否合法


def _generate_id(prefix: str, index: int) -> str:  # 定义函数 _generate_id
    # 生成单条 ID。

    # 手写版 tools/update_section.py 里也是同样的逻辑。
    # 这个 ID 用于给简历中的每条记录（比如每段工作经历）分配唯一标识。

    return f"{prefix}-{index:04d}"  # 生成 ID：前缀 + "-" + 4 位数字序号，比如 "a1b2c3d4-0001"


def _assign_ids(
    submitted_items: list, existing_items: list
) -> list:  # 定义函数 _assign_ids
    # 为新条目分配 ID，保留现有条目 ID。

    # 与手写版 tools/update_section.py _assign_ids 完全相同。
    # 可以理解成：新人来报道，有名字的用自己的名字，没名字的给起个名字。

    # 返回值是分配好 ID 的新列表，后面用来替换 sections 中的内容。

    if existing_items:  # 如果已经有旧的条目（不是第一次添加）
        last_id = (  # 取最后一条的 ID
            existing_items[-1].get("id", "")  # 从最后一条的 dict 中取出 "id" 字段
            if isinstance(existing_items[-1], dict)  # 确保最后一条是 dict 类型
            else ""  # 如果不是 dict，给空字符串
        )
        prefix = last_id.split("-")[  # 用 "-" 分割 ID，取第一部分
            0
        ]  # 从最后一条 ID 中取前缀（比如 "a1b2c3d4-0001" 取 "a1b2c3d4"）
        last_index = int(last_id.split("-")[1])  # 取最后的序号（"0001" → 1）
    else:  # 如果没有旧条目（全新的）
        prefix = secrets.token_hex(  # 用 secrets 生成加密安全的随机字符串
            _ID_FORMAT_PREFIX_LEN
        )  # 随机生成一个 8 位十六进制前缀
        last_index = 0  # 序号从 0 开始

    next_index = last_index + 1  # 下一个要分配的序号
    result = []  # 存放分配好 ID 的结果列表
    for item in submitted_items:  # 遍历所有新提交的条目
        if isinstance(item, dict):  # 如果是字典格式的条目
            if "id" not in item or not item["id"]:  # 如果这个条目没有 ID 或者 ID 是空的
                item["id"] = _generate_id(prefix, next_index)  # 给它分配一个新 ID
                next_index += 1  # 序号 +1，下一个条目的序号
            result.append(item)  # 把处理好的条目加入结果列表
        else:  # 如果不是 dict（可能是其他格式）
            result.append(item)  # 原样保留，不修改
    return result  # 返回分配好 ID 的条目列表，后面替换到 sections 里


def _collect_existing_ids(
    items: list[dict],
) -> set[str]:  # 定义函数 _collect_existing_ids
    # 收集已有条目的 ID 集合。

    # 手写版 tools/update_section.py 中也有相同的逻辑。
    # 返回值是一个 set（集合），后面用来验证新提交的 ID 是否在已有 ID 中。

    return {  # 返回一个集合
        item["id"] for item in items if isinstance(item, dict) and item.get("id")
    }  # 遍历每个条目，如果是 dict 且有 id 字段，就把 id 加入集合


def _validate_item_ids_for_tool(  # 定义函数 _validate_item_ids_for_tool
    submitted_items: list[dict], existing_ids: set[str], item_type: str
) -> list[str]:
    # 验证提交的条目 ID 是否有效。

    # 与手写版 translate_resume.py _validate_item_ids 行为一致。
    # 返回值是一个错误信息列表，如果为空表示没有错误。

    # LangGraph 版和手写版的区别：
    # - 手写版：这个方法在 TranslateResumeTool 类内部
    # - LangGraph 版：作为独立函数，被 update_section 和 translate_resume 两个 @tool 函数共用

    errors = []  # 初始化错误列表，用来存放发现的错误
    submitted_ids: list[str] = []  # 初始化已提交的 ID 列表

    for i, item in enumerate(submitted_items):  # 遍历提交的每个条目（i 是序号）
        if not isinstance(item, dict):  # 如果条目不是 dict 格式
            continue  # 跳过，不处理
        item_id = item.get("id")  # 取出条目的 id 字段
        field_path = f"{item_type}[{i}]"  # 生成字段路径，比如 "items[3]"，错误时告诉用户具体哪里错了

        if not item_id:  # 如果条目没有 id
            continue  # 新条目不需要 ID，跳过验证
        if not _ID_FORMAT.match(
            str(item_id)
        ):  # 如果 ID 格式不合法（不是 "8位十六进制-4位数字"）
            errors.append(  # 添加错误：格式不对
                f"  - {field_path}.id '{item_id}': invalid format."
            )
            continue  # 跳过这个条目
        if item_id not in existing_ids:  # 如果 ID 不在已有的 ID 集合中
            errors.append(  # 添加错误：找不到这个 ID
                f"  - {field_path}.id '{item_id}': not found in original content."
            )
            continue  # 跳过这个条目
        submitted_ids.append(item_id)  # 把合法的 ID 加入已提交列表

    duplicates = [  # 找出在 submitted_ids 中出现次数 > 1 的 ID
        id_ for id_, count in Counter(submitted_ids).items() if count > 1
    ]  # Counter 统计每个 ID 出现的次数
    if duplicates:  # 如果有重复的 ID
        errors.append(f"  - Duplicate IDs found: {duplicates}.")  # 添加重复错误

    return errors  # 返回所有错误列表，调用方判断是否为空来决定是否继续

    # ====================================================================
    # 工具 1: update_section
    # 对应手写版: tools/update_section.py UpdateSectionTool
    # ====================================================================
    # 手写版：class UpdateSectionTool(BaseTool): → def execute(self, args, context)
    # LangGraph 版：@tool def update_section(section_id, value, sections, section_id_to_type)
    # 区别：手写版需要继承 BaseTool 并实现 execute 方法，LangGraph 版加个 @tool 就行了


@tool  # @tool 是 LangChain 的装饰器，把函数变成"AI 可以调用的工具"
def update_section(  # 定义"更新板块"工具函数
    section_id: Annotated[
        str, "要更新的板块 ID"
    ],  # 告诉 AI：这个参数是要更新的板块的 ID
    value: Annotated[  # 告诉 AI：这个参数是要更新的内容
        dict,
        "部分更新对象。标量板块（personal_info, summary）只包含要修改的字段。数组板块传入完整的 items/categories 数组。",
    ],
    sections: Annotated[
        list[dict], InjectedToolArg
    ],  # InjectedToolArg 标记：这个参数由系统注入（不是 AI 提供的）
    # 手写版通过 ToolExecutionContext.sections 注入，LangGraph 版通过 InjectedToolArg 注入
    section_id_to_type: Annotated[
        dict[str, str], InjectedToolArg
    ],  # 同样由系统注入：板块 ID → 类型映射
) -> str:  # 返回一个字符串（成功或失败的消息）
    # Update the content of a specific resume section using a partial update object.

    # 对应手写版 UpdateSectionTool.execute()。
    # 行为完全一致：验证 section_id → 验证数据（Pydantic） → 验证 ID 格式 → 分配 ID → 更新 sections。

    section_type = (
        section_id_to_type.get(  # 将 section_id_to_type.get( 赋值给 section_type
            section_id
        )
    )  # 通过 ID 查这个板块是什么类型（比如 work_experience）
    if section_type is None:  # 如果查不到，说明 ID 无效
        return f"Unknown Section ID: {section_id}"  # 返回错误消息：不知道这个 ID

    # 1. 查找目标板块
    target_section = None  # 初始化目标板块为 None
    for section in sections:  # 遍历所有板块
        if section["id"] == section_id:  # 如果找到 ID 匹配的板块
            target_section = section  # 记下这个板块
            break  # 找到了，跳出循环

    if target_section is None:  # 如果遍历完了还没找到
        return f"Section {section_id} not found."  # 返回错误消息：没找到这个板块

    content = target_section.get(  # 将 target_section.get( 赋值给 content
        "content", {}
    )  # 取出这个板块的内容字典（比如 {"items": [...]}）

    # 2. Pydantic 数据校验
    model = SECTION_TYPE_TO_MODEL.get(  # 将 SECTION_TYPE_TO_MODEL.get( 赋值给 model
        section_type
    )  # 根据板块类型找到对应的 Pydantic 校验模型
    if model is None:  # 如果没有对应的校验模型
        return f"Unknown section type: {section_type}"  # 返回错误：未知的板块类型

    try:  # 开始数据校验（可能会抛异常）
        if section_type in (
            "personal_info",
            "summary",
            "custom",
        ):  # 如果是"单值"类型板块（一个人只有一个个人信息、一个摘要）
            model.model_validate(value)  # 直接用 Pydantic 校验整个 value
        elif section_type in (  # 如果是"列表"类型板块
            "work_experience",
            "education",
            "projects",
            "certifications",
            "languages",
            "github",
        ):
            for item_data in value.get("items", []):  # 遍历 value 里的每一条数据
                model.model_validate(item_data)  # 逐条用 Pydantic 校验
        elif section_type == "skills":  # 如果是"技能"板块（结构不同，有 categories）
            for cat_data in value.get("categories", []):  # 遍历每个分类
                model.model_validate(cat_data)  # 逐条校验
    except Exception as e:  # 如果校验过程中有任意一条数据不合法
        return f"[{section_type}] Validation failed: {e}"  # 返回校验失败消息，告诉 AI 哪里错了

    # 3. ID 格式验证 + 分配
    if section_type in (  # 如果是列表类型的板块
        "work_experience",
        "education",
        "projects",
        "certifications",
        "languages",
        "github",
    ):
        existing_ids = (
            _collect_existing_ids(  # 将 _collect_existing_ids( 赋值给 existing_ids
                content.get("items", [])
            )
        )  # 从已有的 items 中收集所有 ID
        id_errors = _validate_item_ids_for_tool(  # 验证提交的 item ID 是否合法
            value.get("items", []), existing_ids, "items"
        )
        if id_errors:  # 如果验证有错误
            return f"[{section_type}] Item ID validation failed:\n" + "\n".join(
                id_errors  # 把所有错误拼成一段文字返回
            )
            content["items"] = _assign_ids(  # 将 _assign_ids( 赋值给 content["items"]
                value.get("items", []), content.get("items", [])
            )  # 给新条目分配 ID，然后替换原内容
    elif (
        section_type == "skills"
    ):  # 如果是技能板块（结构不同，没有 items 而是 categories）
        existing_ids = (
            _collect_existing_ids(  # 将 _collect_existing_ids( 赋值给 existing_ids
                content.get("categories", [])
            )
        )  # 收集已有的分类 ID
        id_errors = _validate_item_ids_for_tool(  # 验证提交的分类 ID 是否合法
            value.get("categories", []), existing_ids, "categories"
        )
        if id_errors:  # 如果有 ID 错误
            return (
                f"[{section_type}] Category ID validation failed:\n"
                + "\n".join(  # 返回所有 ID 错误消息
                    id_errors
                )
            )
        content["categories"] = _assign_ids(  # 为新的分类分配 ID，替换原来的分类数据
            value.get("categories", []), content.get("categories", [])
        )
    elif section_type in (
        "personal_info",
        "summary",
    ):  # 如果是个人信息或摘要（不需要 ID 校验）
        content.update(value)  # 直接更新对应字段（只改传进来的字段）

    return f"Successfully updated section {section_id}."  # 返回成功消息给 AI

    # ====================================================================
    # 工具 2: add_section
    # 对应手写版: tools/add_section.py AddSectionTool
    # ====================================================================


@tool  # @tool 装饰器：把函数变成 AI 可调用的工具，自动生成 name/description/input_schema
def add_section(  # 定义函数 add_section
    type: Annotated[  # type 是 Python 关键字，但这里用作参数名
        str,
        "板块类型，如 work_experience, education, skills, summary, projects, certifications, languages, github, qr_codes, custom",
    ],  # 告诉 AI 可以添加哪些类型的板块
    title: Annotated[str, "板块的显示标题"],  # 告诉 AI 这个参数是板块的标题
    sections: Annotated[
        list[dict], InjectedToolArg
    ],  # InjectedToolArg：由系统注入的 sections 列表
    section_id_to_type: Annotated[
        dict[str, str], InjectedToolArg
    ],  # InjectedToolArg：由系统注入的 ID→类型映射
) -> str:  # 返回字符串（成功或失败）
    # Add a new section to the resume.

    # 对应手写版 AddSectionTool.execute()。
    # 行为一致：检查重复 → 创建板块 → 追加到 sections → 排序。

    # 检查是否已存在相同类型（custom 除外）
    existing_types = {  # 将 { 赋值给 existing_types
        s.get("type") for s in sections
    }  # 收集所有已有板块的类型，放到一个集合里
    if (
        type in existing_types and type != "custom"
    ):  # 如果这个类型已经存在（而且不是 custom 类型）
        return (
            f"Section of type '{type}' already exists"  # 返回错误：这个类型已经存在了
        )

    resume_id = (  # 将 ( 赋值给 resume_id
        sections[0]["resume_id"] if sections else "unknown"
    )  # 取第一个板块的 resume_id
    next_sort_order = (  # 将 ( 赋值给 next_sort_order
        sections[-1]["sort_order"] + 1 if sections else 0
    )  # 新的排序序号 = 最后一个板块的序号 + 1

    new_id = str(uuid.uuid4())  # 生成一个全局唯一的 ID（uuid4 是随机 UUID）
    new_section = {  # 构建新的板块字典
        "id": new_id,  # 唯一 ID
        "type": type,  # 板块类型
        "title": title,  # 显示标题
        "resume_id": resume_id,  # 所属简历的 ID
        "sort_order": next_sort_order,  # 排序序号
        "content": {},  # 初始内容为空
    }

    sections.append(new_section)  # 把新板块追加到 sections 列表末尾
    sections.sort(
        key=lambda x: x.get(
            "sort_order", 0
        )  # 将 lambda x: x.get("sort_order",  赋值给 key
    )  # 按 sort_order 重新排序（新板块插到正确位置）

    # 更新 id_to_type
    section_id_to_type[new_id] = type  # 在新的 ID → 类型映射中注册

    return f"Successfully added section {new_id}."  # 返回成功消息给 AI

    # ====================================================================
    # 工具 3: section_info
    # 对应手写版: tools/section_info.py SectionInfoTool
    # ====================================================================


_SECTION_DEFINITIONS: dict[str, str] = {  # 定义所有板块类型的字段说明字典
    # 手写版在 SectionInfoTool 类中也有同样的定义
    # LangGraph 版作为模块级变量，供 section_info 工具使用
    "personal_info": (  # 个人信息板块的字段说明
        "# 个人信息板块的字段说明\n"
        "Personal Information Section\n"
        "Contains the card owner's basic identifying information.\n"
        "Fields:\n"
        "- full_name (string): Full legal name\n"
        "- job_title (string): Target position/intended role\n"
        "- email (string): Contact email address\n"
        "- phone (string): Contact phone number\n"
        "- location (string): Current city of residence\n"
        "- salary (string): Expected salary range\n"
        "- age (string): Age\n"
        "- gender (string): Gender\n"
        "- political_status (string): Political affiliation\n"
        "- education_level (string): Highest education level\n"
        "- ethnicity (string): Ethnicity\n"
        "- hometown (string): Hometown\n"
        "- marital_status (string): Marital status\n"
        "- years_of_experience (string): Years of work experience\n"
        "- wechat (string): WeChat ID\n"
        "- website (string): Personal website\n"
        "- linkedin (string): LinkedIn profile"
    ),
    "summary": (  # 个人摘要板块的字段说明
        "# 个人摘要板块的字段说明\n"
        "Personal Summary Section\n"
        "A narrative paragraph introducing the card owner.\n"
        "Fields:\n"
        "- text (text): Free-form introduction text"
    ),
    "work_experience": (  # 工作经历板块的字段说明
        "# 工作经历板块的字段说明\n"
        "Work Experience Section\n"
        "List of past employment and professional positions.\n"
        'Structure: Contains an "items" array.\n'
        "Each item:\n"
        "- id (string): Unique identifier\n"
        "- company (string): Organization name\n"
        "- position (string): Job title/role\n"
        "- location (string): Work location\n"
        "- start_date (string): Start date in YYYY-MM format\n"
        '- end_date (string): End date or "Present"\n'
        "- current (boolean): Whether this is the current job\n"
        "- description (text): Detailed job description\n"
        "- technologies (array[string]): Tech stack\n"
        "- highlights (array[string]): Key achievements"
    ),
    "education": (  # 教育背景板块的字段说明
        "# 教育背景板块的字段说明\n"
        "Education Background Section\n"
        "List of educational history entries.\n"
        'Structure: Contains an "items" array.\n'
        "Each item:\n"
        "- id (string): Unique identifier\n"
        "- institution (string): School/university name\n"
        "- degree (string): Degree earned\n"
        "- field (string): Major/field of study\n"
        "- location (string): Geographic location\n"
        "- start_date (string): Enrollment date\n"
        "- end_date (string): Expected graduation date\n"
        "- gpa (string): Grade point average\n"
        "- highlights (array[string]): Honors/achievements"
    ),
    "skills": (  # 技能板块的字段说明
        "# 技能板块的字段说明\n"
        "Skills Section\n"
        "Skills organized by category.\n"
        'Structure: Contains a "categories" array.\n'
        "Each category:\n"
        "- id (string): Unique identifier\n"
        "- name (string): Category name\n"
        "- skills (array[string]): List of skills in this category"
    ),
    "languages": (  # 语言能力板块的字段说明
        "# 语言能力板块的字段说明\n"
        "Language Proficiency Section\n"
        "List of languages the person can use.\n"
        'Structure: Contains an "items" array.\n'
        "Each item:\n"
        "- id (string): Unique identifier\n"
        "- language (string): Language name\n"
        "- proficiency (string): Proficiency level\n"
        "- description (string): Additional notes"
    ),
    "projects": (  # 项目经验板块的字段说明
        "# 项目经验板块的字段说明\n"
        "Project Experience Section\n"
        "List of independent projects or portfolio items.\n"
        'Structure: Contains an "items" array.\n'
        "Each item:\n"
        "- id (string): Unique identifier\n"
        "- name (string): Project name\n"
        "- description (text): Detailed project description\n"
        "- technologies (array[string]): Tech stack\n"
        "- highlights (array[string]): Key features/achievements\n"
        "- url (string): Project link\n"
        "- start_date (string): Start date\n"
        "- end_date (string): End date"
    ),
    "certifications": (  # 证书板块的字段说明
        "# 证书板块的字段说明\n"
        "Certifications Section\n"
        "List of professional certifications and qualifications.\n"
        'Structure: Contains an "items" array.\n'
        "Each item:\n"
        "- id (string): Unique identifier\n"
        "- name (string): Certification name\n"
        "- issuer (string): Issuing organization\n"
        "- date (string): Date obtained\n"
        "- description (string): Certification description"
    ),
    "github": (  # GitHub 项目板块的字段说明
        "# GitHub 项目板块的字段说明\n"
        "GitHub Projects Section\n"
        "Showcase of GitHub repositories.\n"
        'Structure: Contains an "items" array.\n'
        "Each item:\n"
        "- id (string): Unique identifier\n"
        "- repo_url (string): GitHub repository URL\n"
        "- name (string): Repository name\n"
        "- stars (int): Number of stars received\n"
        "- language (string): Primary programming language\n"
        "- description (text): Repository description"
    ),
    "qr_codes": (  # 二维码板块的字段说明
        "# 二维码板块的字段说明\n"
        "QR Codes Section\n"
        "Collection of QR code links.\n"
        'Structure: Contains an "items" array (may be empty).\n'
        "Each item:\n"
        "- id (string): Unique identifier\n"
        "- url (string): URL the QR code points to\n"
        "- label (string): Display label for the QR code"
    ),
    "custom": (  # 自定义板块的字段说明
        "# 自定义板块的字段说明\n"
        "Custom Section\n"
        "User-defined section for miscellaneous content like competitions.\n"
        'Structure: Contains an "items" array.\n'
        "Each item:\n"
        "- id (string): Unique identifier\n"
        "- title (string): Item title\n"
        "- description (text): Item description\n"
        "- date (string): Date range"
    ),
}  # 这个字典是给 section_info 工具用的，AI 查询某个板块类型时返回对应的字段说明


@tool  # @tool 装饰器：把函数变成 AI 可调用的工具
def section_info(  # 定义函数 section_info
    type: Annotated[  # 参数：要查询的板块类型
        Literal[  # Literal 限定 AI 只能从这些值中选择
            "personal_info",
            "summary",
            "work_experience",
            "projects",
            "education",
            "skills",
            "languages",
            "certifications",
            "qr_codes",
            "github",
            "custom",
        ],
        "要查询定义的板块类型",  # 告诉 AI 这个参数的含义
    ],
) -> str:  # 返回一个字符串（板块的字段定义）
    # 获取指定板块类型的详细字段定义。

    # 对应手写版 SectionInfoTool.execute()。
    # 行为完全一致。

    return _SECTION_DEFINITIONS.get(
        type, f"Unknown section type: {type}"
    )  # 从字典中查找并返回对应板块的字段说明

    # ====================================================================
    # 工具 4: translate_resume
    # 对应手写版: tools/translate_resume.py TranslateResumeTool
    # ====================================================================


_MAX_RETRIES = 5  # 翻译失败时的最大重试次数


def _is_content_empty(
    content: dict, section_type: str
) -> bool:  # 定义函数 _is_content_empty
    # 检查板块内容是否为空。

    # 手写版 TranslateResumeTool 中也有相同的检查逻辑。
    # 返回值给 translate_resume 工具用，跳过空板块不翻译。

    if not content:  # 如果内容字典为空（比如 {}）
        return True  # 返回 True：是空的
    if section_type in ("personal_info", "summary", "custom"):  # 如果是单值板块
        return not any(
            content.values()
        )  # 检查所有字段的值是否都是空的（any 有值就返回 True，取反就是 False）
    if section_type in (  # 如果是列表板块
        "work_experience",
        "education",
        "projects",
        "certifications",
        "languages",
        "github",
    ):
        return not content.get("items")  # 检查 items 列表是否为空
    if section_type == "skills":  # 如果是技能板块
        return not content.get("categories")  # 检查 categories 列表是否为空
    return False  # 其他情况默认不是空的


def _validate_translated_content(  # 定义函数 _validate_translated_content
    content: dict, section_type: str, original_content: dict
) -> tuple[bool, str | None]:
    # 验证翻译后的内容。与手写版 validate_translated_content 行为一致。

    # 返回值是 (是否通过验证, 错误信息)。
    # 通过验证后内容才能更新到 sections 中。

    model = SECTION_TYPE_TO_MODEL.get(  # 将 SECTION_TYPE_TO_MODEL.get( 赋值给 model
        section_type
    )  # 根据板块类型找到对应的 Pydantic 校验模型
    if model is None:  # 如果没有对应的校验模型
        return False, f"Unknown section type: {section_type}"  # 返回验证失败

    try:  # 尝试进行数据校验
        if section_type in ("personal_info", "summary", "custom"):  # 单值板块
            model.model_validate(content)  # 直接用 Pydantic 校验整个 content
        elif section_type in (  # 列表板块
            "work_experience",
            "education",
            "projects",
            "certifications",
            "languages",
            "github",
        ):
            for item_data in content.get("items", []):  # 遍历每个条目
                model.model_validate(item_data)  # 逐条校验
        elif section_type == "skills":  # 技能板块
            for cat_data in content.get("categories", []):  # 遍历每个分类
                model.model_validate(cat_data)  # 逐条校验
    except Exception as e:  # 校验出错
        return False, f"[{section_type}] Schema validation failed: {e}"  # 返回失败原因

    # ID 验证
    existing_ids = (  # 收集已有 ID
        {
            item["id"]
            for item in original_content.get("items", [])
            if isinstance(item, dict) and item.get("id")
        }  # 遍历原内容的 items，取出所有有 ID 的条目的 ID
        if section_type not in ("personal_info", "summary", "custom", "skills")
        else set()  # 单值板块没有 ID，直接返回空集合
    )

    if section_type == "skills":  # 如果是技能板块（结构不同）
        existing_ids = {  # 从 categories 中收集 ID
            cat["id"]
            for cat in original_content.get("categories", [])
            if isinstance(cat, dict) and cat.get("id")
        }

    if section_type in (  # 如果是列表板块
        "work_experience",
        "education",
        "projects",
        "certifications",
        "languages",
        "github",
    ):
        id_errors = _validate_item_ids_for_tool(  # 验证翻译后内容的 ID
            content.get("items", []), existing_ids, "items"
        )
        if id_errors:  # 如果有 ID 错误
            return False, f"[{section_type}] ID validation failed:\n" + "\n".join(
                id_errors  # 拼接所有错误
            )
    elif section_type == "skills":  # 如果是技能板块
        id_errors = _validate_item_ids_for_tool(  # 验证分类 ID
            content.get("categories", []), existing_ids, "categories"
        )
        if id_errors:  # 如果有错误
            return False, f"[{section_type}] ID validation failed:\n" + "\n".join(
                id_errors
            )

    return True, None  # 所有验证都通过了，返回 True


@tool  # @tool 装饰器（这个工具是 async 的，因为需要异步调用 LLM）
async def translate_resume(  # 定义异步函数 translate_resume
    target_language: Annotated[
        str, "目标语言代码，如 zh, en"
    ],  # AI 告诉我们要翻译成什么语言
    section_id: Annotated[
        str | None, "要翻译的板块 ID，省略则翻译整个简历"
    ] = None,  # 可选参数：只翻译某个板块
    sections: Annotated[list[dict], InjectedToolArg] = None,  # 由系统注入：简历板块列表
    section_id_to_type: Annotated[
        dict[str, str], InjectedToolArg
    ] = None,  # 由系统注入：ID→类型映射
    llm: Annotated[Any, InjectedToolArg] = None,  # 由系统注入：LangChain LLM 实例
) -> str:  # 返回翻译结果（成功或失败信息）
    # Translate a resume (or a specific section) to the target language.

    # 对应手写版 TranslateResumeTool.execute()。
    # 行为完全一致：调用 LLM 翻译 → 重试 → JSON repair → 校验 → 更新 sections。
    # DB 同步在外部处理。

    if (
        not sections or not section_id_to_type
    ):  # 如果 sections 或 id_to_type 为空（注入失败）
        return "Error: sections context not available"  # 返回错误

    if (
        section_id is not None and section_id not in section_id_to_type
    ):  # 如果指定了 ID 但找不到
        return f"Invalid section ID: {section_id}"  # 返回错误：无效 ID

    target_sections = (  # 确定要翻译哪些板块
        [s for s in sections if s["id"] == section_id]  # 如果指定了 ID，只翻译那个板块
        if section_id is not None
        else list(sections)  # 否则翻译所有板块
    )

    # 过滤空板块
    non_empty = [  # 筛选出"非空"的板块
        s for s in target_sections if _is_content_empty(s.get("content", {}), s["type"])
    ]  # _is_content_empty 返回 True 表示"是空的"，这里取反所以是"非空"
    skipped = len(target_sections) - len(non_empty)  # 跳过了多少个空板块

    if not non_empty:  # 如果没有需要翻译的内容
        return "No content to translate."  # 返回：没有需要翻译的

    # 构建翻译请求
    system_prompt = _build_translate_system_prompt(  # 将 _build_translate_system_prompt 赋值给 system_prompt
        target_language
    )  # 构建系统提示词，告诉 LLM 要翻译成什么语言
    user_prompt = _build_translate_user_prompt(  # 将 _build_translate_user_prompt( 赋值给 user_prompt
        non_empty
    )  # 构建用户提示词，把板块内容发给 LLM

    messages: list[ConversationMessage] = [  # 构建消息列表
        ConversationMessage.from_user_text(user_prompt)
    ]  # 把用户提示词包装成手写版的消息格式

    section_map: dict[str, dict] = {  # 将 { 赋值给 section_map: dict[str, dict]
        s["id"]: s for s in sections
    }  # 创建板块 ID → 板块本身的映射，翻译成功后直接更新

    import json_repair  # lazy import for availability（延迟导入，万一没装 json_repair 也不影响主功能）

    for attempt in range(1, _MAX_RETRIES + 1):  # 重试循环，最多 _MAX_RETRIES 次
        raw_content, call_error = await _call_translation(  # 调用 LLM 进行翻译
            llm, messages, system_prompt
        )
        if call_error:  # 如果调用出错
            return f"Translation failed: {call_error}"  # 返回错误

        try:  # 尝试解析 LLM 返回的 JSON
            translated_list = (
                json_repair.loads(  # 将 json_repair.loads( 赋值给 translated_list
                    raw_content
                )
            )  # 用 json_repair 解析（可以自动修复一些 JSON 语法错误）
            if not isinstance(translated_list, list):  # 如果解析结果不是列表
                raise ValueError(
                    f"Expected list, got {type(translated_list).__name__}"
                )  # 抛出错误
        except Exception as e:  # 解析出错
            return f"Translation failed: JSON parse error: {e}"  # 返回错误

        # 验证翻译结果
        results: list[dict] = []  # 存放每个板块的翻译结果
        all_valid = True  # 标记是否所有板块都验证通过
        for i, translated_item in enumerate(
            translated_list
        ):  # 遍历翻译结果中的每个板块
            if i >= len(non_empty):  # 如果超出原板块数量
                break  # 停止
            original = non_empty[i]  # 原板块
            sec_id = original["id"]  # 板块 ID
            sec_type = original["type"]  # 板块类型
            original_content = original.get("content", {})  # 原内容
            new_content = translated_item.get("content", {})  # 翻译后的新内容

            is_valid, error_msg = _validate_translated_content(  # 验证翻译结果是否合法
                new_content, sec_type, original_content
            )

            if is_valid:  # 如果验证通过
                if sec_id in section_map:  # 如果在映射表中能找到这个板块
                    section_map[sec_id]["content"] = new_content  # 直接更新板块内容
                results.append(  # 记录成功结果
                    {"success": True, "section_id": sec_id, "section_type": sec_type}
                )
            else:  # 如果验证失败
                all_valid = False  # 标记为"不是全部通过"
                results.append(  # 记录失败结果
                    {
                        "success": False,
                        "section_id": sec_id,
                        "section_type": sec_type,
                        "error": error_msg,
                    }
                )

        if all_valid:  # 如果所有板块都通过了验证
            # 构建结果报告
            lines = [  # 构建成功的行
                f"✓ {r['section_id']} ({r['section_type']})"
                for r in results
                if r["success"]
            ]
            if skipped:  # 如果有跳过的空板块
                lines.append(
                    f"Skipped {skipped} empty section(s)"
                )  # 加入"跳过了 N 个空板块"
            lines.append(  # 加入总结
                f"\nTotal: {len(non_empty)} translated, {sum(1 for r in results if r['success'])} succeeded"
            )
            return "\n".join(lines)  # 返回格式化的结果报告

        # 重试：将错误信息发给 LLM 修复
        messages.append(  # 把 LLM 刚才的输出追加到消息历史
            ConversationMessage(
                role="assistant", content=[TextBlock(text=raw_content)]
            )  # 将 "assistant", content=[TextBloc 赋值给 ConversationMessage(role
        )
        error_summary_parts = []  # 收集错误信息
        for r in results:  # 遍历每个结果
            if not r["success"]:  # 如果失败了
                error_summary_parts.append(  # 添加错误描述
                    f"**Section {r['section_id']} ({r['section_type']}) errors:**\n{r['error']}"
                )

        retry_msg = (  # 构建重试消息
            "Some sections failed validation. Please fix ALL sections below "
            "and return the complete corrected JSON array.\n\n"
            + "\n\n".join(error_summary_parts)
        )
        messages.append(
            ConversationMessage.from_user_text(retry_msg)
        )  # 把重试指令追加到消息历史

        if attempt < _MAX_RETRIES:  # 如果还没到最大重试次数
            await asyncio.sleep(
                0.5 * attempt
            )  # 等一会儿再重试（递增等待：0.5s, 1s, 1.5s...）

    return f"Translation failed after {_MAX_RETRIES} attempts."  # 所有重试都失败了


def _build_translate_system_prompt(
    target_language: str,
) -> str:
    # 构建翻译系统提示词。与手写版 build_system_prompt 一致。

    # 返回值是一个字符串，告诉 LLM 它的角色是翻译官。
    return f"""\
You will receive a JSON array of resume sections.
Your task is to translate the resume content to {target_language}.
Return a JSON array only, no explanation.
Keep the original JSON array structure and order.
"""


def _build_translate_user_prompt(
    sections: list[dict],
) -> str:
    # 构建翻译用户提示词。与手写版 build_sections_user_prompt 一致。

    # 返回值是一个字符串，包含要翻译的板块内容的 JSON。
    filtered = [
        {k: v for k, v in s.items() if k not in ("updated_at", "created_at")}
        for s in sections
    ]
    return f"""\
Here is the JSON resume content:

---
{json.dumps(filtered, indent=2, ensure_ascii=False)}
---
"""


async def _call_translation(  # 定义异步函数 _call_translation
    llm: Any,  # LangChain LLM 实例
    messages: list[ConversationMessage],  # 消息列表
    system_prompt: str | None,  # 系统提示词
) -> tuple[str, str | None]:  # 返回 (翻译内容, 错误信息)
    # 执行单次翻译 LLM 调用。与手写版 _call_translation 行为一致。

    # 手写版直接调用 api_client.stream_message()。
    # LangGraph 版用 LangChain 的 llm.ainvoke()，行为等价。
    # 返回值是 (翻译文本, 错误信息)，给 translate_resume 工具用。

    if llm is None:  # 如果 LLM 未注入
        return (
            "",
            "Translation client not available (llm not injected)",
        )  # 返回错误

    try:  # 尝试调用 LLM
        # 将手写版 ConversationMessage 转为 LangChain 消息
        lc_messages: list = []  # 构建 LangChain 消息列表
        if system_prompt:  # 如果有系统提示词
            lc_messages.append(
                SystemMessage(content=system_prompt)
            )  # 加入系统提示词消息
        for msg in messages:  # 遍历每条消息
            text = "".join(  # 提取所有文本块拼接成纯文本
                b.text for b in msg.content if isinstance(b, TextBlock)
            )
            if msg.role == "user":  # 用户消息
                lc_messages.append(HumanMessage(content=text))
            elif msg.role == "assistant":  # AI 消息
                lc_messages.append(AIMessage(content=text))

        # 用 LangChain LLM 一次调用（非流式），获取完整响应
        response = await llm.ainvoke(lc_messages)
        accumulated_content = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )  # 提取文本内容

        if not accumulated_content:  # 如果没有累积到任何内容
            return "", "No content in response"  # 返回错误
        return accumulated_content, None  # 返回翻译好的内容和空错误
    except Exception as e:  # 如果调用过程中出错
        return "", f"Stream error: {type(e).__name__}: {e}"  # 返回错误

    # ====================================================================
    # 工具列表（用于 bind_tools 和 ToolNode）
    # ====================================================================


tools = [  # 将 [ 赋值给 tools
    update_section,
    add_section,
    section_info,
    translate_resume,
]  # 所有工具的列表
# 所有工具的列表，供 LangChain 的 bind_tools() 和 ToolNode 使用。

# 对应手写版 ToolRegistry 中注册的工具。

# 手写版：
# tool_registry = ToolRegistry()
# tool_registry.register(UpdateSectionTool())
# tool_registry.register(AddSectionTool())
# tool_registry.to_api_schema_v2(sections)  # 手动生成 JSON Schema

# LangGraph 版：
# tools = [update_section, add_section, section_info, translate_resume]
# llm.bind_tools(tools)  # 自动生成 JSON Schema 并绑定到 LLM
