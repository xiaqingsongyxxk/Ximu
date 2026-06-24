"""简历提示词构建器模块。  # 模块级别的文档字符串，说明这个文件是干什么的

本模块提供将简历数据格式化为LLM提示词的功能：  # 告诉使用者这个模块的核心能力
1. PersonalInfoFields - 个人信息字段配置  # 第一个类：控制个人信息显示哪些字段
2. ItemFields - 条目字段配置  # 第二个类：控制条目（如工作经历）显示哪些字段
3. SectionHeaderConfig - 板块头部配置  # 第三个类：控制板块标题的显示方式
4. ResumePromptBuilder - 提示词构建器核心类  # 第四个类：最核心的类，负责拼装提示词

用于JD分析和简历助手场景，将简历内容转换为LLM可理解的文本。  # 说明应用场景：分析职位描述(JD)和简历匹配
"""  # 文档字符串结束

# 让Python支持类型注解的延迟求值，写类型提示更灵活
from __future__ import annotations

# @dataclass装饰器自动生成__init__等方法，field用于定义字段默认值
from dataclasses import dataclass, field

# 从简历类型定义文件导入各种数据类型
from shared.types.resume import (
    CertificationsSection,  # 证书板块
    CustomSection,  # 自定义板块
    EducationItem,  # 教育经历单条目
    EducationSection,  # 教育经历板块
    GitHubSection,  # GitHub板块
    LanguagesSection,  # 语言能力板块
    PersonalInfoSection,  # 个人信息板块
    ProjectsSection,  # 项目经历板块
    QrCodesSection,  # 二维码板块
    ResumeSectionSchema,  # 所有板块的基类/联合类型
    SkillsSection,  # 技能板块
    SummarySection,  # 个人简介板块
    WorkExperienceItem,  # 工作经历单条目
    WorkExperienceSection,  # 工作经历板块
)


@dataclass  # 用装饰器把这个类变成数据类，自动生成__init__、__repr__等方法
class PersonalInfoFields:  # 定义个人信息字段配置类
    """个人信息字段配置。  # 类的文档字符串

    控制哪些个人信息字段包含在提示词中。  # 说明用途：可以开关每个字段
    """

    full_name: bool = True  # 姓名，默认显示
    age: bool = True  # 年龄，默认显示
    gender: bool = True  # 性别，默认显示
    email: bool = True  # 邮箱，默认显示
    phone: bool = True  # 电话，默认显示
    education_level: bool = True  # 学历（如本科、硕士），默认显示
    job_title: bool = True  # 期望职位，默认显示
    salary: bool = True  # 期望薪资，默认显示
    location: bool = True  # 所在地点，默认显示
    political_status: bool = True  # 政治面貌（如党员、群众），默认显示
    ethnicity: bool = True  # 民族，默认显示
    hometown: bool = True  # 籍贯（老家在哪），默认显示
    marital_status: bool = True  # 婚姻状况（已婚/未婚），默认显示
    years_of_experience: bool = True  # 工作年限，默认显示
    wechat: bool = True  # 微信号，默认显示
    website: bool = True  # 个人网站，默认显示
    linkedin: bool = True  # LinkedIn主页链接，默认显示


@dataclass  # 同样用装饰器变成数据类
class ItemFields:  # 定义条目字段配置类（用于工作经历、教育经历等条目）
    """条目字段配置（工作经历/教育等）。  # 说明适用场景"""

    location: bool = True  # 地点字段，默认显示


@dataclass  # 装饰器，自动生成基础方法
class SectionHeaderConfig:  # 定义板块头部配置类
    """板块头部配置。  # 控制板块标题区域的显示内容"""

    include_section_id: bool = False  # 是否在头部显示板块ID，默认不显示


@dataclass  # 核心类也用数据类装饰器
class ResumePromptBuilder:  # 定义简历提示词构建器，这是整个文件最核心的类
    """简历提示词构建器。  # 类文档字符串

    将简历数据格式化为LLM可理解的文本格式。  # 核心功能：把结构化的简历数据变成一段文本给AI看
    """

    personal_info_fields: PersonalInfoFields = field(
        default_factory=PersonalInfoFields
    )  # 个人信息字段配置，默认创建一个新实例
    item_fields: ItemFields = field(
        default_factory=ItemFields
    )  # 条目字段配置，默认创建一个新实例
    section_header: SectionHeaderConfig = field(
        default_factory=SectionHeaderConfig
    )  # 板块头部配置，默认创建一个新实例
    job_desc_prefix: str = (
        "#Job Description:"  # 职位描述的前缀文本，用来标识JD内容的开始
    )

    def build_user_prompt(  # 定义构建用户提示词的方法
        self,  # 实例方法的第一个参数
        sections: list[ResumeSectionSchema],  # 简历的所有板块列表
        job_description: str,  # 职位描述(JD)的文本内容
        job_title: str | None = None,  # 职位名称，可选参数
    ) -> str:  # 返回值类型是字符串
        """构建用户提示词。  # 方法文档字符串：把简历和JD拼成一段完整的提示词"""
        final_content_list = []  # 用来存放每个板块转换后的文本

        for section in sections:  # 遍历简历中的每一个板块
            if isinstance(section, PersonalInfoSection):  # 如果是个人信息板块
                lines = self._build_personal_info_section(
                    section
                )  # 调用个人信息处理方法
            elif isinstance(section, SummarySection):  # 如果是个人简介板块
                lines = self._build_summary_section(section)  # 调用个人简介处理方法
            elif isinstance(section, WorkExperienceSection):  # 如果是工作经历板块
                lines = self._build_work_experience_section(
                    section
                )  # 调用工作经历处理方法
            elif isinstance(section, ProjectsSection):  # 如果是项目经历板块
                lines = self._build_projects_section(section)  # 调用项目经历处理方法
            elif isinstance(section, EducationSection):  # 如果是教育经历板块
                lines = self._build_education_section(section)  # 调用教育经历处理方法
            elif isinstance(section, SkillsSection):  # 如果是技能板块
                lines = self._build_skills_section(section)  # 调用技能处理方法
            elif isinstance(section, LanguagesSection):  # 如果是语言能力板块
                lines = self._build_languages_section(section)  # 调用语言能力处理方法
            elif isinstance(section, CertificationsSection):  # 如果是证书板块
                lines = self._build_certifications_section(section)  # 调用证书处理方法
            elif isinstance(section, GitHubSection):  # 如果是GitHub板块
                lines = self._build_github_section(section)  # 调用GitHub处理方法
            elif isinstance(section, QrCodesSection):  # 如果是二维码板块
                lines = self._build_qrcodes_section(section)  # 调用二维码处理方法
            elif isinstance(section, CustomSection):  # 如果是自定义板块
                lines = self._build_custom_section(section)  # 调用自定义板块处理方法
            else:  # 如果是不认识的板块类型
                continue  # 直接跳过，不处理

            final_content_list.append(
                "\n".join(lines)
            )  # 把当前板块的多行文本用换行符拼成一个字符串，加入列表

        user_prompt = "\n\n".join(
            final_content_list
        )  # 把所有板块的文本用两个换行符拼起来（板块之间空一行）
        return f"{self.job_desc_prefix}\n---\n{job_description}\n---\n\n{user_prompt}"  # 最终格式：JD前缀 + 分隔线 + JD内容 + 分隔线 + 简历内容

    def _build_section_header(
        self, section: ResumeSectionSchema
    ) -> list[str]:  # 构建板块头部，返回多行文本
        """构建板块通用头部。  # 每个板块开头都有的标准格式"""
        lines = [  # 开始构建头部的行列表
            "---",  # 水平分隔线，视觉上区分不同板块
            f"# {section.type} - {section.title}",  # 标题行：# 板块类型 - 板块标题
        ]
        if self.section_header.include_section_id:  # 如果配置了要显示板块ID
            lines.append(f"section_id: {section.id}")  # 追加一行板块ID信息
        return lines  # 返回头部行列表

    def _append_section_footer(
        self, lines: list[str]
    ) -> None:  # 给板块末尾加分隔线，直接修改传入的列表
        """添加板块尾部。  # 在板块末尾加一条分隔线"""
        lines.append("---")  # 添加水平分隔线作为板块结束标记

    def _build_personal_info_section(
        self, section: PersonalInfoSection
    ) -> list[str]:  # 处理个人信息板块
        """构建个人信息板块。  # 把个人信息转成LLM能读的文本格式"""
        lines = self._build_section_header(section)  # 先加上板块头部（分隔线+标题）

        if section.content:  # 如果有个人信息内容
            content = section.content  # 取出内容对象，后面方便引用
            cfg = self.personal_info_fields  # 取出字段配置，决定显示哪些字段

            # 根据配置收集字段  # 下面根据配置开关，决定哪些字段要放进提示词
            optional_fields: list[
                tuple[str, str]
            ] = []  # 存放要显示的字段名和值的配对列表
            if (
                cfg.full_name and content.full_name
            ):  # 如果配置允许显示姓名，并且姓名不为空
                optional_fields.append(("name", content.full_name))  # 把姓名加进去
            if cfg.age and content.age:  # 如果配置允许显示年龄，并且年龄不为空
                optional_fields.append(("age", content.age))  # 把年龄加进去
            if cfg.gender and content.gender:  # 如果配置允许显示性别，并且性别不为空
                optional_fields.append(("gender", content.gender))  # 把性别加进去
            if cfg.email and content.email:  # 如果配置允许显示邮箱，并且邮箱不为空
                optional_fields.append(("email", content.email))  # 把邮箱加进去
            if cfg.phone and content.phone:  # 如果配置允许显示电话，并且电话不为空
                optional_fields.append(("phone", content.phone))  # 把电话加进去
            if (
                cfg.education_level and content.education_level
            ):  # 如果配置允许显示学历，并且学历不为空
                optional_fields.append(
                    ("education_level", content.education_level)
                )  # 把学历加进去
            if (
                cfg.job_title and content.job_title
            ):  # 如果配置允许显示职位，并且职位不为空
                optional_fields.append(("job_title", content.job_title))  # 把职位加进去
            if cfg.salary and content.salary:  # 如果配置允许显示薪资，并且薪资不为空
                optional_fields.append(("salary", content.salary))  # 把薪资加进去
            if (
                cfg.location and content.location
            ):  # 如果配置允许显示地点，并且地点不为空
                optional_fields.append(("location", content.location))  # 把地点加进去
            if (
                cfg.political_status and content.political_status
            ):  # 如果配置允许显示政治面貌，并且政治面貌不为空
                optional_fields.append(
                    ("political_status", content.political_status)
                )  # 把政治面貌加进去
            if (
                cfg.ethnicity and content.ethnicity
            ):  # 如果配置允许显示民族，并且民族不为空
                optional_fields.append(("ethnicity", content.ethnicity))  # 把民族加进去
            if (
                cfg.hometown and content.hometown
            ):  # 如果配置允许显示籍贯，并且籍贯不为空
                optional_fields.append(("hometown", content.hometown))  # 把籍贯加进去
            if (
                cfg.marital_status and content.marital_status
            ):  # 如果配置允许显示婚姻状况，并且婚姻状况不为空
                optional_fields.append(
                    ("marital_status", content.marital_status)
                )  # 把婚姻状况加进去
            if (
                cfg.years_of_experience and content.years_of_experience
            ):  # 如果配置允许显示工作年限，并且工作年限不为空
                optional_fields.append(
                    ("years_of_experience", content.years_of_experience)
                )  # 把工作年限加进去
            if cfg.wechat and content.wechat:  # 如果配置允许显示微信，并且微信不为空
                optional_fields.append(("wechat", content.wechat))  # 把微信号加进去
            if cfg.website and content.website:  # 如果配置允许显示网站，并且网站不为空
                optional_fields.append(("website", content.website))  # 把个人网站加进去
            if (
                cfg.linkedin and content.linkedin
            ):  # 如果配置允许显示LinkedIn，并且LinkedIn不为空
                optional_fields.append(
                    ("linkedin", content.linkedin)
                )  # 把LinkedIn链接加进去

            for field_name, field_value in optional_fields:  # 遍历所有收集到的字段
                lines.append(
                    f"{field_name}: {field_value}"
                )  # 格式化成 "字段名: 字段值" 的形式追加到行列表
        else:  # 如果没有任何个人信息内容
            lines.append("[user did not provide any content]")  # 提示用户没有提供内容

        self._append_section_footer(lines)  # 在末尾加分隔线
        return lines  # 返回完整的个人信息板块文本

    def _build_summary_section(
        self, section: SummarySection
    ) -> list[str]:  # 处理个人简介板块
        """构建个人简介板块。  # 把个人简介/自我评价转成文本"""
        lines = self._build_section_header(section)  # 先加上板块头部

        if section.content and section.content.text:  # 如果有简介内容，并且文本不为空
            lines.append(f"text: {section.content.text}")  # 把简介文本加进去
        else:  # 如果没有简介内容
            lines.append("[user did not provide any content]")  # 提示用户没有提供内容

        self._append_section_footer(lines)  # 在末尾加分隔线
        return lines  # 返回完整的个人简介板块文本

    def _build_work_experience_section(
        self, section: WorkExperienceSection
    ) -> list[str]:  # 处理工作经历板块
        """构建工作经历板块。  # 把多段工作经历转成文本"""
        lines = self._build_section_header(section)  # 先加上板块头部

        if (
            section.content and section.content.items
        ):  # 如果有工作经历内容，并且条目列表不为空
            for idx, item in enumerate(
                section.content.items
            ):  # 遍历每一条工作经历，idx是索引
                item_lines = self._format_work_experience_item(
                    item, idx + 1
                )  # 格式化单条工作经历，编号从1开始
                lines.extend(item_lines)  # 把单条经历的多行文本追加到总列表
        else:  # 如果没有工作经历
            lines.append("[user did not provide any content]")  # 提示用户没有提供内容

        self._append_section_footer(lines)  # 在末尾加分隔线
        return lines  # 返回完整的工作经历板块文本

    def _format_work_experience_item(
        self, item: WorkExperienceItem, idx: int
    ) -> list[str]:  # 格式化单条工作经历
        """格式化单个工作经历条目。  # 把一条工作经历转成多行文本"""
        lines = [  # 开始构建这一条工作经历的行列表
            f"## [{idx}] {item.company}",  # 二级标题：序号 + 公司名
            f"position: {item.position}",  # 职位名称
        ]

        if (
            self.item_fields.location and item.location
        ):  # 如果配置允许显示地点，并且地点不为空
            lines.append(f"location: {item.location}")  # 追加工作地点

        date_range = _format_date_range(
            item.start_date, item.end_date, item.current
        )  # 调用工具函数格式化日期范围
        lines.append(f"date: {date_range}")  # 追加工作时间段

        if item.description:  # 如果有工作描述
            lines.append(f"description: {item.description}")  # 追加工作描述

        if item.highlights:  # 如果有工作亮点/成就列表
            lines.append("highlights:")  # 先加一个"highlights:"标题
            for h in item.highlights:  # 遍历每一条亮点
                lines.append(f"  - {h}")  # 用列表格式（两个空格+短横线）追加每条亮点

        return lines  # 返回这条工作经历的所有行

    def _build_projects_section(
        self, section: ProjectsSection
    ) -> list[str]:  # 处理项目经历板块
        """构建项目经历板块。  # 把多个项目经历转成文本"""
        lines = self._build_section_header(section)  # 先加上板块头部

        if (
            section.content and section.content.items
        ):  # 如果有项目经历内容，并且条目列表不为空
            for idx, item in enumerate(section.content.items):  # 遍历每一个项目
                item_lines = _format_project_item(
                    item, idx + 1
                )  # 调用模块级函数格式化单个项目，编号从1开始
                lines.extend(item_lines)  # 把单个项目的多行文本追加到总列表
        else:  # 如果没有项目经历
            lines.append("[user did not provide any content]")  # 提示用户没有提供内容

        self._append_section_footer(lines)  # 在末尾加分隔线
        return lines  # 返回完整的项目经历板块文本

    def _build_education_section(
        self, section: EducationSection
    ) -> list[str]:  # 处理教育经历板块
        """构建教育经历板块。  # 把多段教育经历转成文本"""
        lines = self._build_section_header(section)  # 先加上板块头部

        if (
            section.content and section.content.items
        ):  # 如果有教育经历内容，并且条目列表不为空
            for idx, item in enumerate(section.content.items):  # 遍历每一段教育经历
                item_lines = self._format_education_item(
                    item, idx + 1
                )  # 格式化单段教育经历，编号从1开始
                lines.extend(item_lines)  # 把单段经历的多行文本追加到总列表
        else:  # 如果没有教育经历
            lines.append("[user did not provide any content]")  # 提示用户没有提供内容

        self._append_section_footer(lines)  # 在末尾加分隔线
        return lines  # 返回完整的教育经历板块文本

    def _format_education_item(
        self, item: EducationItem, idx: int
    ) -> list[str]:  # 格式化单段教育经历
        """格式化单个教育经历条目。  # 把一段教育经历转成多行文本"""
        lines = [f"## [{idx}] {item.institution}"]  # 二级标题：序号 + 学校名

        if item.degree:  # 如果有学位信息（如学士、硕士）
            lines.append(f"degree: {item.degree}")  # 追加学位
        if item.field:  # 如果有专业信息
            lines.append(f"field: {item.field}")  # 追加专业
        if (
            self.item_fields.location and item.location
        ):  # 如果配置允许显示地点，并且地点不为空
            lines.append(f"location: {item.location}")  # 追加学校所在地
        if item.start_date or item.end_date:  # 如果有开始日期或结束日期
            date_range = (
                f"{item.start_date} - {item.end_date}"
                if item.end_date
                else item.start_date
            )  # 有结束日期就显示范围，否则只显示开始日期
            lines.append(f"date: {date_range}")  # 追加就读时间段
        if item.gpa:  # 如果有GPA成绩
            lines.append(f"gpa: {item.gpa}")  # 追加GPA
        if item.highlights:  # 如果有教育相关的亮点（如获奖、荣誉）
            lines.append("highlights:")  # 先加一个"highlights:"标题
            for h in item.highlights:  # 遍历每一条亮点
                lines.append(f"  - {h}")  # 用列表格式追加每条亮点

        return lines  # 返回这段教育经历的所有行

    def _build_skills_section(
        self, section: SkillsSection
    ) -> list[str]:  # 处理技能板块
        """构建技能板块。  # 把技能分类列表转成文本"""
        lines = self._build_section_header(section)  # 先加上板块头部

        if (
            section.content and section.content.categories
        ):  # 如果有技能内容，并且分类列表不为空
            for category in section.content.categories:  # 遍历每一个技能分类
                if (
                    category.name and category.skills
                ):  # 如果分类有名字并且有具体技能列表
                    lines.append(f"## {category.name}")  # 用分类名作为二级标题
                    lines.append(
                        f"skills: {', '.join(category.skills)}"
                    )  # 把技能列表用逗号拼接显示
                elif category.name:  # 如果只有分类名没有具体技能
                    lines.append(f"## {category.name}")  # 只显示分类名
        else:  # 如果没有技能信息
            lines.append("[user did not provide any content]")  # 提示用户没有提供内容

        self._append_section_footer(lines)  # 在末尾加分隔线
        return lines  # 返回完整的技能板块文本

    def _build_languages_section(
        self, section: LanguagesSection
    ) -> list[str]:  # 处理语言能力板块
        """构建语言能力板块。  # 把语言能力列表转成文本"""
        lines = self._build_section_header(section)  # 先加上板块头部

        if (
            section.content and section.content.items
        ):  # 如果有语言能力内容，并且条目列表不为空
            for item in section.content.items:  # 遍历每一项语言能力
                item_lines = [f"## {item.language}"]  # 用语言名称作为二级标题
                if item.proficiency:  # 如果有熟练程度（如精通、熟练）
                    item_lines.append(
                        f"proficiency: {item.proficiency}"
                    )  # 追加熟练程度
                if item.description:  # 如果有额外描述
                    item_lines.append(f"description: {item.description}")  # 追加描述
                lines.extend(item_lines)  # 把这一项语言的多行追加到总列表
        else:  # 如果没有语言能力信息
            lines.append("[user did not provide any content]")  # 提示用户没有提供内容

        self._append_section_footer(lines)  # 在末尾加分隔线
        return lines  # 返回完整的语言能力板块文本

    def _build_certifications_section(
        self, section: CertificationsSection
    ) -> list[str]:  # 处理证书板块
        """构建证书板块。  # 把证书列表转成文本"""
        lines = self._build_section_header(section)  # 先加上板块头部

        if (
            section.content and section.content.items
        ):  # 如果有证书内容，并且条目列表不为空
            for idx, item in enumerate(section.content.items):  # 遍历每一个证书
                lines.append(f"## [{idx + 1}] {item.name}")  # 二级标题：序号 + 证书名称
                if item.issuer:  # 如果有发证机构
                    lines.append(f"issuer: {item.issuer}")  # 追加发证机构
                if item.date:  # 如果有获得日期
                    lines.append(f"date: {item.date}")  # 追加获得日期
        else:  # 如果没有证书信息
            lines.append("[user did not provide any content]")  # 提示用户没有提供内容

        self._append_section_footer(lines)  # 在末尾加分隔线
        return lines  # 返回完整的证书板块文本

    def _build_github_section(
        self, section: GitHubSection
    ) -> list[str]:  # 处理GitHub板块
        """构建GitHub板块。  # 把GitHub仓库列表转成文本"""
        lines = self._build_section_header(section)  # 先加上板块头部

        if (
            section.content and section.content.items
        ):  # 如果有GitHub内容，并且条目列表不为空
            for item in section.content.items:  # 遍历每一个GitHub仓库
                lines.append(f"## {item.name}")  # 用仓库名作为二级标题
                if item.repo_url:  # 如果有仓库链接
                    lines.append(f"url: {item.repo_url}")  # 追加仓库URL
                if item.description:  # 如果有仓库描述
                    lines.append(f"description: {item.description}")  # 追加描述
                if item.language:  # 如果有主要编程语言
                    lines.append(f"language: {item.language}")  # 追加编程语言
                if item.stars:  # 如果有star数
                    lines.append(f"stars: {item.stars}")  # 追加star数量
        else:  # 如果没有GitHub信息
            lines.append("[user did not provide any content]")  # 提示用户没有提供内容

        self._append_section_footer(lines)  # 在末尾加分隔线
        return lines  # 返回完整的GitHub板块文本

    def _build_qrcodes_section(
        self, section: QrCodesSection
    ) -> list[str]:  # 处理二维码板块
        """构建二维码板块。  # 把二维码链接列表转成文本"""
        lines = self._build_section_header(section)  # 先加上板块头部

        if (
            section.content and section.content.items
        ):  # 如果有二维码内容，并且条目列表不为空
            for item in section.content.items:  # 遍历每一个二维码
                lines.append(f"## {item.label}")  # 用标签名作为二级标题
                if item.url:  # 如果有链接地址
                    lines.append(f"url: {item.url}")  # 追加链接
        else:  # 如果没有二维码信息
            lines.append("[user did not provide any content]")  # 提示用户没有提供内容

        self._append_section_footer(lines)  # 在末尾加分隔线
        return lines  # 返回完整的二维码板块文本

    def _build_custom_section(
        self, section: CustomSection
    ) -> list[str]:  # 处理自定义板块
        """构建自定义板块。  # 把用户自定义的内容转成文本"""
        lines = self._build_section_header(section)  # 先加上板块头部

        if (
            section.content and section.content.items
        ):  # 如果有自定义内容，并且条目列表不为空
            for idx, item in enumerate(section.content.items):  # 遍历每一个自定义条目
                item_lines = [
                    f"## [{idx + 1}] {item.title}"
                ]  # 二级标题：序号 + 自定义标题
                if item.date:  # 如果有日期
                    item_lines.append(f"date: {item.date}")  # 追加日期
                if item.description:  # 如果有描述
                    item_lines.append(f"description: {item.description}")  # 追加描述
                lines.extend(item_lines)  # 把这一条的多行追加到总列表
        else:  # 如果没有自定义内容
            lines.append("[user did not provide any content]")  # 提示用户没有提供内容

        self._append_section_footer(lines)  # 在末尾加分隔线
        return lines  # 返回完整的自定义板块文本


def _format_project_item(item, idx: int) -> list[str]:  # 模块级函数：格式化单个项目条目
    """格式化单个项目条目。  # 把一个项目转成多行文本"""
    lines = [f"## [{idx}] {item.name}"]  # 二级标题：序号 + 项目名称

    if item.url:  # 如果有项目链接
        lines.append(f"url: {item.url}")  # 追加项目URL
    if item.description:  # 如果有项目描述
        lines.append(f"description: {item.description}")  # 追加描述
    if item.technologies:  # 如果有技术栈列表
        lines.append(
            f"technologies: {', '.join(item.technologies)}"
        )  # 用逗号拼接技术栈并追加
    if item.start_date or item.end_date:  # 如果有开始日期或结束日期
        date_range = (
            f"{item.start_date} - {item.end_date}"
            if item.end_date
            else f"{item.start_date} - 至今"
        )  # 有结束日期显示范围，否则显示"至今"
        lines.append(f"date: {date_range}")  # 追加项目时间段
    if item.highlights:  # 如果有项目亮点/成果
        lines.append("highlights:")  # 先加一个"highlights:"标题
        for h in item.highlights:  # 遍历每一条亮点
            lines.append(f"  - {h}")  # 用列表格式追加每条亮点

    return lines  # 返回这个项目的所有行


def _format_date_range(
    start_date: str, end_date: str, current: bool
) -> str:  # 模块级函数：格式化日期范围
    """格式化日期范围。  # 把开始日期、结束日期、是否在职拼成一个时间段字符串"""
    if current:  # 如果当前还在职/在读
        return (
            f"{start_date} - 至今" if start_date else "至今"
        )  # 有开始日期就显示"开始 - 至今"，否则只显示"至今"
    if end_date:  # 如果有结束日期（已离职/毕业）
        return (
            f"{start_date} - {end_date}" if start_date else end_date
        )  # 有开始日期就显示范围，否则只显示结束日期
    return start_date if start_date else ""  # 都没有的话返回开始日期或空字符串
