import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Generic, Optional, TypeVar

from fastcrud import FastCRUD

from config.settings import settings
from senweaver.auth import models
from senweaver.auth.channel.base import Channel, TokenProtocolType
from senweaver.constants import TokenTypeEnum


class DatabaseChannel(
    Channel[models.UserProtocolType, models.ID],
    Generic[models.UserProtocolType, models.ID],
):
    def __init__(self, token_model: type[TokenProtocolType]):
        self.token_model = token_model

    async def read_token(
        self, token: Optional[str], token_type: TokenTypeEnum = TokenTypeEnum.access
    ) -> Optional[models.UserProtocolType]:
        obj = await FastCRUD(self.token_model).get(
            self.auth.db.session,
            token=token,
            token_type=token_type.value,
            one_or_none=True,
        )
        if obj is None:
            return None
        if obj["expired_at"] < datetime.now(timezone.utc):
            await self.destroy_token(token=token)
            return None
        try:
            parsed_id = self.auth.parse_id(obj["user_id"])
            return await self.auth.get_user(id=parsed_id, is_active=True)
        except Exception as e:
            return None

    async def write_token(
        self,
        user: models.UserProtocolType,
        expires_delta: timedelta = None,
        token_type: TokenTypeEnum = TokenTypeEnum.access,
        **kwargs
    ) -> tuple[str, datetime]:
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=(
                    settings.TOKEN_EXPIRE_MINUTES
                    if token_type == TokenTypeEnum.access
                    else settings.TOKEN_REFRESH_EXPIRE_MINUTES
                )
            )
        token = secrets.token_urlsafe()
        model = self.token_model(
            token=token,
            token_type=token_type.value,
            created_time=datetime.now(timezone.utc),
            user_id=user.id,
            expired_at=expire,
        )
        await FastCRUD(self.token_model).create(self.auth.db.session, model)
        return token, expire

    async def destroy_token(self, token: str, user: models.UserProtocolType) -> None:
        await FastCRUD(self.token_model).db_delete(self.auth.db.session, token=token)
