"""求职信相关类型定义模块。

本模块定义了求职信的数据模型：
1. CoverLetterSchema - 求职信的API数据结构
"""  # 模块文档字符串

from datetime import datetime  # 导入日期时间类型

from pydantic import (  # 导入Pydantic组件
    BaseModel,
    ConfigDict,
    Field,
    alias_generators,
)


class CoverLetterSchema(BaseModel):
    """求职信的API数据模型。

    对应数据库中的求职信表，用于API请求和响应。
    """
    id: int = Field(description="求职信唯一ID")
    resume_id: str = Field(description="关联的简历ID")
    content: str = Field(description="求职信内容")
    create_at: datetime = Field(description="创建时间")
    update_at: datetime = Field(description="修改时间")

    model_config = ConfigDict(
        from_attributes=True,  # 允许从ORM对象填充
        alias_generator=alias_generators.to_camel,  # 自动生成camelCase别名
        populate_by_name=True,  # 允许使用原始字段名或别名
    )
