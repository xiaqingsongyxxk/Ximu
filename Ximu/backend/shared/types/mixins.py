"""Pydantic混入类模块。

本模块提供混入类，用于修改Pydantic模型的默认行为：
1. NoneToDefaultMixin - 将None值转换为字段默认值

这些混入类被多个模型继承，提供通用的验证逻辑。
"""  # 模块文档字符串

from pydantic import model_validator  # 导入模型验证器


class NoneToDefaultMixin:
    """None转默认值混入类。

    当模型字段接收到None时，自动替换为字段的默认值。
    用于LLM返回的数据中，某些字段可能是None，但我们需要默认值。
    """

    @model_validator(mode="before")  # 在验证前执行
    @classmethod
    def _none_to_default(cls, v):
        """将None值转换为字段默认值。"""
        if v is None:  # 如果整个输入是None
            v = {}  # 转为空字典
        if not isinstance(v, dict):  # 如果不是字典
            return v  # 直接返回
        result = {}  # 结果字典
        for key, value in v.items():  # 遍历输入字段
            if value is None:  # 如果值是None
                field = cls.model_fields.get(key)  # 获取字段定义
                if field is not None:  # 如果字段存在
                    default = field.default  # 获取默认值
                    result[key] = default() if callable(default) else default  # 使用默认值
#                     情况 2：default 是函数/类（可调用）
# class MyModel(BaseModel):
#     tags: list = Field(default_factory=list)
#     # 注意：有些 Pydantic 配置下 field.default 可能返回 list 函数本身
# default = field.default   # → <class 'list'> （list 这个类）
# callable(default)         # → True（类是 callable 的，调用 list() 返回 []）
# result[key] = default()   # → []    ← 调函数拿值
#                 else:  # 字段不存在
                    result[key] = None  # 保持None
            else:  # 值不是None
                result[key] = value  # 保持原值
        return result
