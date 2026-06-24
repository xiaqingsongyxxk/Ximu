"""查询板块信息的工具模块。

本模块定义了SectionInfoTool，用于AI Agent查询板块类型的详细定义。
当AI需要了解某个板块的结构和字段时，会调用此工具。
"""  # 模块文档字符串，说明这个文件是做什么的

from typing import Literal  # 导入Literal类型，用于限制字段只能取特定的值

from pydantic import BaseModel, Field  # 导入Pydantic组件，用于定义数据模型和字段验证

from shared.types.base_tool import (
    BaseTool,
    ToolExecutionContext,
    ToolResult,
)  # 导入工具基类，所有工具都需要继承这些基类

# 各板块类型的详细定义（英文，供LLM理解结构）
# 这个字典定义了每个板块类型的字段结构和说明，用于告诉AI Agent每个板块包含哪些字段
_SECTION_DEFINITIONS: dict[str, str] = {
    "personal_info": """
Personal Information Section
Contains the card owner's basic identifying information.
Fields:
- full_name (string): Full legal name
- job_title (string): Target position/intended role
- email (string): Contact email address
- phone (string): Contact phone number
- location (string): Current city of residence
- salary (string): Expected salary range
- age (string): Age
- gender (string): Gender
- political_status (string): Political affiliation
- education_level (string): Highest education level
- ethnicity (string): Ethnicity
- hometown (string): Hometown
- marital_status (string): Marital status
- years_of_experience (string): Years of work experience
- wechat (string): WeChat ID
- website (string): Personal website
- linkedin (string): LinkedIn profile
""",  # 个人信息板块的字段定义
    "summary": """
Personal Summary Section
A narrative paragraph introducing the card owner.
Fields:
- text (text): Free-form introduction text
""",  # 个人总结板块的字段定义
    "work_experience": """Work Experience Section
List of past employment and professional positions.
Structure: Contains an "items" array.
Each item:
- id (string): Unique identifier
- company (string): Organization name
- position (string): Job title/role
- location (string): Work location
- start_date (string): Start date in YYYY-MM format
- end_date (string): End date or "Present"
- current (boolean): Whether this is the current job
- description (text): Detailed job description
- technologies (array[string]): Tech stack
- highlights (array[string]): Key achievements
""",  # 工作经历板块的字段定义
    "education": """
Education Background Section
List of educational history entries.
Structure: Contains an "items" array.
Each item:
- id (string): Unique identifier
- institution (string): School/university name
- degree (string): Degree earned
- field (string): Major/field of study
- location (string): Geographic location
- start_date (string): Enrollment date
- end_date (string): Expected graduation date
- gpa (string): Grade point average
- highlights (array[string]): Honors/achievements
""",  # 教育背景板块的字段定义
    "skills": """
Skills Section
Skills organized by category.
Structure: Contains a "categories" array.
Each category:
- id (string): Unique identifier
- name (string): Category name
- skills (array[string]): List of skills in this category
""",  # 技能板块的字段定义
    "languages": """
Language Proficiency Section
List of languages the person can use.
Structure: Contains an "items" array.
Each item:
- id (string): Unique identifier
- language (string): Language name
- proficiency (string): Proficiency level
- description (string): Additional notes
""",  # 语言能力板块的字段定义
    "projects": """Project Experience Section
List of independent projects or portfolio items.
Structure: Contains an "items" array.
Each item:
- id (string): Unique identifier
- name (string): Project name
- description (text): Detailed project description
- technologies (array[string]): Tech stack
- highlights (array[string]): Key features/achievements
- url (string): Project link
- start_date (string): Start date
- end_date (string): End date
""",  # 项目经验板块的字段定义
    "certifications": """Certifications Section
List of professional certifications and qualifications.
Structure: Contains an "items" array.
Each item:
- id (string): Unique identifier
- name (string): Certification name
- issuer (string): Issuing organization
- date (string): Date obtained
- description (string): Certification description
""",  # 证书板块的字段定义
    "github": """
GitHub Projects Section
Showcase of GitHub repositories.
Structure: Contains an "items" array.
Each item:
- id (string): Unique identifier
- repo_url (string): GitHub repository URL
- name (string): Repository name
- stars (int): Number of stars received
- language (string): Primary programming language
- description (text): Repository description
""",  # GitHub项目板块的字段定义
    "qr_codes": """
QR Codes Section
Collection of QR code links.
Structure: Contains an "items" array (may be empty).
Each item:
- id (string): Unique identifier
- url (string): URL the QR code points to
- label (string): Display label for the QR code
""",  # 二维码板块的字段定义
    "custom": """
Custom Section
User-defined section for miscellaneous content like competitions.
Structure: Contains an "items" array.
Each item:
- id (string): Unique identifier
- title (string): Item title
- description (text): Item description
- date (string): Date range
""",  # 自定义板块的字段定义
}


class SectionInfoToolInput(BaseModel):
    """查询板块信息的输入数据模型。"""

    type: Literal[  # 板块类型（只能是以下值之一）
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
    ] = Field(description="要查询定义的板块类型")  # 用于指定要查询哪个板块的定义


class SectionInfoTool(BaseTool):
    """查询板块信息的工具类。

    AI Agent调用此工具来了解某个板块的结构和字段定义。
    """

    name = "section_info"  # 工具名称，用于标识这个工具
    description = "获取指定板块类型的详细定义"  # 工具描述，告诉AI Agent这个工具的作用
    input_model = SectionInfoToolInput  # 指定输入数据模型

    async def execute(
        self, arguments: SectionInfoToolInput, context: ToolExecutionContext
    ) -> ToolResult:
        """执行工具：返回板块类型的定义。

        Args:
            arguments: 输入参数（包含板块类型）。
            context: 工具执行上下文。

        Returns:
            包含板块定义的工具结果。
        """
        # 从预定义的字典中获取板块定义，如果不存在则返回错误信息
        return ToolResult(
            output=_SECTION_DEFINITIONS.get(
                arguments.type, f"Unknown section type: {arguments.type}"
#                 .get(key) 在做什么
# _SECTION_DEFINITIONS.get("personal_info", "默认值")
# # → "Personal Information Section\n..."  ← 返回字符串 ✅
# _SECTION_DEFINITIONS.get("不存在的类型", "默认值")
# # → "默认值"  ← 也是字符串 ✅
            )
        )
# 那 section_info 为什么还存在
# 它是个"查漏补缺"的备选工具，不是主流路径需要的。
# 信息来源	什么时候给 LLM	特点
# 系统提示词	每次请求都带	但可能被长对话压缩掉
# 工具 input_schema	每次请求都带	但它只描述入参结构，不是完整字段含义
# section_info	LLM 主动调用时才给	LLM 不确定时可以"翻手册"
# 什么场景会用到
# 场景 1：长对话后上下文被压缩
# 第 1 轮：系统提示词里有完整的板块结构
# 第 10 轮：对话历史已经很长了，系统提示词可能被 auto-compact 压缩
#           LLM 对某些字段的记忆变模糊了
#           → 调用 section_info 确认
# 场景 2：LLM 不确定某些字段
# LLM 知道 update_section 的 input_schema 里 value 是个 object，但具体这个 object 有哪些 key、每个 key 是什么含义——input_schema 的描述可能不够详细。_SECTION_DEFINITIONS 里写了 20 行的自然语言描述，比 JSON Schema 更友好。
# 但它确实是多余的
# 正常流程里 LLM 不需要调用 section_info，因为它已经有足够的信息了。这个工具的存在是一种"防御性设计"——给 LLM 一个"不懂就问"的选项，但大部分时候它用不上。
# 就像你写代码时旁边放着一本 API 参考手册——你大多数时候不需要翻它，但偶尔不确定某个函数参数时，翻一下比硬猜好