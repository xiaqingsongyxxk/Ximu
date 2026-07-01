# 对话历史持久化模块（LangGraph 版）。

# 对应手写版: conversation_store.py

# 与手写版 ConversationStore 接口完全一致：
# - read(resume_id) → list[ConversationMessage]
# - append(resume_id, message)
# - extend(resume_id, messages)
# - write(resume_id, messages)
# - delete(resume_id)
# - exists(resume_id) → bool

# 内部存储格式不变（JSONL），同时支持 LangGraph 的 checkpointer。


import json  # 导入 json 模块，把消息对象转成 JSON 字符串存入文件
from pathlib import Path  # 导入 Path 类，跨平台地操作文件路径

from shared.types.messages import (
    ConversationMessage,
)  # 导入消息类型（手写版定义，LangGraph 版复用）

# _BASE_DIR：对话历史文件的存储目录
# 放在 .conversation_store 文件夹下，每个 resume（简历）一个 .jsonl 文件
# Path(__file__).parent.parent.parent 是往上级跳三级找到项目根目录
_BASE_DIR = (
    Path(__file__).parent.parent.parent / ".conversation_store"
)  # 对话历史 JSONL 文件的存储根目录


class ConversationStore:  # 对话历史存储类（与手写版接口完全一致）
    # 对话历史存储类（LangGraph 版）。

    # 与手写版 ConversationStore 完全相同的接口。

    def __init__(
        self, base_dir: str | Path = _BASE_DIR
    ):  # 初始化对话存储：指定数据文件存放的目录
        # 创建对话历史存储实例。
        if isinstance(base_dir, str):  # 如果传进来的是字符串路径
            self.base_dir = Path(base_dir)  # 把字符串转成 Path 对象
        elif isinstance(base_dir, Path):  # 如果传进来的已经是 Path 对象
            self.base_dir = Path(base_dir)  # 也转成 Path 对象（确保是 Path 类型）
        else:  # 传了不合法参数
            raise ValueError("base_dir 必须是字符串或 Path")  # 直接报错

        # 确保存储目录存在，如果不存在就自动创建
        self.base_dir.mkdir(
            parents=True, exist_ok=True
        )  # 创建目录（如果已存在也不报错）

    def _get_cache_file(
        self, resume_id: str
    ) -> Path:  # 根据简历 ID 获取对应的 JSONL 文件路径
        # 返回该简历的缓存文件路径。
        return (
            self.base_dir / f"{resume_id}.jsonl"
        )  # 拼接成 /path/to/.conversation_store/{resume_id}.jsonl

    def exists(self, resume_id: str) -> bool:  # 检查指定简历是否有缓存的历史对话
        # 判断该简历是否有缓存的历史对话。
        return self._get_cache_file(resume_id).exists()  # 检查对应的 JSONL 文件是否存在

    def read(
        self, resume_id: str
    ) -> list[ConversationMessage]:  # 从 JSONL 文件读取历史对话
        # 读取该简历的历史对话。
        # 返回值用于：
        # - 传给 AgentRuntime.execute()，让 AI 看到历史对话上下文
        # - 手写版和 LangGraph 版都从同一个地方读，保证体验一致
        cache_file = self._get_cache_file(resume_id)  # 获取该简历对应的 JSONL 文件路径

        if not cache_file.exists():  # 如果文件还不存在（第一次对话）
            return []  # 返回空列表，没有历史消息

        messages = []  # 创建一个空列表，用来装读出来的消息

        for line in cache_file.read_text(
            encoding="utf-8"
        ).splitlines():  # 逐行读取 JSONL 文件
            # 跳过空行
            if line.strip():  # 如果这一行不是空白
                # 从 JSON 字符串还原成 ConversationMessage 对象
                messages.append(  # 把反序列化的消息对象追加到列表
                    ConversationMessage.model_validate(
                        json.loads(line)
                    )  # 先用 json.loads 解析 JSON，再用 Pydantic 验证
                )  # 最终得到 ConversationMessage 对象

        return messages  # 返回读到的所有历史消息

    def append(
        self, resume_id: str, message: ConversationMessage
    ) -> None:  # 追加单条消息到 JSONL 文件
        # 追加一条消息到该简历的缓存文件。
        self.extend(resume_id, [message])  # 复用 extend 方法，批量追加一条消息

    def extend(
        self, resume_id: str, messages: list[ConversationMessage]
    ) -> None:  # 批量追加消息
        # 批量追加消息到该简历的缓存文件。
        # runtime 在 finaly 块中调用，把本轮迭代中所有待持久化的消息一次写入。
        cache_file = self._get_cache_file(resume_id)  # 获取该简历对应的 JSONL 文件路径

        with open(cache_file, "a", encoding="utf-8") as f:  # 以追加模式打开文件
            for msg in messages:  # 遍历每一条要存的消息
                # 把消息对象转成 JSON 字符串，ensure_ascii=False 保留中文
                line = json.dumps(
                    msg.model_dump(mode="json"), ensure_ascii=False
                )  # 消息 → JSON 字符串
                f.write(line + "\n")  # 写入一行（JSONL 格式：每行一条 JSON）

    def write(
        self, resume_id: str, messages: list[ConversationMessage]
    ) -> None:  # 覆盖写入整批消息
        # 覆盖写入该简历的缓存文件。
        self._write(resume_id, messages)  # 调用内部写方法

    def _write(
        self, resume_id: str, messages: list[ConversationMessage]
    ) -> None:  # 内部写方法：先清空再写入
        # 实际的写入实现。
        cache_file = self._get_cache_file(resume_id)  # 获取该简历对应的 JSONL 文件路径
        with open(cache_file, "w", encoding="utf-8") as f:  # 以写入（覆盖）模式打开
            for msg in messages:  # 遍历所有要存的消息
                line = json.dumps(
                    msg.model_dump(mode="json"), ensure_ascii=False
                )  # 消息对象 → JSON 字符串
                f.write(line + "\n")  # 写入一行

    def delete(self, resume_id: str) -> None:  # 删除指定简历的缓存文件
        # 删除该简历的缓存文件。
        # 当用户删除简历时调用。
        cache_file = self._get_cache_file(resume_id)  # 获取该简历对应的 JSONL 文件路径

        if cache_file.exists():  # 如果文件存在
            cache_file.unlink()  # 删除文件
