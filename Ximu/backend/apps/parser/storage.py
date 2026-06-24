"""上传文件的存储管理模块。

本模块负责将用户上传的简历文件保存到磁盘：
1. 定义上传目录（backend/upload/）
2. 读取上传文件内容
3. 生成新的文件名（使用任务ID）
4. 写入磁盘
"""  # 模块文档字符串

import asyncio  # 导入异步IO库，用于在线程池中执行同步操作
from pathlib import Path  # 导入Path类，用于路径操作

from fastapi import UploadFile  # 导入FastAPI的上传文件类型

# 计算上传文件存储目录的绝对路径
# __file__ = backend/apps/parser/storage.py
# .parent = backend/apps/parser/
# .parent.parent = backend/apps/
# .parent.parent.parent = backend/
# / "upload" = backend/upload/
UPLOAD_DIR = Path(__file__).parent.parent.parent / "upload"
UPLOAD_DIR.mkdir(exist_ok=True)  # 创建目录（如果已存在不报错）


def _read_file_contents(file) -> bytes:
    """同步读取文件内容。

    Args:
        file: 文件对象。

    Returns:
        文件的字节内容。
    """
    return file.file.read()  # 读取文件流的全部内容
# 关键在于：*file.file.read() 本身就是一个同步阻塞调用*，你没办法让它变成"真正的异步"。


def _write_file(file_path: Path, contents: bytes) -> None:
    """同步写入文件。

    Args:
        file_path: 文件路径。
        contents: 要写入的字节内容。
    """
    with open(file_path, "wb") as f:  # 以二进制写入模式打开
        f.write(contents)  # 写入内容


async def save_upload_file(
    file: UploadFile, task_id: str
) -> tuple[str, str]:
    """保存上传文件到磁盘。

    使用任务ID作为文件名，保留原始扩展名。
    文件大小限制为10MB。

    Args:
        file: FastAPI的上传文件对象。
        task_id: 任务ID（用作新文件名）。

    Returns:
        (文件绝对路径, 原始文件名) 的元组。

    Raises:
        ValueError: 文件大小超过10MB时抛出。
    """
    # 在线程池中读取文件内容（避免阻塞事件循环）
    contents = await asyncio.to_thread(_read_file_contents, file)
# 关键在于：*file.file.read() 本身就是一个同步阻塞调用*，你没办法让它变成"真正的异步"。
    # 检查文件大小
    if len(contents) > 10 * 1024 * 1024:  # 10MB = 10 * 1024 * 1024 字节
        raise ValueError("文件大小超过10MB限制")

    # 生成新文件名
    original_name = file.filename or "unknown"  # 原始文件名
    ext = original_name.rsplit(".", 1)[-1] if "." in original_name else ""  # 提取扩展名
    new_filename = f"{task_id}.{ext}" if ext else task_id  # 新文件名：任务ID.扩展名

    # 保存文件
    file_path = UPLOAD_DIR / new_filename  # 完整文件路径
    await asyncio.to_thread(_write_file, file_path, contents)  # 在线程池中写入

    return str(file_path.absolute()), original_name  # 返回绝对路径和原始文件名
