from pathlib import Path
from typing import Generic, Optional

from config.settings import settings
from fastapi import FastAPI, Request
from fastapi.security.utils import get_authorization_scheme_param
from starlette.authentication import AuthenticationBackend
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import HTTPConnection

from senweaver.auth import models
from senweaver.auth.auth import Auth
from senweaver.auth.helper import AuthManagerProtocol
from senweaver.auth.schemas import IToken
from senweaver.constants import TokenTypeEnum
from senweaver.module.base import Module
from senweaver.utils.globals import g

from .router import AuthRouter


class AuthManager(
    AuthenticationBackend,
    Module,
    AuthManagerProtocol,
    Generic[models.UserProtocolType, models.ID],
):
    app: FastAPI
    auth_router: Optional[AuthRouter] = None

    def __init__(self, module_path: Path, package: str):
        self.auth_router = self.auth_router or AuthRouter(route_class=self.route_class)
        self.auth_router.sw_module = self
        super().__init__("auth", module_path=module_path, package=package, name="auth")

    def start(self, app: FastAPI):
        self.app = app
        self.app.add_middleware(AuthenticationMiddleware, backend=self)
        self.auth_router.add_routes()
        self.app.include_router(self.auth_router.router)
        self.ready = True

    async def create_superuser(self, username: str, password: str, email: str):
        pass

    async def get_auth(self, conn: Optional[HTTPConnection] = None):
        raise NotImplementedError()  # pragma: no cover

    def get_token(
        self, conn: HTTPConnection, header_name: str, cookie_name: str, query_name: str
    ) -> Optional[str]:
        authorization: str = conn.headers.get(header_name)
        scheme, token = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            token = conn.cookies.get(cookie_name) or conn.query_params.get(query_name)
        return token

    async def create_token(
        self, request: Request, user: models.UserProtocolType
    ) -> IToken:
        auth: Auth = request.auth
        access_token, access_token_expires = await auth.channel.write_token(
            user, token_type=TokenTypeEnum.access
        )
        refresh_token, refresh_token_expires = await auth.channel.write_token(
            user, token_type=TokenTypeEnum.refresh
        )
        return IToken(
            access=access_token,
            token_type="bearer",
            refresh=refresh_token,
            access_token_lifetime=settings.TOKEN_EXPIRE_MINUTES * 60,
            refresh_token_lifetime=settings.TOKEN_REFRESH_EXPIRE_MINUTES * 60,
            user=user.model_dump(exclude={"password", "password_time"}),
        )

    async def authenticate(
        self, conn: HTTPConnection
    ) -> tuple[Auth, Optional[models.UserProtocolType]]:
        auth: Auth = await self.get_auth(conn)
        if conn.scope["type"] == "websocket":
            async with auth.db():
                user = await auth.get_current_user(conn)
                g.user = user
                return auth, user
        g.request = Request(conn.scope)
        user = await auth.get_current_user(conn)
        g.user = user
        return auth, user
