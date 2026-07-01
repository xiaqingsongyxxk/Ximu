# Ximu Backend

AI 简历优化平台后端服务。提供简历解析、AI 对话优化、JD 匹配分析、求职信生成、PDF 导出等能力。

## 技术栈

| 组件 | 技术 |
|------|------|
| 框架 | FastAPI |
| Python | 3.13+ |
| 包管理 | uv |
| 数据库 | SQLite + SQLAlchemy (async, aiosqlite) |
| LLM | OpenAI / Anthropic |
| PDF 生成 | Playwright (Chromium) |
| PDF 解析 | PyMuPDF |

## 快速开始

### 前置条件

- Python 3.13+
- uv（包管理器）

### 安装与运行

```bash
# 安装依赖
uv sync

# 启动开发服务器
uv run python main.py
```

服务默认运行在 `http://localhost:8000`。

首次启动时会自动：
- 创建 SQLite 数据库文件 `app.db`
- 创建所有数据库表
- 安装 Playwright Chromium 浏览器（用于 PDF 导出）

### 常用命令

```bash
uv run python main.py      # 启动服务
uv run ruff check           # 代码检查
uv run ruff format          # 代码格式化
uv add <package>            # 添加依赖
uv sync                     # 同步依赖
```

## 项目结构

```
backend/
├── main.py                  # FastAPI 应用入口，路由注册、中间件、生命周期
├── pyproject.toml           # 项目配置与依赖
├── .python-version          # Python 版本声明
├── uv.lock                  # 依赖锁定文件
├── app.db                   # SQLite 数据库文件（运行时生成）
│
├── shared/                  # 共享基础设施层
│   ├── database.py          # 数据库连接、会话工厂、依赖注入
│   ├── models.py            # SQLAlchemy ORM 模型
│   ├── task_state.py        # 异步任务状态管理（内存）
│   ├── resume_prompt.py     # 简历相关 LLM prompt 模板
│   ├── resume_section_factory.py  # 简历板块工厂
│   ├── api/                 # LLM API 客户端封装
│   │   ├── client.py        # 客户端基类
│   │   ├── openai_client.py # OpenAI 兼容实现
│   │   ├── errors.py        # API 错误定义
│   │   └── usage.py         # Token 用量追踪
│   ├── exceptions/          # 异常定义
│   │   └── base.py          # APIException 基类
│   └── types/               # Pydantic 数据结构定义
│       ├── strict_model.py  # 严格基类（禁止额外字段、camelCase）
│       ├── resume.py        # 简历类型
│       ├── messages.py      # LLM 对话消息类型
│       ├── jd_analysis.py   # JD 分析类型
│       ├── cover_letter.py  # 求职信类型
│       ├── work.py          # 工作任务类型
│       ├── task.py          # 任务状态类型
│       ├── template.py      # 模板类型
│       ├── base_tool.py     # Agent 工具基础类型
│       └── mixins.py        # API Response Mixin
│
└── apps/                    # 功能模块（API 层）
    ├── config/              # AI 提供商配置管理
    ├── resume/              # 简历 CRUD（主简历/子简历）
    ├── resume_section/      # 简历板块 CRUD
    ├── parser/              # PDF 简历解析
    ├── jd_analysis/         # JD 匹配分析
    ├── cover_letter/        # AI 求职信生成
    ├── resume_assistant/    # AI 简历优化助手（核心模块）
    │   ├── agent/           # Agent 核心（工具循环、状态管理、上下文压缩）
    │   └── tools/           # Agent 可用工具（查询/更新/添加板块、翻译）
    ├── export/              # PDF 导出（Playwright 渲染）
    ├── template/            # 模板管理
    ├── conversation_message/ # 对话历史管理
    └── work/                # 异步任务状态与 SSE 推送
```

## API 概览

| 模块 | 端点 | 说明 |
|------|------|------|
| Config | `GET/PUT /config/provider` | AI 提供商配置 |
| Resume | `POST/GET/PUT/DELETE /resume/...` | 简历 CRUD |
| Resume Section | `POST/GET/PUT/DELETE /resume-sections/...` | 简历板块 CRUD |
| Parser | `POST /parser/parse` | 上传 PDF 并解析为结构化简历 |
| JD Analysis | `POST /jd-analysis/analyze` | 简历与职位描述匹配分析 |
| Cover Letter | `POST /cover-letter/generate` | AI 生成求职信（SSE 流式） |
| Resume Assistant | `POST /resume-assistant/chat` | AI 对话优化简历（SSE 流式） |
| Export | `POST /export/pdf` | 简历导出为 PDF |
| Template | `GET/POST /templates` | 模板管理 |
| Conversation | `GET /conversations/...` | 对话历史查询 |
| Work | `GET /work/...` | 异步任务状态查询 |
| Work SSE | `GET /work/sse/...` | 任务状态 SSE 推送 |

## 开发规范

- **Python 命令**：始终使用 `uv run`，不要直接用 `python`
- **代码检查**：编辑后执行 `uv run ruff check`
- **代码格式化**：检查后执行 `uv run ruff format`
- **文档字符串**：使用 Google 风格
- **异步**：全项目使用 `async/await`
- **类型定义**：API 数据结构放在 `shared/types/`
- **数据库模型**：ORM 模型放在 `shared/models.py`
- **模块结构**：每个功能模块包含 `router.py`、`schemas.py`、`service.py`

## 环境配置

通过 API 动态配置 AI 提供商（OpenAI / Anthropic），无需环境变量。配置存储在数据库 `UserConfig` 表中。

## 依赖管理

```bash
# 添加依赖
uv add <package>

# 添加开发依赖
uv add --dev <package>

# 删除依赖
uv remove <package>

# 同步所有依赖
uv sync
```

所有依赖安装在项目本地虚拟环境 `backend/.venv/` 中，不污染全局。
