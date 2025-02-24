from collections.abc import AsyncGenerator
from typing import Optional, Union

import redis.asyncio as aioredis
from fastapi import Request
from redis.asyncio import Redis, RedisError
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from config.settings import settings
from senweaver.logger import logger

async_engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

async_session_maker = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


def create_engine_by_url(db_url: Optional[str] = None) -> Union[Engine, AsyncEngine]:
    if db_url is None:
        return async_engine
    try:
        # 尝试创建异步 AsyncEngine
        return create_async_engine(db_url, echo=False, future=True)
    except Exception as e:
        print(f"Failed to create asynchronous engine: {e}")
        # 尝试创建同步 Engine
        try:
            return create_engine(db_url)
        except Exception as e:
            print(f"Failed to create synchronous engine: {e}")
            raise ValueError(
                "Failed to create both asynchronous and synchronous engines."
            )


async def create_redis_pool() -> Redis:
    logger.info("开始连接redis...")
    redis = await aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf8",
        decode_responses=True,
        health_check_interval=20,
    )
    try:
        connection = await redis.ping()
        if connection:
            logger.info("redis连接成功")
        else:
            logger.error("redis连接失败")
    except RedisError as e:
        logger.error(f"redis连接错误：{e}")
    return redis


async def get_redis(request: Request) -> Redis:
    return request.app.state.redis
