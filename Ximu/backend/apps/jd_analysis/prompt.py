"""职位描述分析的提示词构建模块。

本模块定义了发送给LLM的提示词：
1. SYSTEM - 系统提示词模板，告诉LLM它的角色和输出格式
2. build_user_prompt - 构建用户提示词的函数

提示词是LLM理解任务的关键，好的提示词能显著提高分析质量。
"""  # 模块文档字符串

from shared.resume_prompt import (  # 从shared/resume_prompt.py导入简历提示词构建工具
    ItemFields,  # 条目字段配置类（控制哪些字段显示在提示词中）
    PersonalInfoFields,  # 个人信息字段配置类
    ResumePromptBuilder,  # 简历提示词构建器（核心工具类）
    SectionHeaderConfig,  # 板块头部配置类
)

# 定义职位分析需要的个人信息字段配置
# 只包含对职位匹配分析有用的字段，排除联系方式等无关信息
JD_ANALYSIS_PERSONAL_INFO_FIELDS = PersonalInfoFields(
    full_name=True,  # ✓ 包含姓名（影响第一印象）
    age=True,  # ✓ 包含年龄（某些岗位有年龄要求）
    gender=True,  # ✓ 包含性别（某些岗位有性别要求）
    email=False,  # ✗ 不包含邮箱（与匹配度无关）
    phone=False,  # ✗ 不包含电话（与匹配度无关）
    education_level=True,  # ✓ 包含学历（很多岗位有学历要求）
    job_title=True,  # ✓ 包含职位名称（核心匹配信息）
    salary=True,  # ✓ 包含期望薪资（影响匹配度）
    location=True,  # ✓ 包含地点（影响工作地点匹配）
    political_status=True,  # ✓ 包含政治面貌（某些岗位需要）
    ethnicity=True,  # ✓ 包含民族（某些岗位需要）
    hometown=True,  # ✓ 包含籍贯（某些岗位需要）
    marital_status=True,  # ✓ 包含婚姻状况（某些岗位需要）
    years_of_experience=True,  # ✓ 包含工作年限（核心匹配信息）
    wechat=False,  # ✗ 不包含微信（与匹配度无关）
    website=True,  # ✓ 包含个人网站（技术岗位加分）
    linkedin=True,  # ✓ 包含LinkedIn（外企岗位加分）
)

# 定义职位分析需要的条目字段配置
JD_ANALYSIS_ITEM_FIELDS = ItemFields(
    location=False,  # 不包含条目中的地点（避免信息过载）
)

# 定义职位分析需要的板块头部配置
JD_ANALYSIS_SECTION_HEADER = SectionHeaderConfig(
    include_section_id=True,  # 包含板块ID（LLM返回建议时需要引用板块ID）
)

# 创建职位分析专用的简历提示词构建器实例
JD_ANALYSIS_BUILDER = ResumePromptBuilder(
    personal_info_fields=JD_ANALYSIS_PERSONAL_INFO_FIELDS,  # 传入个人信息字段配置
    item_fields=JD_ANALYSIS_ITEM_FIELDS,  # 传入条目字段配置
    section_header=JD_ANALYSIS_SECTION_HEADER,  # 传入板块头部配置
)
# 如果添加 nbdx_mode=True，实例会包含4个属性。
# JD_ANALYSIS_BUILDER = ResumePromptBuilder(
#     personal_info_fields=JD_ANALYSIS_PERSONAL_INFO_FIELDS,
#     item_fields=JD_ANALYSIS_ITEM_FIELDS,
#     section_header=JD_ANALYSIS_SECTION_HEADER,
#     nbdx_mode=True,  # 新增参数
# )
# 访问方式：
# JD_ANALYSIS_BUILDER.personal_info_fields  # 个人信息配置
# JD_ANALYSIS_BUILDER.item_fields          # 条目配置
# JD_ANALYSIS_BUILDER.section_header       # 区块头部配置
# JD_ANALYSIS_BUILDER.nbdx_mode            # True
# 系统提示词模板，指导LLM如何分析职位描述
# 传入的参数会覆盖默认值。
# # 类定义（默认值）
# class ResumePromptBuilder:
#     personal_info_fields: PersonalInfoFields = field(default_factory=PersonalInfoFields)  # 默认值
#     item_fields: ItemFields = field(default_factory=ItemFields)  # 默认值
#     section_header: SectionHeaderConfig = field(default_factory=SectionHeaderConfig)  # 默认值
# # 创建实例（传入自定义值）
# JD_ANALYSIS_BUILDER = ResumePromptBuilder(
#     personal_info_fields=JD_ANALYSIS_PERSONAL_INFO_FIELDS,  # 覆盖默认值
#     item_fields=JD_ANALYSIS_ITEM_FIELDS,                    # 覆盖默认值
#     section_header=JD_ANALYSIS_SECTION_HEADER,              # 覆盖默认值
# )
# 区别：
# 方式
# 不传参数
# 传入参数
# 为什么传入自定义值：
# # 默认值：包含所有字段
# PersonalInfoFields(
#     full_name=True,
#     email=True,
#     phone=True,
#     ...
# )
# # 自定义值：只包含特定字段
# JD_ANALYSIS_PERSONAL_INFO_FIELDS = PersonalInfoFields(
#     full_name=True,
#     email=False,  # 不包含邮箱
#     phone=False,  # 不包含电话
#     ...
# )
# 系统提示词模板
# 告诉LLM它的角色、规则和输出格式
SYSTEM = """\
You are a professional job description analyst. Analyze the match between the provided resume and the job description (JD).
# 你是一位专业的职位描述分析师。分析提供的简历与职位描述(JD)之间的匹配度。

# Core Rules:
# 核心规则：
- Return ONLY valid JSON content, no additional descriptions or explanations
# - 仅返回有效的JSON内容，不要添加额外描述或解释
- Your analysis should be accurate and provide practical suggestions
# - 你的分析应该准确并提供实用的建议

Below is the JSON schema definition you must follow:
# 以下是必须遵循的JSON模式定义：
---
{json_schema}
---"""


def build_user_prompt(  # 定义构建用户提示词的函数
    sections,  # 参数：简历板块列表
    job_description: str,  # 参数：职位描述文本
    job_title: str | None = None,  # 参数：职位名称（可选）
) -> str:  # 返回值类型：字符串
    """构建发送给LLM的用户提示词。

    将简历板块内容和职位描述组合成LLM能理解的文本格式。
    提示词包含：
    1. 简历的所有板块内容（个人信息、工作经历等）
    2. 目标职位的描述文本
    3. 目标职位名称（如果有）

    Args:
        sections: 简历板块列表（ResumeSectionSchema对象列表）。
        job_description: 目标职位的描述文本。
        job_title: 目标职位名称（可选）。

    Returns:
        构建好的用户提示词字符串。
    """  # 文档字符串
    return JD_ANALYSIS_BUILDER.build_user_prompt(sections, job_description, job_title)
    # 调用提示词构建器的build_user_prompt方法
    # 该方法定义在 shared/resume_prompt.py 中
    # 它会将简历板块格式化为可读文本，与职位描述组合
