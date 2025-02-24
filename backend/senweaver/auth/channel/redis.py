import secrets
from datetime import datetime, timedelta
from typing import Generic, Optional

import redis.asyncio

from config.settings import settings
from senweaver.auth import models
from senweaver.auth.channel.base import Channel
from senweaver.constants import TokenTypeEnum


class RedisChannel(
    Channel[models.UserProtocolType, models.ID],
    Generic[models.UserProtocolType, models.ID],
):
    def __init__(
        self,
        redis: redis.asyncio.Redis,
        *,
        key_prefix: str = "senweaver_token:",
    ):
        self.redis = redis
        self.key_prefix = key_prefix

    async def read_token(
        self, token: Optional[str], token_type: TokenTypeEnum = TokenTypeEnum.access
    ) -> Optional[models.UserProtocolType]:
        if token is None:
            return None

        user_id = await self.redis.get(
            f"{self.key_prefix}:{token_type.value}:{token_type.value}{token}"
        )
        if user_id is None:
            return None
        try:
            parsed_id = self.auth.parse_id(user_id)
            return await self.auth.get_user(id=parsed_id, is_active=True)
        except Exception as e:
            return None

    async def write_token(
        self,
        user: models.UserProtocolType,
        expires_delta: timedelta = None,
        token_type: TokenTypeEnum = TokenTypeEnum.access,
        **kwargs,
    ) -> tuple[str, datetime]:
        if expires_delta:
            expire = expires_delta
        else:
            expire = timedelta(
                minutes=(
                    settings.TOKEN_EXPIRE_MINUTES
                    if token_type == TokenTypeEnum.access
                    else settings.TOKEN_REFRESH_EXPIRE_MINUTES
                )
            )

        token = secrets.token_urlsafe()
        await self.redis.set(
            f"{self.key_prefix}:{token_type.value}:{token_type.value}{token}",
            str(user.id),
            ex=expire.seconds,
        )
        return token

    async def destroy_token(self, token: str, user: models.UserProtocolType) -> None:
        await self.redis.delete(f"{self.key_prefix}{token}")
