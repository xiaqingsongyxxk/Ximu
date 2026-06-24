"""Work application package. 工作应用包。

This module exposes the FastAPI router for work-related functionality 本模块暴露工作相关功能的FastAPI路由器
and defines the public surface of the package. 并定义包的公共接口。
"""

from apps.work.router import router  # 导入工作模块的路由器

__all__ = ["router"]  # 定义包的公共导出接口
