"""职位描述分析相关类型定义模块。

本模块定义了JD分析的数据模型：
1. SuggestionItem - 单条优化建议
2. JobDescriptionAnalysisSchema - 完整的分析结果
"""  # 模块文档字符串

from datetime import datetime  # 导入日期时间类型

from pydantic import Field  # 导入Pydantic字段定义

from shared.types.strict_model import StrictBaseModel  # 导入严格基础模型


class SuggestionItem(StrictBaseModel):
    """针对简历特定板块的优化建议。

    LLM会返回多条建议，每条针对一个板块。
    """
    section_id: str = Field(description="板块唯一标识符")  # 要优化的板块ID
    current: str = Field(description="当前内容")  # 板块的当前内容
    suggested: str = Field(description="建议修改")  # 建议修改为的内容


class JobDescriptionAnalysisSchema(StrictBaseModel):
    """职位描述分析结果的完整数据结构。

    包含评分、关键词匹配、优化建议等。
    """
    id: int = Field(description="分析记录唯一标识符")
    resume_id: str = Field(description="关联的简历ID")
    job_description: str = Field(description="职位描述原文")
    overall_score: int = Field(description="总体匹配评分（0-100分）")
    ats_score: int = Field(description="ATS兼容性评分（0-100分）")
    summary: str = Field(description="AI生成的分析摘要")
    keyword_matches: list[str] = Field(description="简历中匹配的关键词列表")
    missing_keywords: list[str] = Field(description="简历中缺失的关键词列表")
    suggestions: list[SuggestionItem] = Field(description="优化建议列表")
    created_at: datetime | None = Field(default=None, description="创建时间")
