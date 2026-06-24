"""严格基础模型模块。

本模块定义了StrictBaseModel类：
- 禁止额外字段（extra="forbid"）
- 自动camelCase别名（alias_generator=to_camel）
- 允许通过字段名或别名填充（populate_by_name=True）

所有需要严格验证的Pydantic模型都应继承此类。
"""  # 模块文档字符串

from pydantic import (  # 导入Pydantic组件
    BaseModel,
    ConfigDict,
    alias_generators,
)


class StrictBaseModel(BaseModel):
    """严格基础模型。

    禁止额外字段，自动处理camelCase别名。
    用于LLM返回的数据验证，确保数据格式严格正确。
    """
    model_config = ConfigDict(
        extra="forbid",  # 禁止额外字段（LLM返回多余字段时报错）
        alias_generator=alias_generators.to_camel,  # 自动生成camelCase别名
        populate_by_name=True,  # 允许使用原始字段名或别名
    )
