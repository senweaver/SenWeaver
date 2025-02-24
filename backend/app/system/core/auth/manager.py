from pathlib import Path
from typing import Generic, Optional, Type
from uuid import uuid4

from fastapi import (
    APIRouter,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketException,
    status,
)
from fastcrud import FastCRUD
from starlette.requests import HTTPConnection

from app.system.core.auth import SystemAuth
from app.system.model.user import User
from config.settings import settings
from senweaver.auth import models
from senweaver.auth.auth import Auth
from senweaver.auth.channel.jwt import JWTChannel
from senweaver.auth.manager import AuthManager
from senweaver.auth.security import requires_user
from senweaver.db.session import get_session
from senweaver.exception.http_exception import DuplicateValueException
from senweaver.logger import logger
from senweaver.utils.generics import SnowflakeID

from ..websocket import manager
from .router import SystemAuthRouter


class SystemAuthManager(
    AuthManager[models.UserProtocolType, models.ID],
    Generic[models.UserProtocolType, models.ID],
):
    auth: Auth[models.UserProtocolType, models.ID]

    def __init__(self):
        channel = JWTChannel(secret=settings.SECRET_KEY, token_model=None)
        self.auth = SystemAuth[User, SnowflakeID](
            name="admin", manager=self, user_model=User, channel=channel
        )
        self.auth_router = SystemAuthRouter(self.auth)
        super().__init__(module_path=Path(__file__).parent, package=__package__)

    async def get_auth(self, conn: Optional[HTTPConnection] = None):
        return self.auth

    def run(self):
        self.add_websocket()

    async def create_superuser(self, username: str, password: str, email: str):
        async for db in get_session():
            crud = FastCRUD(User)
            exists = await crud.exists(db, username=username)
            if exists:  # pragma: no cover
                raise DuplicateValueException(f"UserName {username} is already exists")
            hash_password = self.auth.get_hash_password(password, encrypted=False)
            user = User(id=1, username=username, password=hash_password, email=email)
            await crud.create(db, user)

    def add_websocket(self):
        router = APIRouter(tags=["websocket"])

        @router.websocket("/ws/message/{group_name}/{username}")
        @requires_user()
        async def websocket_endpoint(
            websocket: WebSocket, group_name: str, username: str
        ):
            """Websocket endpoint."""
            try:
                await websocket.accept()
                if not websocket.user:
                    await websocket.close(
                        code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized"
                    )
                client_id = f"{username}"
                await manager.handle_websocket(client_id, websocket)
            except WebSocketException as exc:
                logger.error(f"Websocket exrror: {exc}")
                await websocket.close(
                    code=status.WS_1011_INTERNAL_ERROR, reason=str(exc)
                )
            except Exception as exc:
                logger.error(f"Error in chat websocket: {exc}")
                messsage = exc.detail if isinstance(exc, HTTPException) else str(exc)
                if "Could not validate credentials" in str(exc):
                    await websocket.close(
                        code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized"
                    )
                else:
                    await websocket.close(
                        code=status.WS_1011_INTERNAL_ERROR, reason=messsage
                    )

        self.app.include_router(router)
