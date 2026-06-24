"""简历相关类型定义模块。

本模块定义了简历系统的完整数据结构：
1. ResumeSchema - 简历主数据模型
2. 各种板块内容模型（PersonalInfo、WorkExperienceItem等）
3. 各种板块Section模型（PersonalInfoSection等）
4. ResumeSectionSchema - 板块联合类型（Discriminated Union）
"""  # 模块文档字符串

from __future__ import annotations  # 支持延迟注解求值

import json  # JSON序列化模块
from datetime import datetime  # 日期时间类型
from typing import Annotated, Any, Literal  # 类型注解工具

from pydantic import (  # Pydantic组件
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    Tag,
    TypeAdapter,
    alias_generators,
    model_validator,
)

from shared.types.strict_model import StrictBaseModel  # 严格基础模型


class ResumeSchema(BaseModel):
    """简历主数据模型。

    包含简历的基本信息（ID、标题、模板等）。
    """
    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,  # camelCase别名
        populate_by_name=True,
    )

    id: str | None = Field(default=None, description="简历唯一标识")
    workspace_id: str | None = Field(default=None, description="所属Workspace ID，为空表示本身就是Workspace")
    title: str = Field(default="未命名简历", description="简历标题")
    theme_config: dict[str, Any] = Field(default_factory=dict, description="主题配置")
    template: str = Field(default="classic", description="模板名称")
    is_default: bool = Field(default=False, description="是否为用户的默认简历")
    language: str = Field(default="zh", description="简历语言")
    share_token: str | None = Field(default=None, description="分享链接Token")
    is_public: bool = Field(default=False, description="是否公开简历")
    share_password: str | None = Field(default=None, description="分享密码")
    view_count: int = Field(default=0, description="浏览次数")
    meta_info: dict[str, Any] | None = Field(default=None, description="子简历元数据")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="最后更新时间")


# ══════════════════════════════════════════════════════════════
#  条目模型（每种板块的具体条目结构）
# ══════════════════════════════════════════════════════════════

class WorkExperienceItem(StrictBaseModel):
    """工作经历条目。"""
    id: str = Field(default="", description="工作经历ID")
    company: str = Field(default="", description="公司名称")
    position: str = Field(default="", description="职位名称")
    location: str = Field(default="", description="工作地点")
    start_date: str = Field(default="", description="开始时间")
    end_date: str = Field(default="", description="结束时间")
    current: bool = Field(default=False, description="是否至今")
    description: str = Field(default="", description="工作描述")
    technologies: list[str] = Field(default_factory=list, description="技术栈")
    highlights: list[str] = Field(default_factory=list, description="工作亮点")


class EducationItem(StrictBaseModel):
    """教育经历条目。"""
    id: str = Field(default="", description="教育经历ID")
    institution: str = Field(default="", description="学校名称")
    degree: str = Field(default="", description="学位")
    field: str = Field(default="", description="专业")
    location: str = Field(default="", description="地点")
    start_date: str = Field(default="", description="开始时间")
    end_date: str = Field(default="", description="结束时间")
    gpa: str = Field(default="", description="GPA")
    highlights: list[str] = Field(default_factory=list, description="亮点")


class ProjectItem(StrictBaseModel):
    """项目经历条目。"""
    id: str = Field(default="", description="项目ID")
    name: str = Field(default="", description="项目名称")
    url: str = Field(default="", description="项目链接")
    description: str = Field(default="", description="项目描述")
    technologies: list[str] = Field(default_factory=list, description="技术栈")
    highlights: list[str] = Field(default_factory=list, description="亮点")
    start_date: str = Field(default="", description="开始时间")
    end_date: str = Field(default="", description="结束时间")


class SkillItem(StrictBaseModel):
    """技能分类条目。"""
    id: str = Field(default="", description="技能ID")
    name: str = Field(default="", description="分类名称")
    skills: list[str] = Field(default_factory=list, description="技能列表")


class LanguageItem(StrictBaseModel):
    """语言能力条目。"""
    id: str = Field(default="", description="语言ID")
    language: str = Field(default="", description="语言")
    proficiency: str = Field(default="", description="熟练程度")
    description: str = Field(default="", description="描述")


class CertificationItem(StrictBaseModel):
    """证书条目。"""
    id: str = Field(default="", description="证书ID")
    name: str = Field(default="", description="证书名称")
    issuer: str = Field(default="", description="颁发机构")
    date: str = Field(default="", description="获得日期")
    description: str = Field(default="", description="描述")


class QrCodeItem(StrictBaseModel):
    """二维码条目。"""
    id: str = Field(default="", description="二维码ID")
    label: str = Field(default="", description="标签（如'微信'、'主页'）")
    url: str = Field(default="", description="链接")
    image_url: str = Field(default="", description="二维码图片地址")


class GitHubItem(StrictBaseModel):
    """GitHub仓库条目。"""
    id: str = Field(default="", description="仓库ID")
    repo_url: str = Field(default="", description="仓库链接")
    name: str = Field(default="", description="仓库名")
    stars: int = Field(default=0, description="星标数")
    language: str = Field(default="", description="编程语言")
    description: str = Field(default="", description="仓库描述")


# ══════════════════════════════════════════════════════════════
#  Content 模型（板块的内容结构，列表统一放在 items/categories）
# ══════════════════════════════════════════════════════════════

class PersonalInfo(StrictBaseModel):
    """个人信息内容。"""
    full_name: str = Field(default="", description="姓名")
    job_title: str = Field(default="", description="预期岗位")
    phone: str = Field(default="", description="手机号")
    email: str = Field(default="", description="邮箱")
    salary: str = Field(default="", description="期望薪资")
    location: str = Field(default="", description="城市")
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
    avatar: str = Field(default="", description="头像")


class Summary(StrictBaseModel):
    """个人简介内容。"""
    text: str = Field(default="", description="简介")


class WorkExperienceContent(StrictBaseModel):
    """工作经历内容。"""
    items: list[WorkExperienceItem] = Field(default_factory=list, description="工作经历列表")


class ProjectsContent(StrictBaseModel):
    """项目经历内容。"""
    items: list[ProjectItem] = Field(default_factory=list, description="项目列表")


class EducationContent(StrictBaseModel):
    """教育经历内容。"""
    items: list[EducationItem] = Field(default_factory=list, description="教育经历列表")


class SkillsContent(StrictBaseModel):
    """技能内容（使用categories而不是items）。"""
    categories: list[SkillItem] = Field(default_factory=list, description="技能分类列表")


class LanguagesContent(StrictBaseModel):
    """语言能力内容。"""
    items: list[LanguageItem] = Field(default_factory=list, description="语言列表")


class CertificationsContent(StrictBaseModel):
    """证书内容。"""
    items: list[CertificationItem] = Field(default_factory=list, description="证书列表")


class QrCodesContent(StrictBaseModel):
    """二维码内容。"""
    items: list[QrCodeItem] = Field(default_factory=list, description="二维码列表")


class GitHubContent(StrictBaseModel):
    """GitHub内容。"""
    items: list[GitHubItem] = Field(default_factory=list, description="仓库列表")


class CustomContent(StrictBaseModel):
    """自定义内容。"""
    id: str = Field(default="", description="自定义项ID")
    title: str = Field(default="", description="标题")
    date: str = Field(default="", description="日期")
    description: str = Field(default="", description="描述")


# ══════════════════════════════════════════════════════════════
#  核心基类：content JSON 字符串自动反序列化
# ══════════════════════════════════════════════════════════════

class ResumeSectionBase(BaseModel):
    """简历板块基类。

    数据库中content字段存储的是JSON字符串，
    通过model_validator在验证前自动反序列化为字典。
    """
    id: str = Field(description="板块唯一标识")
    resume_id: str = Field(description="所属简历ID")
    title: str = Field(description="板块显示标题")
    sort_order: int = Field(default=0, description="排序序号")
    visible: bool = Field(default=True, description="是否可见")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    @model_validator(mode="before")  # 在字段验证前执行
    @classmethod
    def _deserialize_content(cls, values: Any) -> Any:
        """将content字段从JSON字符串反序列化为字典。"""
        if isinstance(values, dict) and isinstance(values.get("content"), str):
            try:
                values = {**values, "content": json.loads(values["content"])}
            except json.JSONDecodeError as e:
                raise ValueError(f"content字段不是合法JSON：{e}") from e
        return values


# ══════════════════════════════════════════════════════════════
#  各具体 Section 子类（每种板块类型对应一个）
# ══════════════════════════════════════════════════════════════

class PersonalInfoSection(ResumeSectionBase):
    """个人信息板块。"""
    type: Literal["personal_info"] = "personal_info"
    content: PersonalInfo | None = Field(default=None)


class SummarySection(ResumeSectionBase):
    """个人简介板块。"""
    type: Literal["summary"] = "summary"
    content: Summary | None = Field(default=None)


class WorkExperienceSection(ResumeSectionBase):
    """工作经历板块。"""
    type: Literal["work_experience"] = "work_experience"
    content: WorkExperienceContent | None = Field(default=None)


class ProjectsSection(ResumeSectionBase):
    """项目经历板块。"""
    type: Literal["projects"] = "projects"
    content: ProjectsContent | None = Field(default=None)


class EducationSection(ResumeSectionBase):
    """教育背景板块。"""
    type: Literal["education"] = "education"
    content: EducationContent | None = Field(default=None)


class SkillsSection(ResumeSectionBase):
    """技能特长板块。"""
    type: Literal["skills"] = "skills"
    content: SkillsContent | None = Field(default=None)


class LanguagesSection(ResumeSectionBase):
    """语言能力板块。"""
    type: Literal["languages"] = "languages"
    content: LanguagesContent | None = Field(default=None)


class CertificationsSection(ResumeSectionBase):
    """资格证书板块。"""
    type: Literal["certifications"] = "certifications"
    content: CertificationsContent | None = Field(default=None)


class QrCodesSection(ResumeSectionBase):
    """二维码板块。"""
    type: Literal["qr_codes"] = "qr_codes"
    content: QrCodesContent | None = Field(default=None)


class GitHubSection(ResumeSectionBase):
    """GitHub板块。"""
    type: Literal["github"] = "github"
    content: GitHubContent | None = Field(default=None)


class CustomSection(ResumeSectionBase):
    """自定义板块。"""
    type: Literal["custom"] = "custom"
    content: CustomContent | None = Field(default=None)


# ══════════════════════════════════════════════════════════════
#  Discriminated Union 入口类型（通过type字段区分具体类型）
# ══════════════════════════════════════════════════════════════

ResumeSectionSchema = Annotated[
    Annotated[PersonalInfoSection, Tag("personal_info")]
    | Annotated[SummarySection, Tag("summary")]
    | Annotated[WorkExperienceSection, Tag("work_experience")]
    | Annotated[ProjectsSection, Tag("projects")]
    | Annotated[EducationSection, Tag("education")]
    | Annotated[SkillsSection, Tag("skills")]
    | Annotated[LanguagesSection, Tag("languages")]
    | Annotated[CertificationsSection, Tag("certifications")]
    | Annotated[QrCodesSection, Tag("qr_codes")]
    | Annotated[GitHubSection, Tag("github")]
    | Annotated[CustomSection, Tag("custom")],
    Discriminator("type"),  # 通过type字段区分具体类型
]

# 类型别名（方便导入）
ResumeSectionType = (
    PersonalInfoSection
    | SummarySection
    | WorkExperienceSection
    | ProjectsSection
    | EducationSection
    | SkillsSection
    | LanguagesSection
    | CertificationsSection
    | QrCodesSection
    | GitHubSection
    | CustomSection
)

# 类型适配器（用于验证和转换）
section_adapter = TypeAdapter(ResumeSectionSchema)
# 因为ORM 关心的是怎么存，Pydantic 关心的是怎么用。
# ORM 端：一张表通吃
# class ResumeSection(Base):
#     type: str        # "personal_info" / "work_experience" / ...
#     content: str     # JSON 字符串，不关心里面是什么结构
# 数据库不关心 content 的结构，只要是个字符串就能存。加新板块类型不需要改表结构。
# Pydantic 端：每种板块一个类
# class PersonalInfoSection(ResumeSectionBase):
#     content: PersonalInfo | None           # IDE 知道有 full_name、phone...
# class WorkExperienceSection(ResumeSectionBase):
#     content: WorkExperienceContent | None  # IDE 知道有 items: list[...]
# 没有这些独立类的话，你写代码时就是这样：
# # 假设只有一个 Section 类，content 是 dict
# section.content["full_name"]        # ❌ 字符串 key，没有 IDE 补全
# section.content.get("full_name", "")  # ❌ 全靠手写
# # 有独立类型的话：
# personal_info_section.content.full_name  # ✅ IDE 自动补全，类型检查
# Discriminated Union 的作用：
# ResumeSectionSchema = Annotated[
#     PersonalInfoSection | SummarySection | ...,
#     Discriminator("type"),  # 根据 type 字段自动选择正确的类
# ]
# 前端发来 {"type": "personal_info", "content": {"full_name": "张三"}}，Pydantic 自动识别出这是 PersonalInfoSection，把 content 验证为 PersonalInfo。如果 content 里写了 items（工作经历的字段），Pydantic 直接报错。
# 对比总结：
#  	ORM ResumeSection	Pydantic 各 Section 子类
# 目的	存到数据库	用在代码里
# content 类型	str（JSON 字符串）	PersonalInfo / WorkExperienceContent / ...
# 加新板块	不改表，直接加 type	加一个新类，加到 Union 里
# IDE 补全	❌ 没有	✅ 全有
# 验证	❌ 不验证 content 结构	✅ 按类型严格验证
# ORM 追求存储灵活，Pydantic 追求使用安全。两边各司其职，所以就是"ORM 一个类，Pydantic 十几个类"。
# 板块类型到内容模型的映射
SECTION_TYPE_TO_MODEL: dict[str, type[BaseModel]] = {
    "personal_info": PersonalInfo,
    "summary": Summary,
    "work_experience": WorkExperienceItem,
    "education": EducationItem,
    "projects": ProjectItem,
    "certifications": CertificationItem,
    "languages": LanguageItem,
    "github": GitHubItem,
    "custom": CustomContent,
    "skills": SkillItem,
}
