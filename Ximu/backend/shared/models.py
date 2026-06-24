"""Chiren 后端共享的 ORM 模型模块。

本模块定义了 SQLAlchemy ORM 模型及相关混入类（Mixin），
用于持久化简历、简历板块、对话消息、模板、用户配置、
职位描述分析等所有数据库表。
"""  # 模块级文档字符串，说明本模块定义了所有数据库表的映射模型

from __future__ import (
    annotations,
)  # 导入未来注解特性，允许在类型注解中使用 Python 3.10+ 的语法（如 str | None）

import json  # 导入JSON模块，用于将Python字典转换为JSON字符串（存入数据库）和反向转换
import uuid  # 导入UUID模块，用于生成全局唯一标识符（如简历ID、板块ID）
from datetime import (
    datetime,
    timedelta,
    timezone,
)  # 导入日期时间类：datetime用于时间戳，timedelta用于时间差，timezone用于时区
from typing import (
    Any,
    TypeVar,
)  # 导入类型注解工具：Any表示任意类型，TypeVar用于定义泛型变量

# 定义上海时区（UTC+8），因为项目面向中国用户
SHANGHAI_TZ = timezone(
    timedelta(hours=8)
)  # 创建UTC+8时区对象，timedelta(hours=8)表示比UTC快8小时
utc_now = lambda: datetime.now(
    SHANGHAI_TZ
)  # 定义获取当前上海时间的lambda函数，所有时间戳都用这个获取

from pydantic import BaseModel  # 从Pydantic导入BaseModel，所有数据验证模型的基类
from sqlalchemy import (  # 从SQLAlchemy导入各种列类型，用于定义数据库表的字段类型
    JSON,  # JSON类型列，存储JSON格式数据（SQLite中实际存为文本）
    Boolean,  # 布尔类型列，存储True/False
    DateTime,  # 日期时间类型列，存储时间戳
    ForeignKey,  # 外键约束，定义表与表之间的关联关系
    Integer,  # 整数类型列
    String,  # 字符串类型列，需要指定最大长度
    Text,  # 文本类型列，不限长度（适合存储长文本如JSON字符串）
)
from sqlalchemy.orm import (  # 从SQLAlchemy ORM模块导入映射相关工具
    DeclarativeBase,  # 声明式基类，所有ORM模型都要继承它
    Mapped,  # 映射类型注解，声明Python属性对应数据库列
    mapped_column,  # 映射列函数，定义列的具体类型和约束
    relationship,  # 关系函数，定义表与表之间的关联关系（一对多、一对一等）
)

from shared.types.jd_analysis import (  # 从shared/types/jd_analysis.py导入职位分析相关类型
    JobDescriptionAnalysisSchema,  # 职位分析数据的Pydantic模型，用于API请求/响应的数据验证
    SuggestionItem,  # 建议条目的Pydantic模型，表示一条优化建议
)
from shared.types.messages import (
    ConversationMessageSchema,
)  # 从shared/types/messages.py导入对话消息的Pydantic模型
from shared.types.resume import (  # 从shared/types/resume.py导入简历相关类型
    ResumeSchema,  # 简历数据的Pydantic模型
    ResumeSectionSchema,  # 简历板块数据的Pydantic模型（联合类型，包含11种板块）
    section_adapter,  # 板块类型验证适配器，用于将字典数据转换为具体的板块类型
)

S = TypeVar(
    "S", bound=BaseModel
)  # 定义泛型类型变量S，限定必须是BaseModel的子类，用于Mixin类的类型注解


class PydanticMixin[S: BaseModel]:
    """ORM模型与Pydantic schema之间的转换混入类。

    所有需要与Pydantic模型互转的ORM模型都应该继承此类，
    并实现 to_pydantic 和 from_pydantic 方法。
    这样可以在数据库对象（ORM）和API数据对象（Pydantic）之间轻松转换。
    """  # 文档字符串，说明这是一个用于ORM和Pydantic互转的混入类

    def to_pydantic(self) -> S:  # 定义将ORM实例转换为Pydantic对象的方法
        """将当前ORM实例转换为对应的Pydantic schema对象。

        子类必须实现此方法，将数据库记录转换为API响应格式。
        """  # 文档字符串
        raise NotImplementedError  # 抛出未实现异常，提醒子类必须实现这个方法

    @classmethod  # 类方法装饰器，可以通过类名直接调用，不需要实例化
    def from_pydantic(
        cls, schema: S
    ) -> PydanticMixin[S]:  # 定义从Pydantic对象创建ORM实例的方法
        """从Pydantic schema创建ORM实例。

        子类必须实现此方法，将API请求数据转换为数据库记录。
        """  # 文档字符串
        raise NotImplementedError  # 抛出未实现异常，提醒子类必须实现这个方法


class Base(DeclarativeBase):  # 定义所有ORM模型的基类，继承SQLAlchemy的DeclarativeBase
    __abstract__ = True  # 标记为抽象类，不会在数据库中创建对应的表


class Resume(
    PydanticMixin, Base
):  # 定义简历模型，继承PydanticMixin（可转换为Pydantic）和Base（ORM基类）
    """简历数据库模型。

    对应数据库中的 resumes 表，存储简历的基本信息。
    支持"工作区-子简历"结构：workspace_id为NULL的是主简历（工作区），
    workspace_id指向主简历ID的是子简历。
    """  # 文档字符串，说明简历模型的数据结构和业务逻辑

    __tablename__ = "resumes"  # 指定数据库表名为 "resumes"

    id: Mapped[str] = mapped_column(  # 定义主键字段 id
        String(
            36
        ),  # 字符串类型，最大36字符（UUID格式如 "550e8400-e29b-41d4-a716-446655440000"）
        primary_key=True,  # 设为主键，每条记录唯一标识
        default=lambda: str(uuid.uuid4()),  # 默认值：自动生成UUID字符串
        comment="简历唯一标识，主键",  # 数据库列注释
    )
    workspace_id: Mapped[str | None] = mapped_column(  # 定义所属工作区ID（外键）
        String(36),  # 字符串类型，最大36字符
        ForeignKey(
            "resumes.id"
        ),  # 外键关联到resumes表的id字段（自关联，简历指向其父简历）
        nullable=True,  # 允许为空（主简历的workspace_id为NULL）
        index=True,  # 创建索引，加速按workspace_id查询子简历
        comment="所属 Workspace（主简历）的 ID，为空表示本身就是主简历",  # 数据库列注释
    )
    title: Mapped[str] = mapped_column(  # 定义简历标题字段
        String(100),  # 字符串类型，最大100字符
        nullable=False,  # 不允许为空
        default="未命名简历",  # 默认值
        comment="简历标题",  # 数据库列注释
    )
    template: Mapped[str] = mapped_column(  # 定义模板名称字段
        String(50),  # 字符串类型，最大50字符
        nullable=False,  # 不允许为空
        default="two-column",  # 默认使用双栏模板
        comment="使用的模板名称，对应前端模板组件",  # 数据库列注释
    )
    theme_config: Mapped[str] = mapped_column(  # 定义主题配置字段（JSON字符串）
        Text,  # 文本类型（因为JSON字符串可能很长）
        nullable=False,  # 不允许为空
        default="{}",  # 默认空JSON对象
        comment="主题配置，存储为JSON字符串（如颜色、字体等设置）",  # 数据库列注释
    )
    is_default: Mapped[bool] = mapped_column(  # 定义是否为默认简历字段
        Boolean,  # 布尔类型
        nullable=False,  # 不允许为空
        default=False,  # 默认不是默认简历
        comment="是否为用户的默认简历",  # 数据库列注释
    )
    language: Mapped[str] = mapped_column(  # 定义简历语言字段
        String(10),  # 字符串类型，最大10字符
        nullable=False,  # 不允许为空
        default="zh",  # 默认中文
        comment="简历语言（zh=中文, en=英文等）",  # 数据库列注释
    )
    share_token: Mapped[str | None] = mapped_column(  # 定义分享链接令牌字段
        String(64),  # 字符串类型，最大64字符
        nullable=True,  # 允许为空（未开启分享时为空）
        unique=True,  # 唯一约束，每个分享令牌只能对应一份简历
        comment="分享链接Token，为空表示未开启分享功能",  # 数据库列注释
    )
    is_public: Mapped[bool] = mapped_column(  # 定义是否公开字段
        Boolean,  # 布尔类型
        nullable=False,  # 不允许为空
        default=False,  # 默认不公开
        comment="是否公开简历（公开后可通过链接访问）",  # 数据库列注释
    )
    share_password: Mapped[str | None] = mapped_column(  # 定义分享密码字段
        String(128),  # 字符串类型，最大128字符
        nullable=True,  # 允许为空（无密码保护时为空）
        comment="分享密码（可选），为空表示无密码保护",  # 数据库列注释
    )
    view_count: Mapped[int] = mapped_column(  # 定义浏览次数字段
        Integer,  # 整数类型
        nullable=False,  # 不允许为空
        default=0,  # 默认0次
        comment="公开/分享页面的浏览次数",  # 数据库列注释
    )
    created_at: Mapped[datetime] = mapped_column(  # 定义创建时间字段
        DateTime(timezone=True),  # 带时区的日期时间类型
        nullable=False,  # 不允许为空
        default=utc_now,  # 默认值：创建时自动设置为当前上海时间
        comment="记录创建时间",  # 数据库列注释
    )
    updated_at: Mapped[datetime] = mapped_column(  # 定义更新时间字段
        DateTime(timezone=True),  # 带时区的日期时间类型
        nullable=False,  # 不允许为空
        default=utc_now,  # 创建时默认为当前时间
        onupdate=utc_now,  # 每次更新记录时自动设置为当前时间
        comment="最后更新时间（自动更新）",  # 数据库列注释
    )
    meta_info: Mapped[dict[str, Any] | None] = mapped_column(  # 定义元数据字段
        JSON,  # JSON类型（SQLAlchemy自动处理序列化/反序列化）
        nullable=True,  # 允许为空
        default=None,  # 默认无元数据
        comment="子简历元数据，包含目标职位描述(JD)、职位名称等",  # 数据库列注释
    )

    # ===== 以下是表与表之间的关系定义（不创建数据库列，只用于Python代码中方便地访问关联数据） =====
# # 场景：新建一个子简历，想挂到父简历下
# child = Resume(title="针对腾讯的简历")
# parent = db.get(Resume, 'A')
# # 方式一：设外键
# child.workspace_id = 'A'
# # 方式二（有 back_populates 时可用）：
# parent.versions.append(child)
# # 效果等价于 child.workspace_id = 'A'，且 child.workspace 也自动指向 parent
# 有 back_populates 时：
# parent.versions.append(child)
# # SQLAlchemy 自动执行：
# #   1. child.workspace_id = parent.id
# #   2. child.workspace = parent  （内存中同步）
# 没有 back_populates 时：
# parent.versions.append(child)
# # 只做了 1：child.workspace_id = parent.id
# # child.workspace 还是 None（内存中没同步）
# # 但数据库层面效果一样，因为 workspace_id 确实设上了
# 所以 back_populates 只影响内存中的对象状态，不影响数据库行为。业务代码里从来没人通过 .workspace 访问父简历，所以同步到 child.workspace 没有意义，删掉不影响任何功能。
    workspace = relationship(  # 定义"所属工作区"关系（多对一）
        "Resume",  # 关联到Resume表自身（自关联）
        remote_side=[id],  # 指定远程侧是id字段（即父简历的id）
        # SQLAlchemy 的逻辑：remote_side=[id] 标记对方（父表）的 id 是远程主键，我的 workspace_id 指向它 → 只能指向一个父记录 → uselist 默认为 False → 多对一
        back_populates="versions",  # 反向关联到父简历的versions字段
    )
    versions = relationship(  # 定义"子简历列表"关系（一对多）
        "Resume",  # 关联到Resume表自身
        back_populates="workspace",  # 反向关联到子简历的workspace字段
        foreign_keys=[workspace_id],  # 指定通过workspace_id字段关联   # ← 外键在对面（子表），找所有 workspace_id = 我的 id 的行
        # foreign_keys 指向 Resume.workspace_id（对方的字段），意味着"去找那些 workspace_id 等于我 id 的 Resume 记录" → 可能找到多条 → uselist 默认为 True → 一对多
        cascade="all, delete-orphan",  # 级联操作：删除主简历时，所有子简历也一起删除
    )
#     实际上 SQLAlchemy 要求 back_populates 引用的关系名必须存在，但不要求对面也有 back_populates。
# 只留一个的情况：
# # 方案 A：versions 有 back_populates，workspace 没有
# versions = relationship("Resume", back_populates="workspace", ...)
# workspace = relationship("Resume", ...)   # 没有 back_populates
# # 行为：
# parent.versions.append(child)  → 同步 child.workspace = parent  ✅
# child.workspace = parent       → 不会同步到 parent.versions      ❌（单向同步）
# # 方案 B：workspace 有 back_populates，versions 没有
# versions = relationship("Resume", ...)                            # 没有 back_populates
# workspace = relationship("Resume", back_populates="versions", ...)
# # 行为：
# child.workspace = parent       → 同步 parent.versions.append(child)  ✅
# parent.versions.append(child)  → 不会同步 child.workspace             ❌（单向同步）
# 但在这个代码库里，两种同步都没人用。 创建子简历时都是直接设 workspace_id：
# # parser/service.py 或 resume_assistant 里创建子简历
# sub_resume = Resume(workspace_id=parent_id, ...)  # 直接写外键
# 没有出现过 parent.versions.append(child) 或 child.workspace = parent 这种写法。所以无论 back_populates 怎么配置（两个都有、一个没有、两个都没有），对现有代码的行为零影响。
# SQLAlchemy 唯一真正的硬要求是：如果写了 back_populates="workspace"，workspace 这个关系必须在对面存在（不管有没有 back_populates），否则模型定义阶段就会报错。
    sections = relationship(  # 定义"简历板块列表"关系（一对多）
        "ResumeSection",  # 关联到ResumeSection表
        back_populates="resume",  # 反向关联到板块的resume字段
        cascade="all, delete-orphan",  # 级联操作：删除简历时，所有板块也一起删除
    )
    job_description_analyses = relationship(  # 定义"职位分析列表"关系（一对多）
        "JobDescriptionAnalysis",  # 关联到JobDescriptionAnalysis表
        back_populates="resume",  # 反向关联到分析记录的resume字段
        cascade="all, delete-orphan",  # 级联操作：删除简历时，所有分析记录也一起删除
    )

    def to_pydantic(self) -> ResumeSchema:  # 将ORM对象转换为Pydantic模型
        """将当前ORM实例转换为ResumeSchema Pydantic对象。

        用于API响应时将数据库记录转换为JSON格式。
        注意：theme_config在数据库中是JSON字符串，需要json.loads转为字典。
        """  # 文档字符串
        return ResumeSchema(  # 创建并返回ResumeSchema对象
            id=self.id,  # 传递简历ID
            workspace_id=self.workspace_id,  # 传递所属工作区ID
            title=self.title,  # 传递简历标题
            template=self.template,  # 传递模板名称
            theme_config=json.loads(
                self.theme_config
            ),  # 将数据库中的JSON字符串转为Python字典
            is_default=self.is_default,  # 传递是否默认简历
            language=self.language,  # 传递语言
            share_token=self.share_token,  # 传递分享令牌
            is_public=self.is_public,  # 传递是否公开
            share_password=self.share_password,  # 传递分享密码
            view_count=self.view_count,  # 传递浏览次数
            created_at=self.created_at,  # 传递创建时间
            updated_at=self.updated_at,  # 传递更新时间
            meta_info=self.meta_info,  # 传递元数据（已经是字典，JSON类型自动反序列化）
        )

    @classmethod  # 类方法
    def from_pydantic(cls, schema: ResumeSchema) -> Resume:  # 从Pydantic对象创建ORM实例
        """从ResumeSchema Pydantic对象创建Resume ORM实例。

        用于保存数据时将API请求数据转换为数据库记录。
        """  # 文档字符串
        created = (
            schema.created_at or utc_now()
        )  # 如果Pydantic对象没有提供创建时间，则使用当前时间
        updated = (
            schema.updated_at or utc_now()
        )  # 如果Pydantic对象没有提供更新时间，则使用当前时间

        return cls(  # 创建并返回Resume ORM实例
            id=schema.id,  # 设置简历ID
            workspace_id=schema.workspace_id,  # 设置所属工作区ID
            title=schema.title,  # 设置标题
            template=schema.template,  # 设置模板名称
            theme_config=json.dumps(  # 将Python字典转为JSON字符串存入数据库
                schema.theme_config,
                ensure_ascii=False,  # ensure_ascii=False允许中文直接显示而非转义
            ),
            is_default=schema.is_default,  # 设置是否默认简历
            language=schema.language,  # 设置语言
            share_token=schema.share_token,  # 设置分享令牌
            is_public=schema.is_public,  # 设置是否公开
            share_password=schema.share_password,  # 设置分享密码
            view_count=schema.view_count,  # 设置浏览次数
            created_at=created,  # 设置创建时间
            updated_at=updated,  # 设置更新时间
            meta_info=schema.meta_info,  # 设置元数据
        )


class ResumeSection(PydanticMixin, Base):  # 定义简历板块模型
    """简历板块数据库模型。

    对应数据库中的 resume_sections 表，存储简历的各个板块内容。
    每份简历有多个板块（如个人信息、工作经历、教育背景等），
    通过 resume_id 字段关联到所属简历。
    """  # 文档字符串

    __tablename__ = "resume_sections"  # 数据库表名

    id: Mapped[str] = mapped_column(  # 板块唯一ID
        String(36),  # UUID字符串
        primary_key=True,  # 主键
        default=lambda: str(uuid.uuid4()),  # 自动生成UUID
        comment="板块唯一标识",  # 列注释
    )
    resume_id: Mapped[str] = mapped_column(  # 所属简历ID
        String(36),  # UUID字符串
        ForeignKey("resumes.id"),  # 外键关联到resumes表
        nullable=False,  # 不允许为空（每个板块必须属于一份简历）
        index=True,  # 创建索引（频繁按简历ID查询板块）
        comment="所属简历ID（外键）",  # 列注释
    )
    type: Mapped[str] = mapped_column(  # 板块类型
        String(50),  # 字符串
        nullable=False,  # 不允许为空
        comment="板块类型标识（如 personal_info, work_experience, education 等）",  # 列注释
    )
    title: Mapped[str] = mapped_column(  # 板块显示标题
        String(100),  # 字符串
        nullable=False,  # 不允许为空
        comment="板块显示标题（如'个人信息'、'工作经历'）",  # 列注释
    )
    sort_order: Mapped[int] = mapped_column(  # 排序序号
        Integer,  # 整数
        nullable=False,  # 不允许为空
        default=0,  # 默认0
        comment="排序序号，数值越小越靠前显示",  # 列注释
    )
    visible: Mapped[bool] = mapped_column(  # 是否可见
        Boolean,  # 布尔类型
        nullable=False,  # 不允许为空
        default=True,  # 默认可见
        comment="是否在简历中显示此板块",  # 列注释
    )
    content: Mapped[str] = mapped_column(  # 板块内容（JSON字符串）
        Text,  # 文本类型
        nullable=False,  # 不允许为空
        default="{}",  # 默认空JSON对象
        comment="板块内容，存储为JSON字符串（结构因板块类型而异）",  # 列注释
    )
    created_at: Mapped[datetime] = mapped_column(  # 创建时间
        DateTime(timezone=True),  # 带时区的时间
        nullable=False,  # 不允许为空
        default=utc_now,  # 默认当前时间
        comment="创建时间",  # 列注释
    )
    updated_at: Mapped[datetime] = mapped_column(  # 更新时间
        DateTime(timezone=True),  # 带时区的时间
        nullable=False,  # 不允许为空
        default=utc_now,  # 默认当前时间
        onupdate=utc_now,  # 更新时自动刷新
        comment="最后更新时间（自动更新）",  # 列注释
    )

    resume = relationship(
        "Resume", back_populates="sections"
    )  # 定义所属简历关系，反向关联到Resume.sections

    def to_pydantic(self) -> ResumeSectionSchema:  # 转换为Pydantic对象
        """将ORM实例转换为ResumeSectionSchema。

        使用 section_adapter 验证器将字典数据转换为具体的板块类型
        （如 PersonalInfoSection、SummarySection 等）。
        """  # 文档字符串
        data = dict(  # 构建字典数据
            id=self.id,  # 板块ID
            resume_id=self.resume_id,  # 所属简历ID
            title=self.title,  # 板块标题
            type=self.type,  # 板块类型（用于区分器判断具体类型）
            sort_order=self.sort_order,  # 排序序号
            visible=self.visible,  # 是否可见
            content=json.loads(self.content),  # 将JSON字符串反序列化为Python字典/列表
            created_at=self.created_at,  # 创建时间
            updated_at=self.updated_at,  # 更新时间
        )
        return section_adapter.validate_python(  # 使用Pydantic验证器将字典转换为具体的板块类型
            data  # section_adapter 根据 type 字段自动选择正确的板块类（Discriminator机制）
        )

    @classmethod  # 类方法
    def from_pydantic(
        cls, schema: ResumeSectionSchema
    ) -> ResumeSection:  # 从Pydantic创建ORM实例
        """从Pydantic schema创建ResumeSection ORM实例。

        处理content字段的序列化，根据板块类型提供不同的默认值。
        """  # 文档字符串
        if schema.content is not None:  # 如果有内容数据
            content = json.dumps(  # 将内容序列化为JSON字符串
                schema.content.model_dump(),  # model_dump()将Pydantic对象转为字典
                ensure_ascii=False,  # 允许中文直接显示
            )
        elif schema.type in {
            "personal_info",
            "summary",
            "custom",
        }:  # 个人信息、简介、自定义板块的默认值
            content = "{}"  # 空JSON对象
        elif schema.type == "skills":  # 技能板块的默认值
            content = '{"categories": []}'  # 包含空分类列表
        else:  # 其他板块（工作经历、教育背景等）的默认值
            content = '{"items": []}'  # 包含空条目列表
        created = schema.created_at or utc_now()  # 使用传入的创建时间，没有则用当前时间
        updated = schema.updated_at or utc_now()  # 使用传入的更新时间，没有则用当前时间
        return cls(  # 创建并返回ORM实例
            id=schema.id,  # 板块ID
            resume_id=schema.resume_id,  # 所属简历ID
            title=schema.title,  # 板块标题
            type=schema.type,  # 板块类型
            sort_order=schema.sort_order,  # 排序序号
            visible=schema.visible,  # 是否可见
            content=content,  # 序列化后的JSON内容字符串
            created_at=created,  # 创建时间
            updated_at=updated,  # 更新时间
        )


class BaseWork(Base):  # 定义通用任务流模型
    """通用任务流数据库模型。

    对应数据库中的 work 表，用于跟踪后台异步任务的状态。
    所有后台任务（如JD评分、PDF导出等）都使用这张表记录。
    """  # 文档字符串

    __tablename__ = "work"  # 数据库表名

    id: Mapped[str] = mapped_column(  # 任务唯一ID
        String(36), primary_key=True, comment="任务唯一ID（UUID）"
    )
    task_type: Mapped[str] = mapped_column(  # 任务类型
        String(50),  # 字符串
        nullable=False,  # 不允许为空
        comment="任务类型标识（如 jd_score, export_pdf 等）",  # 列注释
    )
    status: Mapped[str] = mapped_column(  # 任务状态
        String(20),  # 字符串
        nullable=True,  # 允许为空
        default="pending",  # 默认待处理状态
        comment="当前状态（pending/running/success/error）",  # 列注释
    )
    meta_info: Mapped[dict[str, Any] | None] = mapped_column(  # 任务元数据
        JSON,  # JSON类型
        nullable=True,  # 允许为空
        default=dict,  # 默认空字典
        comment="任务元数据（如关联的resume_id等）",  # 列注释
    )
    error_message: Mapped[str | None] = mapped_column(  # 错误信息
        Text,  # 文本类型
        nullable=True,  # 允许为空（任务成功时为空）
        comment="任务失败时的错误信息",  # 列注释
    )
    created_at: Mapped[datetime] = mapped_column(  # 创建时间
        DateTime(timezone=True),  # 带时区的时间
        nullable=False,  # 不允许为空
        default=utc_now,  # 默认当前时间
        comment="任务创建时间",  # 列注释
    )
    updated_at: Mapped[datetime] = mapped_column(  # 更新时间
        DateTime(timezone=True),  # 带时区的时间
        nullable=False,  # 不允许为空
        default=utc_now,  # 默认当前时间
        onupdate=utc_now,  # 更新时自动刷新
        comment="最后更新时间（自动更新）",  # 列注释
    )


class ConversationMessageRecord(PydanticMixin, Base):  # 定义对话消息模型
    """对话消息数据库模型。

    对应数据库中的 conversation_messages 表，
    存储用户与AI助手的对话消息（简历优化助手的聊天记录）。
    """  # 文档字符串

    __tablename__ = "conversation_messages"  # 数据库表名

    id: Mapped[int] = mapped_column(  # 消息自增ID
        Integer,  # 整数类型
        primary_key=True,  # 主键
        autoincrement=True,  # 自动递增（第一条消息ID=1，第二条=2...）
        comment="消息自增ID",  # 列注释
    )
    conversation_id: Mapped[str] = mapped_column(  # 所属会话ID
        String(36),  # UUID字符串
        nullable=False,  # 不允许为空
        index=True,  # 创建索引（频繁按会话ID查询消息）
        comment="所属会话ID（通常等于简历ID）",  # 列注释
    )
    role: Mapped[str] = mapped_column(  # 消息角色
        String(20),  # 字符串
        nullable=False,  # 不允许为空
        comment="消息角色：user（用户）或 assistant（AI助手）",  # 列注释
    )
    content: Mapped[str] = mapped_column(  # 消息内容
        Text,  # 文本类型
        nullable=False,  # 不允许为空
        default="[]",  # 默认空数组的JSON字符串
        comment="消息内容，JSON字符串格式",  # 列注释
    )
    reasoning: Mapped[str | None] = mapped_column(  # AI思考过程
        Text,  # 文本类型
        nullable=True,  # 允许为空（用户消息没有思考过程）
        default=None,  # 默认为空
        comment="AI的思考推理过程（仅assistant消息有）",  # 列注释
    )
    created_at: Mapped[datetime] = mapped_column(  # 创建时间
        DateTime(timezone=True),  # 带时区的时间
        nullable=False,  # 不允许为空
        default=utc_now,  # 默认当前时间
        comment="消息创建时间",  # 列注释
    )

    def to_pydantic(self) -> ConversationMessageSchema:  # 转换为Pydantic对象
        """将ORM实例转换为ConversationMessageSchema Pydantic对象。"""  # 文档字符串
        return ConversationMessageSchema.model_validate(  # 使用Pydantic验证器创建对象
            {
                "id": self.id,  # 消息ID
                "conversation_id": self.conversation_id,  # 会话ID
                "role": self.role,  # 消息角色
                "content": json.loads(self.content)
                if self.content
                else [],  # 反序列化JSON内容，空内容返回空列表
                "reasoning": self.reasoning,  # 思考过程
                "created_at": self.created_at,  # 创建时间
            }
        )

    @classmethod  # 类方法
    def from_pydantic(
        cls, schema: ConversationMessageSchema
    ) -> ConversationMessageRecord:  # 从Pydantic创建ORM实例
        """从ConversationMessageSchema创建ORM实例。"""  # 文档字符串
        return cls(  # 创建并返回ORM实例
            id=schema.id,  # 消息ID
            conversation_id=schema.conversation_id,  # 会话ID
            role=schema.role,  # 消息角色
            content=json.dumps(
                schema.content, ensure_ascii=False
            ),  # 将内容序列化为JSON字符串
            reasoning=schema.reasoning,  # 思考过程
            created_at=schema.created_at,  # 创建时间
        )


class Template(Base):  # 定义模板模型
    """简历模板数据库模型。

    对应数据库中的 template 表，存储简历模板的元数据。
    注意：模板的样式组件（React组件）定义在前端代码中，
    这里只存储模板的基本信息和启用状态。
    """  # 文档字符串

    __tablename__ = "template"  # 数据库表名

    id: Mapped[str] = mapped_column(  # 模板ID
        String(100),  # 字符串
        nullable=False,  # 不允许为空
        primary_key=True,  # 主键
        comment="模板唯一标识（如 classic, modern, minimal）",  # 列注释
    )
    name: Mapped[str] = mapped_column(  # 模板英文名
        String(100),  # 字符串
        default="未命名模板",  # 默认值
        nullable=False,  # 不允许为空
        comment="模板英文名称（代码中使用的标识）",  # 列注释
    )
    display_name: Mapped[str] = mapped_column(  # 模板中文名
        String(100),  # 字符串
        default="未命名模板",  # 默认值
        nullable=False,  # 不允许为空
        comment="模板显示名称（用户看到的中文名）",  # 列注释
    )
    preview_image_url: Mapped[str] = mapped_column(  # 预览图地址
        String(100),  # 字符串
        default="",  # 默认空
        nullable=False,  # 不允许为空
        comment="模板预览图片的URL地址",  # 列注释
    )
    is_active: Mapped[bool] = mapped_column(  # 是否启用
        default=False,  # 默认不启用
        nullable=True,  # 允许为空
        comment="模板是否启用（只有启用的模板才会显示给用户）",  # 列注释
    )
    description: Mapped[str] = mapped_column(  # 模板描述
        String(100),  # 字符串
        default="",  # 默认空
        nullable=True,  # 允许为空
        comment="模板的简要描述",  # 列注释
    )
    created_at: Mapped[datetime] = mapped_column(  # 创建时间
        DateTime(timezone=True),  # 带时区的时间
        nullable=False,  # 不允许为空
        default=utc_now,  # 默认当前时间
        comment="创建时间",  # 列注释
    )
    updated_at: Mapped[datetime] = mapped_column(  # 更新时间
        DateTime(timezone=True),  # 带时区的时间
        nullable=False,  # 不允许为空
        default=utc_now,  # 默认当前时间
        onupdate=utc_now,  # 更新时自动刷新
        comment="最后修改时间（自动更新）",  # 列注释
    )


class UserConfig(Base):  # 定义用户配置模型
    """用户配置数据库模型。

    对应数据库中的 user_config 表，使用键值对结构存储各种配置。
    这种设计允许在不修改表结构的情况下灵活添加新配置项。
    例如：AI提供商配置、用户偏好设置等。
    """  # 文档字符串

    __tablename__ = "user_config"  # 数据库表名

    key: Mapped[str] = mapped_column(  # 配置项键名
        String(50),  # 字符串
        nullable=False,  # 不允许为空
        primary_key=True,  # 主键（每个配置项的key唯一）
        comment="配置项标识键（如 'ai_provider', 'theme' 等）",  # 列注释
    )
    value: Mapped[dict] = mapped_column(  # 配置项值
        JSON,  # JSON类型
        nullable=False,  # 不允许为空
        default=dict,  # 默认空字典
        comment="配置值，JSON对象格式",  # 列注释
    )
    updated_at: Mapped[datetime] = mapped_column(  # 最后更新时间
        DateTime(timezone=True),  # 带时区的时间
        nullable=False,  # 不允许为空
        default=utc_now,  # 默认当前时间
        onupdate=utc_now,  # 更新时自动刷新
        comment="最后更新时间（自动更新）",  # 列注释
    )


class JobDescriptionAnalysis(PydanticMixin, Base):  # 定义职位描述分析模型
    """职位描述分析数据库模型。

    对应数据库中的 job_description_analysis 表，
    存储AI对简历与职位描述（JD）匹配度的分析结果。
    包括总体评分、ATS评分、关键词匹配、缺失关键词和优化建议。
    """  # 文档字符串

    __tablename__ = "job_description_analysis"  # 数据库表名

    id: Mapped[int] = mapped_column(  # 分析记录自增ID
        Integer,  # 整数类型
        primary_key=True,  # 主键
        autoincrement=True,  # 自动递增
        comment="分析记录自增ID",  # 列注释
    )
    resume_id: Mapped[str] = mapped_column(  # 关联的简历ID
        String(36),  # UUID字符串
        ForeignKey("resumes.id"),  # 外键关联到resumes表
        nullable=False,  # 不允许为空
        index=True,  # 创建索引（频繁按简历ID查询分析记录）
        comment="关联的简历ID（外键）",  # 列注释
    )
    job_description: Mapped[str] = mapped_column(  # 职位描述原文
        Text,  # 文本类型
        nullable=False,  # 不允许为空
        default="",  # 默认空字符串
        comment="目标职位的描述文本（JD原文）",  # 列注释
    )
    overall_score: Mapped[int] = mapped_column(  # 总体匹配评分
        Integer,  # 整数类型
        nullable=False,  # 不允许为空
        default=0,  # 默认0分
        comment="总体匹配评分（0-100分）",  # 列注释
    )
    ats_score: Mapped[int] = mapped_column(  # ATS兼容性评分
        Integer,  # 整数类型
        nullable=False,  # 不允许为空
        default=0,  # 默认0分
        comment="ATS（简历筛选系统）兼容性评分（0-100分）",  # 列注释
    )
    summary: Mapped[str] = mapped_column(  # 分析摘要
        Text,  # 文本类型
        nullable=False,  # 不允许为空
        default="",  # 默认空字符串
        comment="AI生成的匹配度分析摘要",  # 列注释
    )
    keyword_matches: Mapped[str] = mapped_column(  # 匹配的关键词
        Text,  # 文本类型
        nullable=False,  # 不允许为空
        default="[]",  # 默认空数组JSON字符串
        comment="简历中匹配JD要求的关键词列表（JSON数组）",  # 列注释
    )
    missing_keywords: Mapped[str] = mapped_column(  # 缺失的关键词
        Text,  # 文本类型
        nullable=False,  # 不允许为空
        default="[]",  # 默认空数组JSON字符串
        comment="JD要求但简历中缺失的关键词列表（JSON数组）",  # 列注释
    )
    suggestions: Mapped[str] = mapped_column(  # 优化建议
        Text,  # 文本类型
        nullable=False,  # 不允许为空
        default="[]",  # 默认空数组JSON字符串
        comment="针对各板块的优化建议列表（JSON数组）",  # 列注释
    )
    created_at: Mapped[datetime] = mapped_column(  # 创建时间
        DateTime(timezone=True),  # 带时区的时间
        nullable=False,  # 不允许为空
        default=utc_now,  # 默认当前时间
        onupdate=utc_now,  # 更新时自动刷新
        comment="分析记录创建时间",  # 列注释
    )

    resume = relationship(  # 定义所属简历关系
        "Resume",  # 关联到Resume表
        back_populates="job_description_analyses",  # 反向关联到Resume.job_description_analyses
    )

    def to_pydantic(self) -> JobDescriptionAnalysisSchema:  # 转换为Pydantic对象
        """将ORM实例转换为JobDescriptionAnalysisSchema Pydantic对象。"""  # 文档字符串
        suggestions = [  # 将JSON字符串反序列化为SuggestionItem对象列表
            SuggestionItem.model_validate(suggestion)  # 验证并创建每条建议
            for suggestion in json.loads(
                self.suggestions
            )  # 先将JSON字符串转为Python列表
        ]
# 可以，Pydantic v2 会自动把 list[dict] 转为 list[SuggestionItem]：
# # 现在的写法：
# suggestions = [
#     SuggestionItem.model_validate(s)
#     for s in json.loads(self.suggestions)
# ]
# # 省掉手动循环，完全等价：
# suggestions = json.loads(self.suggestions)
# # Pydantic 在构造时自动把每个 dict 转成 SuggestionItem
        return JobDescriptionAnalysisSchema(  # 创建并返回Pydantic对象
            id=self.id,  # 记录ID
            resume_id=self.resume_id,  # 关联简历ID
            job_description=self.job_description,  # 职位描述原文
            overall_score=self.overall_score,  # 总体评分
            ats_score=self.ats_score,  # ATS评分
            summary=self.summary,  # 分析摘要
            keyword_matches=json.loads(self.keyword_matches),  # 反序列化匹配关键词
            missing_keywords=json.loads(self.missing_keywords),  # 反序列化缺失关键词
            suggestions=suggestions,  # 建议列表
            created_at=self.created_at,  # 创建时间
        )

    @classmethod  # 类方法
    def from_pydantic(
        cls, schema: JobDescriptionAnalysisSchema
    ) -> JobDescriptionAnalysis:  # 从Pydantic创建ORM实例
        """从JobDescriptionAnalysisSchema创建ORM实例。"""  # 文档字符串
        suggestions = [  # 将SuggestionItem对象转为字典列表
            suggestion.model_dump()
            for suggestion in schema.suggestions  # model_dump()将Pydantic对象转为字典
        ]
        return cls(  # 创建并返回ORM实例
            resume_id=schema.resume_id,  # 关联简历ID
            job_description=schema.job_description,  # 职位描述原文
            overall_score=schema.overall_score,  # 总体评分
            ats_score=schema.ats_score,  # ATS评分
            summary=schema.summary,  # 分析摘要
            keyword_matches=json.dumps(  # 序列化匹配关键词为JSON字符串
                schema.keyword_matches, ensure_ascii=False
            ),
            missing_keywords=json.dumps(  # 序列化缺失关键词为JSON字符串
                schema.missing_keywords, ensure_ascii=False
            ),
            suggestions=json.dumps(
                suggestions, ensure_ascii=False
            ),  # 序列化建议列表为JSON字符串
        )
