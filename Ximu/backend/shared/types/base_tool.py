"""工具执行的基础类型和注册表模块。

本模块定义了AI Agent工具系统的核心类型：
1. ToolExecutionContext - 工具执行上下文
2. ToolResult - 工具执行结果
3. BaseTool - 工具抽象基类
4. ToolRegistry - 工具注册表

所有具体工具（如UpdateSectionTool、AddSectionTool）都应继承BaseTool。
"""  # 模块文档字符串

from __future__ import annotations  # 支持延迟注解求值

from abc import ABC, abstractmethod  # 抽象基类和抽象方法装饰器
from dataclasses import dataclass, field  # 数据类装饰器
from typing import Any  # 任意类型

from pydantic import BaseModel  # Pydantic基类


@dataclass
class ToolExecutionContext:
    """工具执行上下文。

    包含工具执行时需要的额外信息（如板块列表、元数据）。
    """
    sections: list[dict[str, Any]]  # 板块列表（工具的输入/输出数据）
    metadata: dict[str, Any] = field(default_factory=dict)  # 额外元数据


@dataclass(frozen=True)  # frozen=True：实例不可变
class ToolResult:
    """工具执行结果。

    标准化的工具执行结果，包含输出内容和状态。
    """
    output: str  # 工具的文本输出
    is_error: bool = False  # 是否出错
    metadata: dict[str, Any] = field(default_factory=dict)  # 额外信息


class BaseTool(ABC):
    """工具抽象基类。

    所有具体工具都应继承此类，并实现execute方法。
    """
    name: str  # 工具名称
    description: str  # 工具描述
    input_model: type[BaseModel]  # 输入数据的Pydantic模型类

    @abstractmethod
    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        """执行工具（抽象方法，子类必须实现）。

        Args:
            arguments: 工具输入数据（Pydantic模型实例）。
            context: 执行上下文。

        Returns:
            工具执行结果。
        """
        ...

    def is_read_only(self, arguments: BaseModel) -> bool:
        """返回操作是否为只读（默认返回False，表示会修改状态）。"""
        return False

    def to_api_schema(self) -> dict[str, Any]:
        """返回API格式的工具定义（用于Anthropic/OpenAI SDK）。"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
        }

    def to_api_schema_v2(self, sections: list[dict[str, Any]]) -> dict[str, Any]:
        """返回API v2格式的工具定义（可覆盖以提供更丰富的schema）。"""
        return self.to_api_schema()


class ToolRegistry:
    """工具注册表。

    管理所有可用工具的注册和查找。
    """
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}  # 工具名到工具实例的映射

    def register(self, tool: BaseTool) -> None:
        """注册工具实例。"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """根据名称获取工具。"""
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """返回所有已注册的工具。"""
        return list(self._tools.values())

    def to_api_schema(self) -> list[dict[str, Any]]:
        """返回所有工具的API格式定义。"""
        return [tool.to_api_schema() for tool in self._tools.values()]

    def to_api_schema_v2(self, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """返回所有工具的API v2格式定义。"""
        return [tool.to_api_schema_v2(sections) for tool in self._tools.values()]
