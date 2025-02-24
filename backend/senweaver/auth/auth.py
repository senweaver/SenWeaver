from datetime import datetime, timezone
from time import time
from typing import Any, Generic, Optional, Sequence, Union

from fastapi import File, Form, Request, Response, UploadFile
from fastcrud import FastCRUD
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import HTTPConnection

from senweaver.auth import models
from senweaver.auth.channel.base import Channel
from senweaver.auth.constants import Logical, LoginTypeChoices
from senweaver.auth.helper import (
    AuthManagerProtocol,
    AuthProtocol,
    CaptchaHelper,
    CaptchaHelperProtocol,
    DBSessionProtocolType,
)
from senweaver.auth.password import PasswordHelper, PasswordHelperProtocol
from senweaver.auth.schemas import (
    IChangePassword,
    ILogin,
    ILoginLog,
    IOperationLog,
    IResetPassword,
    IToken,
    IUserProfile,
)
from senweaver.db.types import ModelType
from senweaver.exception.http_exception import (
    BadRequestException,
    CustomException,
    ForbiddenException,
)
from senweaver.helper import get_secret_value
from senweaver.middleware.db import db as async_db
from senweaver.utils.encrypt import AESCipherV2
from senweaver.utils.request import parse_client_info


class Auth(AuthProtocol, Generic[models.UserProtocolType, models.ID]):
    name: str
    manager: AuthManagerProtocol[models.UserProtocolType, models.ID] = None
    user_model: type[models.UserProtocolType] = None
    channel: Channel[models.UserProtocolType, models.ID]
    crud: Optional[FastCRUD] = (None,)
    password_helper: Optional[PasswordHelperProtocol] = None
    captcha_helper: Optional[CaptchaHelperProtocol] = None
    db: type[DBSessionProtocolType] = None

    def __init__(
        self,
        name: str,
        manager: AuthManagerProtocol[models.UserProtocolType, models.ID],
        user_model: type[models.UserProtocolType],
        channel: Channel[models.UserProtocolType, models.ID],
        password_helper: Optional[PasswordHelperProtocol] = None,
        crud: Optional[FastCRUD] = None,
        captcha_helper: Optional[CaptchaHelperProtocol] = None,
        db: type[DBSessionProtocolType] = None,
        header_name: str = "Authorization",
        cookie_name: str = "X-Token",
        query_name: str = "sw_token",
    ):
        self.name = name
        self.db = db or async_db
        self.manager = manager
        self.user_model = user_model
        self.channel = channel
        self.channel.auth = self
        self.password_helper = password_helper or PasswordHelper()
        self.captcha_helper = captcha_helper or CaptchaHelper()
        self.crud = crud or FastCRUD(user_model)
        self.header_name = header_name
        self.cookie_name = cookie_name
        self.query_name = query_name

    async def get_current_user(
        self, conn: HTTPConnection
    ) -> Optional[models.UserProtocolType]:
        if "user" in conn.scope:
            return conn.scope["user"]
        token = self.manager.get_token(
            conn, self.header_name, self.cookie_name, self.query_name
        )
        user = await self.channel.read_token(token) if token else None
        if not user:
            return None
        conn.scope["user"] = user
        return user

    async def get_user(
        self, db: AsyncSession = None, **kwargs: Any
    ) -> Optional[Union[dict, BaseModel]]:

        return await self.crud.get(
            db or self.db.session,
            schema_to_select=self.user_model,
            return_as_model=True,
            one_or_none=True,
            is_deleted=False,
            **kwargs,
        )

    def get_hash_password(
        self, value: str, key: Optional[str] = None, encrypted: Optional[bool] = True
    ) -> str:
        if len(value) < 8:
            raise BadRequestException("Password must be at least 8 characters")
        return self.password_helper.hash(value)

    def get_creator_data(
        self, model: type[ModelType], conn: Optional[HTTPConnection] = None
    ) -> dict[str, Any]:
        return {}

    def get_role_scope(
        self, conn: Optional[HTTPConnection] = None
    ) -> tuple[set[str], set[models.ID]]:
        raise NotImplementedError()  # pragma: no cover

    async def get_data_filters(
        self, model: type[ModelType], conn: Optional[HTTPConnection] = None
    ):
        raise NotImplementedError()  # pragma: no cover

    async def get_allow_fields(
        self, model: type[ModelType], conn: Optional[HTTPConnection] = None
    ):
        raise NotImplementedError()  # pragma: no cover

    async def login(
        self, request: Request, response: Response, param: ILogin, captcha_enabled: bool
    ) -> tuple[Optional[IToken], Optional[str]]:
        if request.scope.get("user"):
            data = await self.manager.create_token(request, request.user)
            return data, "已登录"

        if captcha_enabled:
            await self.captcha_helper.check_captcha(
                request=request,
                captcha_key=param.captcha_key,
                captcha_code=param.captcha_code,
            )
        user = await self.get_user(username=param.username)
        if not user:
            raise CustomException("用户不存在")
        password = get_secret_value(param.password)
        valid, _ = self.password_helper.verify_and_update(password, user.password)
        if not valid:
            raise CustomException("密码错误")
        client = await parse_client_info(request)
        # 登录日志
        log = ILoginLog(
            user_id=user.id,
            username=user.username,
            status=True,
            login_type=LoginTypeChoices.USERNAME,
            client=client,
        )
        if not user.is_active:
            log.remark = "用户未激活"
            log.status = False
            await self.add_login_log(request, log, user)
            raise CustomException("用户未激活")

        data = await self.manager.create_token(request, user)
        log.status = True
        # 更新最后登录时间
        last_login_time = datetime.now(timezone.utc)
        await self.crud.update(
            self.db.session, {"last_login": last_login_time}, id=user.id
        )
        user.last_login = last_login_time
        request.scope["user"] = user
        await self.add_login_log(request, log, user)
        return data, "登录成功"

    async def add_login_log(
        self, request: Request, log: ILoginLog, user: models.UserProtocolType
    ): ...

    async def add_oper_log(self, log: IOperationLog): ...

    async def logout(self, request: Request, response: Response) -> None:
        token = self.manager.get_token(
            request, self.header_name, self.cookie_name, self.query_name
        )
        try:
            await self.channel.destroy_token(token=token, user=request.user)
        except Exception:
            pass
        return None

    async def register(
        self, request: Request, response: Response, data: models.UserRegProtocolType
    ):
        raise ForbiddenException("forbidden.")

    async def get_current_user_info(self, request: Request):
        data = request.user.model_dump(exclude={"password", "password_time"})
        return data

    async def upload_avatar(
        self,
        request: Request,
        path: Optional[str] = Form(None),
        file: Optional[UploadFile] = File(None),
    ):
        raise NotImplementedError()  # pragma: no cover

    async def check_file_permission(self, request: Request):
        pass

    async def change_password(self, request: Request, data: IChangePassword):
        if not data.old_password or not data.sure_password:
            raise CustomException("密码不能为空")
        user: models.UserProtocolType = request.user
        old_password = AESCipherV2(user.username).decrypt(data.old_password)
        sure_password = AESCipherV2(user.username).decrypt(data.sure_password)
        valid, _ = self.password_helper.verify_and_update(old_password, user.password)
        if not valid:
            raise CustomException("旧密码错误")
        new_password_hash = self.password_helper.hash(sure_password)
        new_password_time = datetime.now(timezone.utc)
        await self.crud.update(
            self.db.session,
            {"password": new_password_hash, "password_time": new_password_time},
            id=request.user.id,
        )
        user.password = new_password_hash
        user.password_time = new_password_time
        request.scope["user"] = user

    async def reset_password(self, request: Request, data: IResetPassword):
        pass

    async def update_profile(self, request: Request, profile: IUserProfile):
        data = await self.crud.update(
            self.db.session,
            {"nickname": profile.nickname, "gender": profile.gender},
            id=request.user.id,
        )
        request.user.nickname = profile.nickname
        request.user.gender = profile.gender
        return data

    async def has_permission(
        self,
        conn: HTTPConnection,
        scope_type: str,
        scopes: Sequence[str],
        logical: Logical = Logical.AND,
    ) -> bool:
        # 验证是否登录
        if not conn.user:
            return False
        # 判断类型
        if scope_type not in conn.scope:
            return False
        auth_scopes = conn.scope[scope_type]
        if scope_type == "user":
            return True
        if logical == Logical.AND:
            return all(scope in auth_scopes for scope in scopes)
        elif logical == Logical.OR:
            return any(scope in auth_scopes for scope in scopes)
