from typing import Any, Generic, Optional, Sequence, Union

import orjson
from fastapi import File, Form, UploadFile
from fastapi.requests import Request
from fastcrud import FastCRUD
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from starlette.requests import HTTPConnection

from app.system.core.auth.permission import get_allow_fields, get_data_filters
from app.system.logic.common_logic import CommonLogic
from app.system.model import Dept, LoginLog, Menu, OperationLog, User
from app.system.model.role_menu import RoleMenu
from senweaver.auth import models
from senweaver.auth.auth import Auth
from senweaver.auth.constants import (
    SENWEAVER_FIELDS,
    SENWEAVER_FILTERS,
    SENWEAVER_MENUS,
    SENWEAVER_PERMS,
    SENWEAVER_REQ_MENU,
    SENWEAVER_ROLE_IDS,
    SENWEAVER_ROLES,
    SENWEAVER_SUPERUSER,
    Logical,
)
from senweaver.auth.models import IntegerIDMixin
from senweaver.auth.schemas import ILoginLog, IOperationLog
from senweaver.core.helper import get_file_url
from senweaver.db.types import ModelType
from senweaver.exception.http_exception import BadRequestException, ForbiddenException
from senweaver.utils.encrypt import AESCipherV2
from senweaver.utils.globals import g


class SystemAuth(
    IntegerIDMixin,
    Auth[models.UserProtocolType, models.ID],
    Generic[models.UserProtocolType, models.ID],
):

    async def add_login_log(
        self, request: Request, log: ILoginLog, user: models.UserProtocolType
    ):
        client = log.client
        await FastCRUD(LoginLog).create(
            request.auth.db.session,
            LoginLog(
                creator_id=log.user_id,
                modifier_id=log.user_id,
                status=log.status,
                ipaddress=client.ip,
                country=client.country,
                region=client.region,
                city=client.city,
                browser=client.browser,
                system=client.os,
                agent=client.user_agent,
                login_type=log.login_type,
            ),
        )

    async def add_oper_log(self, log: IOperationLog):
        client = log.client
        oper_log = OperationLog(
            module=log.title,
            path=log.path,
            body=orjson.dumps(log.request_data),
            method=log.method,
            ipaddress=client.ip,
            country=client.country,
            region=client.region,
            city=client.city,
            browser=client.browser,
            system=client.os,
            response_code=log.response_code,
            respone_result=orjson.dumps(log.response_result),
            status_code=log.status_code,
            cost_time=log.cost_time,
        )
        async with self.db(commit_on_exit=True):
            await FastCRUD(OperationLog).create(self.db.session, oper_log)

    async def get_user(
        self, db: AsyncSession = None, **kwargs: Any
    ) -> Optional[Union[dict, BaseModel]]:
        session: AsyncSession = db or self.db.session
        filters = self.crud._parse_filters(**kwargs)
        result = await session.execute(
            select(self.user_model)
            .options(selectinload(User.roles))
            .options(selectinload(User.posts))
            .options(joinedload(User.dept).options(selectinload(Dept.roles)))
            .filter(*filters)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return None
        user.avatar = get_file_url(user.avatar)
        return user

    def get_hash_password(
        self, value: str, key: Optional[str] = None, encrypted: Optional[bool] = True
    ) -> str:
        password = value
        if encrypted:
            request: Request = g.request
            if request and key is None:
                key = request.user.username
            password = AESCipherV2(key).decrypt(value)
        if len(password) < 8:
            raise BadRequestException("Password must be at least 8 characters")
        return self.password_helper.hash(password)

    def get_creator_data(
        self, model: type[ModelType], conn: Optional[HTTPConnection] = None
    ) -> dict[str, Any]:
        data = {}
        conn = conn or g.request
        if conn is None or not conn.user:
            return data
        user: User = conn.user
        if hasattr(model, "creator_id"):
            data["creator_id"] = user.id
        if hasattr(model, "dept_belong_id"):
            data["dept_belong_id"] = user.dept_id
        return data

    async def get_current_user_info(self, request: Request):
        user: User = request.user
        data = user.model_dump(exclude={"password", "password_time"})
        # 初始化两个集合来存储用户和部门的角色
        roles, _ = self.get_role_scope(request)
        data["roles"] = roles
        data["posts"] = [post.code for post in request.user.posts]
        data["dept"] = request.user.dept if "dept" in request.user else None
        return data

    async def upload_avatar(
        self,
        request: Request,
        path: Optional[str] = Form(None),
        file: Optional[UploadFile] = File(None),
    ):
        if not path and not file:
            raise BadRequestException("path 和 file 不能同时为空")
        if path:
            if not path or "/./" in path or "//" in path or path.startswith("/"):
                raise ForbiddenException("Invalid path format")
        else:
            data = await CommonLogic.upload(
                request, request.user.id, "avatar", "", [file]
            )
            path = data[0].filepath
        session: AsyncSession = self.db.session
        # file_data = await FastCRUD(Attachment).get(session,
        #                                              one_or_none=True, creator_id=request.user.id, path=path)
        # if not file_data:
        #     raise NotFoundException("文件不存在")
        await FastCRUD(User).update(session, {"avatar": path}, id=request.user.id)
        return {"path": path}

    async def check_file_permission(self, request: Request):
        pass

    def get_role_scope(
        self, conn: Optional[HTTPConnection] = None
    ) -> tuple[set[str], set[models.ID]]:
        conn = conn or g.request
        user: User = conn.user
        if not user:
            return set(), set()
        role_scope = conn.scope.get(SENWEAVER_ROLES, None)
        role_id_scope = conn.scope.get(SENWEAVER_ROLE_IDS, None)
        if role_scope is None or role_id_scope is None:
            role_scope = set()
            role_id_scope = set()
            user_roles = user.roles if user.roles else []
            dept_roles = user.dept.roles if user.dept and user.dept.roles else []
            roles = user_roles + dept_roles
            for role in roles:
                role_scope.add(role.code)
                role_id_scope.add(role.id)
            conn.scope[SENWEAVER_ROLES] = role_scope
            conn.scope[SENWEAVER_ROLE_IDS] = role_id_scope
        return role_scope, role_id_scope

    async def get_menu_scope(self, conn: Optional[HTTPConnection] = None):
        conn = conn or g.request
        _, role_ids = self.get_role_scope(conn)
        menu_scope = getattr(conn.state, SENWEAVER_MENUS, None)
        if menu_scope is None:
            menu_scope = set()
            result = await FastCRUD(RoleMenu).get_multi(
                self.db.session,
                role_id__in=role_ids,
                limit=None,
                return_total_count=False,
            )
            role_menus = result["data"]
            menu_ids = [rm["menu_id"] for rm in role_menus]
            menu_scope = set(menu_ids)
            setattr(conn.state, SENWEAVER_MENUS, menu_scope)
        return menu_scope

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
        user: User = conn.user
        if user.id == 1:
            setattr(conn.state, SENWEAVER_SUPERUSER, True)  # 超级管理员
            return True
        db: AsyncSession = self.db.session
        auth_scopes = conn.scope.get(SENWEAVER_PERMS, None)
        menu_scopes = await self.get_menu_scope(conn)
        menu_id = getattr(conn.state, SENWEAVER_REQ_MENU, 0)
        if auth_scopes is None or not menu_id:
            auth_scopes = set()
            auth_menus = await FastCRUD(Menu).get_multi(
                db,
                return_total_count=False,
                is_active=True,
                limit=None,
                id__in=menu_scopes,
                auths__or={"is_not": None, "ne": ""},
            )
            route_path = conn.scope["route"].path
            scopes_set = set(scopes)
            url_path_menu = []
            route_path_menu = []
            scope_menu = []
            scope_method = conn.scope.get("method")
            for menu in auth_menus["data"]:
                menu_auths = menu["auths"].split(",")
                auth_list = [auth.strip() for auth in menu_auths if auth.strip()]
                if menu["menu_type"] == Menu.MenuChoices.PERMISSION.value:
                    if conn.url.path == menu["path"] and scope_method == menu["method"]:
                        url_path_menu.append(menu["id"])
                    elif route_path == menu["path"] and scope_method == menu["method"]:
                        route_path_menu.append(menu["id"])
                    elif scopes_set & set(auth_list):
                        scope_menu.append(menu["id"])
                auth_scopes.update(auth_list)
            if url_path_menu:
                menu_id = url_path_menu[0]
            elif route_path_menu:
                menu_id = route_path_menu[0]
            elif scope_menu:
                menu_id = scope_menu[0]
            setattr(conn.state, SENWEAVER_REQ_MENU, menu_id)
            conn.scope[SENWEAVER_PERMS] = auth_scopes
        scope_data = conn.scope.get(scope_type, None)
        if scope_data is None:
            return False
        if scope_type == "user":
            return True
        # return (
        #     all(scope in scope_data for scope in scopes)
        #     if logical == Logical.AND
        #     else any(scope in scope_data for scope in scopes)
        # )
        return True

    async def get_data_filters(
        self, model: type[ModelType], conn: Optional[HTTPConnection] = None
    ):
        conn = conn or g.request
        filters = getattr(conn.state, SENWEAVER_FILTERS, None)
        if filters is None:
            filters = await get_data_filters(model, conn)
            setattr(conn.state, SENWEAVER_FILTERS, filters)
        return filters

    async def get_allow_fields(
        self, model: type[ModelType], conn: Optional[HTTPConnection] = None
    ):
        conn = conn or g.request
        fields = getattr(conn.state, SENWEAVER_FIELDS, None)
        if fields is None:
            fields = await get_allow_fields(conn)
            setattr(conn.state, SENWEAVER_FIELDS, fields)
        if fields is None:
            return {}
        return fields.get(model.__senweaver_name__, {})
