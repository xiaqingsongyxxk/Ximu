"""Playwright浏览器管理模块。

本模块负责管理Playwright Chromium浏览器的安装和状态：
1. 检查浏览器是否已安装
2. 后台自动安装浏览器（首次启动时）
3. 提供浏览器就绪检查（PDF生成前调用）

浏览器安装是异步的，不会阻塞应用启动。
"""  # 模块文档字符串

import asyncio  # 导入异步IO库
import logging  # 导入日志库

from fastapi import HTTPException  # 导入HTTP异常
from playwright.async_api import async_playwright  # 导入Playwright异步API

log = logging.getLogger(__name__)  # 创建日志记录器

_browser_ready = asyncio.Event()  # 浏览器就绪事件（用于通知其他协程）
_install_lock = asyncio.Lock()  # 安装锁（防止并发安装）


async def is_browser_installed() -> bool:
    """检查Chromium是否已安装。

    Returns:
        True如果Playwright能找到Chromium可执行路径，否则False。
    """
    try:
        async with async_playwright() as p:  # 启动Playwright
            return p.chromium.executable_path is not None  # 检查可执行路径
    except Exception:
        return False  # 异常时返回False


async def ensure_browser() -> None:
    """确保Chromium可用，如果需要则在后台安装。

    此函数是幂等的：重复调用不会触发多次安装。
    安装完成后，内部Event会被设置，允许check_browser_ready()通过。
    """
    async with _install_lock:  # 获取安装锁
        if _browser_ready.is_set():  # 如果已就绪
            return  # 直接返回

        if await is_browser_installed():  # 如果已安装
            _browser_ready.set()  # 设置就绪事件
            log.info("Chromium已安装")
            return

        log.info("Chromium未找到，开始后台安装...")
        proc = await asyncio.create_subprocess_exec(  # 创建子进程
            "python", "-m", "playwright", "install", "chromium",  # 安装命令
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()  # 等待安装完成

        if proc.returncode == 0:  # 安装成功
            log.info("Chromium安装成功")
            _browser_ready.set()  # 设置就绪事件
        else:  # 安装失败
            err_msg = stderr.decode().strip() or stdout.decode().strip() or "未知错误"
            log.error("Chromium安装失败: %s", err_msg)


def check_browser_ready() -> None:
    """检查浏览器是否就绪，未就绪则抛出503异常。

    在PDF生成前调用此函数，确保浏览器可用。

    Raises:
        HTTPException: 浏览器未就绪时抛出503。
    """
    if not _browser_ready.is_set():  # 如果未就绪
        raise HTTPException(
            status_code=503,  # 服务不可用
            detail="PDF服务初始化中，浏览器内核尚未就绪，请稍后重试",
        )
