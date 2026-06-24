"""简历解析的API路由模块。

本模块提供简历文件解析功能：
1. POST /parser - 上传文件并启动解析任务（PDF/图片 → 结构化简历数据）
2. POST /parser/retry/{task_id} - 重试失败的解析任务

解析流程：用户上传简历文件 → 调用AI识别内容 → 生成结构化简历数据
"""  # 模块文档字符串

import uuid  # 导入UUID模块，用于生成唯一任务ID
from typing import (  # 导入类型注解工具
    Annotated,  # 用于给参数添加元数据
    Literal,  # 用于限定参数为固定值
)

from fastapi import (  # 从FastAPI框架导入核心组件
    APIRouter,  # API路由器
    BackgroundTasks,  # 后台任务管理器
    Depends,  # 依赖注入
    File,  # 文件上传参数
    Form,  # 表单参数
    HTTPException,  # HTTP异常
    UploadFile,  # 上传文件类型
)
from sqlalchemy import select  # SQL查询构建器
from sqlalchemy.ext.asyncio import AsyncSession  # 异步数据库会话

from apps.parser.service import (  # 从apps/parser/service.py导入业务逻辑函数
    infer_parser_type,  # 推断文件类型（PDF/图片/文本）
    retry_parser_task,  # 重试解析任务
    run_parser_task,  # 执行解析任务
)
from shared.api import get_client  # 获取LLM客户端的函数
from shared.database import get_session  # 获取数据库会话的依赖函数
from shared.models import BaseWork  # 工作任务的ORM模型
from shared.task_state import create_task, tasks  # 任务状态管理：创建任务、任务存储字典
from shared.types.task import TaskStatus, TaskType  # 任务状态和类型枚举
from shared.types.work import TaskIdResponse  # 任务ID响应模型

# 创建解析模块的API路由器
router = APIRouter(
    prefix="/parser",  # URL前缀：/parser
    tags=["parser"],  # API文档标签
)


@router.post(  # 定义POST请求路由
    "",  # 路径为空，完整路径为 /parser
    summary="上传简历文件并启动AI解析任务",  # API文档描述
    responses={  # 定义可能的错误响应
        400: {"description": "不支持的文件类型或文件超过10MB"},
    },
)
async def parse_document(  # 定义异步处理函数
    background_tasks: BackgroundTasks,  # 后台任务管理器
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
    file: Annotated[  # 上传的文件
        UploadFile, File(description="要解析的简历文件（PDF/图片），最大10MB")
    ],
    type: Annotated[  # LLM供应商类型
        Literal["openai", "anthropic"],  # 只能是这两个值之一
        Form(description="LLM供应商类型"),
    ],
    base_url: Annotated[  # LLM API地址
        str,
        Form(description="AI API地址"),
    ],
    api_key: Annotated[  # LLM API密钥
        str, Form(description="AI API密钥")
    ],
    model: Annotated[  # 模型名称
        str, Form(description="模型名称（如gpt-4o）")
    ],
    template: Annotated[  # 模板名称
        str, Form(description="简历模板名称（如classic）")
    ],
    title: Annotated[  # 简历标题
        str,
        Form(description="简历标题"),
    ] = "未命名简历",  # 默认值
) -> TaskIdResponse:  # 返回值类型：任务ID响应
    """上传简历文件并启动AI解析任务。

    流程：
    1. 验证文件类型
    2. 保存上传文件到本地
    3. 创建任务记录
    4. 启动后台AI解析任务
    5. 返回task_id供前端轮询

    Args:
        background_tasks: FastAPI后台任务管理器。
        db: 异步数据库会话。
        file: 上传的简历文件。
        type: LLM供应商类型。
        base_url: LLM API地址。
        api_key: LLM API密钥。
        model: 模型名称。
        template: 简历模板名称。
        title: 简历标题。
    """  # 文档字符串
    # 第一步：验证文件类型是否支持
    try:
        infer_parser_type(file.filename, file.content_type)  # 推断文件类型
# 上传的文件	file.filename 结果
# resume.pdf	"resume.pdf"
# 张三-简历.docx	"张三-简历.docx"
# photo.png	"photo.png"
    except ValueError as e:  # 如果文件类型不支持
        raise HTTPException(status_code=400, detail=str(e))  # 返回400错误

    # 第二步：生成任务ID并创建内存任务记录
    task_id = str(uuid.uuid4())  # 生成唯一任务ID
    create_task(task_id, TaskType.PARSE)  # 在内存中创建任务状态记录

    # 第三步：保存上传文件到本地
    from apps.parser.storage import save_upload_file  # 延迟导入，避免循环依赖

    file_path, original_name = await save_upload_file(file, task_id)  # 保存文件，返回路径和原始文件名

    # 第四步：创建数据库任务记录
    work = BaseWork(
        id=task_id,  # 任务ID
        task_type=TaskType.PARSE.value,  # 任务类型：解析
        status=TaskStatus.PENDING.value,  # 初始状态：待处理
        meta_info={  # 元数据
            "file_name": original_name,  # 原始文件名
            "src": file_path,  # 文件存储路径
            "template": template,  # 使用的模板
            "title": title,  # 简历标题
        },
    )
    db.add(work)  # 添加到数据库会话
    await db.commit()  # 提交事务

    # 第五步：获取LLM客户端并启动后台解析任务
    client = get_client(type, api_key, base_url)  # 根据配置获取LLM客户端

    background_tasks.add_task(  # 添加后台任务
        run_parser_task,  # 执行解析的函数（定义在apps/parser/service.py中）
        db,  # 数据库会话
        task_id,  # 任务ID
        file_path,  # 文件路径
        client,  # LLM客户端
        model,  # 模型名称
        template,  # 模板名称
        title,  # 简历标题
    )

    return TaskIdResponse(task_id=task_id)  # 返回任务ID


@router.post(  # 定义POST请求路由
    "/retry/{task_id}",  # URL路径：POST /parser/retry/{task_id}
    summary="重试失败的解析任务",  # API文档描述
    responses={  # 定义可能的错误响应
        404: {"description": "任务不存在"},
        400: {"description": "任务状态不是错误，无法重试"},
    },
)
async def retry_failed_task(  # 定义异步处理函数
    background_tasks: BackgroundTasks,  # 后台任务管理器
    task_id: str,  # 路径参数：要重试的任务ID
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
    type: Annotated[  # LLM供应商类型
        Literal["openai", "anthropic"],
        Form(description="LLM供应商类型"),
    ],
    base_url: Annotated[  # LLM API地址
        str,
        Form(description="AI API地址"),
    ],
    api_key: Annotated[  # LLM API密钥
        str, Form(description="AI API密钥")
    ],
    model: Annotated[  # 模型名称
        str, Form(description="模型名称")
    ],
) -> TaskIdResponse:  # 返回值类型：任务ID响应
    """重试失败的解析任务。

    只有状态为error的任务才能重试。
    使用原始文件和新的LLM配置重新执行解析。

    Args:
        background_tasks: FastAPI后台任务管理器。
        task_id: 要重试的任务ID。
        db: 异步数据库会话。
        type: LLM供应商类型。
        base_url: LLM API地址。
        api_key: LLM API密钥。
        model: 模型名称。
    """  # 文档字符串
    # 检查任务是否已在内存中（正在执行）
    if task_id in tasks:  # 如果任务已在运行
        return TaskIdResponse(task_id=task_id)  # 直接返回任务ID

    # 从数据库查询任务记录
    result = await db.execute(select(BaseWork).where(BaseWork.id == task_id))  # 按ID查询
    work = result.scalar_one_or_none()  # 获取结果
    if not work:  # 如果任务不存在
        raise HTTPException(status_code=404, detail="任务不存在")  # 抛出404异常

    # 检查任务状态是否为错误（只有错误状态才能重试）
    if work.status != TaskStatus.ERROR.value:  # 如果不是错误状态
        raise HTTPException(  # 抛出400异常
            status_code=400, detail="只有错误状态的任务才能重试"
        )

    # 从元数据中恢复原始参数
    meta_info = work.meta_info or {}  # 获取元数据
    file_path = meta_info.get("src", "")  # 原始文件路径
    template = meta_info.get("template", "classic")  # 模板名称
    title = meta_info.get("title", "未命名简历")  # 简历标题

    # 重新创建任务记录
    create_task(task_id, TaskType.PARSE)  # 在内存中创建任务状态

    # 获取LLM客户端
    client = get_client(type, api_key, base_url)  # 创建LLM客户端

    # 启动后台重试任务
    background_tasks.add_task(
        retry_parser_task,  # 重试函数（定义在apps/parser/service.py中）
        db, task_id, file_path, client, model, template, title,  # 参数
    )

    return TaskIdResponse(task_id=task_id)  # 返回任务ID
