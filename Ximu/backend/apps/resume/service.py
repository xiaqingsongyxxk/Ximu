"""简历相关业务逻辑模块。

本模块包含操作简历数据的辅助函数：
1. create_default_sections - 为新简历创建6个默认板块
2. copy_sections_from_workspace - 从主简历复制板块到子简历

这些函数供路由层（router.py）调用以执行领域操作，
不暴露数据库细节给API层，实现业务逻辑与路由的分离。
"""  # 模块文档字符串，说明本模块的职责

import uuid  # 导入UUID模块，用于为每个板块生成唯一ID

from sqlalchemy import select  # 导入SQLAlchemy的select查询构建器
from sqlalchemy.ext.asyncio import AsyncSession  # 导入异步数据库会话类型

from shared.models import ResumeSection  # 从shared/models.py导入简历板块的ORM模型
from shared.types.resume import (  # 从shared/types/resume.py导入各种板块类型和内容类型
    EducationContent,  # 教育背景内容模型（学校、专业、学历等）
    EducationSection,  # 教育背景板块类型（包含type="education"）
    PersonalInfo,  # 个人信息内容模型（姓名、手机、邮箱等）
    PersonalInfoSection,  # 个人信息板块类型（包含type="personal_info"）
    ProjectsContent,  # 项目经历内容模型（项目列表）
    ProjectsSection,  # 项目经历板块类型（包含type="projects"）
    SkillsContent,  # 技能特长内容模型（技能分类列表）
    SkillsSection,  # 技能特长板块类型（包含type="skills"）
    Summary,  # 个人简介内容模型（简介文本）
    SummarySection,  # 个人简介板块类型（包含type="summary"）
    WorkExperienceContent,  # 工作经历内容模型（工作条目列表）
    WorkExperienceSection,  # 工作经历板块类型（包含type="work_experience"）
)


async def create_default_sections(  # 定义创建默认板块的异步函数
    resume_id: str,  # 参数：简历ID（新创建的简历的UUID）
    db: AsyncSession,  # 参数：异步数据库会话
) -> None:  # 无返回值
    """为新简历创建6个默认板块。

    当用户创建新简历（主简历）时，自动创建以下6个标准板块：
    1. 个人信息（sort_order=0）
    2. 个人简介（sort_order=1）
    3. 工作经历（sort_order=2）
    4. 教育背景（sort_order=3）
    5. 技能特长（sort_order=4）
    6. 项目经历（sort_order=5）

    这样用户打开新简历时就能看到完整的简历结构，只需填写内容即可。
    此函数由 router.py 中的 create_workspace 调用。

    Args:
        resume_id: 新简历的唯一标识符（UUID字符串）。
        db: 异步数据库会话，用于执行数据库操作。
    """  # 文档字符串
    # 创建6个默认板块对象列表
    # 每个板块都有唯一的ID、关联的简历ID、标题、排序序号和空的默认内容
    sections = [
        PersonalInfoSection(  # 创建"个人信息"板块
            id=str(uuid.uuid4()),  # 生成唯一ID
            resume_id=resume_id,  # 关联到新简历
            title="个人信息",  # 板块显示标题
            sort_order=0,  # 排序第0位（最靠前）
            content=PersonalInfo(),  # 创建空的个人信息内容（所有字段默认为空字符串）
        ),
        SummarySection(  # 创建"个人简介"板块
            id=str(uuid.uuid4()),  # 生成唯一ID
            resume_id=resume_id,  # 关联到新简历
            title="个人简介",  # 板块显示标题
            sort_order=1,  # 排序第1位
            content=Summary(),  # 创建空的简介内容
        ),
        WorkExperienceSection(  # 创建"工作经历"板块
            id=str(uuid.uuid4()),  # 生成唯一ID
            resume_id=resume_id,  # 关联到新简历
            title="工作经历",  # 板块显示标题
            sort_order=2,  # 排序第2位
            content=WorkExperienceContent(),  # 创建空的工作经历内容
        ),
        EducationSection(  # 创建"教育背景"板块
            id=str(uuid.uuid4()),  # 生成唯一ID
            resume_id=resume_id,  # 关联到新简历
            title="教育背景",  # 板块显示标题
            sort_order=3,  # 排序第3位
            content=EducationContent(),  # 创建空的教育背景内容
        ),
        SkillsSection(  # 创建"技能特长"板块
            id=str(uuid.uuid4()),  # 生成唯一ID
            resume_id=resume_id,  # 关联到新简历
            title="技能特长",  # 板块显示标题
            sort_order=4,  # 排序第4位
            content=SkillsContent(),  # 创建空的技能内容
        ),
        ProjectsSection(  # 创建"项目经历"板块
            id=str(uuid.uuid4()),  # 生成唯一ID
            resume_id=resume_id,  # 关联到新简历
            title="项目经历",  # 板块显示标题
            sort_order=5,  # 排序第5位
            content=ProjectsContent(),  # 创建空的项目经历内容
        ),
    ]

    # 遍历所有板块，转换为ORM对象并添加到数据库会话
    for section in sections:  # 遍历6个板块
        db.add(
            ResumeSection.from_pydantic(section)
        )  # 将Pydantic对象转为ORM对象，添加到数据库会话
        # ResumeSection.from_pydantic() 定义在 shared/models.py 中
        # 它会将Pydantic对象转为字典，然后JSON序列化content字段，创建ORM实例


async def copy_sections_from_workspace(  # 定义复制板块的异步函数
    source_resume_id: str,  # 参数：源简历ID（主简历）
    target_resume_id: str,  # 参数：目标简历ID（子简历）
    db: AsyncSession,  # 参数：异步数据库会话
) -> None:  # 无返回值
    """从源简历（主简历）复制所有板块到目标简历（子简历）。

    复制每个板块的类型、标题、排序、内容等信息，
    但为目标板块分配新的ID，并关联到目标简历。

    此函数由 router.py 中的 create_sub_resume 调用，
    用于子简历继承主简历的板块结构。

    Args:
        source_resume_id: 源简历ID（主简历的UUID）。
        target_resume_id: 目标简历ID（子简历的UUID）。
        db: 异步数据库会话。
    """  # 文档字符串
    from shared.models import (
        ResumeSection,
    )  # 再次导入ResumeSection（函数内导入，避免顶部循环引用）

    # 查询源简历（主简历）的所有板块
    result = await db.execute(  # 执行数据库查询
        select(ResumeSection).where(  # 查询ResumeSection表
            ResumeSection.resume_id == source_resume_id  # 条件：所属简历ID等于源简历ID
        )
    )
    source_sections = result.scalars().all()  # 获取所有源板块的ORM对象列表

    # 遍历源板块，为每个板块创建副本（新ID，关联到目标简历）
    for section in source_sections:  # 遍历每个源板块
        new_section = ResumeSection(  # 创建新的板块ORM对象
            id=str(uuid.uuid4()),  # 生成新的唯一ID（不复用源板块的ID）
            resume_id=target_resume_id,  # 关联到目标简历（子简历）
            title=section.title,  # 复制板块标题
            type=section.type,  # 复制板块类型（如"personal_info"）
            sort_order=section.sort_order,  # 复制排序序号
            visible=section.visible,  # 复制可见性
            content=section.content,  # 复制内容（JSON字符串，直接复制即可）
        )
        db.add(new_section)  # 将新板块添加到数据库会话
