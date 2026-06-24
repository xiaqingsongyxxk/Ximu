"""简历模板管理的API路由模块。

本模块提供简历模板的CRUD操作：
1. GET /template/list - 获取所有模板列表
2. GET /template/active - 获取启用的模板列表
3. POST /template/create - 创建新模板
4. PUT /template/update - 更新模板
5. DELETE /template/delete - 删除模板

模板定义了简历的视觉样式（如颜色、布局、字体等）。
注意：模板的React组件定义在前端代码中，这里只存储元数据。
"""  # 模块文档字符串

from typing import Annotated  # 导入Annotated类型注解工具

from fastapi import (  # 从FastAPI框架导入核心组件
    APIRouter,  # API路由器
    Depends,  # 依赖注入
    HTTPException,  # HTTP异常
    Query,  # 查询参数装饰器
)
from sqlalchemy import delete, select  # SQL查询和删除构建器
from sqlalchemy.ext.asyncio import AsyncSession  # 异步数据库会话

from shared.database import get_session  # 获取数据库会话的依赖函数
from shared.models import Template  # 模板的ORM模型
from shared.types.template import TemplateSchema  # 模板的Pydantic模型

# 创建模板模块的API路由器
router = APIRouter(
    prefix="/template",  # URL前缀：所有路由都以 /template 开头
    tags=["template"],  # API文档标签
)


@router.get("/list", summary="获取所有简历模板")  # GET /template/list
async def get_template_list(  # 定义异步处理函数
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> list[TemplateSchema]:  # 返回值类型：模板列表
    """获取所有模板（包括启用和未启用的）。

    用于管理后台查看所有模板。

    Args:
        db: 异步数据库会话。
    """  # 文档字符串
    result = await db.execute(select(Template))  # 查询所有模板
    template_list = result.scalars().all()  # 获取所有结果
    return [  # 列表推导式
        TemplateSchema.model_validate(item) for item in template_list  # 将每个ORM对象转为Pydantic模型
    ]


@router.get("/active", summary="获取启用的模板")  # GET /template/active
async def list_active_templates(  # 定义异步处理函数
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> list[TemplateSchema]:  # 返回值类型：模板列表
    """获取所有已启用的模板。

    用于前端创建简历时显示可选的模板列表。

    Args:
        db: 异步数据库会话。
    """  # 文档字符串
    result = await db.execute(  # 执行查询
        select(Template).where(Template.is_active == True)  # 只查询启用的模板
    )
    template_list = result.scalars().all()  # 获取所有结果
    return [  # 列表推导式
        TemplateSchema.model_validate(item) for item in template_list  # 转为Pydantic模型
    ]


@router.post("/create", summary="新增简历模板")  # POST /template/create
async def create_template(  # 定义异步处理函数
    data: TemplateSchema,  # 请求体：模板数据
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> TemplateSchema:  # 返回值类型：创建的模板数据
    """创建新的简历模板。

    Args:
        data: 模板的完整数据。
        db: 异步数据库会话。
    """  # 文档字符串
    d = data.model_dump(  # 将Pydantic对象转为字典
        exclude={"created_at", "updated_at"}  # 排除时间戳字段（数据库会自动生成）
    )
    db_template = Template(**d)  # 使用字典解包创建ORM对象
    db.add(db_template)  # 添加到数据库会话
    try:  # 尝试提交
        await db.commit()  # 提交事务
        await db.refresh(db_template)  # 刷新对象
    except Exception:  # 提交失败
        await db.rollback()  # 回滚事务
        raise HTTPException(status_code=500, detail="新增模板失败")  # 抛出500异常
    return TemplateSchema.model_validate(db_template)  # 验证并返回创建的模板


@router.put("/update", summary="修改模板")  # PUT /template/update
async def update_template(  # 定义异步处理函数
    data: TemplateSchema,  # 请求体：模板数据
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> TemplateSchema:  # 返回值类型：更新后的模板数据
    """更新现有模板的信息。

    Args:
        data: 包含模板ID和要更新的字段。
        db: 异步数据库会话。
    """  # 文档字符串
    result = await db.execute(  # 执行查询
        select(Template).where(Template.id == data.id)  # 按ID查找模板
    )
    template = result.scalar_one_or_none()  # 获取查询结果
    if not template:  # 如果模板不存在
        raise HTTPException(  # 抛出404异常
            status_code=404, detail="模板不存在"
        )
    for key, value in data.model_dump(exclude_unset=True).items():  # 遍历传入的字段
        setattr(template, key, value)  # 动态设置属性
    try:  # 尝试提交
        await db.commit()  # 提交事务
        await db.refresh(template)  # 刷新对象
    except Exception:  # 提交失败
        await db.rollback()  # 回滚事务
        raise HTTPException(status_code=500, detail="修改模板失败")  # 抛出500异常
    return TemplateSchema.model_validate(template)  # 验证并返回更新后的模板


@router.delete("/delete", summary="删除模板")  # DELETE /template/delete?id=xxx
async def delete_template(  # 定义异步处理函数
    id: Annotated[str, Query(description="模板ID")],  # 查询参数：模板ID
    db: Annotated[AsyncSession, Depends(get_session)],  # 依赖注入：数据库会话
) -> None:  # 无返回值
    """删除指定ID的模板。

    Args:
        id: 要删除的模板ID。
        db: 异步数据库会话。
    """  # 文档字符串
    await db.execute(delete(Template).where(Template.id == id))  # 执行删除
    try:  # 尝试提交
        await db.commit()  # 提交事务
    except Exception:  # 提交失败
        raise HTTPException(status_code=500, detail="删除模板失败")  # 抛出500异常
    return None  # 删除成功
