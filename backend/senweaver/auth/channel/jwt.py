from datetime import datetime, timedelta, timezone
from typing import Generic, List, Optional, Protocol, TypeVar, Union

import jwt
import jwt.utils
from fastcrud import FastCRUD
from pydantic import SecretStr

from config.settings import settings
from senweaver.auth import models
from senweaver.auth.channel.base import Channel, TokenProtocolType
from senweaver.constants import TokenTypeEnum
from senweaver.helper import get_secret_value

SecretType = Union[str, SecretStr]


class JWTChannel(
    Channel[models.UserProtocolType, models.ID],
    Generic[models.UserProtocolType, models.ID],
):
    def __init__(
        self,
        secret: SecretType,
        token_model: type[TokenProtocolType] = None,
        token_audience: List[str] = ["senweaver"],
        algorithm: str = "HS256",
        public_key: Optional[SecretType] = None,
    ):
        self.secret = secret
        self.token_audience = token_audience
        self.algorithm = algorithm
        self.public_key = public_key
        self.token_model = token_model

    @property
    def encode_key(self) -> SecretType:
        return self.secret

    @property
    def decode_key(self) -> SecretType:
        return self.public_key or self.secret

    async def read_token(
        self, token: Optional[str], token_type: TokenTypeEnum = TokenTypeEnum.access
    ) -> Optional[models.UserProtocolType]:
        if token is None:
            return None
        try:
            # signing_input, _ = token.encode("utf-8").rsplit(b".", 1)
            # _, claims_segment = signing_input.split(b".", 1)
            # payload = orjson.loads(jwt.utils.base64url_decode(claims_segment))
            # user_id = payload['sub']
            # TODO 使用动态密钥，先获取用户的数据password_time
            secret = get_secret_value(self.decode_key)
            payload = jwt.decode(
                token, secret, audience=self.token_audience, algorithms=self.algorithm
            )
            user_id = payload.get("sub")
            obj_token_type = payload.get("type")
            if user_id is None or obj_token_type != token_type.value:  # type: ignore
                return None
        except jwt.PyJWTError:
            return None
        try:
            parsed_id = self.auth.parse_id(user_id)
            # 判断是否在黑名单里
            if self.token_model:
                return await FastCRUD(self.token_model).exists(
                    self.auth.db.session,
                    token=token,
                    user_id=parsed_id,
                    one_or_none=True,
                )
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
        payload = {
            "sub": str(user.id),
            "aud": self.token_audience,
            "exp": expire,
            "type": token_type.value,
            **kwargs,
        }
        return (
            jwt.encode(
                payload, get_secret_value(self.secret), algorithm=self.algorithm
            ),
            expire,
        )

    async def destroy_token(self, token: str, user: models.UserProtocolType) -> None:
        if self.token_model:
            # 登出账户，并且将账户的access 和 refresh token 加入黑名单
            secret = get_secret_value(self.decode_key)
            payload = jwt.decode(token, secret, algorithms=self.algorithm)
            obj_token_type = payload.get("type")
            expires_at = datetime.fromtimestamp(payload.get("exp"))
            model = self.token_model(
                token=token,
                created_time=datetime.now(timezone.utc),
                token_type=obj_token_type,
                user_id=user.id,
                expired_at=expires_at,
            )
            await FastCRUD(self.token_model).create(self.auth.db.session, model)
        else:
            raise NotImplementedError()  # pragma: no cover
