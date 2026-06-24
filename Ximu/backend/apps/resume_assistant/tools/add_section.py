"""添加板块的工具模块。

本模块定义了AddSectionTool，用于AI Agent向简历添加新板块。
支持添加标准板块和自定义板块。
"""  # 模块文档字符串，说明这个文件是做什么的

import uuid  # 导入UUID模块，用于生成唯一的标识符（ID）
from typing import Any  # 导入Any类型，表示可以是任何类型的数据

from pydantic import BaseModel, Field  # 导入Pydantic组件，用于定义数据模型和字段验证
from sqlalchemy import select  # 导入SQL查询构建器，用于构建数据库查询语句
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)  # 导入异步数据库会话，用于异步操作数据库

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
from shared.types.resume import (  # 导入各种板块类型，用于创建不同类型的板块
    CertificationsContent,
    CertificationsSection,
    CustomContent,
    CustomSection,
    EducationContent,
    EducationSection,
    GitHubContent,
    GitHubSection,
    LanguagesContent,
    LanguagesSection,
    ProjectsContent,
    ProjectsSection,
    QrCodesContent,
    QrCodesSection,
    SkillsContent,
    SkillsSection,
    Summary,
    SummarySection,
    WorkExperienceContent,
    WorkExperienceSection,
)

# 所有可用的板块类型列表
# 这个列表定义了简历中可以添加的所有板块类型
_ALL_TYPES = [
    "personal_info",  # 个人信息板块
    "summary",  # 个人总结板块
    "work_experience",  # 工作经历板块
    "projects",  # 项目经验板块
    "education",  # 教育背景板块
    "skills",  # 技能板块
    "languages",  # 语言能力板块
    "certifications",  # 证书板块
    "qr_codes",  # 二维码板块
    "github",  # GitHub项目板块
    "custom",  # 自定义板块
]

# 板块类型到（Section类, Content类）的映射
# 这个映射用于根据板块类型创建对应的板块实例
_SECTION_TYPE_MAP: dict[str, tuple[type, type | Any]] = {
    "summary": (SummarySection, Summary),  # 个人总结板块对应的类
    "work_experience": (
        WorkExperienceSection,
        WorkExperienceContent,
    ),  # 工作经历板块对应的类
    "projects": (ProjectsSection, ProjectsContent),  # 项目经验板块对应的类
    "education": (EducationSection, EducationContent),  # 教育背景板块对应的类
    "skills": (SkillsSection, SkillsContent),  # 技能板块对应的类
    "languages": (LanguagesSection, LanguagesContent),  # 语言能力板块对应的类
    "certifications": (
        CertificationsSection,
        CertificationsContent,
    ),  # 证书板块对应的类
    "github": (GitHubSection, GitHubContent),  # GitHub项目板块对应的类
    "qr_codes": (QrCodesSection, QrCodesContent),  # 二维码板块对应的类
}


def _create_section(
    section_type: str,
    resume_id: str,
    title: str,
    sort_order: int,
) -> tuple:
    """工厂函数：根据板块类型创建对应的Section实例。

    Args:
        section_type: 板块类型标识。
        resume_id: 简历ID。
        title: 显示标题。
        sort_order: 排序序号。

    Returns:
        (Section实例, Section类) 元组。
    """
    # 从映射中获取对应的Section类和Content类
    section_cls, content_cls = _SECTION_TYPE_MAP[section_type]
    # 创建并返回Section实例
    return section_cls(
        id=str(uuid.uuid4()),  # 生成唯一的UUID作为板块ID
        resume_id=resume_id,  # 设置所属的简历ID
        title=title,  # 设置板块标题
        sort_order=sort_order,  # 设置排序序号
        content=content_cls(),  # 创建空的内容实例
        created_at=utc_now(),  # 设置创建时间
        updated_at=utc_now(),  # 设置更新时间
    ), section_cls  # 同时返回Section类，方便后续使用


async def _restore_hidden_section(
    db: AsyncSession,
    resume_id: str,
    section_type: str,
) -> ResumeSection | None:
    """查找并恢复已存在但被隐藏的板块。

    Args:
        db: 数据库会话。
        resume_id: 简历ID。
        section_type: 板块类型。

    Returns:
        已存在的ResumeSection（已设置visible=True）或None。
    """
    # 在数据库中查找指定简历的指定类型板块
    result = await db.execute(
        select(ResumeSection).where(
            ResumeSection.type == section_type,  # 板块类型匹配
            ResumeSection.resume_id == resume_id,  # 简历ID匹配
        )
    )
    # 获取查询结果（如果存在的话）
    resume_section = result.scalar_one_or_none()
    # 如果找到了隐藏的板块，将其设置为可见
    if resume_section is not None:
        resume_section.visible = True  # 恢复可见性
    return resume_section  # 返回板块对象（如果没找到则返回None）


class AddSectionToolInput(BaseModel):
    """添加板块工具的输入数据模型。"""

    type: str = Field(
        description="要添加的板块类型"
    )  # 板块类型字段，用于指定要添加什么类型的板块
    title: str = Field(
        description="板块的显示标题"
    )  # 板块标题字段，用于设置板块的显示名称


class AddSectionTool(BaseTool):
    """添加板块的工具类。

    AI Agent调用此工具来向简历添加新板块。
    """

    name = "add_section"  # 工具名称，用于标识这个工具
    description = "Add a new section to the resume. Use this when the user wants to add a new section type. Available types: {type_examples}"  # 工具描述，告诉AI Agent这个工具的作用
    input_model = AddSectionToolInput  # 指定输入数据模型

    async def execute(
        self, arguments: AddSectionToolInput, context: ToolExecutionContext
    ) -> ToolResult:
        """执行添加板块操作。

        Args:
            arguments: 输入参数（板块类型和标题）。
            context: 工具执行上下文。

        Returns:
            操作结果。
        """
        # 检查是否已存在同类型的板块（custom类型除外，因为可以有多个自定义板块）
        existing_types = {
            s.get("type") for s in context.sections
        }  # 获取所有已存在的板块类型
        if (
            arguments.type in existing_types and arguments.type != "custom"
        ):  # 如果已存在且不是自定义类型
            return ToolResult(
                is_error=True,  # 标记为错误
                output=f"Section of type '{arguments.type}' already exists",  # 返回错误信息
            )

        # 获取简历ID和下一个排序序号
        resume_id = context.sections[0]["resume_id"]  # 从第一个板块获取简历ID
        next_sort_order = (
            context.sections[-1]["sort_order"] + 1
        )  # 获取最后一个板块的排序序号并加1
        now = utc_now()  # 获取当前时间

        # 使用异步数据库会话执行操作
        async with async_session() as db:
            if arguments.type == "custom":  # 如果是自定义板块
                # 创建自定义板块实例
                section = CustomSection(
                    id=str(uuid.uuid4()),  # 生成唯一ID
                    resume_id=resume_id,  # 设置简历ID
                    title=arguments.title,  # 设置标题
                    sort_order=next_sort_order,  # 设置排序序号
                    content=CustomContent(),  # 创建空的内容
                    created_at=now,  # 设置创建时间
                    updated_at=now,  # 设置更新时间
                )
                # 将板块添加到数据库
                db.add(ResumeSection.from_pydantic(section))
                # 将板块数据添加到上下文
                context.sections.append(section.model_dump())
            else:  # 如果是标准板块
                # 先尝试恢复已隐藏的板块
                resume_section = await _restore_hidden_section(
                    db, resume_id, arguments.type
                )
                if resume_section is not None:  # 如果存在隐藏板块
                    resume_section.updated_at = now  # 更新修改时间
                    db.add(resume_section)  # 将板块添加到数据库
                    context.sections.append(
                        resume_section.to_pydantic().model_dump()
                    )  # 将板块数据添加到上下文
                else:  # 如果不存在隐藏板块，创建新板块
                    section, _ = _create_section(
                        arguments.type, resume_id, arguments.title, next_sort_order
                    )
                    
                    db.add(ResumeSection.from_pydantic(section))  # 将板块添加到数据库
                    context.sections.append(
                        section.model_dump()
                    )  # 将板块数据添加到上下文

            # 更新上下文中的元数据
            section_id = context.sections[-1]["id"]  # 获取新添加板块的ID
            context.metadata["id_to_type"][section_id] = (
                arguments.type
            )  # 记录ID到类型的映射
            context.sections = sorted(
                context.sections, key=lambda x: x["sort_order"]
            )  # 按排序序号重新排序
            await db.commit()  # 提交数据库事务

        return ToolResult(
            output=f"Successfully added section {section_id}."
        )  # 返回成功结果

    def to_api_schema_v2(self, sections: list[dict[str, Any]]) -> dict[str, Any]:
        """生成API Schema v2格式的工具定义。"""
        # 获取已存在的板块类型
        existing_types = {s.get("type") for s in sections if s.get("type")}
        # 计算可用的板块类型（排除已存在的）
        available_types = [t for t in _ALL_TYPES if t not in existing_types]
        # custom类型总是可用的
        if "custom" not in available_types:
            available_types.append("custom")
        # 将可用类型列表转换为字符串格式
        type_examples = '", "'.join(available_types)

        # 返回API Schema格式的工具定义
        return {
            "name": self.name,  # 工具名称
            "description": self.description.format(
                type_examples=type_examples
            ),  # 格式化后的工具描述
            "input_schema": self.input_model.model_json_schema(),  # 输入数据的JSON Schema
        }
