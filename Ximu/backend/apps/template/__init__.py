"""Template 应用入口。"""

from apps.template.router import router  # 导入模板应用的路由实例

__all__ = ["router"]  # 导出路由实例供主应用使用
