"""工作任务相关的API类型定义模块。

本模块定义了工作任务系统的数据模型：
1. WorkSchema - 工作任务的完整数据结构
2. TaskIdResponse - 任务ID响应结构
"""  # 模块文档字符串

from datetime import datetime  # 导入日期时间类型

from pydantic import (  # 导入Pydantic组件
    BaseModel,
    ConfigDict,
    Field,
    alias_generators,
)


class WorkSchema(BaseModel):
    """工作任务的API数据模型。

    对应数据库中的 work 表，用于API请求和响应。
    """
    id: str = Field(default="", description="任务ID")
    task_type: str = Field(default="", description="任务类型标识（如parse、jd_score）")
    status: str = Field(default="", description="任务状态（如pending、running、success、error）")
    meta_info: dict | None = Field(default=None, description="任务元数据（如resume_id）")
    error_message: str | None = Field(default=None, description="错误信息（任务失败时）")
    created_at: datetime | None = Field(default=None, description="创建时间")
    updated_at: datetime | None = Field(default=None, description="更新时间")

    model_config = ConfigDict(
        from_attributes=True,  # 允许从ORM对象填充
        alias_generator=alias_generators.to_camel,  # 自动生成camelCase别名
        populate_by_name=True,  # 允许使用原始字段名或别名
    )


class TaskIdResponse(BaseModel):
    """任务ID响应模型。

    创建任务后返回给前端的响应，包含task_id供轮询状态。
    """
    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    task_id: str  # 任务ID（前端用它来轮询任务状态）
