"""求职信相关的Pydantic数据模型定义模块。

本模块定义了求职信生成的请求数据结构：
1. CoverLetterRequest - 求职信生成请求
"""  # 模块文档字符串，说明这个文件是做什么的

from typing import Literal  # 导入Literal类型，用于限制字段只能取特定的值

from pydantic import BaseModel, Field  # 导入Pydantic组件，用于定义数据模型和字段验证


class CoverLetterRequest(BaseModel):
    """求职信生成的请求数据结构。

    前端调用 POST /cover-letter 时传入。
    """

    resume_id: str = Field(
        description="简历ID"
    )  # 关联的简历ID，用于指定要基于哪份简历生成求职信
    jd_description: str = Field(
        description="目标岗位的职位描述"
    )  # JD原文，用于让AI了解目标岗位的要求
    type: Literal[
        "正式", "亲切", "自信"
    ]  # 求职信风格（三选一），用于指定求职信的语言风格
    language: Literal[
        "中文", "English"
    ]  # 输出语言（中文或英文），用于指定求职信的输出语言
