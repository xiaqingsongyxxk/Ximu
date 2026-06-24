"""任务相关类型定义模块。

本模块定义了任务系统使用的枚举类型：
1. TaskType - 任务类型枚举
2. TaskStatus - 任务状态枚举
"""  # 模块文档字符串

from enum import StrEnum  # 导入字符串枚举基类


class TaskType(StrEnum):
    """任务类型枚举。

    定义系统中支持的所有任务类型。
    """
    PARSE = "parse"  # 解析任务（PDF简历解析）
    JD_GENERATE = "jd_generate"  # JD生成任务（根据JD创建子简历）
    JD_SCORE = "jd_score"  # JD评分任务（简历与JD匹配分析）


class TaskStatus(StrEnum):
    """任务状态枚举。

    定义任务生命周期中的所有可能状态。
    """
    PENDING = "pending"  # 待处理（任务已创建，等待执行）
    RUNNING = "running"  # 运行中（任务正在执行）
    SUCCESS = "success"  # 成功（任务执行完成）
    ERROR = "error"  # 错误（任务执行失败）
