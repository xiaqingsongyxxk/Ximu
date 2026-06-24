import json  # 导入JSON模块，用于将Python字典转为JSON字符串存入数据库（如theme_config字段）
import uuid  # 导入UUID模块，用于生成唯一标识符（简历ID、板块ID等）
from typing import (
    Annotated,
)  # 导入Annotated类型注解工具，用于给FastAPI参数添加元数据（如Body、Query描述）

from fastapi import (  # 从FastAPI框架导入核心组件
    APIRouter,  # API路由器，用于定义一组相关的API端点
    Depends,  # 依赖注入装饰器，用于自动获取数据库会话等共享资源
    HTTPException,  # HTTP异常类，用于返回错误响应（如404、500）
    Query,  # 查询参数装饰器，用于定义URL查询参数（如?id=xxx）
)
from pydantic import Field  # 从Pydantic导入Field，用于定义模型字段的默认值、描述等属性
from sqlalchemy import (
    delete,
    select,
)  # 从SQLAlchemy导入查询构建器：select用于查询，delete用于删除
from sqlalchemy.ext.asyncio import AsyncSession  # 导入异步数据库会话类型
from sqlalchemy.orm import (
    selectinload,
)  # 导入预加载函数，用于一次查询同时加载关联数据（避免N+1查询问题）

from apps.resume.schemas import (  # 从apps/resume/schemas.py导入请求体数据模型
    CreateSubResumeRequest,  # 创建子简历的请求数据模型
    CreateWorkspaceRequest,  # 创建主简历（工作区）的请求数据模型
)
from apps.resume.service import (  # 从apps/resume/service.py导入业务逻辑函数
    copy_sections_from_workspace,  # 从主简历复制板块到子简历的函数
    create_default_sections,  # 为新简历创建默认板块的函数（个人信息、工作经历等6个板块）
)
from shared.database import (
    get_session,
)  # 从shared/database.py导入获取数据库会话的依赖函数
from shared.models import (  # 从shared/models.py导入数据库模型
    ConversationMessageRecord,  # 对话消息记录模型，删除简历时需要级联删除相关对话
    Resume,  # 简历数据库模型，对应resumes表
)
from shared.types.resume import (
    ResumeSchema,
)  # 从shared/types/resume.py导入简历的Pydantic数据模型

# 创建简历模块的API路由器，所有路由都以 /resume 开头
router = APIRouter(
    prefix="/resume", tags=["resume"]
)  # prefix定义URL前缀，tags用于API文档分组


class SubResumeInfo(ResumeSchema):  # 定义子简历简要信息类，继承自ResumeSchema
    """子简历的轻量级表示。

    继承ResumeSchema的所有字段（id、title、template等），
    用于在主简历详情中展示子简历的基本信息。
    注意：子简历没有sub_resume_ids和sub_resumes字段，
    因为子简历不会再有下级子简历。
    """  # 文档字符串，说明子简历信息的数据结构

    model_config = (
        ResumeSchema.model_config
    )  # 继承父类的Pydantic配置（camelCase别名、populate_by_name等）


class WorkspaceSummary(ResumeSchema):  # 定义主简历摘要类，继承自ResumeSchema
    """主简历（工作区）摘要信息。

    在ResumeSchema基础上增加了sub_resume_ids字段，
    用于存储该主简历下所有子简历的ID列表。
    适用于简历列表页面，只需知道有多少个子简历，不需要完整数据。
    """  # 文档字符串

    model_config = ResumeSchema.model_config  # 继承父类的Pydantic配置

    sub_resume_ids: list[str] = Field(  # 定义子简历ID列表字段
        default_factory=list,  # 默认值为空列表（没有子简历时返回[]而非null）
        description="该主简历下的所有子简历ID列表",  # API文档中的字段描述
    )


class WorkspaceDetail(WorkspaceSummary):  # 定义主简历详情类，继承自WorkspaceSummary
    """主简历（工作区）完整详情。

    在WorkspaceSummary基础上增加了sub_resumes字段，
    包含所有子简历的完整对象数据。
    适用于主简历详情页面，需要展示每个子简历的具体信息。
    """  # 文档字符串

    sub_resumes: list[SubResumeInfo] = Field(  # 定义子简历完整列表字段
        default_factory=list,  # 默认值为空列表
        description="该主简历下的所有子简历完整信息列表",  # API文档中的字段描述
    )


# ========== API 端点定义 ==========


@router.get(  # 定义GET请求路由
    "/list",  # URL路径：GET /resume/list
    summary="查询主简历列表",  # API文档中的简要描述
)
async def list_resumes(  # 定义异步处理函数
    db: Annotated[
        AsyncSession, Depends(get_session)
    ],  # 通过依赖注入获取数据库会话，请求结束自动关闭
) -> list[WorkspaceSummary]:  # 返回值类型：WorkspaceSummary列表
    """查询所有主简历（工作区）列表。

    查找workspace_id为NULL的记录（即主简历），
    同时预加载每个主简历的子简历列表，
    返回主简历摘要信息（含子简历ID列表）。

    这个接口用于Dashboard页面显示所有主简历卡片。
    """  # 文档字符串
    result = await db.execute(  # 执行数据库查询
        select(Resume)  # 查询Resume表的所有字段
        .where(Resume.workspace_id.is_(None))  # 条件：workspace_id为NULL（即主简历）
        .options(
            selectinload(Resume.versions)
#             "我的 id"是运行时才知道的，不是定义时写死的。
# selectinload 的完整流程：
# 第一步：执行主查询
#   SELECT id, workspace_id, ... FROM resumes WHERE workspace_id IS NULL
#   → 结果：[{id: 'A', ...}, {id: 'B', ...}, {id: 'C', ...}]
#                                          ↑ 这些就是"我的 id"
# 第二步：selectinload 自动收集所有主查询结果的 id
#   ids = ['A', 'B', 'C']    ← SQLAlchemy 内部做的，你不需要管
# 第三步：用收集到的 ids 执行第二条查询
#   SELECT * FROM resumes WHERE workspace_id IN ('A', 'B', 'C')
# 第四步：按 workspace_id 分组，填充到对应对象的 .versions 属性
#   Resume_A.versions = [子简历1, 子简历2]  ← workspace_id = 'A' 的行
#   Resume_B.versions = [子简历3]          ← workspace_id = 'B' 的行
#   Resume_C.versions = []                ← 没有 workspace_id = 'C' 的行
# 所以"我的 id"并不需要你在代码里指定——SQLAlchemy 先执行主查询拿到所有父简历的 id，然后自动用它们拼出 IN (...) 子句。这是 selectinload 的核心机制：先查父，收集 id，再查子，自动关联。
        )  # 预加载：同时查出子简历列表（避免后续N+1查询）
    )
    resume_list = result.scalars().all()  # 获取所有查询结果，转为Resume对象列表

    return [  # 列表推导式，将每个Resume对象转换为WorkspaceSummary
        WorkspaceSummary(  # 创建WorkspaceSummary对象
            **resume.to_pydantic().model_dump(),  # 将ORM对象转为Pydantic再转为字典，展开所有字段
            sub_resume_ids=[
                v.id for v in resume.versions
            ],  # 提取所有子简历的ID组成列表
        )
        for resume in resume_list  # 遍历每个主简历
    ]


@router.get(  # 定义GET请求路由
    "/{id}",  # URL路径：GET /resume/{id}，{id}是路径参数
    summary="根据ID查询单份简历详情",  # API文档描述
)
async def get_resume(  # 定义异步处理函数
    id: str,  # 路径参数：简历ID
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> WorkspaceDetail:  # 返回值类型：WorkspaceDetail（含子简历详情）
    """根据ID查询单份简历的完整详情。

    查询指定ID的简历，同时预加载其子简历列表。
    返回主简历的完整信息，包括所有子简历的详细数据。

    无论传入的是主简历ID还是子简历ID都能工作：
    - 主简历：返回完整详情（含子简历列表）
    - 子简历：返回详情（sub_resume_ids和sub_resumes为空）
    """  # 文档字符串
    result = await db.execute(  # 执行数据库查询
        select(Resume)
        .where(Resume.id == id)
        .options(selectinload(Resume.versions))  # 按ID查询，同时预加载子简历
    )
    resume = result.scalar_one_or_none()  # 获取单条结果，没有则返回None
    if not resume:  # 如果简历不存在
        raise HTTPException(  # 抛出404异常
            status_code=404,  # HTTP状态码：404 Not Found
            detail="简历不存在",  # 错误详情信息
        )
    return WorkspaceDetail(  # 创建并返回WorkspaceDetail对象
        **resume.to_pydantic().model_dump(),  # 展开简历的所有字段
        sub_resume_ids=[v.id for v in resume.versions],  # 子简历ID列表
        sub_resumes=[  # 子简历完整信息列表
            SubResumeInfo(
                **v.to_pydantic().model_dump()
            )  # 将每个子简历转为SubResumeInfo对象
            for v in resume.versions  # 遍历所有子简历
        ],
    )


@router.post(  # 定义POST请求路由
    "/create",  # URL路径：POST /resume/create
    summary="创建主简历(Workspace)",  # API文档描述
)
async def create_workspace(  # 定义异步处理函数
    data: CreateWorkspaceRequest,  # 请求体：创建主简历的请求数据（通过Pydantic自动验证）
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> WorkspaceSummary:  # 返回值类型：创建的主简历摘要
    """创建新的主简历（工作区）。

    创建一个workspace_id为NULL的新简历（即主简历），
    同时自动创建6个默认板块（个人信息、个人简介、工作经历、教育背景、技能特长、项目经历）。

    前端在用户点击"创建工作区"时调用此接口。
    """  # 文档字符串
    resume_id = str(uuid.uuid4())  # 生成UUID作为新简历的唯一ID

    resume = Resume(  # 创建Resume ORM对象
        id=resume_id,  # 设置简历ID
        workspace_id=None,  # 设为None表示这是主简历（不是子简历）
        title=data.title,  # 设置简历标题
        template=data.template,  # 设置使用的模板
        theme_config=json.dumps(  # 将主题配置字典转为JSON字符串
            data.theme_config,  # 主题配置数据
            ensure_ascii=False,  # 允许中文直接显示
        ),
        language=data.language,  # 设置简历语言
    )
    db.add(resume)  # 将Resume对象添加到数据库会话（此时还未写入数据库）

    # 调用service层函数，为新简历创建6个默认板块
    # 定义在 apps/resume/service.py 中
    await create_default_sections(resume_id, db)

    try:  # 尝试提交事务
        await db.commit()  # 提交事务，将所有变更写入数据库
        await db.refresh(resume)  # 刷新对象，获取数据库生成的值（如created_at）
    except Exception:  # 如果提交失败
        await db.rollback()  # 回滚事务，撤销所有变更
        raise HTTPException(  # 抛出500异常
            status_code=500,
            detail="新增失败",
        )

    return WorkspaceSummary(  # 返回创建的主简历摘要
        **resume.to_pydantic().model_dump(),  # 展开所有字段
        sub_resume_ids=[],  # 新创建的主简历还没有子简历，返回空列表
    )


@router.post(
    "/sub/create", summary="创建子简历"
)  # 定义POST请求路由：POST /resume/sub/create
async def create_sub_resume(  # 定义异步处理函数
    data: CreateSubResumeRequest,  # 请求体：创建子简历的请求数据
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> WorkspaceSummary:  # 返回值类型：创建的子简历摘要
    """在主简历（工作区）下创建新的子简历。

    子简历会继承主简历的板块结构（通过copy_sections_from_workspace复制），
    并关联目标职位描述（job_description）和职位名称（job_title），
    用于后续的AI简历优化和JD匹配分析。

    前端在用户点击"生成子简历"时调用此接口。
    """  # 文档字符串
    # 查询主简历：id等于传入的workspace_id，且workspace_id为NULL（确保是主简历）
    result = await db.execute(
        select(Resume).where(
            Resume.id == data.workspace_id,  # 条件：ID匹配
            Resume.workspace_id.is_(None),  # 条件：必须是主简历（workspace_id为NULL）
        )
    )
    workspace = result.scalar_one_or_none()  # 获取查询结果
    if not workspace:  # 如果主简历不存在
        raise HTTPException(  # 抛出404异常
            status_code=404,
            detail="所属 Workspace 不存在",
        )

    resume_id = str(uuid.uuid4())  # 生成子简历的UUID

    # 构建子简历的元数据（包含目标职位信息）
    meta_info = {"job_description": data.job_description}  # 职位描述（必填）

    if data.job_title:  # 如果提供了职位名称（可选）
        meta_info["job_title"] = data.job_title  # 添加到元数据中

    resume = Resume(  # 创建子简历的ORM对象
        id=resume_id,  # 子简历ID
        workspace_id=data.workspace_id,  # 关联到主简历的ID
        title=data.title,  # 子简历标题
        template=data.template,  # 使用的模板
        theme_config=json.dumps(  # 主题配置转为JSON字符串
            data.theme_config,
            ensure_ascii=False,
        ),
        language=data.language,  # 语言
        meta_info=meta_info,  # 元数据（职位描述和职位名称）
    )

    db.add(resume)  # 添加到数据库会话

    # 从主简历复制所有板块到子简历
    # 定义在 apps/resume/service.py 中
    await copy_sections_from_workspace(
        workspace.id,  # 源：主简历ID
        resume_id,  # 目标：子简历ID
        db,  # 数据库会话
    )
# 假设主简历的工作经历里已经填了一些模板内容，或者用户额外加了一个"证书"板块（自定义），create_default_sections 就不会有它。而 copy_sections_from_workspace 会原样复制：主简历有什么板块、什么顺序、什么内容，子简历就有什么。
    try:  # 尝试提交事务
        await db.commit()  # 提交事务
        await db.refresh(resume)  # 刷新对象
    except Exception:  # 提交失败
        await db.rollback()  # 回滚事务
        raise HTTPException(  # 抛出500异常
            status_code=500,
            detail="新增失败",
        )

    return WorkspaceSummary(  # 返回子简历摘要
        **resume.to_pydantic().model_dump(),  # 展开所有字段
        sub_resume_ids=[],  # 子简历没有下级子简历，返回空列表
    )


@router.put("/update", summary="更新简历")  # 定义PUT请求路由：PUT /resume/update
async def update_resume(  # 定义异步处理函数
    data: ResumeSchema,  # 请求体：包含要更新字段的简历数据
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> ResumeSchema:  # 返回值类型：更新后的简历数据
    """更新现有简历的信息。

    只更新请求中传入的字段（exclude_unset=True），
    未传入的字段保持原值不变（部分更新）。

    前端在用户编辑简历标题、切换模板、修改主题等操作时调用此接口。
    """  # 文档字符串
    result = await db.execute(  # 执行查询
        select(Resume).where(Resume.id == data.id)  # 按ID查找要更新的简历
    )
    resume = result.scalar_one_or_none()  # 获取查询结果
    if not resume:  # 如果简历不存在
        raise HTTPException(  # 抛出404异常
            status_code=404,
            detail="简历不存在",
        )

    # 遍历请求中传入的所有字段（exclude_unset=True只包含显式设置的字段）
    for key, value in data.model_dump(
        exclude_unset=True  # 只包含前端传入的字段，未传入的字段跳过
    ).items():
        if key == "theme_config":  # 如果是主题配置字段
            value = json.dumps(value, ensure_ascii=False)  # 将字典转为JSON字符串
        setattr(resume, key, value)  # 动态设置对象属性（如resume.title = "新标题"）
# 比如前端只传了 {"title": "新标题", "template": "modern"}：
# # 第一轮：key="title", value="新标题"
# setattr(resume, "title", "新标题")
# # 等价于：resume.title = "新标题"
# # 第二轮：key="template", value="modern"
# setattr(resume, "template", "modern")
# # 等价于：resume.template = "modern"
# 不用 setattr 的写法：
# if data.title is not None:
#     resume.title = data.title
# if data.template is not None:
#     resume.template = data.template
# if data.language is not None:
#     resume.language = data.language
# # ... 十几行重复 if
    try:  # 尝试提交事务
        await db.commit()  # 提交事务
        await db.refresh(resume)  # 刷新对象
    except Exception:  # 提交失败
        await db.rollback()  # 回滚事务
        raise HTTPException(  # 抛出500异常
            status_code=500,
            detail="修改失败",
        )
    return resume.to_pydantic()  # 将更新后的ORM对象转为Pydantic模型返回


@router.delete(
    "/delete", summary="删除简历"
)  # 定义DELETE请求路由：DELETE /resume/delete?id=xxx
async def delete_resume(  # 定义异步处理函数
    id: Annotated[str, Query(description="简历ID")],  # 查询参数：要删除的简历ID
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> None:  # 无返回值
    """根据ID删除简历及其所有关联数据。

    删除操作会级联处理：
    1. 删除该简历及所有子简历的对话记录
    2. 删除所有子简历（通过cascade级联）
    3. 删除主简历本身
    4. 清理内存中的对话状态

    注意：此操作不可撤销！
    """  # 文档字符串
    # 延迟导入ConversationStore，避免循环依赖
    # 定义在 apps/resume_assistant/conversation_store.py 中
    from apps.resume_assistant.conversation_store import (
        ConversationStore,  # 对话状态存储类，用于管理内存中的对话上下文
    )

    # 查询主简历，同时预加载子简历列表
    result = await db.execute(
        select(Resume).where(Resume.id == id).options(selectinload(Resume.versions))
    )
    parent = result.scalar_one_or_none()  # 获取查询结果
    if not parent:  # 如果简历不存在
        raise HTTPException(  # 抛出404异常
            status_code=404,
            detail="简历不存在",
        )

    # 收集所有需要删除的简历ID（主简历 + 所有子简历）
    all_resume_ids = [parent.id] + [  # 主简历ID + 子简历ID列表
        v.id
        for v in parent.versions  # 遍历所有子简历
    ]

    # 先删除所有关联的对话消息记录（数据库层面）
    await db.execute(
        delete(ConversationMessageRecord).where(
            ConversationMessageRecord.conversation_id.in_(
                all_resume_ids
            )  # IN查询：删除所有相关对话
        )
    )

    # 删除主简历（cascade会自动删除所有子简历和关联的板块）
    await db.delete(parent)

    try:  # 尝试提交事务
        await db.commit()  # 提交事务
        # 清理内存中的对话状态（ConversationStore是内存存储，不走数据库）
        conversation_store = ConversationStore()  # 创建对话状态存储实例
        for resume_id in all_resume_ids:  # 遍历所有简历ID
            conversation_store.delete(resume_id)  # 删除内存中的对话状态
    except Exception:  # 提交失败
        await db.rollback()  # 回滚事务
        raise HTTPException(  # 抛出500异常
            status_code=500,
            detail="删除失败",
        )
    return None  # 删除成功，无返回值
