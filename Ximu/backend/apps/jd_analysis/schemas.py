"""职位描述分析的Pydantic数据模型定义模块。

本模块定义了JD分析相关的数据结构：
1. MatchRequest - 发起匹配评分的请求数据
2. SuggestionItem - 单条优化建议的数据结构
3. MatchResult - LLM返回的匹配分析结果

这些模型用于API请求验证和LLM输出解析。
"""  # 模块文档字符串

from typing import (
    Literal,
)  # 导入Literal类型，用于定义字面量类型（如只能是"openai"或"anthropic"）

from pydantic import Field  # 从Pydantic导入Field，用于定义字段属性

from shared.types.strict_model import (
    StrictBaseModel,
)  # 导入严格基础模型（禁止额外字段）


class MatchRequest(StrictBaseModel):  # 定义匹配请求数据模型
    """发起JD匹配评分的请求数据结构。

    当前端调用 POST /jd-analysis/match 时，
    请求体必须符合此格式。

    Attributes:
        resume_id: 要分析的简历ID。
        type: LLM供应商类型（openai或anthropic）。
        base_url: LLM API的地址。
        api_key: LLM API的密钥。
        model: 要使用的模型名称。
    """  # 文档字符串

    resume_id: str = Field(description="要分析的简历ID")  # 简历ID字段
    type: Literal["openai", "anthropic"] = Field(  # LLM供应商类型（只能是这两个值之一）
        description="LLM供应商类型（openai或anthropic）"
    )
    base_url: str = Field(
        description="LLM API的地址（如https://api.openai.com）"
    )  # API地址
    api_key: str = Field(description="LLM API的密钥")  # API密钥
    model: str = Field(description="要使用的模型名称（如gpt-4、claude-3）")  # 模型名称


class SuggestionItem(StrictBaseModel):  # 定义单条优化建议的数据模型
    """单条简历优化建议的数据结构。

    LLM会针对简历的特定板块提出优化建议，
    每条建议包含：哪个板块、当前内容、建议修改为什么。

    Attributes:
        section_id: 要优化的板块ID。
        current: 板块的当前内容。
        suggested: 建议修改为的内容。
    """  # 文档字符串

    section_id: str = Field(
        description="要优化的板块ID（对应ResumeSection的id字段）"
    )  # 板块ID
    current: str = Field(description="该板块的当前内容/文本")  # 当前内容
    suggested: str = Field(description="建议修改为的内容")  # 建议内容


class MatchResult(StrictBaseModel):  # 定义匹配结果数据模型
    """LLM返回的JD匹配分析结果数据结构。

    这是LLM分析简历与职位匹配度后返回的结构化数据。
    包含评分、关键词分析和优化建议。

    Attributes:
        summary: 分析摘要（AI生成的文字总结）。
        overall_score: 总体匹配评分（0-100分）。
        ats_score: ATS兼容性评分（0-100分）。
        keyword_matches: 简历中匹配JD要求的关键词列表。
        missing_keywords: JD要求但简历中缺失的关键词列表。
        suggestions: 针对各板块的优化建议列表。
    """  # 文档字符串

    summary: str = Field(  # 分析摘要
        description="AI生成的匹配度分析摘要（一段文字描述）"
    )
    overall_score: int = Field(  # 总体评分
        description="总体匹配评分（0-100分）",  # 字段描述
        ge=0,  # 最小值：0
        le=100,  # 最大值：100
    )
    ats_score: int = Field(  # ATS评分
        description="ATS（简历筛选系统）兼容性评分（0-100分）",
        ge=0,  # 最小值：0
        le=100,  # 最大值：100
    )
    keyword_matches: list[str] = Field(  # 匹配的关键词列表
        default_factory=list,  # 默认空列表
        description="简历中匹配JD要求的关键词列表",
    )
    missing_keywords: list[str] = Field(  # 缺失的关键词列表
        default_factory=list,  # 默认空列表
        description="JD要求但简历中缺失的关键词列表",
    )
    suggestions: list[SuggestionItem] = Field(  # 优化建议列表
        default_factory=list,  # 默认空列表
        description="针对各板块的优化建议列表",
    )
