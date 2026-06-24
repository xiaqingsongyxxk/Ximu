"""简历助手工具包的初始化模块。

本模块导出所有可用的工具类：
1. AddSectionTool - 添加新板块工具
2. SectionInfoTool - 查询板块信息工具
3. UpdateSectionTool - 更新板块内容工具
4. TranslateResumeTool - 翻译简历工具

这些工具供AI Agent调用，用于操作简历数据。
"""  # 模块文档字符串，说明这个文件是做什么的

# 从其他文件导入我们需要使用的工具类
# 这样做的目的是：当我们需要使用这些工具时，可以直接从这个包导入，而不需要知道它们具体在哪个文件中
from apps.resume_assistant.tools.add_section import (
    AddSectionTool,
)  # 导入添加板块工具，用于向简历添加新的板块
from apps.resume_assistant.tools.section_info import (
    SectionInfoTool,
)  # 导入查询板块信息工具，用于了解某个板块的结构和字段
from apps.resume_assistant.tools.translate_resume import (
    TranslateResumeTool,
)  # 导入翻译简历工具，用于将简历翻译成其他语言
from apps.resume_assistant.tools.update_section import (
    UpdateSectionTool,
)  # 导入更新板块工具，用于修改简历中某个板块的内容

# 定义这个包对外提供的所有工具类
# 这样做的目的是：当其他代码使用 "from apps.resume_assistant.tools import *" 时，只会导入这里列出的工具
__all__ = [
    "AddSectionTool",  # 添加板块工具，用于向简历添加新的板块
    "SectionInfoTool",  # 查询板块信息工具，用于了解某个板块的结构和字段
    "UpdateSectionTool",  # 更新板块工具，用于修改简历中某个板块的内容
    "TranslateResumeTool",  # 翻译简历工具，用于将简历翻译成其他语言
]
