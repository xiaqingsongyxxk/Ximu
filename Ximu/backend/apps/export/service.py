"""简历导出的业务逻辑模块。

本模块提供简历数据的导出功能：
1. export_json - 导出为JSON格式
2. export_txt - 导出为纯文本格式

每种格式都会查询简历及其所有板块，然后按格式组装数据。
"""  # 模块文档字符串

from sqlalchemy import select  # SQL查询构建器
from sqlalchemy.ext.asyncio import AsyncSession  # 异步数据库会话

from shared.models import Resume, ResumeSection  # 简历和板块的ORM模型


async def _fetch_resume_with_sections(
    resume_id: str, db: AsyncSession
) -> tuple[Resume, list[ResumeSection]]:
    """查询简历及其所有板块。

    Args:
        resume_id: 简历ID。
        db: 数据库会话。

    Returns:
        (简历对象, 板块列表) 的元组。

    Raises:
        ValueError: 简历不存在时抛出。
    """
    resume_result = await db.execute(
        select(Resume).where(Resume.id == resume_id)  # 查询简历
    )
    resume = resume_result.scalar_one_or_none()  # 获取结果
    if not resume:  # 如果不存在
        raise ValueError("简历不存在")

    section_result = await db.execute(
        select(ResumeSection)
        .where(ResumeSection.resume_id == resume_id)  # 按简历ID查询板块
        .order_by(ResumeSection.sort_order)  # 按排序序号
    )
    sections = list(section_result.scalars().all())  # 获取所有板块
    return resume, sections


async def export_json(resume_id: str, db: AsyncSession) -> dict:
    """将简历导出为JSON字典。

    Args:
        resume_id: 简历ID。
        db: 数据库会话。

    Returns:
        包含简历和板块数据的字典。
    """
    resume, sections = await _fetch_resume_with_sections(resume_id, db)
    return {
        "resume": resume.to_pydantic().model_dump(),  # 简历数据
        "sections": [
            section.to_pydantic().model_dump() for section in sections  # 板块数据列表
        ],
    }
# model_dump(mode='json') 返回的仍然是 Python dict，不是 JSON 字符串。只是值变了：
# # model_dump()（默认）
# {
#     "id": UUID("550e..."),   # ← UUID 对象
#     "time": datetime(...),    # ← datetime 对象
# }
# # model_dump(mode='json')
# {
#     "id": "550e8400-...",            # ← str
#     "time": "2026-05-20T10:30:00",   # ← str（ISO 格式）
# }
# 两者都是 dict，都不是 JSON 字符串。 JSONResponse 拿到后都会做 json.dumps() 序列化成真正的 JSON 字符串。
# 区别只是 mode='json' 产出的 dict 里的每个值都是 json.dumps 能识别的类型（str/int/float/bool/None），不会崩。
# data（dict，含 UUID/datetime）
#   → json.dumps()  → ❌ TypeError
# data（dict，含 str/ISO字符串）
#   → json.dumps()  → ✅ '{"id":"550e...","time":"2026-05-20T10:30:00"}'
# 不用再额外做任何事，直接给 JSONResponse 就行。

async def export_txt(resume_id: str, db: AsyncSession) -> str:
    """将简历导出为格式化的纯文本。

    根据板块类型格式化内容，跳过隐藏的板块。

    Args:
        resume_id: 简历ID。
        db: 数据库会话。

    Returns:
        格式化的纯文本简历。
    """
    resume, sections = await _fetch_resume_with_sections(resume_id, db)
    section_texts: list[str] = []  # 存储每个板块的文本

    for section in sections:  # 遍历所有板块
        if not section.visible:  # 跳过隐藏板块
            continue

        pydantic_section = section.to_pydantic()  # 转为Pydantic
        content = pydantic_section.content  # 板块内容
        section_type = pydantic_section.type  # 板块类型
        title = pydantic_section.title  # 板块标题

        lines: list[str] = []  # 当前板块的行

        if section_type == "personal_info":  # 个人信息
            if content is None: continue
            lines.append(f"== {title} ==")
            info = content
            for field, label in [
                (info.full_name, "姓名"), (info.job_title, "岗位"),
                (info.phone, "电话"), (info.email, "邮箱"),
            ]:
                if field:
                    lines.append(f"{label}: {field}")

        elif section_type == "summary":  # 个人简介
            if content is None: continue
            lines.append(f"== {title} ==")
            lines.append(content.text)

        elif section_type == "work_experience":  # 工作经历
            if content is None: continue
            lines.append(f"== {title} ==")
            for item in content.items:
                date_range = f"{item.start_date} - {item.end_date}" if item.end_date else item.start_date
                lines.append(f"{item.company} - {item.position} ({date_range})")
                for hl in item.highlights:
                    lines.append(f"  • {hl}")

        elif section_type == "education":  # 教育背景
            if content is None: continue
            lines.append(f"== {title} ==")
            for item in content.items:
                date_range = f"{item.start_date} - {item.end_date}" if item.end_date else item.start_date
                lines.append(f"{item.institution} - {item.degree} ({date_range})")
                for hl in item.highlights:
                    lines.append(f"  • {hl}")

        elif section_type == "projects":  # 项目经历
            if content is None: continue
            lines.append(f"== {title} ==")
            for item in content.items:
                line = item.name
                if item.url: line += f" ({item.url})"
                lines.append(line)
                for hl in item.highlights:
                    lines.append(f"  • {hl}")

        elif section_type == "skills":  # 技能特长
            if content is None: continue
            lines.append(f"== {title} ==")
            for category in content.categories:
                skills_str = ", ".join(category.skills)
                lines.append(f"{category.name}: {skills_str}")

        elif section_type == "languages":  # 语言能力
            if content is None: continue
            lines.append(f"== {title} ==")
            for item in content.items:
                lines.append(f"{item.language} ({item.proficiency})")

        elif section_type == "certifications":  # 资格证书
            if content is None: continue
            lines.append(f"== {title} ==")
            for item in content.items:
                lines.append(f"{item.name} - {item.issuer} ({item.date})")

        elif section_type == "qr_codes":  # 二维码
            if content is None: continue
            lines.append(f"== {title} ==")
            for item in content.items:
                lines.append(f"{item.label}: {item.url}")

        elif section_type == "github":  # GitHub
            if content is None: continue
            lines.append(f"== {title} ==")
            for item in content.items:
                lines.append(f"{item.name} - {item.language} (★{item.stars})")

        elif section_type == "custom":  # 自定义板块
            if content is None: continue
            lines.append(f"== {title} ==")
            lines.append(content.title)
            if content.date: lines.append(content.date)
            if content.description: lines.append(content.description)

        if lines:  # 如果有内容
            section_texts.append("\n".join(lines))  # 合并为板块文本

    return "\n\n".join(section_texts)  # 合并所有板块，用空行分隔
