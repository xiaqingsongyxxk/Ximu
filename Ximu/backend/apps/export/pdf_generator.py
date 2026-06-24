"""使用Playwright的PDF生成器模块。

本模块提供将HTML内容渲染为PDF的功能：
1. 启动无头Chromium浏览器
2. 加载HTML内容
3. 等待字体就绪（特别是中文字体）
4. 渲染为A4尺寸的PDF
5. 返回PDF字节内容

使用Playwright库控制Chromium浏览器。
"""  # 模块文档字符串

import asyncio  # 导入异步IO库
import contextlib  # 导入上下文管理工具（用于忽略异常）

from playwright.async_api import async_playwright  # 导入Playwright异步API

from apps.export.browser_manager import check_browser_ready  # 导入浏览器就绪检查函数


async def generate_pdf(html_content: str, timeout_ms: int = 30000) -> bytes:
    """将HTML内容渲染为PDF。

    启动无头Chromium浏览器，加载HTML，等待网络空闲和字体就绪，
    然后渲染为A4尺寸、零边距的PDF。

    Args:
        html_content: 要渲染的HTML内容。
        timeout_ms: 最大允许时间（毫秒）。超时会抛出asyncio.TimeoutError。

    Returns:
        PDF的字节内容。
    """
    check_browser_ready()  # 检查浏览器是否就绪
    coro = _generate_pdf_internal(html_content)  # 创建协程
    pdf_bytes = await asyncio.wait_for(coro, timeout=timeout_ms / 1000.0)  # 带超时执行
    return pdf_bytes


async def _generate_pdf_internal(html_content: str) -> bytes:
    """内部PDF生成函数。

    启动浏览器、加载HTML、渲染PDF、关闭浏览器。

    Args:
        html_content: HTML内容。

    Returns:
        PDF字节内容。
    """
    browser = None  # 浏览器实例
    page = None  # 页面实例
    try:
        async with async_playwright() as p:  # 启动Playwright
            browser = await p.chromium.launch(headless=True)  # 启动无头浏览器
            page = await browser.new_page()  # 创建新页面
            await page.set_viewport_size({"width": 794, "height": 1123})  # 设置视口为A4尺寸
            await page.set_content(html_content, wait_until="networkidle")  # 加载HTML，等待网络空闲
            await page.evaluate("document.fonts.ready")  # 等待字体加载完成
            await asyncio.sleep(0.2)  # 短暂延迟，确保CJK字体渲染完成
            pdf_bytes = await page.pdf(  # 生成PDF
                format="A4",  # A4纸张
                print_background=True,  # 打印背景色/图片
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},  # 零边距
            )
            return pdf_bytes
    finally:  # 无论成功失败都执行清理
        if page is not None:  # 如果页面已创建
            with contextlib.suppress(Exception):  # 忽略关闭异常
                await page.close()  # 关闭页面
        if browser is not None:  # 如果浏览器已创建
            with contextlib.suppress(Exception):  # 忽略关闭异常
                await browser.close()  # 关闭浏览器
