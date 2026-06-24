# 从router模块导入router对象
# 这个router对象包含了所有求职信相关的API路由
# 后续其他模块可以通过导入这个router来使用求职信功能
from apps.cover_letter.router import router

# 定义这个模块对外提供的接口
# 当其他代码使用 "from apps.cover_letter import *" 时，只会导入router
__all__ = ["router"]
