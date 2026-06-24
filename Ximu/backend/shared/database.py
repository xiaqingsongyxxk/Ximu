"""数据库工具模块。

本模块提供数据库设置辅助工具，供后端其他部分使用。
包括异步引擎、会话工厂和用于初始化数据库架构、提供会话的辅助工具。
"""  # 模块文档字符串，描述本模块的用途：管理数据库连接和会话

from collections.abc import (
    AsyncGenerator,
)  # 导入异步生成器类型，用于 get_session 函数的返回类型注解
from pathlib import Path  # 导入Path类，用于跨平台处理文件路径（比字符串拼接更安全）
from typing import Any  # 导入Any类型，用于类型注解中的"任意类型"

from sqlalchemy.ext.asyncio import (  # 从SQLAlchemy的异步扩展中导入以下组件
    AsyncSession,  # 异步数据库会话类，用于执行数据库操作
    async_sessionmaker,  # 异步会话工厂，用于批量创建会话实例
    create_async_engine,  # 创建异步数据库引擎的函数，引擎是数据库连接的核心
)

from shared.models import (
    Base,
)  # 导入ORM基类，定义在 shared/models.py 中，所有数据库模型都继承它

# 计算数据库文件的绝对路径
# __file__ = backend/shared/database.py
# .parent = backend/shared/
# .parent.parent = backend/
# / "app.db" = backend/app.db
db_path = (
    Path(__file__).parent.parent / "app.db"
)  # SQLite数据库文件将保存在 backend/app.db

# 创建异步数据库引擎
# f"sqlite+aiosqlite:///{db_path}" 是数据库连接字符串，表示使用SQLite数据库
# aiosqlite 是SQLite的异步驱动，让数据库操作可以使用 async/await
# echo=True 表示在控制台打印所有SQL语句（调试用，生产环境应关闭）
engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=True)

# 创建异步会话工厂
# session工厂就像一个"会话制造机"，每次调用都能创建一个新的数据库会话
# class_=AsyncSession 指定创建的会话类型是异步会话
# expire_on_commit=False 表示提交事务后对象不会过期（提交后仍能访问对象属性）
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """初始化数据库架构。

    创建SQLAlchemy Base元数据上定义的所有表。
    在应用启动时调用，确保所有数据库表在处理请求之前已创建。
    """
    # engine.begin() 开始一个数据库连接，async with 确保连接用完后自动关闭
    async with engine.begin() as conn:
        # conn.run_sync 在异步上下文中执行同步函数
        # Base.metadata.create_all 会根据所有模型类定义，自动创建对应的数据库表
        # 如果表已存在则跳过（不会重复创建）
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, Any]:
    """生成一个异步数据库会话。

    此生成器为数据库操作块提供新的AsyncSession，
    并确保使用后会话被关闭。

    Yields:
        AsyncSession: 新的SQLAlchemy异步会话，绑定到引擎。

    用法示例（在FastAPI的Depends中使用）：
        async def my_endpoint(db: AsyncSession = Depends(get_session)):
            result = await db.execute(select(User))
    """
    # async_session() 创建一个新的数据库会话
    # async with 确保会话在使用完毕后自动关闭（即使发生异常也会关闭）
    async with async_session() as session:
        yield session  # 将会话"产出"给调用方使用，yield 使函数变成生成器
