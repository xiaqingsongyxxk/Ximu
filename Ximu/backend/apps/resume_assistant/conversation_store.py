"""对话历史存储模块。

本模块提供简历助手的对话历史持久化功能：
使用JSONL文件格式存储对话消息，每个简历一个文件。
支持追加、读取、删除等操作。

存储位置：backend/.conversation_store/{resume_id}.jsonl
"""  # 模块文档字符串

import json  # 导入JSON模块
from pathlib import Path  # 导入路径操作类

from shared.types.messages import ConversationMessage  # 对话消息类型

# 对话存储的基础目录
_BASE_DIR = Path(__file__).parent.parent.parent / ".conversation_store"


class ConversationStore:
    """对话历史存储类。

    使用JSONL文件格式存储对话消息。
    每个简历对应一个文件：{resume_id}.jsonl
    每行一条消息，格式为JSON。
    """

    def __init__(self, base_dir: str | Path = _BASE_DIR):
        """初始化存储目录。

        Args:
            base_dir: 存储目录路径。
        """
        if isinstance(base_dir, str):  # 如果传入的是字符串路径
            self.base_dir = Path(base_dir)  # 转成Path对象，后续方便做路径拼接
        elif isinstance(base_dir, Path):  # 如果传入的已经是Path对象
            self.base_dir = Path(base_dir)  # 也转一下，确保类型一致
        else:  # 如果既不是字符串也不是Path
            raise ValueError(
                "base_dir必须是字符串或Path"
            )  # 抛出错误，告诉调用者参数类型不对

        self.base_dir.mkdir(parents=True, exist_ok=True)  # 创建目录

    def _get_cache_file(self, resume_id: str) -> Path:
        """获取简历的对话缓存文件路径。"""
        return self.base_dir / f"{resume_id}.jsonl"

    def exists(self, resume_id: str) -> bool:
        """检查对话历史是否存在。"""
        return self._get_cache_file(
            resume_id
        ).exists()  # 检查缓存文件是否存在，返回True或False

    def read(self, resume_id: str) -> list[ConversationMessage]:
        """读取对话历史。

        Args:
            resume_id: 简历ID。

        Returns:
            对话消息列表。
        """
        cache_file = self._get_cache_file(
            resume_id
        )  # 获取这个简历对应的对话缓存文件路径，后续用来读取历史消息
        if not cache_file.exists():  # 检查缓存文件是否存在
            return []  # 文件不存在说明没有历史对话，返回空列表，后续调用方会直接开始新对话
        messages = []  # 创建空列表，用来存放解析后的对话消息对象
        for line in cache_file.read_text(
            encoding="utf-8"
        ).splitlines():  # 读取文件内容，按行分割，逐行遍历
            if line.strip():  # 跳过空行（比如文件末尾的换行符）
                messages.append(
                    ConversationMessage.model_validate(json.loads(line))
                )  # 把每行JSON文本解析成字典，再验证成ConversationMessage对象，添加到列表中
        return messages  # 返回所有对话消息列表，后续用于恢复对话上下文

    def append(self, resume_id: str, message: ConversationMessage) -> None:
        """追加一条消息到对话历史。

        Args:
            resume_id: 简历ID。
            message: 要追加的消息。
        """
        cache_file = self._get_cache_file(
            resume_id
        )  # 获取这个简历对应的对话缓存文件路径
        line = json.dumps(
            message.model_dump(mode="json"), ensure_ascii=False
        )  # 把消息对象转成字典，再序列化成JSON字符串（ensure_ascii=False确保中文正常显示）
        with open(
            cache_file, "a", encoding="utf-8"
        ) as f:  # 以追加模式打开文件（不会清空原有内容）
            f.write(
                line + "\n"
            )  # 把JSON字符串写入文件末尾，加换行符保持每行一条消息的格式

    def extend(self, resume_id: str, messages: list[ConversationMessage]) -> None:
        """批量追加消息到对话历史。

        Args:
            resume_id: 简历ID。
            messages: 要追加的消息列表。
        """
        cache_file = self._get_cache_file(
            resume_id
        )  # 获取这个简历对应的对话缓存文件路径
        with open(
            cache_file, "a", encoding="utf-8"
        ) as f:  # 以追加模式打开文件（不会清空原有内容）
            for msg in messages:  # 遍历要追加的消息列表
                line = json.dumps(
                    msg.model_dump(mode="json"), ensure_ascii=False
                )  # 把消息对象转成JSON字符串
                f.write(line + "\n")  # 写入文件，每条消息占一行

    def write(self, resume_id: str, messages: list[ConversationMessage]) -> None:
        """覆盖写入对话历史。

        Args:
            resume_id: 简历ID。
            messages: 要写入的消息列表。
        """
        cache_file = self._get_cache_file(
            resume_id
        )  # 获取这个简历对应的对话缓存文件路径
        with open(
            cache_file, "w", encoding="utf-8"
        ) as f:  # 以写入模式打开文件（会清空原有内容，实现覆盖写入）
            for msg in messages:  # 遍历要写入的消息列表
                line = json.dumps(
                    msg.model_dump(mode="json"), ensure_ascii=False
                )  # 把消息对象转成JSON字符串
                f.write(line + "\n")  # 写入文件，每条消息占一行

    def delete(self, resume_id: str) -> None:
        """删除对话历史文件。

        Args:
            resume_id: 简历ID。
        """
        cache_file = self._get_cache_file(
            resume_id
        )  # 获取这个简历对应的对话缓存文件路径
        if cache_file.exists():  # 检查文件是否存在，避免删除不存在的文件报错
            cache_file.unlink()  # 删除文件，后续该简历的对话历史就不存在了
