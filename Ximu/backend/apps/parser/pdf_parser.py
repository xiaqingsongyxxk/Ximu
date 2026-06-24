"""PDF文件解析模块。

本模块提供PDF文件的文本提取功能：
1. 打开PDF文件
2. 检查页数限制（最多100页）
3. 逐页提取文本内容
4. 合并为单个字符串返回

使用pymupdf库（fitz）处理PDF文件。
"""  # 模块文档字符串

import pymupdf  # 导入pymupdf库（也叫fitz），用于PDF文件处理

from shared.exceptions.base import (
    ParseError,
)  # 从shared/exceptions/base.py导入自定义解析异常


class PDFParser:
    """PDF文档解析器类。"""

    @property  # 将方法转为属性（可以像属性一样访问：pdf_parser.name）
    def name(self) -> str:
        """解析器名称标识。"""
        return "pdf"  # 返回解析器类型

    async def parse(self, file_path: str) -> dict:
        """解析PDF文件并提取文本内容。

        Args:
            file_path: PDF文件的绝对路径。

        Returns:
            包含页数和提取文本的字典：{"pages": int, "text": str}。

        Raises:
            ParseError: 解析失败或违反约束时抛出。
        """
        try:
            with pymupdf.open(file_path) as doc:  # 打开PDF文件
                if doc.page_count > 100:  # 检查页数限制
                    raise ParseError(
                        f"PDF页数过多（{doc.page_count}页），最大支持100页"
                    )

                text_parts = []  # 存储每页的文本
                for page in doc:  # 遍历每一页
                    text_parts.append(page.get_text())  # 提取当前页文本

                return {  # 返回结果
                    "pages": doc.page_count,  # 总页数
                    "text": "\n".join(text_parts),  # 所有页的文本用换行符连接
                }
        except ParseError:  # 如果是自定义解析错误
            raise  # 直接抛出
        except Exception as e:  # 其他异常
            raise ParseError(f"PDF解析失败: {str(e)}")  # 包装为ParseError


# 创建全局解析器实例
pdf_parser = PDFParser()  # 其他模块通过 import pdf_parser 使用
