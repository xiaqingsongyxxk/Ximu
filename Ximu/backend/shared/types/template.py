"""简历模板相关的API类型定义模块。

本模块定义了简历模板的数据模型：
1. TemplateSchema - 模板的API数据结构
"""  # 模块文档字符串

from datetime import datetime  # 导入日期时间类型

from pydantic import (  # 导入Pydantic组件
    BaseModel,
    ConfigDict,
    Field,
    alias_generators,
)


class TemplateSchema(BaseModel):
    """简历模板的API数据模型。

    对应数据库中的 template 表，用于API请求和响应。
    """
    id: str = Field(default="", description="模板ID（如classic、modern）")
    name: str = Field(default="", description="模板英文名称")
    display_name: str = Field(default="", description="模板中文显示名称")
    preview_image_url: str = Field(default="", description="模板预览图地址")
    is_active: bool | None = Field(default=False, description="是否启用")
    description: str = Field(default="", description="模板描述")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="修改时间")

    model_config = ConfigDict(
        from_attributes=True,  # 允许从ORM对象填充
        alias_generator=alias_generators.to_camel,  # 自动生成camelCase别名
        populate_by_name=True,  # 允许使用原始字段名或别名
    )
