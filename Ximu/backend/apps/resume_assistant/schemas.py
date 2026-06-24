"""简历助手模块的Pydantic数据模型定义。

本模块定义了简历助手相关的数据结构：
1. ResumeAssistantRequest - AI助手请求数据
2. SubResumeCreateRequest - 创建子简历请求数据
3. SubResumeResult - 子简历生成结果
4. 各种简历板块内容类型（与parser模块类似）
"""  # 模块文档字符串

from typing import Literal  # 导入Literal类型

from pydantic import (  # 导入Pydantic组件
    BaseModel,
    ConfigDict,
    Field,
    alias_generators,
)

from shared.types.mixins import NoneToDefaultMixin  # None转默认值混入类
from shared.types.strict_model import StrictBaseModel  # 严格基础模型


class ResumeAssistantRequest(BaseModel):
    """AI简历助手的请求数据结构。

    前端调用 POST /resume-assistant 时传入。
    """

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,  # 自动camelCase别名
        populate_by_name=True,  # 允许原始字段名
    )

    resume_id: str = Field(description="简历ID")  # 要操作的简历
    type: Literal["openai", "anthropic"] = Field(description="LLM供应商类型")
    base_url: str = Field(description="AI API地址")
    api_key: str = Field(description="AI API密钥")
    model: str = Field(description="模型名称")
    input: str = Field(description="用户输入的消息")


class SubResumeCreateRequest(BaseModel):
    """根据JD创建子简历的请求数据结构。

    前端调用 POST /resume-assistant/sub-resumes 时传入。
    """

    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    workspace_id: str = Field(description="主简历（工作区）ID")
    job_description: str = Field(description="目标职位描述（JD原文）")
    job_title: str | None = Field(default=None, description="岗位名称")
    template: str = Field(default="classic", description="简历模板")
    title: str = Field(default="未命名简历", description="子简历标题")
    theme_config: dict = Field(default_factory=dict, description="主题配置")
    language: str = Field(default="zh", description="简历语言")
    type: Literal["openai", "anthropic"] = Field(description="LLM供应商类型")
    base_url: str = Field(description="AI API地址")
    api_key: str = Field(description="AI API密钥")
    model: str = Field(description="模型名称")


class PersonalInfo(NoneToDefaultMixin, StrictBaseModel):
    """个人信息数据模型。"""

    full_name: str = Field(default="", description="姓名")
    job_title: str = Field(default="", description="目标职位")
    phone: str = Field(default="", description="电话号码")
    email: str = Field(default="", description="电子邮箱")
    salary: str = Field(default="", description="期望薪资")
    location: str = Field(default="", description="所在城市")
    age: str = Field(default="", description="年龄")
    gender: str = Field(default="", description="性别")
    political_status: str = Field(default="", description="政治面貌")
    education_level: str = Field(default="", description="学历")
    ethnicity: str = Field(default="", description="民族")
    hometown: str = Field(default="", description="籍贯")
    marital_status: str = Field(default="", description="婚姻状况")
    years_of_experience: str = Field(default="", description="工作年限")
    wechat: str = Field(default="", description="微信号")
    website: str = Field(default="", description="个人网站")
    linkedin: str = Field(default="", description="LinkedIn")


class Summary(NoneToDefaultMixin, StrictBaseModel):
    """个人简介数据模型。"""

    text: str = Field(default="", description="简介内容")


class EducationItem(NoneToDefaultMixin, StrictBaseModel):
    """教育经历条目。"""

    institution: str = Field(default="", description="学校/机构名称")
    degree: str = Field(default="", description="学位")
    field: str = Field(default="", description="专业")
    location: str = Field(default="", description="所在地点")
    start_date: str = Field(default="", description="开始日期")
    end_date: str = Field(default="", description="结束日期")
    gpa: str = Field(default="", description="GPA")
    highlights: list[str] = Field(default_factory=list, description="荣誉/成就")


class WorkExperienceItem(NoneToDefaultMixin, StrictBaseModel):
    """工作经历条目。"""

    company: str = Field(default="", description="公司/组织名称")
    position: str = Field(default="", description="职位")
    location: str = Field(default="", description="工作地点")
    start_date: str = Field(default="", description="开始日期")
    end_date: str = Field(default="", description="结束日期")
    current: bool = Field(default=False, description="是否在任")
    description: str = Field(default="", description="工作描述")
    technologies: list[str] = Field(default_factory=list, description="技术栈")
    highlights: list[str] = Field(default_factory=list, description="工作成就")


class ProjectItem(NoneToDefaultMixin, StrictBaseModel):
    """项目经历条目。"""

    name: str = Field(default="", description="项目名称")
    url: str = Field(default="", description="项目链接")
    description: str = Field(default="", description="项目描述")
    technologies: list[str] = Field(default_factory=list, description="技术栈")
    highlights: list[str] = Field(default_factory=list, description="项目成就")
    start_date: str = Field(default="", description="开始日期")
    end_date: str = Field(default="", description="结束日期")


class SkillCategory(NoneToDefaultMixin, StrictBaseModel):
    """技能分类。"""

    name: str = Field(default="", description="分类名称")
    skills: list[str] = Field(default_factory=list, description="技能列表")


class LanguageItem(NoneToDefaultMixin, StrictBaseModel):
    """语言能力条目。"""

    language: str = Field(default="", description="语言名称")
    proficiency: str = Field(default="", description="熟练程度")
    description: str = Field(default="", description="附加说明")


class CertificationItem(NoneToDefaultMixin, StrictBaseModel):
    """资格证书条目。"""

    name: str = Field(default="", description="证书名称")
    issuer: str = Field(default="", description="颁发机构")
    date: str = Field(default="", description="获得日期")
    description: str = Field(default="", description="证书描述")


class GitHubItem(NoneToDefaultMixin, StrictBaseModel):
    """GitHub仓库条目。"""

    repo_url: str = Field(default="", description="仓库地址")
    name: str = Field(default="", description="仓库名称")
    stars: int = Field(default=0, description="Star数量")
    language: str = Field(default="", description="主要编程语言")
    description: str = Field(default="", description="仓库描述")


class CustomItem(NoneToDefaultMixin, StrictBaseModel):
    """自定义条目。"""

    title: str = Field(default="", description="标题")
    date: str = Field(default="", description="日期")
    description: str = Field(default="", description="描述内容")


class SubResumeResult(StrictBaseModel):
    """AI生成的子简历结果数据结构。

    包含简历的所有板块内容。
    """

    personal_info: PersonalInfo = Field(
        default_factory=PersonalInfo, description="个人信息"
    )
    summary: Summary = Field(default_factory=Summary, description="个人简介")
    education: list[EducationItem] = Field(default_factory=list, description="教育经历")
    work_experience: list[WorkExperienceItem] = Field(
        default_factory=list, description="工作经历"
    )
    projects: list[ProjectItem] = Field(default_factory=list, description="项目经历")
    skills: list[SkillCategory] = Field(default_factory=list, description="技能列表")
    languages: list[LanguageItem] = Field(default_factory=list, description="语言能力")
    certifications: list[CertificationItem] = Field(
        default_factory=list, description="证书"
    )
    github: list[GitHubItem] = Field(default_factory=list, description="GitHub仓库")
    custom: list[CustomItem] = Field(default_factory=list, description="自定义条目")
