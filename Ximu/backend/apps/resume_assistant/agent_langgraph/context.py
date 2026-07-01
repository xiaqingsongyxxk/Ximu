# Agent 运行时配置模块（LangGraph 版）。

# 对应手写版: agent/context.py (QueryContext)

# 手写版 QueryContext 打包所有依赖，LangGraph 版 AgentConfig 同样如此。
# 但 LangGraph 版用 LangChain 的模型类替代了手写的 SupportsStreamingMessages 协议。


# 导入 dataclass 装饰器和 field 函数
# dataclass 自动生成 __init__，field 提供字段默认值的灵活配置
from dataclasses import dataclass, field  # 导入数据类工具（自动生成构造函数等样板代码）

# Any 类型：任意类型，用于 metadata 这种不确定类型的字段
from typing import Any  # 导入 Any 类型（用于 metadata 这种不限定类型的字段）

# ChatAnthropic：LangChain 封装的 Anthropic（Claude）客户端
# 手写版用的是自定义 SupportsStreamingMessages 协议调用 API
# LangGraph 版用 LangChain 的 ChatAnthropic 包装类
from langchain_anthropic import (
    ChatAnthropic,
)  # 导入 LangChain 的 Claude 客户端（LangGraph 版用）

# BaseChatModel：所有 LangChain 聊天模型的基类
# 用来定义 llm 字段的类型：支持 ChatAnthropic 和 ChatOpenAI 等多种实现
from langchain_core.language_models.chat_models import (
    BaseChatModel,
)  # 导入 LangChain 聊天模型基类（用于类型标注）

# ChatOpenAI：LangChain 封装的 OpenAI 客户端
from langchain_openai import (
    ChatOpenAI,
)  # 导入 LangChain 的 OpenAI 客户端（LangGraph 版用）


# @dataclass 装饰器：自动为 AgentConfig 生成 __init__, __repr__, __eq__ 等方法
# 手写版 QueryContext 是手动定义的类，这里用 dataclass 减少样板代码
@dataclass  # 自动生成构造函数、字符串表示等方法的装饰器
class AgentConfig:  # Agent 运行时配置类（对应手写版 QueryContext）
    # Agent 运行时配置。

    # 对应手写版: QueryContext

    # 对比：
    # ────────────────────────────────────────────────
    # QueryContext                  AgentConfig
    # ────────────────────────────────────────────────
    # api_client                    llm (BaseChatModel 实例)
    # tool_registry                 不需要（@tool 自动注册）
    # model                         model
    # max_tokens                    max_tokens
    # temperature                   temperature
    # max_iterations                max_iterations
    # stop_reasons                  stop_reasons
    # metadata                      metadata
    # ────────────────────────────────────────────────

    # llm: LangChain 的 LLM 实例
    # 由外部创建好后传进来（可以是 ChatAnthropic 或 ChatOpenAI）
    # 手写版用的是自建的 api_client，LangGraph 版直接用 LangChain 的模型对象
    llm: BaseChatModel | None = None  # LangChain LLM 实例（外部传入，不传就自动创建）

    # 模型配置（当 llm 字段为 None 时，由 build_llm 方法自动创建）
    provider: str = "anthropic"  # 模型提供商：anthropic（Claude）或 openai
    model: str = "claude-sonnet-4-20250514"  # 模型名称
    api_key: str | None = None  # API 密钥（从环境变量读取，一般不传）
    base_url: str | None = None  # 自定义 API 地址（用于代理或私有部署）
    max_tokens: int | None = None  # 最大输出 token 数
    temperature: float = 1.0  # 温度参数（越高回答越有创意，越低越保守）

    # Agent 循环控制
    max_iterations: int = 30  # 最多迭代 30 轮（防止无限循环）
    # 停止原因集合：当 LLM 返回的 stop_reason 属于这个集合时，认为本轮对话结束
    # 手写版 self.context.stop_reasons 也是同样的 set 结构
    stop_reasons: set[str] = field(
        default_factory=lambda: {"end_turn", "stop"}
    )  # 停止原因集合（遇到这些原因就结束本轮）

    # 元数据字典：存放额外的上下文信息（比如会话 ID、用户 ID）
    # 手写版 QueryContext.metadata 也是类似的字典
    metadata: dict[str, Any] = field(  # 元数据字典（存放会话 ID 等额外信息）
        # 使用 default_factory 而不是直接 default={}，避免所有实例共享同一个字典
        default_factory=dict  # 默认是一个空字典（用 factory 避免实例间共享）
    )

    def build_llm(self) -> BaseChatModel:  # 创建 LLM 实例（对应手写版 get_client()）
        # 创建 LLM 实例。

        # 对应手写版 get_client() + to_api_schema_v2()。

        # 手写版：
        # client = get_client(type, api_key, base_url)
        # tools_schema = tool_registry.to_api_schema_v2(sections)

        # LangGraph 版：
        # llm = ChatAnthropic(...)  # 或 ChatOpenAI(...)
        # llm.bind_tools(tools)     # 自动生成 schema

        # 如果外部已经传入了 llm 实例，直接用
        # 这允许调用方创建带有特定配置的 llm（比如设了 max_tokens 或 temperature）
        if self.llm is not None:  # 如果外部传入了 llm 实例
            # 直接返回传入的 llm，不做任何修改
            # 调用方完全控制 LLM 的配置
            return self.llm  # 直接用外部的 LLM（调用方自行控制配置）

        # 准备传递给 LLM 构造函数的参数
        # 手写版 get_client() 也是类似的方式拼接参数字典
        kwargs: dict[str, Any] = {  # 准备传给 LLM 构造函数的参数字典
            "model": self.model,  # 模型名称，必传参数
            "temperature": self.temperature,  # 温度参数
            "max_tokens": self.max_tokens,  # 最大输出 token 数
            "api_key": self.api_key,  # API 密钥（可选）
            "base_url": self.base_url,  # 自定义 API 地址（可选）
        }
        # 以下三个 if 都是可选参数，用户传了才加入
        if self.api_key:  # 如果配置了 API 密钥
            # 将 API 密钥加入参数字典（用于私有部署或切换账号）
            kwargs["api_key"] = self.api_key  # 把 API 密钥加入参数字典
        if self.base_url:  # 如果配置了自定义 API 地址
            # 将自定义 API 地址加入参数字典（用于代理或兼容接口）
            kwargs["base_url"] = self.base_url  # 把自定义地址加入参数字典
        if self.max_tokens:  # 如果配置了最大 token 数
            # 将最大 token 数限制加入参数字典
            kwargs["max_tokens"] = self.max_tokens  # 把最大 token 数加入参数字典

        # 根据 provider 选择创建 Anthropic 还是 OpenAI 的 LLM 实例
        # 手写版这里是用 get_client() 函数返回 SupportsStreamingMessages 实现
        if self.provider == "anthropic":  # 如果用 Claude
            return ChatAnthropic(**kwargs)  # 创建 Claude 客户端
        # 如果 provider 不是 anthropic，默认用 OpenAI（包括 gpt 兼容接口）
        return ChatOpenAI(**kwargs)  # 创建 GPT 客户端
