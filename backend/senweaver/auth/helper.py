import uuid
from datetime import timedelta
from typing import Any, Generic, Optional, Protocol, TypeVar, Union

from fast_captcha import img_captcha
from fastapi import Form, Request
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.concurrency import run_in_threadpool
from starlette.requests import HTTPConnection

from config.settings import settings
from senweaver.auth import models
from senweaver.auth.schemas import IToken
from senweaver.exception.http_exception import BadRequestException, CustomException
from senweaver.logger import logger


class DBSessionProtocol(Protocol):
    @property
    def session(self) -> AsyncSession: ...  # pragma: no cover


DBSessionProtocolType = TypeVar("DBSessionProtocolType", bound=DBSessionProtocol)


class AuthProtocol(Protocol, Generic[models.UserProtocolType, models.ID]):
    name: str
    db: type[DBSessionProtocolType] = None
    conn: HTTPConnection = None

    def parse_id(self, value: Any) -> models.ID:
        raise NotImplementedError()  # pragma: no cover

    async def get_user(
        self, db: AsyncSession = None, **kwargs: Any
    ) -> Optional[Union[dict, BaseModel]]: ...  # pragma: no cover


class AuthManagerProtocol(Protocol, Generic[models.UserProtocolType, models.ID]):
    def get_token(
        self, conn: HTTPConnection, header_name: str, cookie_name: str, query_name: str
    ) -> Optional[str]: ...  # pragma: no cover

    async def create_token(
        self, request: Request, user: models.UserProtocolType
    ) -> IToken: ...  # pragma: no cover


AUTH_CAPTCHA_PREFIX = "senweaver:captcha:"


class CaptchaHelperProtocol(Protocol):
    async def get_captcha(self, request: Request): ...  # pragma: no cover

    async def check_captcha(
        self,
        request: Request,
        captcha_key: Optional[str] = None,
        captcha_code: Optional[str] = None,
    ) -> bool: ...  # pragma: no cover


class CaptchaHelper(CaptchaHelperProtocol):

    async def get_captcha(self, request: Request):
        if not settings.CAPTCHA_ENABLE:
            raise BadRequestException("captcha is disabled")
        captcha_image, code = await run_in_threadpool(img_captcha, img_byte="base64")
        redis: Redis = request.app.state.redis
        captcha_key = str(uuid.uuid4())
        await redis.set(
            f"{AUTH_CAPTCHA_PREFIX}{captcha_key}",
            code,
            ex=timedelta(seconds=settings.CAPTCHA_EXPIRE_SECONDS),
        )
        return dict(
            captcha_key=captcha_key,
            captcha_image=f"data:image/png;base64,{captcha_image}",
            length=len(code),
        )

    async def check_captcha(
        self,
        request: Request,
        captcha_key: Optional[str] = None,
        captcha_code: Optional[str] = None,
    ) -> bool:
        if not captcha_code or not captcha_key:
            raise BadRequestException("验证码不能为空")
        redis: Redis = request.app.state.redis
        captcha_value = await redis.get(f"{AUTH_CAPTCHA_PREFIX}{captcha_key}")
        if not captcha_value:
            raise BadRequestException("验证码已失效")
        if captcha_code.lower() != str(captcha_value).lower():
            raise BadRequestException("验证码错误")
        await redis.delete(f"{AUTH_CAPTCHA_PREFIX}{captcha_key}")
        return True
