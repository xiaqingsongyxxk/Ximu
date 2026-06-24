"""简历路由的请求体Schema定义模块。

本模块定义了简历API接口的请求数据结构（Pydantic模型）：
1. CreateWorkspaceRequest - 创建主简历的请求体
2. CreateSubResumeRequest - 创建子简历的请求体

这些模型用于FastAPI的请求体验证，确保前端传入的数据格式正确。
"""  # 模块文档字符串

from pydantic import (  # 从Pydantic导入数据验证相关的工具
    BaseModel,  # Pydantic基础模型类，所有数据模型都继承它
    ConfigDict,  # Pydantic配置类，用于设置模型行为（如别名生成、验证模式等）
    Field,  # 字段定义工具，用于设置默认值、描述、验证规则等
    alias_generators,  # 别名生成器，用于自动将Python的snake_case转为前端的camelCase
)


class CreateWorkspaceRequest(BaseModel):  # 定义创建主简历的请求数据模型
    """创建主简历（Workspace）的请求体数据结构。

    当前端调用 POST /resume/create 接口时，
    请求体必须符合此模型的格式。

    Attributes:
        title: 简历标题，默认为"未命名简历"。
        theme_config: 主题配置字典（如颜色、字体大小等），默认为空字典。
        template: 使用的模板名称（如"classic"、"modern"），默认为"classic"。
        language: 简历语言代码（"zh"=中文，"en"=英文），默认为"zh"。
    """  # 文档字符串

    model_config = ConfigDict(  # 配置Pydantic模型的行为
        alias_generator=alias_generators.to_camel,  # 自动生成camelCase别名（如theme_config → themeConfig）
        populate_by_name=True,  # 允许使用原始字段名或别名来填充数据（前端传themeConfig或theme_config都行）
    )

    title: str = Field(  # 定义简历标题字段
        default="未命名简历",  # 默认值：未命名简历
        description="简历标题",  # API文档中的描述
    )
    theme_config: dict = Field(  # 定义主题配置字段
        default_factory=dict,  # 默认值：空字典（每次调用都创建新字典，避免共享引用问题）
        description="主题配置（如颜色、字体等设置）",  # API文档描述
    )
    template: str = Field(  # 定义模板名称字段
        default="classic",  # 默认使用经典模板
        description="模板名称（如classic、modern、minimal等）",  # API文档描述
    )
    language: str = Field(  # 定义语言字段
        default="zh",  # 默认中文
        description="简历语言（zh=中文, en=英文）",  # API文档描述
    )


class CreateSubResumeRequest(BaseModel):  # 定义创建子简历的请求数据模型
    """在主简历（Workspace）下创建子简历的请求体数据结构。

    当前端调用 POST /resume/sub/create 接口时，
    请求体必须符合此模型的格式。
    子简历会继承主简历的板块结构，并关联目标职位信息。

    Attributes:
        workspace_id: 父主简历的ID（必填），子简历会关联到此主简历。
        job_description: 目标职位的描述文本（必填），用于AI简历优化。
        title: 子简历标题，默认为"未命名简历"。
        job_title: 目标职位名称（可选），如"前端工程师"。
        theme_config: 主题配置字典，默认为空字典。
        template: 模板名称，默认为"classic"。
        language: 语言代码，默认为"zh"。
    """  # 文档字符串

    model_config = ConfigDict(  # 配置Pydantic模型行为
        alias_generator=alias_generators.to_camel,  # 自动生成camelCase别名
        populate_by_name=True,  # 允许使用原始字段名或别名
    )

    workspace_id: str = Field(  # 定义所属主简历ID字段
        description="所属主简历（Workspace）的ID",  # API文档描述
    )
    job_description: str = Field(  # 定义职位描述字段
        description="目标职位的描述文本（JD原文）",  # API文档描述
    )
    title: str = Field(  # 定义子简历标题字段
        default="未命名简历",  # 默认值
        description="子简历标题",  # API文档描述
    )
    job_title: str | None = Field(  # 定义目标职位名称字段（可选）
        default=None,  # 默认为空（不传此字段时为None）
        description="目标职位名称（可选，如'前端工程师'）",  # API文档描述
    )
    theme_config: dict = Field(  # 定义主题配置字段
        default_factory=dict,  # 默认空字典
        description="主题配置",  # API文档描述
    )
    template: str = Field(  # 定义模板名称字段
        default="classic",  # 默认经典模板
        description="模板名称",  # API文档描述
    )
    language: str = Field(  # 定义语言字段
        default="zh",  # 默认中文
        description="简历语言（zh=中文, en=英文）",  # API文档描述
    )
