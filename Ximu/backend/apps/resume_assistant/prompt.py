"""简历助手的提示词构建模块。

本模块定义了AI简历助手使用的提示词：
1. SYSTEM - 系统提示词，定义AI角色和行为规则
2. SUB_SYSTEM - 子系统提示词，用于JD优化场景
3. JD_ANALYSIS - JD分析结果的提示词模板
4. build_sections_prompt - 构建板块列表提示词
5. build_jd_prompt - 构建JD分析提示词
"""  # 模块文档字符串

from typing import Any  # 导入Any类型

from shared.models import utc_now  # 导入获取当前时间的函数
from shared.types.jd_analysis import (  # 导入JD分析相关类型
    JobDescriptionAnalysisSchema,
    SuggestionItem,
)


def build_sections_prompt(sections: list[dict]) -> str:
    """构建板块列表的提示词文本。

    将板块列表格式化为可读的文本，用于系统提示词。

    Args:
        sections: 板块字典列表。

    Returns:
        格式化的板块列表文本。
    """
    lines = []  # 创建空列表，用来存放格式化后的板块描述行
    for section in sections:  # 遍历每个板块
        lines.append(
            f'  - [{section["type"]}] "{section["title"]}" (section_id: {section["id"]})'
        )  # 把板块的类型、标题、ID格式化成一行文本，添加到列表中
    return "\n".join(
        lines
    )  # 用换行符把所有行拼接成一个字符串返回，后续插入到系统提示词里


def build_jd_prompt(
    jd_analysis: JobDescriptionAnalysisSchema,
    sections: list[dict[str, Any]],
) -> str:
    """构建JD分析结果的提示词。

    将JD分析结果格式化为可读文本，用于指导简历优化。

    Args:
        jd_analysis: JD分析结果。
        sections: 板块列表。

    Returns:
        格式化的JD分析提示词。
    """
    now = utc_now().isoformat()  # 当前时间
    jd_analysis_time = (
        jd_analysis.created_at.isoformat() if jd_analysis.created_at else "N/A"
    )  # 获取JD分析的时间，如果没分析过就显示"N/A"，后续展示给用户看

    # 构建板块ID到类型的映射，后续用来把建议按板块类型分组
    section_id_to_type = {s["id"]: s["type"] for s in sections}

    # 按板块类型分组建议，同一个板块的建议放在一起
    suggestions_by_section: dict[str, list[SuggestionItem]] = {}
    for sug in jd_analysis.suggestions:  # 遍历所有建议
        sec_type = section_id_to_type.get(
            sug.section_id, sug.section_id
        )  # 把板块ID转成板块类型名
# 如果用户后续删了某个板块再重新分析（或者板块ID变了），JD 分析结果里的 sug.section_id 就在当前 sections 里找不到了。
# 用 .get(key, key) 就是为了处理这种情况：
# 情况	section_id_to_type.get(sug.section_id, sug.section_id)
# 板块还在	返回 "work_experience"
# 板块已被删	key 不在 section_id_to_type 里，返回默认值 sug.section_id 本身
# 直接写 section_id_to_type[sug.section_id] 虽然更短，但会抛 KeyError。这种写法就是宁可用原始ID凑合展示，也不能让整个流程崩掉。
#dict.get(key, default)
# #      ↑查什么   ↑找不到时返回什么
        if sec_type not in suggestions_by_section:  # 如果这个板块类型还没创建分组
            suggestions_by_section[sec_type] = []  # 创建空列表
        suggestions_by_section[sec_type].append(sug)  # 把建议添加到对应板块的分组中
# # 初始状态
# suggestions_by_section = {}  # 空字典
# # 第1条建议（work_experience）
# sec_type = "work_experience"
# # 发现不在字典里 → 创建空列表
# suggestions_by_section = {"work_experience": []}
# # 添加建议
# suggestions_by_section = {"work_experience": [sug1]}
# # 第2条建议（work_experience）
# sec_type = "work_experience"
# # 发现已在字典里 → 直接添加
# suggestions_by_section = {"work_experience": [sug1, sug2]}
# # 第3条建议（education）
# sec_type = "education"
# # 发现不在字典里 → 创建空列表
# suggestions_by_section = {"work_experience": [sug1, sug2], "education": []}
# # 添加建议
# suggestions_by_section = {"work_experience": [sug1, sug2], "education": [sug3]}
    # 格式化建议，把每个板块的建议转换成可读的文本
    suggestions_lines = []  # 创建空列表，用来存放格式化后的建议行
    for (
        sec_type,
        items,
    ) in suggestions_by_section.items():  # 遍历每个板块类型和它的建议列表
#         内容示例
# suggestions_by_section = {
#     "work_experience": [
#         SuggestionItem(section_id="xxx-0002", current="前端工程师", suggested="高级前端工程师"),
#         SuggestionItem(section_id="xxx-0002", current="3年经验", suggested="3年React/Vue经验"),
#     ],
#     "education": [
#         SuggestionItem(section_id="xxx-0003", current="本科", suggested="计算机科学本科"),
#     ],
#     "personal_info": [
#         SuggestionItem(section_id="xxx-0001", current="张三", suggested="张三 | 高级前端工程师"),
#     ]
# }
# items() 返回
# suggestions_by_section.items()
# # → 返回键值对列表：
# [
#     ("work_experience", [sug1, sug2]),
#     ("education", [sug3]),
#     ("personal_info", [sug4])
# ]
# 遍历后
# for sec_type, items in suggestions_by_section.items():
#     print(sec_type)   # 板块类型
#     print(items)      # 该板块的建议列表
# "work_experience"
# [SuggestionItem(...), SuggestionItem(...)]
# "education"
# [SuggestionItem(...)]
# "personal_info"
# [SuggestionItem(...)]
        suggestions_lines.append(f"### [{sec_type}]")  # 添加板块类型标题
        for item in items:  # 遍历该板块下的每条建议
            suggestions_lines.append(f"- **Current**: {item.current}")  # 添加当前内容
            suggestions_lines.append(
                f"  **Suggested**: {item.suggested}"
            )  # 添加建议内容
        suggestions_lines.append("")  # 添加空行分隔不同板块

    suggestions_text = "\n".join(suggestions_lines)  # 把所有建议行拼接成一个字符串

    # 构建JD分析结果，把各项分析数据拼接成可读的文本
    jd_result_parts = [
        f"**Overall Score**: {jd_analysis.overall_score}/100",  # 总体匹配分数
        f"**ATS Score**: {jd_analysis.ats_score}/100",  # ATS（简历筛选系统）匹配分数
        "",  # 空行分隔
        f"**Summary**: {jd_analysis.summary}",  # 整体分析摘要
        "",  # 空行分隔
        f"**Matched Keywords**: {', '.join(jd_analysis.keyword_matches) or 'N/A'}",  # 匹配到的关键词，用逗号连接
        f"**Missing Keywords**: {', '.join(jd_analysis.missing_keywords) or 'N/A'}",  # 缺失的关键词
        "",  # 空行分隔
        "## Optimization Suggestions",  # 优化建议标题
        suggestions_text,  # 前面格式化好的建议内容
    ]
# 因为数据结构完全不同，join 根本做不到同样的事。
# # missing_keywords — 扁平字符串列表
# missing_keywords = ["Python", "React", "AWS"]     # list[str]
# ', '.join(missing_keywords)                        # → "Python, React, AWS"
# # filtered — 复杂嵌套结构
# filtered = [
#     {
#         "id": "xxx",
#         "type": "work_experience",
#         "content": {
#             "items": [
#                 {"company": "ABC", "position": "工程师", "technologies": ["Python", "Go"]},
#                 {"company": "XYZ", "position": "架构师", "technologies": ["AWS"]}
#             ]
#         }
#     },
#     {
#         "id": "yyy",
#         "type": "personal_info",
#         "content": {"full_name": "张三", "email": "zhang@example.com"}
#     }
# ]
# 用 json.dumps(indent=2) 得到的是：
# ---
# [
#   {
#     "id": "xxx",
#     "type": "work_experience",
#     "content": {
#       "items": [
#         {"company": "ABC", "position": "工程师", ...},
#         {"company": "XYZ", "position": "架构师", ...}
#       ]
#     }
#   },
#   {
#     "id": "yyy",
#     "type": "personal_info",
#     "content": {"full_name": "张三", ...}
#   }
# ]
# ---
# LLM 看到了完整的字段名、嵌套层级、键名，翻译时才能原样保留结构。
# 如果用 join 会怎样？
# join 只能处理 list[str]，filtered 是 list[dict]，直接用就报错：
# ', '.join(filtered)
# # TypeError: sequence item 0: expected str instance, dict found
# 先转 str 再 join 呢？
# ', '.join(str(s) for s in filtered)
# # → "{'id': 'xxx', 'type': 'work_experience', ...}, {'id': 'yyy', ...}"
# 得到的是 Python repr 格式，JSON 方括号变花括号、null 变 None、缩进全丢。LLM 看到这玩意儿，翻译时字段名都不知道该用啥。
# ---
# 总结
# 场景	数据结构	手法	目的
# missing_keywords	list[str] — 扁平的词列表	join	拼成一行可读文本
# filtered	list[dict] — 复杂嵌套对象	json.dumps(indent=2)	保留完整结构让 LLM 照着输出
    jd_analysis_result = "\n".join(
            jd_result_parts
        )  # 把所有部分拼接成一个完整的分析结果字符串
# join 是为纯文本列表准备的，json.dumps(indent=2) 是为结构化的嵌套数据准备的。
    return JD_ANALYSIS.format(  # 用分析结果填充模板
        now=now,  # 当前时间
        jd_analysis_time=jd_analysis_time,  # 分析时间
        jd_analysis_result=jd_analysis_result,  # 分析结果内容
    )


# 系统提示词：定义AI角色和行为规则
SYSTEM = """\
You are Chiren, a resume optimization expert assistant.

Your task is to help users enhance the professionalism, impact, and ATS-friendliness of their resumes.

# Guidelines
- Provide specific, actionable suggestions.
- Use strong action verbs and quantifiable achievements.
- Maintain a professional and concise tone.

# Key Rules — Section Handling
- **Strictly prohibit** removing, deleting, or skipping any existing sections. The user has manually selected the sections to be included.
- When asked to fill, generate, or refine a resume, you **must** iterate through **all** the sections listed below and attempt to fill them. Do not stop prematurely.
- When updating list-type sections, preserve the `id` of existing items exactly as they are. For any new items added, completely omit the `id` field.

# Key Rules — Information Integrity
- Use only the information provided by the user as the sole source, mapping it to the corresponding fields in each section.
- Call the tool to update a section **only if** the user-provided information matches fields within that section.
- If a section cannot be matched with any provided information, skip it directly. Do not call the tool, and do not insert empty values or placeholders.
- Do not infer, guess, or fabricate any information not explicitly provided by the user.

# The resume currently contains the following sections
{sections}
"""


# 子系统提示词：用于JD优化场景
SUB_SYSTEM = """


# Job Description (JD)
---
{job_description}
---

Please optimize the resume based on this JD to improve role alignment and ATS performance.

Requirements:
- Use keywords and phrasing from the JD where appropriate
- Highlight the most relevant experience and skills
- Keep the content concise and focused

Note: Do not fabricate or introduce any information not provided by the user
"""


# JD分析结果的提示词模板
JD_ANALYSIS = """


# Resume Optimization Suggestions Based on JD Analysis

Based on the latest JD analysis results, provide resume optimization suggestions.

Current Time: {now}
JD Analysis Time: {jd_analysis_time}

## JD Analysis Results
---
{jd_analysis_result}
---"""
