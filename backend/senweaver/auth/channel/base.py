from datetime import datetime, timedelta
from typing import Generic, Optional, Protocol, TypeVar, Union

from senweaver.auth import models
from senweaver.auth.helper import AuthProtocol
from senweaver.auth.schemas import ITokenData
from senweaver.constants import TokenTypeEnum


class TokenProtocol(Protocol[models.ID]):
    id: int
    user_id: models.ID
    token: str
    token_type: str
    created_time: datetime
    expired_at: datetime


TokenProtocolType = TypeVar("TokenProtocolType", bound=TokenProtocol)


class Channel(Protocol, Generic[models.UserProtocolType, models.ID]):
    auth: AuthProtocol[models.UserProtocolType, models.ID] = None

    async def read_token(
        self, token: Optional[str], token_type: TokenTypeEnum = TokenTypeEnum.access
    ) -> Optional[models.UserProtocolType]: ...  # pragma: no cover

    async def write_token(
        self,
        user: models.UserProtocolType,
        expires_delta: timedelta = None,
        token_type: TokenTypeEnum = TokenTypeEnum.access,
        **kwargs
    ) -> tuple[str, datetime]: ...  # pragma: no cover

    async def destroy_token(
        self, token: str, user: models.UserProtocolType
    ) -> None: ...  # pragma: no cover
