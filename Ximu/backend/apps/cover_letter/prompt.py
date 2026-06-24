"""Prompt builders for cover letter generation.

This module defines prompts used to guide the AI in producing structured
cover letters based on resume content and job descriptions.
"""  # 模块文档字符串，说明这个文件是做什么的

from shared.resume_prompt import (  # 导入简历提示词构建器相关组件
    ItemFields,  # 条目字段配置类
    PersonalInfoFields,  # 个人信息字段配置类
    ResumePromptBuilder,  # 简历提示词构建器类
    SectionHeaderConfig,  # 板块标题配置类
)

# 定义JD分析时需要包含的个人信息字段
# 每个字段后面的True/False表示是否在提示词中包含该字段
JD_ANALYSIS_PERSONAL_INFO_FIELDS = PersonalInfoFields(
    full_name=True,  # 包含姓名
    age=True,  # 包含年龄
    gender=True,  # 包含性别
    email=False,  # 不包含邮箱（因为会在签名中单独提供）
    phone=False,  # 不包含电话（因为会在签名中单独提供）
    education_level=True,  # 包含学历
    job_title=True,  # 包含求职意向
    salary=True,  # 包含期望薪资
    location=True,  # 包含所在地
    political_status=True,  # 包含政治面貌
    ethnicity=True,  # 包含民族
    hometown=True,  # 包含籍贯
    marital_status=True,  # 包含婚姻状况
    years_of_experience=True,  # 包含工作年限
    wechat=False,  # 不包含微信
    website=True,  # 包含个人网站
    linkedin=True,  # 包含LinkedIn
)

# 定义JD分析时需要包含的条目字段
JD_ANALYSIS_ITEM_FIELDS = ItemFields(location=False)  # 不包含工作地点

# 定义JD分析时板块标题的配置
JD_ANALYSIS_SECTION_HEADER = SectionHeaderConfig(include_section_id=True)  # 包含板块ID

# 创建JD分析用的简历提示词构建器实例
JD_ANALYSIS_BUILDER = ResumePromptBuilder(
    personal_info_fields=JD_ANALYSIS_PERSONAL_INFO_FIELDS,  # 使用上面定义的个人信息字段配置
    item_fields=JD_ANALYSIS_ITEM_FIELDS,  # 使用上面定义的条目字段配置
    section_header=JD_ANALYSIS_SECTION_HEADER,  # 使用上面定义的板块标题配置
)

# 求职信风格对应的人口学描述
# 这个字典定义了不同求职信风格的语言特点
COVER_LETTER_STYLE_PROMPTS = {
    "正式": "使用正式、专业的语言风格，语气庄重，结构严谨，适合传统行业和知名企业",
    "亲切": "使用亲切、温暖的语言风格，语气友好但不失专业，适合创业公司和中小企业",
    "自信": "使用自信、有力的语言风格，突出个人优势和成就，适合竞争激烈的职位",
}


def build_cover_letter_system_prompt(
    style: str = "正式", language: str = "中文"
) -> str:
    """Build the system prompt used for cover letter generation.

    Args:
        style: Tone/style for the cover letter. One of: 正式, 亲切, 自信.
        language: Output language. Either 中文 or English.
    Returns:
        A string containing the system prompt for the AI model.
    """
    # 获取求职信风格的描述，如果没有匹配的风格则使用默认的"正式"风格
    style_instruction = COVER_LETTER_STYLE_PROMPTS.get(
        style, COVER_LETTER_STYLE_PROMPTS["正式"]
    )
    # 根据语言设置选择相应的语言指令
    lang_instruction = (
        "请使用简体中文输出" if language == "中文" else "Please write in English"
    )

    # 返回完整的系统提示词
    return f"""\
Role: You are a professional career coach and expert cover letter writer.
Task: Write a persuasive cover letter tailored to a specific job application.
Inputs:
The candidate's Resume (including name, email, phone).
The Target Job Description (JD).
Goal: Create a highly customized cover letter that aligns the candidate's strengths with the job requirements,
thereby significantly increasing the likelihood of securing an interview.
Important: The cover letter MUST include the candidate's name, email and phone number in the signature/closing section.
Output only the generated cover letter content, without including your own reasoning logic.
Style Requirements: {style_instruction}
Language Requirement: {lang_instruction}
---"""


def build_cover_letter_user_prompt(
    sections,
    job_description: str,
    full_name: str,
    email: str,
    phone: str,
) -> str:
    """Build the user prompt for cover letter generation including personal data.

    Args:
        sections: Resume sections used to compose the resume content in the prompt.
        job_description: Description of the target job.
        full_name: Candidate's full name for the signature.
        email: Candidate's email for the signature.
        phone: Candidate's phone for the signature.
    Returns:
        The user prompt string to guide the AI in generating the cover letter.
    """
    # 使用 JD_ANALYSIS_BUILDER 构建简历内容
    # 这个构建器会根据配置提取简历中的关键信息
    resume_content = JD_ANALYSIS_BUILDER.build_user_prompt(
        sections,
        job_description,
        None,  # sections是简历板块，job_description是职位描述，None表示不使用额外参数
    )

    # 添加个人信息用于求职信签名
    # 这些信息会被添加到简历内容前面，确保AI在生成求职信时包含这些联系信息
    personal_info = f"""
Candidate Contact Information (MUST include in cover letter signature):
- Name: {full_name}
- Email: {email}
- Phone: {phone}

{resume_content}
"""
    return personal_info  # 返回完整的用户提示词
