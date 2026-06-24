"""LLM对话消息的Pydantic模型定义模块。

本模块定义了与LLM对话时使用的消息结构：
1. TextBlock - 文本内容块
2. ToolUseBlock - 工具调用块
3. ToolResultBlock - 工具结果块
4. ConversationMessage - 对话消息
5. ConversationMessageSchema - 对话消息的数据库schema

这些模型用于构建发送给LLM的消息，以及解析LLM的响应。
"""  # 模块文档字符串

from __future__ import annotations  # 支持延迟注解求值

from datetime import datetime  # 导入日期时间类型
from typing import Annotated, Any, Literal  # 导入类型注解工具
from uuid import uuid4  # 导入UUID生成函数

from pydantic import (  # 导入Pydantic组件
    BaseModel,
    ConfigDict,
    Field,
    alias_generators,
)


class TextBlock(BaseModel):
    """文本内容块。

    表示消息中的纯文本内容。
    """
    type: Literal["text"] = "text"  # 类型标识
    text: str  # 文本内容


class ToolUseBlock(BaseModel):
    """工具调用块。

    表示AI请求调用某个工具。
    """
    type: Literal["tool_use"] = "tool_use"  # 类型标识
    id: str = Field(default_factory=lambda: f"toolu_{uuid4().hex}")  # 唯一ID
    name: str  # 工具名称
    input: dict[str, Any] = Field(default_factory=dict)  # 工具输入参数


class ToolResultBlock(BaseModel):
    """工具结果块。

    表示工具执行的结果。
    """
    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,  # camelCase别名
        populate_by_name=True,
    )

    type: Literal["tool_result"] = "tool_result"  # 类型标识
    tool_use_id: str  # 对应的工具调用ID
    content: str  # 结果内容
    is_error: bool = False  # 是否出错


# 内容块联合类型（通过type字段区分）
ContentBlock = Annotated[
    TextBlock | ToolUseBlock | ToolResultBlock,
    Field(discriminator="type"),
]


class ConversationMessageSchema(BaseModel):
    """对话消息的数据库schema。

    用于API请求和响应，对应数据库中的conversation_messages表。
    """
    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    id: int = Field(description="消息唯一标识")
    conversation_id: str = Field(description="所属会话ID")
    role: Literal["user", "assistant"] = Field(description="消息角色")
    content: list[ContentBlock] = Field(default_factory=list, description="消息内容块列表")
    reasoning: str | None = Field(default=None, description="AI思考过程（可选）")
    created_at: datetime | None = Field(default=None, description="创建时间")


class ConversationMessage(BaseModel):
    """对话消息类。

    表示一条用户或助手的消息，包含多个内容块。
    """
    role: Literal["user", "assistant"]  # 消息角色
    content: list[ContentBlock] = Field(default_factory=list)  # 内容块列表

    @classmethod
    def from_user_text(cls, text: str) -> ConversationMessage:
        """从纯文本创建用户消息。"""
        return cls(role="user", content=[TextBlock(text=text)])

    @property
    def text(self) -> str:
        """返回所有文本块的拼接内容。"""
        return "".join(block.text for block in self.content if isinstance(block, TextBlock))

    @property
    def tool_uses(self) -> list[ToolUseBlock]:
        """返回消息中的所有工具调用块。"""
        return [block for block in self.content if isinstance(block, ToolUseBlock)]

    def to_api_param(self) -> dict[str, Any]:
        """将消息转换为API参数格式（Anthropic/OpenAI SDK需要dict格式）。"""
        return {
            "role": self.role,
            "content": [serialize_content_block(block) for block in self.content],
        }


def serialize_content_block(block: ContentBlock) -> dict[str, Any]:
    """将内容块序列化为API兼容的字典格式。"""
    if isinstance(block, TextBlock):
        return {"type": "text", "text": block.text}

    if isinstance(block, ToolUseBlock):
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
        }

    return {
        "type": "tool_result",
        "tool_use_id": block.tool_use_id,
        "content": block.content,
        "is_error": block.is_error,
    }


def assistant_message_from_api(raw_message: Any) -> ConversationMessage:
    """将API返回的消息对象转换为ConversationMessage。

    解析Anthropic/OpenAI SDK返回的消息，转换为内部格式。
    """
    content: list[ContentBlock] = []
    reasoning: str | None = None

    for raw_block in getattr(raw_message, "content", []):
        block_type = getattr(raw_block, "type", None)
        if block_type == "text":
            content.append(TextBlock(text=getattr(raw_block, "text", "")))
        elif block_type == "tool_use":
#             tool_use 这个字段名是 Anthropic API 团队选的，不是模型起的。模型输出的是原始 token 流，API 层解析这些 token、赋予结构、取名字、包装成 JSON 再返回给你。
# 就像 OpenAI API 选了 tool_calls、function.arguments 这些名字一样——都是 API 层的协议设计。
            content.append(
                ToolUseBlock(
                    id=getattr(raw_block, "id", f"toolu_{uuid4().hex}"),
                    name=getattr(raw_block, "name", ""),
                    input=dict(getattr(raw_block, "input", {}) or {}),
                )
            )
        elif block_type == "thinking":
            reasoning = getattr(raw_block, "thinking", None)

    conversation_message = ConversationMessage(role="assistant", content=content)
    if reasoning is not None:
        conversation_message._reasoning = reasoning  # 存储思考过程
    return conversation_message
# 具体看 tool_use 这个名字从哪来的
# 模型内部（简化）                          API 层
# ─────────────                          ──────
# 模型输出一串 token：                     
# "<tool_use_name>update_section         见到 <tool_use_name> →
# </tool_use_name>                       知道这是个工具调用开始
# <tool_use_input>                       取出 update_section 作为 name
# {\"id\": 1}                            解析 {"id":1} 作为 input
# </tool_use_input>"                     包装成：
#                                        {
#                                          type: "tool_use",         ← API 层选的名字
#                                          name: "update_section",
#                                          input: {"id": 1}
#                                        }