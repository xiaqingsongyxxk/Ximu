"""Parser 解析领域。"""  # 模块文档字符串：说明本模块是解析领域

# TODO: 这个模块还未考虑如果用户上传的pdf是空的或者信息不够ai会乱填的情况, 需要优化  # 待办事项注释：指出当前实现的不足
from apps.parser.router import router  # 从router模块导入路由实例

__all__ = ["router"]  # 定义模块公开接口：只导出router
