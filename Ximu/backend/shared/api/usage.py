"""Token使用量快照模块。

本模块定义了UsageSnapshot类，用于记录LLM调用的token消耗：
1. input_tokens - 输入token数
2. output_tokens - 输出token数
3. total_tokens - 总token数（属性）
"""  # 模块文档字符串

from pydantic import BaseModel  # 导入Pydantic基类


class UsageSnapshot(BaseModel):
    """Token使用量快照。

    记录一次LLM调用消耗的token数量。
    """

    input_tokens: int = 0  # 输入token数
    output_tokens: int = 0  # 输出token数

    @property
    def total_tokens(self) -> int:
        """返回token总数。"""
        return self.input_tokens + self.output_tokens
