"""简历板块工厂模块。

本模块提供通用的简历板块创建逻辑：
1. SectionConfig - 板块配置数据类
2. create_resume_sections - 批量创建板块的工厂函数

用于解析简历和创建子简历时，统一创建板块的逻辑。
"""  # 模块文档字符串

import json  # 导入JSON模块
from collections.abc import Callable  # 导入Callable类型
from dataclasses import dataclass  # 导入dataclass装饰器
from typing import Any  # 导入Any类型

from pydantic import BaseModel  # 导入Pydantic BaseModel
from sqlalchemy.ext.asyncio import AsyncSession  # 导入异步数据库会话

from shared.models import ResumeSection  # 导入板块ORM模型


@dataclass
class SectionConfig:
    """单个简历板块的配置。

    定义板块的类型、标题、内容提取函数和默认内容函数。
    """
    type: str  # 板块类型标识（如"personal_info"、"work_experience"）
    title: str  # 板块显示标题（如"个人信息"、"工作经历"）
    content_fn: Callable[[], dict]  # 内容提取函数：从解析结果提取内容
    default_fn: Callable[[], dict]  # 默认内容函数：当字段为空时使用
    field_name: str | None = None  # 可选的字段名覆盖（默认使用type作为字段名）


def create_resume_sections(
    db: AsyncSession,
    resume_id: str,
    result: BaseModel,
    section_configs: list[SectionConfig],
    field_name_fn: Callable[[str], str] | None = None,
    extra_sections_fn: Callable[[Any, str, int], list[ResumeSection]] | None = None,
) -> None:
    """批量创建简历的所有板块。

    按照配置列表的顺序创建板块，缺失的板块使用默认空内容填充。
    不自行commit/rollback，由调用方管理事务。

    Args:
        db: 数据库会话。
        resume_id: 简历ID。
        result: LLM解析结果（ParserResult或SubResumeResult）。
        section_configs: 板块配置列表。
        field_name_fn: 可选，将板块类型映射到result字段名的函数。
        extra_sections_fn: 可选，创建额外板块的函数（如custom）。
    """
    sections = []  # 板块列表
    sort_order = 0  # 排序序号

    for config in section_configs:  # 遍历每个板块配置
        section_type = config.type

        # 确定字段名
        if config.field_name is not None:
            field_name = config.field_name
        elif field_name_fn is not None:
            field_name = field_name_fn(section_type)
        else:
            field_name = section_type

        field_value = getattr(result, field_name, None)  # 从解析结果获取字段值

        # 根据字段值是否存在选择内容
        if field_value is not None:
            content = config.content_fn()  # 使用内容提取函数
        else:
            content = config.default_fn()  # 使用默认内容函数

        # 创建板块ORM对象
        sections.append(
            ResumeSection(
                resume_id=resume_id,
                type=section_type,
                title=config.title,
                sort_order=sort_order,
                visible=True,
                content=json.dumps(content, ensure_ascii=False),  # 序列化为JSON字符串
            )
        )
        sort_order += 1

    # 处理额外板块（如custom）
    if extra_sections_fn is not None:
        extra = extra_sections_fn(result, resume_id, sort_order)
        sections.extend(extra)

    db.add_all(sections)  # 批量添加所有板块到数据库会话
