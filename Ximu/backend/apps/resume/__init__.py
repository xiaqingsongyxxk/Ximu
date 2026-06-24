"""简历模块入口点。

本模块暴露简历功能的FastAPI路由，并在__all__中导出以便导入。
"""

from apps.resume.router import router  # 导入模块

__all__ = ["router"]  # 赋值语句
