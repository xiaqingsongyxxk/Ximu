"""Config Pydantic 模型。"""  # 模块文档字符串：说明本模块用途

from typing import Literal  # 从typing导入Literal类型

from pydantic import (  # 导入pydantic相关组件
    BaseModel,
    ConfigDict,
    Field,
    alias_generators,
)

LLM_PROVIDERS = Literal["openai", "anthropic"]  # 定义LLM提供商类型字面量


class ProviderConfigItem(BaseModel):  # 定义提供商配置项类：继承BaseModel
    """Single provider configuration item."""  # 类文档字符串

    model_config = ConfigDict(  # 模型配置
        alias_generator=alias_generators.to_camel,  # 别名生成器：转为驼峰命名，自动处理蛇形和驼峰转换
        populate_by_name=True,  # 允许通过字段名或别名填充
    )

    base_url: str = Field(default="", description="API 地址")  # 字段：API地址
    api_key: str = Field(default="", description="API 密钥")  # 字段：API密钥
    model: str = Field(default="", description="模型名称")  # 字段：模型名称


class ProviderConfig(BaseModel):  # 定义提供商配置类：继承BaseModel
    """Provider configuration structure."""  # 类文档字符串

    model_config = ConfigDict(  # 模型配置
        alias_generator=alias_generators.to_camel,  # 别名生成器：转为驼峰命名
        populate_by_name=True,  # 允许通过字段名或别名填充
    )

    providers: dict[str, ProviderConfigItem] = Field(  # 字段：所有提供商配置
        default_factory=dict,  # 默认工厂：空字典
        description="所有 provider 配置,key 为 provider 类型",  # 字段描述
    )
    active: LLM_PROVIDERS = Field(  # 字段：当前激活的提供商
        default="openai",
        description="当前激活的 provider 类型",  # 默认值："openai"
    )


class ProviderConfigUpdate(BaseModel):  # 定义提供商配置更新类：继承BaseModel
    """Model for updating provider configuration requests."""  # 类文档字符串

    model_config = ConfigDict(  # 模型配置
        alias_generator=alias_generators.to_camel,  # 别名生成器：转为驼峰命名
        populate_by_name=True,  # 允许通过字段名或别名填充
    )

    type: LLM_PROVIDERS = Field(
        description="Provider 类型，openai 或 anthropic"
    )  # 字段：提供商类型
    base_url: str | None = Field(default=None, description="API 地址")  # 字段：API地址
    api_key: str | None = Field(default=None, description="API 密钥")  # 字段：API密钥
    model: str | None = Field(default=None, description="模型名称")  # 字段：模型名称


class ProviderSwitch(BaseModel):  # 定义提供商切换类：继承BaseModel
    """Model for switching the active provider."""  # 类文档字符串

    model_config = ConfigDict(  # 模型配置
        alias_generator=alias_generators.to_camel,  # 别名生成器：转为驼峰命名
        populate_by_name=True,  # 允许通过字段名或别名填充
    )

    active: LLM_PROVIDERS = Field(
        description="要激活的 provider 类型"
    )  # 字段：要激活的提供商类型
