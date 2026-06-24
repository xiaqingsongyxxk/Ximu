"""系统配置管理的API路由模块。

本模块提供AI提供商配置的管理功能：
1. GET /config/provider - 获取当前提供商配置
2. PUT /config/provider - 更新提供商配置
3. PATCH /config/provider/switch - 切换激活的提供商
"""  # 模块文档字符串

from typing import Annotated  # 导入Annotated类型注解

from fastapi import APIRouter, Depends  # 导入FastAPI核心组件
from sqlalchemy import select  # SQL查询构建器
from sqlalchemy.ext.asyncio import AsyncSession  # 异步数据库会话

from apps.config.schemas import (  # 导入配置相关数据模型
    ProviderConfig,  # 提供商配置
    ProviderConfigUpdate,  # 提供商配置更新
    ProviderSwitch,  # 提供商切换
)
from shared.database import get_session  # 获取数据库会话的依赖函数
from shared.models import UserConfig  # 用户配置ORM模型

# 创建配置模块的API路由器
router = APIRouter(prefix="/config", tags=["config"])

# 提供商配置在数据库中的键名
PROVIDER_CONFIG_KEY = "provider_config"


async def _get_provider_config_from_db(db: AsyncSession) -> ProviderConfig:
    """从数据库获取提供商配置。"""
    result = await db.execute(
        select(UserConfig).where(UserConfig.key == PROVIDER_CONFIG_KEY)
    )
    row = result.scalar_one_or_none()
    if not row:  # 如果没有配置记录
        return ProviderConfig()  # 返回默认空配置
    return ProviderConfig.model_validate(row.value)  # 验证并返回配置


async def _save_provider_config(db: AsyncSession, config: ProviderConfig) -> None:
    """保存提供商配置到数据库。"""
    result = await db.execute(
        select(UserConfig).where(UserConfig.key == PROVIDER_CONFIG_KEY)
    )
    row = result.scalar_one_or_none()
    if row:  # 如果记录存在
        row.value = config.model_dump()  # 更新配置值
    else:  # 如果记录不存在
        db.add(UserConfig(key=PROVIDER_CONFIG_KEY, value=config.model_dump()))  # 创建新记录
    await db.commit()


@router.get("/provider", summary="获取提供商配置")  # GET /config/provider
async def get_provider_config(
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ProviderConfig:
    """获取当前的AI提供商配置。"""
    return await _get_provider_config_from_db(db)


@router.put("/provider", summary="更新提供商配置")  # PUT /config/provider
async def update_provider_config(
    update: ProviderConfigUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ProviderConfig:
    """更新指定提供商的配置。"""
    config = await _get_provider_config_from_db(db)

    if update.type not in config.providers:  # 如果提供商不存在
        from apps.config.schemas import ProviderConfigItem
        config.providers[update.type] = ProviderConfigItem()  # 创建空配置

    provider = config.providers[update.type]
    if update.base_url is not None:
        provider.base_url = update.base_url
    if update.api_key is not None:
        provider.api_key = update.api_key
    if update.model is not None:
        provider.model = update.model

    await _save_provider_config(db, config)
    return config


@router.patch("/provider/switch", summary="切换激活的提供商")  # PATCH /config/provider/switch
async def switch_provider(
    switch: ProviderSwitch,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ProviderConfig:
    """切换当前激活的AI提供商。"""
    config = await _get_provider_config_from_db(db)

    if switch.active not in config.providers:  # 如果目标提供商不存在
        from apps.config.schemas import ProviderConfigItem
        config.providers[switch.active] = ProviderConfigItem()  # 创建空配置

    config.active = switch.active
    await _save_provider_config(db, config)
    return config
