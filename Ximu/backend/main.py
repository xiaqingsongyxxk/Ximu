"""FastAPI 应用入口。"""  # 模块级文档字符串，说明这是FastAPI应用的主入口文件

import asyncio  # 导入异步IO库，用于执行异步任务（如后台启动浏览器）
import logging  # 导入日志库，用于在控制台输出运行信息
from contextlib import (
    asynccontextmanager,
)  # 导入异步上下文管理器，用于定义应用启动和关闭时执行的逻辑

from fastapi import FastAPI  # 从fastapi框架导入FastAPI类，这是创建Web应用的核心类
from fastapi.middleware.cors import (
    CORSMiddleware,
)  # 导入CORS中间件，用于处理跨域请求（前端在不同端口/域名访问后端时需要）
from fastapi.routing import APIRoute  # 导入APIRoute类，用于遍历和配置路由

from apps.config import (
    router as config_router,
)  # 导入配置模块的路由，定义在 apps/config/router.py 中
from apps.conversation_message import (
    router as conversation_message_router,
)  # 导入对话消息模块的路由，定义在 apps/conversation_message/router.py 中
from apps.cover_letter import (
    router as cover_letter_router,
)  # 导入求职信模块的路由，定义在 apps/cover_letter/router.py 中
from apps.export import (
    router as export_router,
)  # 导入导出模块的路由，定义在 apps/export/router.py 中
from apps.export.browser_manager import (
    ensure_browser,
)  # 导入浏览器管理函数，用于启动时自动安装和启动Playwright浏览器（PDF生成需要）
from apps.jd_analysis import (
    router as jd_analysis_router,
)  # 导入职位分析模块的路由，定义在 apps/jd_analysis/router.py 中
from apps.parser import (
    router as parser_router,
)  # 导入简历解析模块的路由，定义在 apps/parser/router.py 中
from apps.resume import (
    router as resume_router,
)  # 导入简历模块的路由，定义在 apps/resume/router.py 中
from apps.resume_assistant import (
    router as resume_assistant_router,
)  # 导入简历助手模块的路由（AI对话优化简历），定义在 apps/resume_assistant/router.py 中
from apps.resume_section import (
    router as resume_section_router,
)  # 导入简历板块模块的路由，定义在 apps/resume_section/router.py 中
from apps.template import (
    router as template_router,
)  # 导入模板模块的路由，定义在 apps/template/router.py 中
from apps.work import (
    router as work_router,
)  # 导入工作任务模块的路由（任务状态管理），定义在 apps/work/router.py 中
from shared.database import (
    init_db,
)  # 导入数据库初始化函数，定义在 shared/database.py 中，用于创建所有数据库表


@asynccontextmanager  # 这是一个装饰器，将函数变成异步上下文管理器
async def lifespan(app: FastAPI):  # 定义应用生命周期函数，在应用启动和关闭时执行
    """应用启动时执行初始化，关闭时执行清理。"""  # 函数文档字符串
    await (
        init_db()
    )  # 调用数据库初始化函数，创建所有表（如果不存在），定义在 shared/database.py 中
    asyncio.create_task(
        ensure_browser()
    )  # 在后台异步启动浏览器（Playwright Chromium），用于PDF生成，定义在 apps/export/browser_manager.py 中
    yield  # yield 之前是启动时执行的代码，yield 之后是关闭时执行的代码（这里关闭时没有需要清理的）


app = FastAPI(
    lifespan=lifespan
)  # 创建FastAPI应用实例，并将生命周期函数传入，这样启动时会自动调用 lifespan 函数

logging.basicConfig(
    level=logging.INFO
)  # 配置日志系统，设置日志级别为INFO，这样INFO、WARNING、ERROR级别的日志都会显示

# CORS 中间件配置（跨域资源共享）
app.add_middleware(  # 向应用添加中间件
    CORSMiddleware,  # 使用CORS中间件，处理前端跨域请求
    allow_origins=["*"],  # 允许所有来源的请求（开发模式，生产环境应该限制为具体域名）
    allow_credentials=True,  # 允许携带凭证（如Cookie、Authorization头）
    allow_methods=["*"],  # 允许所有HTTP方法（GET、POST、PUT、DELETE等）
    allow_headers=["*"],  # 允许所有请求头
)

# 注册路由：将各个模块的路由注册到主应用中
app.include_router(config_router)  # 注册配置模块路由，提供系统配置相关的API接口
app.include_router(parser_router)  # 注册简历解析模块路由，提供PDF简历解析相关的API接口
app.include_router(
    work_router
)  # 注册工作任务模块路由，提供任务状态查询和SSE推送相关的API接口
app.include_router(
    resume_router
)  # 注册简历模块路由，提供简历CRUD（增删改查）相关的API接口
app.include_router(
    resume_section_router
)  # 注册简历板块模块路由，提供简历板块（个人信息、工作经历等）的CRUD接口
app.include_router(template_router)  # 注册模板模块路由，提供简历模板的CRUD接口
app.include_router(
    jd_analysis_router
)  # 注册职位分析模块路由，提供简历与职位匹配分析的API接口
app.include_router(cover_letter_router)  # 注册求职信模块路由，提供AI生成求职信的API接口
app.include_router(
    resume_assistant_router
)  # 注册简历助手模块路由，提供AI对话优化简历的API接口
app.include_router(
    conversation_message_router
)  # 注册对话消息模块路由，提供对话历史记录的API接口
app.include_router(export_router)  # 注册导出模块路由，提供简历导出为PDF的API接口

# 遍历所有注册的路由，设置响应模型使用别名（camelCase）
for route in app.routes:  # 遍历应用中所有已注册的路由
    if isinstance(route, APIRoute):  # 检查是否是APIRoute类型（排除静态文件等其他路由）
        route.response_model_by_alias = True  # 启用别名模式，使响应JSON使用camelCase字段名（如 resumeId 而不是 resume_id），与前端JavaScript命名风格一致
# backend/
# ├── pyproject.toml                    # Python 项目配置文件，定义依赖、版本、工具配置
# ├── .python-version                    # Python 版本声明文件，指定项目使用 Python 3.13
# ├── main.py                           # FastAPI 应用入口，注册所有路由、中间件、生命周期
# ├── shared/                           # 共享模块，供其他模块复用
# │   ├── __init__.py                   # 包初始化文件
# │   ├── database.py                   # 数据库连接、引擎、会话工厂、get_session 依赖注入函数
# │   ├── models.py                     # SQLAlchemy ORM 模型定义（Resume、ResumeSection 等）
# │   └── types/                        # Pydantic 类型定义（API 数据结构）
# │       ├── __init__.py               # 类型模块导出入口
# │       ├── jd_analysis.py            # JD 分析相关类型（SuggestionItem、JobDescriptionAnalysisSchema）
# │       ├── messages.py               # LLM 对话消息类型（TextBlock、ToolUseBlock、ConversationMessage）
# │       ├── resume.py                  # 简历类型定义（ResumeSchema、各板块 Section 类型）
# │       └── strict_model.py           # 严格基础模型（禁止额外字段、自动 camelCase）
# └── apps/                             # 功能模块，每个子目录是一个独立功能
#     ├── __init__.py                   # 包初始化文件
#     ├── config/                       # AI 提供商配置管理模块
#     │   ├── __init__.py               # 导出 router
#     │   ├── router.py                 # 配置 API 路由（获取/更新/切换 Provider）
#     │   └── schemas.py                # 配置 Pydantic 模型（ProviderConfig、ProviderConfigUpdate）
#     ├── conversation_message/         # 对话消息管理模块
#     │   ├── __init__.py               # 导出 router
#     │   └── router.py                 # 消息 API 路由（查询历史消息）
#     ├── cover_letter/                 # 求职信生成模块
#     │   ├── __init__.py               # 导出 router
#     │   ├── router.py                 # 求职信 API 路由
#     │   ├── schemas.py                # 求职信数据模型
#     │   ├── service.py                # 求职信业务逻辑
#     │   └── prompt.py                 # LLM prompt 模板
#     ├── export/                       # PDF 导出模块
#     │   ├── __init__.py               # 导出 router
#     │   ├── router.py                 # 导出 API 路由（生成 PDF）
#     │   ├── service.py                # 导出业务逻辑
#     │   ├── pdf_generator.py         # PDF 生成器（Playwright 渲染 HTML）
#     │   └── browser_manager.py        # Playwright 浏览器管理（启动、关闭）
#     ├── jd_analysis/                  # JD 匹配分析模块
#     │   ├── __init__.py               # 导出 router
#     │   ├── router.py                 # 分析 API 路由（分析简历与 JD 匹配度）
#     │   ├── schemas.py                # 分析结果数据模型
#     │   ├── service.py                # 分析业务逻辑
#     │   ├── prompt.py                 # LLM prompt 模板
#     │   └── call_llm.py               # LLM 调用封装
#     ├── parser/                       # 简历解析模块（PDF 解析为结构化数据）
#     │   ├── __init__.py               # 导出 router
#     │   ├── router.py                 # 解析 API 路由（上传 PDF 解析）
#     │   ├── schemas.py                # 解析请求/响应模型
#     │   ├── service.py                # 解析业务逻辑
#     │   ├── pdf_parser.py             # PDF 文本提取（pymupdf）
#     │   ├── prompt.py                 # LLM prompt 模板
#     │   ├── storage.py                # 解析结果存储
#     │   └── call_llm.py               # LLM 调用封装
#     ├── resume/                       # 简历管理模块（主简历/子简历 CRUD）
#     │   ├── __init__.py               # 导出 router
#     │   ├── router.py                 # 简历 API 路由（创建/查询/更新/删除）
#     │   ├── schemas.py                # 创建简历请求模型
#     │   └── service.py                # 简历业务逻辑（创建默认板块、复制板块）
#     ├── resume_assistant/             # AI 简历助手模块（对话优化简历）
#     │   ├── __init__.py               # 导出 router
#     │   ├── router.py                 # 助手 API 路由（SSE 流式对话）
#     │   ├── schemas.py                # 助手数据模型
#     │   ├── agent_service.py          # Agent 服务（AI 对话核心）
#     │   ├── task_service.py           # 任务服务（后台任务管理）
#     │   ├── conversation_store.py     # 对话状态存储（内存）
#     │   ├── prompt.py                 # LLM prompt 模板
#     │   ├── agent/                    # Agent 核心组件
#     │   │   ├── __init__.py           # 导出
#     │   │   ├── core.py               # Agent 核心逻辑
#     │   │   ├── runtime.py            # 运行时管理
#     │   │   ├── events.py             # 事件定义
#     │   │   ├── state.py              # Agent 状态管理
#     │   │   ├── context.py            # 上下文管理
#     │   │   ├── formatters.py         # 输出格式化
#     │   │   └── compact.py            # 上下文压缩
#     │   └── tools/                    # Agent 可用工具
#     │       ├── __init__.py           # 导出
#     │       ├── update_section.py     # 更新简历板块工具
#     │       ├── add_section.py        # 添加板块工具
#     │       ├── section_info.py       # 获取板块信息工具
#     │       └── translate_resume.py   # 简历翻译工具
#     ├── resume_section/               # 简历板块管理模块
#     │   ├── __init__.py               # 导出 router
#     │   └── router.py                 # 板块 API 路由（CRUD）
#     ├── template/                     # 模板管理模块
#     │   └── __init__.py               # 导出 router
#     └── work/                         # 任务管理模块（异步任务状态跟踪）
#         ├── __init__.py               # 导出 router
#         ├── router.py                 # 任务 API 路由
#         └── sse.py                    # SSE 流式任务状态













# backend/
# ├── pyproject.toml                    # Python 项目配置文件，定义依赖、版本、工具配置
# ├── .python-version                    # Python 版本声明文件，指定项目使用 Python 3.13
# ├── main.py                           # FastAPI 应用入口，注册所有路由、中间件、生命周期
# │
# ├── shared/                           # 共享模块，供其他模块复用（基础设施层）
# │   ├── __init__.py                   # 包初始化文件
# │   │
# │   ├── database.py                   # 数据库连接、引擎、会话工厂、get_session 依赖注入函数
# │   │
# │   ├── models.py                     # SQLAlchemy ORM 模型定义（Resume、ResumeSection、UserConfig 等）
# │   │
# │   ├── task_state.py                 # 任务状态管理（内存存储，追踪异步任务进度）
# │   │
# │   ├── resume_prompt.py               # 简历相关的 LLM prompt 模板（解析、生成）
# │   │
# │   ├── resume_section_factory.py      # 简历板块工厂（创建默认板块结构）
# │   │
# │   ├── exceptions/                   # 异常定义
# │   │   ├── __init__.py               # 导出
# │   │   └── base.py                    # 基础异常类（APIException）
# │   │
# │   ├── api/                          # LLM API 客户端封装
# │   │   ├── __init__.py               # 导出 get_client 函数
# │   │   ├── client.py                 # API 客户端基类、事件类型定义
# │   │   ├── openai_client.py          # OpenAI 兼容 API 客户端实现
# │   │   ├── errors.py                 # API 错误定义
# │   │   └── usage.py                  # Token 用量追踪
# │   │
# │   └── types/                        # Pydantic 类型定义（API 数据结构）
# │       ├── __init__.py               # 类型模块导出入口
# │       │
# │       ├── strict_model.py           # 严格基础模型（禁止额外字段、自动 camelCase）
# │       │
# │       ├── base_tool.py              # Agent 工具基础类型定义
# │       │
# │       ├── mixins.py                 # 混入类（API Response Mixin）
# │       │
# │       ├── messages.py               # LLM 对话消息类型（TextBlock、ToolUseBlock、ConversationMessage）
# │       │
# │       ├── resume.py                  # 简历类型定义（ResumeSchema、各板块 Section 类型）
# │       │
# │       ├── jd_analysis.py            # JD 分析相关类型（SuggestionItem、JobDescriptionAnalysisSchema）
# │       │
# │       ├── cover_letter.py           # 求职信类型定义（CoverLetterRequest）
# │       │
# │       ├── work.py                   # 工作任务类型定义（WorkTaskSchema）
# │       │
# │       ├── task.py                   # 任务相关类型定义（TaskStatus）
# │       │
# │       └── template.py               # 模板类型定义（TemplateSchema）
# │
# └── apps/                             # 功能模块，每个子目录是一个独立功能（API 层）
#     ├── __init__.py                   # 包初始化文件
#     │
#     ├── config/                       # AI 提供商配置管理模块（最基础的配置）
#     │   ├── __init__.py               # 导出 router
#     │   ├── schemas.py                # 配置 Pydantic 模型（ProviderConfig、ProviderConfigUpdate）
#     │   └── router.py                 # 配置 API 路由（获取/更新/切换 Provider）
#     │
#     ├── resume/                       # 简历管理模块（主简历/子简历 CRUD）
#     │   ├── __init__.py               # 导出 router
#     │   ├── schemas.py                # 创建简历请求模型（CreateWorkspaceRequest、CreateSubResumeRequest）
#     │   ├── service.py                # 简历业务逻辑（创建默认板块、复制板块）
#     │   └── router.py                 # 简历 API 路由（创建/查询/更新/删除）
#     │
#     ├── resume_section/               # 简历板块管理模块（单板块 CRUD）
#     │   ├── __init__.py               # 导出 router
#     │   └── router.py                 # 板块 API 路由（查询/创建/更新/删除/排序）
#     │
#     ├── conversation_message/         # 对话消息管理模块
#     │   ├── __init__.py               # 导出 router
#     │   └── router.py                 # 消息 API 路由（查询历史消息、导出 Markdown）
#     │
#     ├── parser/                       # 简历解析模块（PDF 解析为结构化数据）
#     │   ├── __init__.py               # 导出 router
#     │   ├── schemas.py                # 解析请求/响应模型（ParseResumeRequest）
#     │   ├── prompt.py                 # LLM prompt 模板（PDF 解析提示词）
#     │   ├── pdf_parser.py             # PDF 文本提取（pymupdf）
#     │   ├── storage.py                # 解析结果存储
#     │   ├── call_llm.py               # LLM 调用封装
#     │   ├── service.py                # 解析业务逻辑
#     │   └── router.py                 # 解析 API 路由（上传 PDF 解析）
#     │
#     ├── jd_analysis/                  # JD 匹配分析模块
#     │   ├── __init__.py               # 导出 router
#     │   ├── schemas.py                # 分析请求/响应模型（AnalyzeJDRequest）
#     │   ├── prompt.py                 # LLM prompt 模板（JD 分析提示词）
#     │   ├── call_llm.py               # LLM 调用封装
#     │   ├── service.py                # 分析业务逻辑
#     │   └── router.py                 # 分析 API 路由（分析简历与 JD 匹配度）
#     │
#     ├── cover_letter/                 # 求职信生成模块
#     │   ├── __init__.py               # 导出 router
#     │   ├── schemas.py                # 求职信请求模型（CoverLetterRequest）
#     │   ├── prompt.py                 # LLM prompt 模板（求职信生成提示词）
#     │   ├── service.py                # 求职信业务逻辑（SSE 流式生成）
#     │   └── router.py                 # 求职信 API 路由（SSE 流式响应）
#     │
#     ├── export/                       # PDF 导出模块
#     │   ├── __init__.py               # 导出 router
#     │   ├── browser_manager.py        # Playwright 浏览器管理（启动、关闭、复用）
#     │   ├── pdf_generator.py           # PDF 生成器（Playwright 渲染 HTML 为 PDF）
#     │   ├── service.py                # 导出业务逻辑
#     │   └── router.py                 # 导出 API 路由（生成 PDF）
#     │
#     ├── resume_assistant/             # AI 简历助手模块（对话优化简历，核心复杂模块）
#     │   ├── __init__.py               # 导出 router
#     │   ├── schemas.py                # 助手数据模型（ChatRequest、ChatResponse）
#     │   ├── prompt.py                 # LLM prompt 模板（助手系统提示词）
#     │   ├── conversation_store.py     # 对话状态存储（内存，保存对话历史）
#     │   ├── agent_service.py          # Agent 服务（AI 对话核心，工具调用）
#     │   ├── task_service.py           # 任务服务（后台任务管理、SSE 流式）
#     │   ├── router.py                 # 助手 API 路由（SSE 流式对话）
#     │   │
#     │   ├── agent/                    # Agent 核心组件
#     │   │   ├── __init__.py           # 导出
#     │   │   ├── events.py             # 事件定义（SSE 事件类型）
#     │   │   ├── state.py              # Agent 状态管理（RunningState）
#     │   │   ├── context.py            # 上下文管理（构建、压缩）
#     │   │   ├── core.py               # Agent 核心逻辑（工具调用循环）
#     │   │   ├── runtime.py            # 运行时管理（消息处理、工具执行）
#     │   │   ├── formatters.py         # 输出格式化（工具结果格式化）
#     │   │   └── compact.py            # 上下文压缩（对话历史压缩策略）
#     │   │
#     │   └── tools/                    # Agent 可用工具
#     │       ├── __init__.py           # 导出
#     │       ├── section_info.py       # 获取板块信息工具（get_section_info）
#     │       ├── update_section.py     # 更新简历板块工具（update_section）
#     │       ├── add_section.py        # 添加简历板块工具（add_section）
#     │       └── translate_resume.py   # 简历翻译工具（translate_resume）
#     │
#     ├── template/                     # 模板管理模块
#     │   ├── __init__.py               # 导出 router
#     │   └── router.py                 # 模板 API 路由（查询/创建/更新模板）
#     │
#     └── work/                         # 任务管理模块（异步任务状态跟踪）
#         ├── __init__.py               # 导出 router
#         ├── sse.py                    # SSE 流式任务状态（任务进度推送）
#         └── router.py                 # 任务 API 路由（创建/查询任务状态）
# ---
# 文件数量统计
# 模块
# shared/ 基础设施层
# apps/config/
# apps/resume/
# apps/resume_section/
# apps/conversation_message/
# apps/parser/
# apps/jd_analysis/
# apps/cover_letter/
# apps/export/
# apps/resume_assistant/
# apps/template/
# apps/work/
# 总计
# ---
# 创建顺序（依赖关系）
# 第一层：类型定义（types/）
#          ↓
# 第二层：数据库层（database.py, models.py）
#          ↓
# 第三层：共享工具（api/, exceptions/, task_state.py, resume_prompt.py, resume_section_factory.py）
#          ↓
# 第四层：基础功能模块（config/, resume/）
#          ↓
# 第五层：业务功能模块（parser/, jd_analysis/, cover_letter/, export/, resume_section/, work/）
#          ↓
# 第六层：复杂功能模块（resume_assistant/, template/, conversation_message/）
#          ↓
# 入口：main.py












# backend/
# │
# ├── 2026-04-02  初始化项目结构
# │
# ├── 2026-04-03  parser/ 简历 PDF 解析模块
# │   │
# │   ├── pyproject.toml                   # 项目依赖配置
# │   │
# │   ├── shared/
# │   │   ├── __init__.py                  # shared 包初始化
# │   │   └── types/
# │   │       ├── __init__.py              # types 包初始化
# │   │       ├── strict_model.py          # 严格基础模型（禁止额外字段、自动 camelCase）
# │   │       └── resume.py                # 简历类型定义（ResumeSchema、各板块 Section 类型）
# │   │
# │   └── apps/
# │       ├── __init__.py                  # apps 包初始化
# │       └── parser/
# │           ├── __init__.py              # parser 包初始化
# │           ├── router.py                # 解析 API 路由（上传 PDF 解析）
# │           ├── schemas.py               # 解析请求/响应模型（ParseResumeRequest）
# │           ├── pdf_parser.py            # PDF 文本提取（pymupdf）
# │           ├── prompt.py                # LLM prompt 模板（PDF 解析提示词）
# │           ├── call_llm.py              # LLM 调用封装
# │           ├── storage.py               # 解析结果存储
# │           └── service.py               # 解析业务逻辑
# │
# ├── 2026-04-05  resume_assistant/ AI 对话优化简历模块（初版）
# │   │
# │   └── apps/
# │       └── resume_assistant/
# │           ├── __init__.py              # resume_assistant 包初始化
# │           ├── router.py                # 助手 API 路由（SSE 流式对话）
# │           ├── schemas.py               # 助手数据模型（ChatRequest、ChatResponse）
# │           ├── conversation_store.py    # 对话状态存储（内存，保存对话历史）
# │           ├── agent_service.py         # Agent 服务（AI 对话核心，工具调用）
# │           ├── task_service.py          # 任务服务（后台任务管理、SSE 流式）
# │           ├── prompt.py                # LLM prompt 模板（助手系统提示词）
# │           │
# │           ├── agent/                    # Agent 核心组件
# │           │   ├── __init__.py          # 导出
# │           │   ├── core.py              # Agent 核心逻辑（工具调用循环）
# │           │   ├── runtime.py           # 运行时管理（消息处理、工具执行）
# │           │   ├── events.py            # 事件定义（SSE 事件类型）
# │           │   ├── state.py             # Agent 状态管理（RunningState）
# │           │   ├── context.py           # 上下文管理（构建、压缩）
# │           │   ├── formatters.py        # 输出格式化（工具结果格式化）
# │           │   └── compact.py           # 上下文压缩（对话历史压缩策略）
# │           │
# │           └── tools/                   # Agent 可用工具
# │               ├── __init__.py          # 导出
# │               ├── section_info.py       # 获取板块信息工具（get_section_info）
# │               ├── update_section.py    # 更新简历板块工具（update_section）
# │               ├── add_section.py       # 添加简历板块工具（add_section）
# │               └── translate_resume.py  # 简历翻译工具（translate_resume）
# │
# ├── 2026-04-07  shared/ 共享模块提取重构
# │   │
# │   └── shared/
# │       ├── database.py                  # 数据库连接、引擎、会话工厂、get_session 依赖注入函数
# │       │
# │       ├── models.py                    # SQLAlchemy ORM 模型定义（Resume、ResumeSection、UserConfig 等）
# │       │
# │       ├── api/                         # LLM API 客户端封装
# │       │   ├── __init__.py              # 导出 get_client 函数
# │       │   ├── client.py                # API 客户端基类、事件类型定义
# │       │   ├── openai_client.py         # OpenAI 兼容 API 客户端实现
# │       │   ├── errors.py                # API 错误定义
# │       │   └── usage.py                 # Token 用量追踪
# │       │
# │       ├── exceptions/                  # 异常定义
# │       │   ├── __init__.py              # 导出
# │       │   └── base.py                  # 基础异常类（APIException）
# │       │
# │       └── types/
# │           ├── messages.py              # LLM 对话消息类型（TextBlock、ToolUseBlock、ConversationMessage）
# │           ├── jd_analysis.py           # JD 分析相关类型（SuggestionItem、JobDescriptionAnalysisSchema）
# │           ├── base_tool.py             # Agent 工具基础类型定义
# │           └── mixins.py                # 混入类（API Response Mixin）
# │
# ├── 2026-04-09  config/ AI 提供商配置管理模块
# │   │
# │   └── apps/
# │       └── config/
# │           ├── __init__.py              # config 包初始化
# │           ├── schemas.py               # 配置 Pydantic 模型（ProviderConfig、ProviderConfigUpdate）
# │           └── router.py                # 配置 API 路由（获取/更新/切换 Provider）
# │
# ├── 2026-04-11  resume/ 和 resume_section/ 简历管理模块
# │   │
# │   ├── shared/
# │   │   ├── resume_prompt.py             # 简历相关的 LLM prompt 模板（解析、生成）
# │   │   │
# │   │   ├── resume_section_factory.py    # 简历板块工厂（创建默认板块结构）
# │   │   │
# │   │   └── task_state.py                # 任务状态管理（内存存储，追踪异步任务进度）
# │   │
# │   └── apps/
# │       ├── resume/
# │       │   ├── __init__.py             # resume 包初始化
# │       │   ├── router.py               # 简历 API 路由（创建/查询/更新/删除）
# │       │   ├── schemas.py              # 创建简历请求模型（CreateWorkspaceRequest、CreateSubResumeRequest）
# │       │   └── service.py              # 简历业务逻辑（创建默认板块、复制板块）
# │       │
# │       └── resume_section/
# │           ├── __init__.py             # resume_section 包初始化
# │           └── router.py               # 板块 API 路由（查询/创建/更新/删除/排序）
# │
# ├── 2026-04-11  jd_analysis/ JD 匹配分析模块
# │   │
# │   └── apps/
# │       └── jd_analysis/
# │           ├── __init__.py             # jd_analysis 包初始化
# │           ├── router.py               # 分析 API 路由（分析简历与 JD 匹配度）
# │           ├── schemas.py              # 分析请求/响应模型（AnalyzeJDRequest）
# │           ├── prompt.py               # LLM prompt 模板（JD 分析提示词）
# │           ├── call_llm.py             # LLM 调用封装
# │           └── service.py              # 分析业务逻辑
# │
# ├── 2026-04-15  cover_letter/ 求职信生成模块
# │   │
# │   ├── shared/
# │   │   └── types/
# │   │       └── cover_letter.py         # 求职信类型定义（CoverLetterRequest）
# │   │
# │   └── apps/
# │       └── cover_letter/
# │           ├── __init__.py            # cover_letter 包初始化
# │           ├── router.py              # 求职信 API 路由（SSE 流式响应）
# │           ├── schemas.py             # 求职信请求模型（CoverLetterRequest）
# │           ├── prompt.py              # LLM prompt 模板（求职信生成提示词）
# │           └── service.py             # 求职信业务逻辑（SSE 流式生成）
# │
# ├── 2026-04-15  conversation_message/ 对话消息管理
# │   │
# │   └── apps/
# │       └── conversation_message/
# │           ├── __init__.py            # conversation_message 包初始化
# │           └── router.py              # 消息 API 路由（查询历史消息、导出 Markdown）
# │
# ├── 2026-04-16  work/ 任务系统重构
# │   │
# │   ├── shared/
# │   │   └── types/
# │   │       ├── work.py                # 工作任务类型定义（WorkTaskSchema）
# │   │       └── task.py                # 任务相关类型定义（TaskStatus）
# │   │
# │   └── apps/
# │       └── work/
# │           ├── __init__.py           # work 包初始化
# │           ├── router.py             # 任务 API 路由（创建/查询任务状态）
# │           └── sse.py                # SSE 流式任务状态（任务进度推送）
# │
# ├── 2026-04-22  resume_assistant/agent/ Agent 核心模块完善
# │   │
# │   └── apps/
# │       └── resume_assistant/
# │           └── agent/
# │               └── (已在上方列出)
# │
# ├── 2026-04-23  export/ PDF 导出模块
# │   │
# │   └── apps/
# │       └── export/
# │           ├── __init__.py           # export 包初始化
# │           ├── router.py             # 导出 API 路由（生成 PDF）
# │           ├── browser_manager.py    # Playwright 浏览器管理（启动、关闭、复用）
# │           ├── pdf_generator.py      # PDF 生成器（Playwright 渲染 HTML 为 PDF）
# │           └── service.py           # 导出业务逻辑
# │
# ├── 2026-04-25  收尾
# │   │
# │   ├── shared/
# │   │   └── types/
# │   │       └── template.py           # 模板类型定义（TemplateSchema）
# │   │
# │   └── apps/
# │       └── template/
# │           ├── __init__.py          # template 包初始化
# │           └── router.py            # 模板 API 路由（查询/创建/更新模板）
# │
# └── main.py  应用入口（最后组装）
#     │
#     └── main.py                      # FastAPI 应用入口，注册所有路由、中间件、生命周期













# 阶段 1：初始化项目结构 (2026-04-02)
# backend/
# ├── pyproject.toml      # 定义项目依赖
# ├── .python-version     # 指定 Python 3.13
# ├── shared/__init__.py  # 包初始化
# └── shared/types/
#     ├── __init__.py
#     ├── strict_model.py # 最基础的类型定义
#     └── resume.py      # 简历类型
# 为什么先创建这些？
# 文件	原因
# pyproject.toml	所有 Python 项目的起点，没有依赖就无法运行代码
# .python-version	锁定 Python 版本，避免兼容性问题
# strict_model.py	最基础的类型定义，其他所有类型都可能继承它
# resume.py	业务核心类型，简历系统的所有数据结构都从这里开始
# 技术原因
# strict_model.py 继承链：
#     BaseModel → StrictBaseModel → 所有业务类型
    
# resume.py 继承链：
#     StrictBaseModel → ResumeSchema → 所有板块类型
    
# → 这两个文件是整个类型系统的"根"
# ---
# 阶段 2：parser 模块 (2026-04-03)
# apps/parser/
# ├── router.py      # API 路由
# ├── schemas.py     # 请求模型
# ├── pdf_parser.py  # PDF 提取
# ├── prompt.py      # LLM 提示词
# ├── call_llm.py    # LLM 调用
# ├── storage.py     # 结果存储
# └── service.py     # 业务逻辑
# 为什么最先实现 parser？
# 原因	解释
# 核心功能	用户的第一个需求："上传简历 PDF，提取内容"
# 独立性最强	不依赖其他模块，只需数据库保存结果
# MVP 思维	先做最小可用产品，验证核心价值
# 降低风险	如果 PDF 解析做不了，整个项目无法继续
# 技术决策
# 用户上传 PDF
#     ↓
# pymupdf 提取文本（pdf_parser.py）
#     ↓
# LLM 解析为结构化数据（call_llm.py + prompt.py）
#     ↓
# 保存到数据库（storage.py + service.py）
#     ↓
# 返回给前端（router.py）
# ---
# 阶段 3：resume_assistant 模块 (2026-04-05)
# apps/resume_assistant/
# ├── router.py              # SSE 流式对话
# ├── schemas.py             # 对话请求/响应
# ├── conversation_store.py  # 对话历史存储
# ├── agent_service.py       # Agent 核心服务
# ├── task_service.py       # 任务管理
# ├── prompt.py            # 系统提示词
# ├── agent/               # Agent 核心
# │   ├── core.py          # 工具调用循环
# │   ├── runtime.py       # 运行时管理
# │   ├── events.py        # SSE 事件定义
# │   ├── state.py         # 状态机
# │   ├── context.py       # 上下文管理
# │   ├── formatters.py    # 格式化输出
# │   └── compact.py       # 上下文压缩
# └── tools/              # 可用工具
#     ├── section_info.py  # 查询板块
#     ├── update_section.py # 修改板块
#     ├── add_section.py   # 添加板块
#     └── translate_resume.py # 翻译
# 为什么第二实现 AI 助手？
# 原因	解释
# 差异化功能	简历工具很多，但"AI 对话优化"是亮点
# 可利用 parser	需要知道简历结构（parser 已定义）
# AI Agent 复杂	需要工具调用、SSE 流式、状态管理
# 用户价值高	直接解决"不知道怎么写简历"的问题
# 技术架构
# 用户消息
#     ↓
# conversation_store 保存对话历史
#     ↓
# agent_service 启动 Agent
#     ↓
# agent/core.py 循环：
#     1. 根据上下文构建消息
#     2. 调用 LLM
#     3. 解析工具调用
#     4. 执行工具（section_info/update_section/add_section/translate_resume）
#     5. SSE 推送结果给前端
# ---
# 阶段 4：shared 模块提取 (2026-04-07)
# shared/
# ├── database.py      # 数据库连接
# ├── models.py        # ORM 模型
# ├── api/             # LLM API 客户端
# │   ├── client.py
# │   ├── openai_client.py
# │   ├── errors.py
# │   └── usage.py
# ├── exceptions/      # 异常定义
# └── types/           # 补充类型
#     ├── messages.py
#     ├── jd_analysis.py
#     ├── base_tool.py
#     └── mixins.py
# 为什么这时候提取 shared？
# 原因	解释
# 发现重复代码	parser 和 resume_assistant 都在调用 LLM
# 避免未来重复	预计会有更多模块需要调用 LLM
# 依赖关系清晰	把被依赖的代码抽取出来
# 重构最佳时机	功能已跑通，正是重构的好时候
# 重构内容
# 重构前：
#     parser/call_llm.py ← 自己的 LLM 调用
#     resume_assistant/agent_service.py ← 自己的 LLM 调用
# 重构后：
#     shared/api/client.py ← 统一的 LLM 客户端
#     shared/api/openai_client.py ← OpenAI 兼容实现
    
# → parser/call_llm.py 调用 shared/api/
# → resume_assistant/agent_service.py 调用 shared/api/
# ---
# 阶段 5：config 模块 (2026-04-09)
# apps/config/
# ├── schemas.py    # ProviderConfig, ProviderConfigUpdate, ProviderSwitch
# └── router.py     # GET/PUT /config/provider, PATCH /config/provider/switch
# 为什么这时候添加配置模块？
# 原因	解释
# 需求驱动	parser 和 resume_assistant 都在硬编码 API Key
# 用户需要配置	用户不可能接受固定某个 API Key
# 简单但重要	只是 key-value 存储，没有复杂逻辑
# 被依赖方	其他模块都依赖配置，不依赖其他模块
# 技术实现
# UserConfig 表结构：
# ┌─────────────────┬──────────────────────────────┐
# │      key        │            value              │
# ├─────────────────┼──────────────────────────────┤
# │ provider_config │ {"providers": {...}, "active": "openai"} │
# └─────────────────┴──────────────────────────────┘
# → config/router.py 提供 CRUD 接口
# → 其他模块读取配置获取 API Key
# ---
# 阶段 6：resume/ 和 resume_section/ (2026-04-11)
# shared/
# ├── resume_prompt.py         # 简历 LLM 提示词
# └── resume_section_factory.py # 默认板块工厂
# apps/resume/
# ├── router.py    # 简历 CRUD
# ├── schemas.py   # 创建请求模型
# └── service.py   # 业务逻辑
# apps/resume_section/
# └── router.py    # 板块 CRUD
# 为什么这时候添加简历管理？
# 原因	解释
# 数据需要管理	parser 解析的结果需要组织和展示
# workspace 概念	主简历（workspace）+ 子简历（针对不同职位）
# 自然演进	parser → 有数据 → 需要管理数据
# JD 分析前提	子简历需要针对特定职位描述
# 技术架构
# Workspace（主简历）
# ├── 子简历 1（针对 JD A）
# ├── 子简历 2（针对 JD B）
# └── 子简历 3（针对 JD C）
# → 每个子简历有独立的板块内容
# → 但共享主简历的模板和主题
# ---
# 阶段 7：jd_analysis/ (2026-04-11)
# apps/jd_analysis/
# ├── router.py    # POST /jd-analysis/analyze
# ├── schemas.py   # AnalyzeJDRequest
# ├── prompt.py    # JD 分析提示词
# ├── call_llm.py  # LLM 调用
# └── service.py  # 分析逻辑
# 为什么和 resume 同时添加？
# 原因	解释
# 核心需求	用户需要知道简历和职位的匹配度
# 依赖清晰	需要简历数据（resume）+ 职位描述（JD）
# 技术复用	和 parser 类似的 LLM 调用模式
# 独立功能	可以单独测试和使用
# 分析内容
# 输入：
#     - 简历内容（来自 resume 模块）
#     - 职位描述（用户输入）
# 输出：
#     - 总体匹配评分（0-100）
#     - ATS 兼容性评分
#     - 关键词匹配
#     - 缺失关键词
#     - 优化建议
# ---
# 阶段 8：cover_letter/ 和 conversation_message/ (2026-04-15)
# apps/cover_letter/
# ├── router.py   # SSE 流式生成
# ├── schemas.py  # CoverLetterRequest
# ├── prompt.py   # 求职信提示词
# └── service.py  # 生成逻辑
# apps/conversation_message/
# └── router.py   # 查询历史消息
# 为什么这时候添加？
# 原因	解释
# 周边功能	不是核心功能，是增值功能
# 用户场景	有简历了，需要生成配套材料
# 时间节点	核心功能完成后开始完善周边
# conversation_message	AI 助手需要保存对话历史
# ---
# 阶段 9：work/ 任务系统 (2026-04-16)
# apps/work/
# ├── router.py    # 任务 CRUD
# └── sse.py       # SSE 流式推送
# shared/
# ├── task_state.py # 任务状态管理
# └── types/
#     ├── work.py   # WorkTaskSchema
#     └── task.py   # TaskStatus
# 为什么需要任务系统？
# 原因	解释
# 异步任务	JD 分析、求职信生成是耗时的
# 状态追踪	用户需要知道任务进度
# SSE 推送	实时更新任务状态
# 统一管理	多种任务类型需要统一处理
# 任务状态
# pending → running → success
#               ↓
#             error
# → work/sse.py 推送状态变化给前端
# → task_state.py 管理内存中的任务状态
# ---
# 阶段 10：export/ PDF 导出 (2026-04-23)
# apps/export/
# ├── router.py          # POST /export/pdf
# ├── browser_manager.py # Playwright 浏览器管理
# ├── pdf_generator.py   # HTML → PDF
# └── service.py         # 导出逻辑
# 为什么最后添加导出？
# 原因	解释
# 用户价值高	简历最终需要导出
# 技术复杂	需要 Playwright、浏览器管理
# 周边功能	核心功能（解析、AI、JD分析）已完成
# 依赖其他模块	需要完整的简历数据才能导出
# 技术流程
# HTML 模板（前端渲染）
#     ↓
# 后端请求导出
#     ↓
# Playwright 浏览器渲染 HTML
#     ↓
# 截图/导出为 PDF
#     ↓
# 返回 PDF 文件
# ---
# 阶段 11：template/ 模板管理 (2026-04-25)
# apps/template/
# └── router.py   # 模板 CRUD
# shared/types/
# └── template.py # TemplateSchema
# 为什么最后添加模板管理？
# 原因	解释
# 可选功能	可以用固定模板，不需要管理系统
# 优先级低	先把简历功能做好，再考虑模板
# 依赖数据	需要先有简历数据才能定义模板结构
# ---
# 阶段 12：main.py 组装
# main.py
# 为什么最后组装？
# 原因	解释
# 模块化开发	先让每个模块独立运行
# 最后整合	所有功能完成后注册路由
# 迭代式	可以先只注册部分模块测试
# 统一入口	集中管理 CORS、lifespan、日志
# main.py 内容
# # 注册所有路由
# app.include_router(config_router)
# app.include_router(resume_router)
# app.include_router(resume_section_router)
# # ... 其他所有 router
# # 配置 CORS
# app.add_middleware(CORSMiddleware, ...)
# # lifespan（启动/关闭钩子）
# async def lifespan(app: FastAPI):
#     await init_db()        # 启动时初始化数据库
#     await ensure_browser() # 启动时初始化浏览器
#     yield
#     # 关闭时清理资源
# # 日志
# logging.basicConfig(level=logging.INFO)
# ---
# 总结：项目演进规律
# ┌─────────────────────────────────────────────────────────────────┐
# │  第 1 步：基础搭建（依赖最少）                                     │
# │  ├── pyproject.toml (.python-version)                           │
# │  └── shared/types/ (strict_model.py, resume.py)                  │
# │                                                                  │
# │  第 2 步：核心功能 MVP（解决核心问题）                             │
# │  └── apps/parser/ (PDF 解析)                                      │
# │                                                                  │
# │  第 3 步：差异化功能（竞争优势）                                   │
# │  └── apps/resume_assistant/ (AI 对话优化)                         │
# │                                                                  │
# │  第 4 步：架构优化（减少重复）                                     │
# │  └── shared/ (api/, database.py, models.py)                      │
# │                                                                  │
# │  第 5 步：基础设施（被其他模块依赖）                               │
# │  └── apps/config/ (API Key 配置)                                 │
# │                                                                  │
# │  第 6 步：业务完善（核心功能补充）                                  │
# │  ├── apps/resume/ (简历管理)                                     │
# │  ├── apps/jd_analysis/ (JD 分析)                                  │
# │  └── apps/resume_section/ (板块管理)                              │
# │                                                                  │
# │  第 7 步：增值功能（提升用户体验）                                  │
# │  ├── apps/cover_letter/ (求职信)                                  │
# │  ├── apps/conversation_message/ (消息历史)                        │
# │  └── apps/work/ (任务系统)                                        │
# │                                                                  │
# │  第 8 步：输出功能（完成工作流闭环）                               │
# │  └── apps/export/ (PDF 导出)                                     │
# │                                                                  │
# │  第 9 步：收尾（可选功能）                                         │
# │  └── apps/template/ (模板管理)                                   │
# │                                                                  │
# │  第 10 步：组装入口                                               │
# │  └── main.py                                                     │
# └─────────────────────────────────────────────────────────────────┘
# ---
# 这个顺序的核心理念
# 理念	应用
# MVP 思维	先做核心功能，再完善周边
# 依赖驱动	先实现被依赖的，再实现依赖别人的
# 重构时机	功能跑通后立即重构，避免技术债累积
# 用户价值	高价值功能优先，低价值功能靠后
# 渐进式	每个阶段都能交付可用的产品