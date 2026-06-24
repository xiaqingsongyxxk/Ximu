"""简历解析的Pydantic数据模型定义模块。

本模块定义了LLM解析简历后返回的数据结构：
1. PersonalInfo - 个人信息
2. EducationItem - 教育背景条目
3. SkillCategory - 技能分类
4. ProjectItem - 项目经历条目
5. CertificationItem - 资格证书条目
6. WorkExperienceItem - 工作经历条目
7. LanguageItem - 语言能力条目
8. ParserResult - 完整的解析结果（包含以上所有）

这些模型用于验证LLM返回的JSON数据格式。
"""  # 模块文档字符串

from pydantic import (
    Field,  # 字段定义工具
    model_validator,  # 模型验证器
)

from shared.types.mixins import NoneToDefaultMixin  # None转默认值的混入类
from shared.types.strict_model import StrictBaseModel  # 严格基础模型（禁止额外字段）


class PersonalInfo(NoneToDefaultMixin, StrictBaseModel):
    """个人信息数据模型。

    包含姓名、联系方式、基本人口统计信息等。
    继承NoneToDefaultMixin：如果字段值为None，自动转为空字符串。
    """
    full_name: str = Field(default="", description="姓名")
    job_title: str = Field(default="", description="求职意向/目标职位")
    email: str = Field(default="", description="电子邮箱")
    phone: str = Field(default="", description="电话号码")
    location: str = Field(default="", description="所在城市")
    salary: str = Field(default="", description="期望薪资")
    age: str = Field(default="", description="年龄")
    gender: str = Field(default="", description="性别")
    political_status: str = Field(default="", description="政治面貌")
    education_level: str = Field(default="", description="学历层次")
    ethnicity: str = Field(default="", description="民族")
    hometown: str = Field(default="", description="籍贯")
    marital_status: str = Field(default="", description="婚姻状况")
    years_of_experience: str = Field(default="", description="工作年限")
    wechat: str = Field(default="", description="微信号")
    website: str = Field(default="", description="个人网站")
    linkedin: str = Field(default="", description="LinkedIn")


class EducationItem(NoneToDefaultMixin, StrictBaseModel):
    """教育背景条目数据模型。"""
    institution: str = Field(default="", description="学校/机构名称")
    degree: str = Field(default="", description="学位")
    field: str = Field(default="", description="专业/研究领域")
    location: str = Field(default="", description="地点")
    start_date: str = Field(default="", description="开始日期")
    end_date: str = Field(default="", description="结束日期")
    gpa: str = Field(default="", description="GPA成绩")
    highlights: list[str] = Field(default_factory=list, description="荣誉/成就列表")


class SkillCategory(NoneToDefaultMixin, StrictBaseModel):
    """技能分类数据模型。"""
    name: str = Field(default="", description="分类名称（如'前端技术'）")
    skills: list[str] = Field(default_factory=list, description="该分类下的技能列表")


class ProjectItem(NoneToDefaultMixin, StrictBaseModel):
    """项目经历条目数据模型。"""
    name: str = Field(default="", description="项目名称")
    description: str = Field(default="", description="项目描述")
    technologies: list[str] = Field(default_factory=list, description="技术栈列表")
    highlights: list[str] = Field(default_factory=list, description="项目亮点列表")
    url: str = Field(default="", description="项目URL")
    start_date: str = Field(default="", description="开始日期")
    end_date: str = Field(default="", description="结束日期")


class CertificationItem(NoneToDefaultMixin, StrictBaseModel):
    """资格证书条目数据模型。"""
    name: str = Field(default="", description="证书名称")
    issuer: str = Field(default="", description="颁发机构")
    date: str = Field(default="", description="获得日期")
    description: str = Field(default="", description="描述")


class WorkExperienceItem(NoneToDefaultMixin, StrictBaseModel):
    """工作经历条目数据模型。"""
    company: str = Field(default="", description="公司/组织名称")
    position: str = Field(default="", description="职位/角色")
    location: str = Field(default="", description="工作地点")
    start_date: str = Field(default="", description="开始日期")
    end_date: str = Field(default="", description="结束日期")
    current: bool = Field(default=False, description="是否当前在职")
    description: str = Field(default="", description="工作描述")
    technologies: list[str] = Field(default_factory=list, description="技术栈列表")
    highlights: list[str] = Field(default_factory=list, description="成就/亮点列表")


class LanguageItem(NoneToDefaultMixin, StrictBaseModel):
    """语言能力条目数据模型。"""
    language: str = Field(default="", description="语言名称")
    proficiency: str = Field(default="", description="熟练程度")
    description: str = Field(default="", description="附加描述")


class ParserResult(StrictBaseModel):
    """LLM解析简历后返回的完整数据结构。

    这个结构对应提示词中的JSON Schema，
    LLM会返回符合此格式的JSON数据。
    """

    @model_validator(mode="before")  # 在验证前执行
    @classmethod
    def handle_none(cls, v):
        """将None输入规范化为空字典。"""
        if v is None:  # 如果输入是None
            return {}  # 返回空字典（避免验证错误）
        return v

    personal_info: PersonalInfo = Field(
        default_factory=PersonalInfo,  # 默认创建空的个人信息
        description="个人信息",
    )
    summary: str = Field(default="", description="个人简介")
    work_experiences: list[WorkExperienceItem] | None = Field(
        default=None, description="工作经历列表"
    )
    education: list[EducationItem] | None = Field(
        default=None, description="教育背景列表"
    )
    skills: list[SkillCategory] | None = Field(
        default=None, description="技能分类列表"
    )
    projects: list[ProjectItem] | None = Field(
        default=None, description="项目经历列表"
    )
    certifications: list[CertificationItem] | None = Field(
        default=None, description="资格证书列表"
    )
    languages: list[LanguageItem] | None = Field(
        default=None, description="语言能力列表"
    )
