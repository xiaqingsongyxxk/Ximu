"""简历导出的API路由模块。

本模块提供简历导出功能：
1. POST /export/pdf - 将HTML渲染为PDF并下载
2. GET /export/txt/{resume_id} - 导出为纯文本格式
3. GET /export/json/{resume_id} - 导出为JSON格式
"""  # 模块文档字符串

from typing import Annotated  # 导入Annotated类型注解工具

from fastapi import APIRouter, Depends, HTTPException  # 导入FastAPI核心组件
from fastapi.encoders import jsonable_encoder  # 导入JSON编码器
from fastapi.responses import JSONResponse, Response  # 导入响应类型
from pydantic import BaseModel, Field  # 导入Pydantic组件
from sqlalchemy.ext.asyncio import AsyncSession  # 导入异步数据库会话

from apps.export.pdf_generator import (
    generate_pdf,
)  # 从apps/export/pdf_generator.py导入PDF生成函数
from apps.export.service import (
    export_json,
    export_txt,
)  # 从apps/export/service.py导入导出服务函数
from shared.database import get_session  # 获取数据库会话的依赖函数


class ExportPdfRequest(BaseModel):
    """PDF导出请求数据模型。

    Attributes:
        html: 要渲染为PDF的HTML内容。
        timeout_ms: 生成超时时间（毫秒）。
    """

    html: str = Field(description="待渲染的HTML内容")
    timeout_ms: int = Field(default=30000, description="超时时间（毫秒）")


# 创建导出模块的API路由器
router = APIRouter(prefix="/export", tags=["export"])


@router.post("/pdf", summary="导出PDF")  # POST /export/pdf
async def export_pdf(request: ExportPdfRequest) -> Response:
    """将HTML内容渲染为PDF并返回下载。

    前端在编辑器中点击"导出PDF"时调用此接口。
    使用Playwright浏览器渲染HTML为PDF。

    Args:
        request: 包含HTML内容和超时时间的请求。

    Returns:
        包含PDF字节内容的响应。

    Raises:
        HTTPException: HTML内容为空时抛出422。
    """
    if not request.html.strip():  # 如果HTML内容为空
        raise HTTPException(status_code=422, detail="HTML内容不能为空")

    pdf_bytes = await generate_pdf(request.html, request.timeout_ms)  # 生成PDF

    return Response(
        content=pdf_bytes,  # PDF字节内容
        media_type="application/pdf",  # 媒体类型
        headers={"Content-Disposition": "attachment; filename=resume.pdf"},  # 附件下载
    )


@router.get("/txt/{resume_id}", summary="导出TXT")  # GET /export/txt/{resume_id}
async def export_txt_endpoint(
    resume_id: str,  # 路径参数：简历ID
    db: Annotated[AsyncSession, Depends(get_session)],  # 数据库会话
) -> Response:
    """将简历导出为纯文本格式。

    Args:
        resume_id: 简历ID。
        db: 数据库会话。

    Returns:
        包含纯文本简历的响应。
    """
    try:
        text = await export_txt(resume_id, db)  # 调用TXT导出服务
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="简历不存在") from exc

    return Response(
        content=text.encode("utf-8"),  # UTF-8编码的文本
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=resume.txt"},
    )


@router.get("/json/{resume_id}", summary="导出JSON")  # GET /export/json/{resume_id}
async def export_json_endpoint(
    resume_id: str,  # 路径参数：简历ID
    db: Annotated[AsyncSession, Depends(get_session)],  # 数据库会话
) -> Response:
    """将简历导出为JSON格式。

    Args:
        resume_id: 简历ID。
        db: 数据库会话。

    Returns:
        包含JSON简历数据的响应。
    """
    try:
        data = await export_json(resume_id, db)  # 调用JSON导出服务
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="简历不存在") from exc

    return JSONResponse(
        content=jsonable_encoder(data),  # 编码为JSON
#         class User(BaseModel):
#     name: str
#     created_at: datetime
# user = User(name="张三", created_at=datetime.now())
# json.dumps(user)  # ❌ TypeError: Object of type User is not JSON serializable
# Python 内置的 json.dumps 不认识 datetime、Pydantic、UUID、Decimal 等类型，直接序列化会报错。
# jsonable_encoder 做了什么
# from fastapi.encoders import jsonable_encoder
# data = User(name="张三", created_at=datetime.now())
# encoded = jsonable_encoder(data)
# # → {"name": "张三", "created_at": "2026-05-20T10:30:00"}  ← datetime 变字符串
        headers={"Content-Disposition": "attachment; filename=resume.json"},
    )
