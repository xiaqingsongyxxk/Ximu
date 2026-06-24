"""求职信生成的API路由模块。

本模块提供AI生成求职信功能：
POST /cover-letter - 根据简历和职位描述生成求职信
"""  # 模块文档字符串，说明这个文件是做什么的

from typing import Annotated  # 导入Annotated类型注解，用于给参数添加额外信息

from fastapi import (  # 导入FastAPI核心组件
    APIRouter,  # API路由器，用于定义路由
    Body,  # 请求体参数装饰器
    Depends,  # 依赖注入装饰器
    HTTPException,  # HTTP异常类
    status,  # HTTP状态码
)
from sqlalchemy import select  # SQL查询构建器，用于构建数据库查询语句
from sqlalchemy.ext.asyncio import AsyncSession  # 异步数据库会话，用于异步操作数据库

from apps.cover_letter.schemas import CoverLetterRequest  # 求职信请求数据模型
from apps.cover_letter.service import cover_letter_service  # 求职信生成服务
from shared.database import get_session  # 获取数据库会话的依赖函数
from shared.models import Resume, ResumeSection  # 简历和板块ORM模型

# 创建求职信模块的API路由器
# prefix="/cover-letter" 表示所有路由都以 /cover-letter 开头
# tags=["cover-letter"] 表示这些路由在API文档中归类为 cover-letter 组
router = APIRouter(prefix="/cover-letter", tags=["cover-letter"])


@router.post("", summary="AI生成求职信")  # POST /cover-letter
async def generate_cover_letter(
    request: Annotated[
        CoverLetterRequest, Body(description="请求参数")
    ],  # 请求参数，从请求体中解析
    db: Annotated[AsyncSession, Depends(get_session)],  # 数据库会话，通过依赖注入获取
):
    """使用AI流式生成个性化求职信。

    查询简历及其板块，构建提示词，流式返回生成的求职信内容。
    生成的内容不会保存到数据库。

    Args:
        request: 请求参数（包含resume_id、jd_description、type、language）。
        db: 数据库会话。
    """
    # 查询简历
    # 使用select语句查询Resume表，条件是ID等于请求中的resume_id
    result = await db.execute(select(Resume).where(Resume.id == request.resume_id))
    # 获取查询结果（如果存在的话）
    resume = result.scalar_one_or_none()
    # 如果没有找到简历，返回404错误
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="没有该简历")

    # 查询简历的可见板块
    # 使用select语句查询ResumeSection表，条件是简历ID匹配且板块可见
    section = await db.execute(
        select(ResumeSection)
        .where(
            ResumeSection.resume_id == request.resume_id,  # 简历ID匹配
            ResumeSection.visible == True,  # 板块可见
        )
        .order_by(ResumeSection.sort_order)  # 按排序序号排序
    )
    # 获取所有查询结果
    items = section.scalars().all()
    # 将数据库模型转换为Pydantic模型
    sections = [item.to_pydantic() for item in items]

    # 调用服务生成求职信
    # 将请求和简历板块传递给服务层，返回流式响应
    return await cover_letter_service(request, sections, db)
