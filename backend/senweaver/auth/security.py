import asyncio
import functools
import inspect
from typing import Optional
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastcrud.endpoint.helper import _get_primary_key
from starlette._utils import is_async_callable
from starlette.authentication import _P, typing
from starlette.requests import HTTPConnection, Request
from starlette.responses import RedirectResponse
from starlette.websockets import WebSocket

from senweaver.auth.auth import Auth
from senweaver.auth.constants import (
    SENWEAVER_CHECK_DATA_SCOPE,
    SENWEAVER_CHECK_FIELD_SCOPE,
    SENWEAVER_GUEST,
    SENWEAVER_PERMS,
    SENWEAVER_ROLES,
    SENWEAVER_SCOPE_TYPE,
    SENWEAVER_SCOPES,
    SENWEAVER_SUPERUSER,
    Logical,
)
from senweaver.core.helper import create_schema_by_schema
from senweaver.db.types import ModelType, SelectSchemaType
from senweaver.exception.http_exception import (
    CustomException,
    ForbiddenException,
    PermissionException,
    UnauthorizedException,
)
from senweaver.utils.globals import g


class CustomOAuth2PasswordBearer(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        auth: Auth = request.auth
        return auth.manager.get_token(
            request, auth.header_name, auth.cookie_name, auth.query_name
        )


class CustomOAuth2PasswordRequestForm(OAuth2PasswordRequestForm):
    def __init__(
        self,
        username: str = Form(),
        password: str = Form(),
        captcha_key: Optional[str] = Form(default=""),
        captcha: Optional[str] = Form(default=""),
    ):
        super().__init__(username=username, password=password)
        self.captcha_key = captcha_key
        self.captcha = captcha


oauth_token_url = "/auth/oauth/token"
oauth2_scheme = CustomOAuth2PasswordBearer(tokenUrl=oauth_token_url)


async def has_required_scope(
    conn: HTTPConnection,
    scope_type: str,
    scopes: typing.Sequence[str],
    logical: Logical = Logical.AND,
    check_data_scope: bool = True,
    check_field_scope: bool = True,
) -> bool:
    auth: Auth = conn.auth
    setattr(conn.state, SENWEAVER_SCOPE_TYPE, scope_type)
    setattr(conn.state, SENWEAVER_SCOPES, scopes)
    setattr(conn.state, SENWEAVER_CHECK_DATA_SCOPE, check_data_scope)
    setattr(conn.state, SENWEAVER_CHECK_FIELD_SCOPE, check_field_scope)
    if scope_type == SENWEAVER_GUEST:
        return conn.user is None
    return await auth.has_permission(conn, scope_type, scopes, logical)


def requires(
    scopes: str | typing.Sequence[str],
    scope_type: str,
    check_data_scope: bool = True,
    check_field_scope: bool = True,
    err_msg: str | None = None,
    status_code: int = 403,
    logical: Logical = Logical.AND,
    redirect: str | None = None,
) -> typing.Callable[
    [typing.Callable[_P, typing.Any]], typing.Callable[_P, typing.Any]
]:
    if isinstance(scopes, str) and "," in scopes:
        scopes = scopes.split(",")
    scopes_list = [scopes] if isinstance(scopes, str) else list(scopes)

    def decorator(
        func: typing.Callable[_P, typing.Any] = None,
    ) -> typing.Callable[_P, typing.Any]:
        sig = inspect.signature(func)
        parameters = sig.parameters.values()
        for idx, parameter in enumerate(parameters):
            if parameter.name == "request" or parameter.name == "websocket":
                type_ = parameter.name
                break
        else:
            raise Exception(
                f'No "request" or "websocket" argument on function "{func}"'
            )
        if type_ == "websocket":
            # Handle websocket functions. (Always async)
            @functools.wraps(func)
            async def websocket_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> None:
                websocket = kwargs.get(
                    "websocket", args[idx] if idx < len(args) else None
                )
                assert isinstance(websocket, WebSocket)
                async with websocket.auth.db():
                    if not await has_required_scope(
                        websocket,
                        scope_type,
                        scopes_list,
                        logical,
                        check_data_scope,
                        check_field_scope,
                    ):
                        await websocket.close()
                    else:
                        await func(*args, **kwargs)

            websocket_wrapper.__senweaver_scopes__ = scopes_list
            websocket_wrapper.__senweaver_scope_type__ = scope_type
            return websocket_wrapper

        elif is_async_callable(func):
            # Handle async request/response functions.
            @functools.wraps(func)
            async def async_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> typing.Any:
                request: Request = kwargs.get(
                    "request", args[idx] if idx < len(args) else None
                )
                assert isinstance(request, Request)
                if not await has_required_scope(
                    request,
                    scope_type,
                    scopes_list,
                    logical,
                    check_data_scope,
                    check_field_scope,
                ):
                    if redirect is not None:
                        orig_request_qparam = urlencode({"next": str(request.url)})
                        next_url = "{redirect_path}?{orig_request}".format(
                            redirect_path=request.url_for(redirect),
                            orig_request=orig_request_qparam,
                        )
                        return RedirectResponse(url=next_url, status_code=303)
                    raise CustomException(status_code=status_code, detail=err_msg)
                return await func(*args, **kwargs)

            async_wrapper.__senweaver_scopes__ = scopes_list
            async_wrapper.__senweaver_scope_type__ = scope_type
            return async_wrapper

        else:
            # Handle sync request/response functions.
            @functools.wraps(func)
            def sync_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> typing.Any:
                request = kwargs.get("request", args[idx] if idx < len(args) else None)
                assert isinstance(request, Request)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                response = loop.run_until_complete(
                    loop.create_task(
                        has_required_scope(
                            request,
                            scope_type,
                            scopes_list,
                            logical,
                            check_data_scope,
                            check_field_scope,
                        )
                    )
                )
                if not response:
                    if redirect is not None:
                        orig_request_qparam = urlencode({"next": str(request.url)})
                        next_url = "{redirect_path}?{orig_request}".format(
                            redirect_path=request.url_for(redirect),
                            orig_request=orig_request_qparam,
                        )
                        return RedirectResponse(url=next_url, status_code=303)
                    raise CustomException(status_code=status_code)
                return func(*args, **kwargs)

            sync_wrapper.__senweaver_scopes__ = scopes_list
            sync_wrapper.__senweaver_scope_type__ = scope_type
            return sync_wrapper

    return decorator


def requires_user(
    check_data_scope: bool = True,
    check_field_scope: bool = True,
    redirect: str | None = None,
) -> typing.Callable[
    [typing.Callable[_P, typing.Any]], typing.Callable[_P, typing.Any]
]:
    return requires(
        scopes="authenticated",
        scope_type="user",
        check_data_scope=check_data_scope,
        check_field_scope=check_field_scope,
        err_msg="请先登录",
        redirect=redirect,
    )


def requires_roles(
    value: str | typing.Sequence[str],
    logical: Logical = Logical.AND,
    check_data_scope: bool = True,
    check_field_scope: bool = True,
    redirect: str | None = None,
) -> typing.Callable[
    [typing.Callable[_P, typing.Any]], typing.Callable[_P, typing.Any]
]:
    return requires(
        scopes=value,
        scope_type=SENWEAVER_ROLES,
        check_data_scope=check_data_scope,
        check_field_scope=check_field_scope,
        err_msg="You have no permission",
        redirect=redirect,
        logical=logical,
    )


def requires_permissions(
    value: str | typing.Sequence[str],
    logical: Logical = Logical.AND,
    check_data_scope: bool = True,
    check_field_scope: bool = True,
    redirect: str | None = None,
) -> typing.Callable[
    [typing.Callable[_P, typing.Any]], typing.Callable[_P, typing.Any]
]:
    return requires(
        scopes=value,
        scope_type=SENWEAVER_PERMS,
        check_data_scope=check_data_scope,
        check_field_scope=check_field_scope,
        err_msg="You have no permission",
        redirect=redirect,
        logical=logical,
    )


def requires_guest(
    check_data_scope: bool = True,
    check_field_scope: bool = True,
) -> typing.Callable[
    [typing.Callable[_P, typing.Any]], typing.Callable[_P, typing.Any]
]:
    return requires(
        scope_type=SENWEAVER_GUEST,
        scopes=SENWEAVER_GUEST,
        check_data_scope=check_data_scope,
        check_field_scope=check_field_scope,
        err_msg="You have no guest",
    )


async def get_current_user(request: Request = Request, _: str = Depends(oauth2_scheme)):
    if request.user is None:
        raise UnauthorizedException("请先登录")
    return request.user


def get_route_permission(route):
    permission_set = set()
    route_endpoint = route.endpoint
    scopes = getattr(route_endpoint, "__senweaver_scopes__", None)
    scope_type = getattr(route_endpoint, "__senweaver_scope_type__", None)
    if scope_type and scope_type.startswith(SENWEAVER_PERMS) and scopes:
        for item in scopes:
            permission_set.add(item)
    if hasattr(route, "dependant"):
        dependant = route.dependant
        for dep in dependant.dependencies:
            if callable(dep.call):
                dependency_instance = dep.call
                # 检查依赖实例是否为Authorizer类型
                if isinstance(dependency_instance, Authorizer):
                    permissions = dependency_instance.permissions
                    for item in permissions:
                        permission_set.add(item)
    return permission_set


def get_permission_list(app: FastAPI):
    permission_set = set()
    for route in app.routes:
        if not hasattr(route, "methods"):
            continue
        permission_set = permission_set | get_route_permission(route)
    permission_list = sorted(permission_set)
    return permission_list


class Authorizer:
    def __init__(
        self,
        permissions: str | typing.Sequence[str] = None,
        roles: str | typing.Sequence[str] = None,
        check_data_scope: bool = True,
        check_field_scope: bool = True,
    ) -> None:
        self.permissions = (
            [permissions]
            if isinstance(permissions, str)
            else list(permissions)
            if permissions
            else None
        )
        self.roles = (
            [roles] if isinstance(roles, str) else list(roles) if roles else None
        )
        self.check_data_scope = check_data_scope
        self.check_field_scope = check_field_scope

    async def __call__(
        self,
        request: Request,
        # _: str = Depends(oauth2_scheme),
    ) -> Auth:
        has_permission = await has_required_scope(
            request,
            SENWEAVER_PERMS,
            self.permissions,
            self.check_data_scope,
            self.check_field_scope,
        )
        if not has_permission:
            raise PermissionException("You have no permission")
        has_role = await has_required_scope(
            request,
            SENWEAVER_ROLES,
            self.roles,
            self.check_data_scope,
            self.check_field_scope,
        )
        if not has_role:
            raise PermissionException("You have no role")
        return request.auth

    @classmethod
    def get_current_user(cls, conn: Optional[HTTPConnection] = None):
        conn = conn or g.request
        if conn is None:
            return None
        return conn.user

    @classmethod
    def get_current_user_id(cls, conn: Optional[HTTPConnection] = None):
        conn = conn or g.request
        if conn is None:
            return None
        return conn.user.id

    @classmethod
    def is_superuser(cls, conn: Optional[HTTPConnection] = None) -> bool:
        conn = conn or g.request
        if not conn or not conn.user:
            return False
        return bool(getattr(conn.state, SENWEAVER_SUPERUSER, False))

    @classmethod
    def _check_permission(
        cls,
        check_scope: Optional[bool],
        permission_flag: str,
        conn: Optional[HTTPConnection] = None,
    ) -> bool:
        conn = conn or g.request
        if conn is None:
            return False
        if not conn.user or getattr(conn.state, SENWEAVER_SUPERUSER, None):
            return False

        return (
            check_scope
            if check_scope is not None
            else getattr(conn.state, permission_flag, False)
        )

    @classmethod
    def allow_data_permission(
        cls,
        check_data_scope: Optional[bool] = None,
        conn: Optional[HTTPConnection] = None,
    ) -> bool:
        return cls._check_permission(check_data_scope, SENWEAVER_CHECK_DATA_SCOPE, conn)

    @classmethod
    def allow_field_permission(
        cls,
        check_field_scope: Optional[bool] = None,
        conn: Optional[HTTPConnection] = None,
    ) -> bool:
        return cls._check_permission(
            check_field_scope, SENWEAVER_CHECK_FIELD_SCOPE, conn
        )

    @classmethod
    async def get_allow_field_schema(
        cls,
        model: type[ModelType],
        check_field_scope: Optional[bool] = None,
        field_schema: Optional[type[SelectSchemaType]] = None,
        conn: Optional[HTTPConnection] = None,
        **kwargs,
    ):
        conn = conn or g.request
        if not cls.allow_field_permission(check_field_scope, conn):
            return False, field_schema, []
        fields_dict: dict = await conn.auth.get_allow_fields(model, conn)
        fields = list(fields_dict.keys())
        # if not fields:
        #     # 使用主键ID
        #     fields = [_get_primary_key(model)]
        select_schema = field_schema or model
        new_schema = create_schema_by_schema(
            field_schema or model,
            name=f"{select_schema.__name__}FieldPermission",
            include=set(fields),
            set_optional=True,
            **kwargs,
        )
        if field_schema:
            for attr_name, attr_val in vars(field_schema).items():
                if attr_name.startswith("sw_"):
                    setattr(new_schema, attr_name, attr_val)
            # sw_relation_config,sw_filter
        new_schema.sw_allow_fields = fields
        return True, new_schema, fields

    @classmethod
    def permit_all(cls) -> bool:
        return True

    @classmethod
    def deny_all(cls) -> bool:
        raise ForbiddenException(detail="Access denied.")

    @classmethod
    def anonymous(cls, conn: Optional[HTTPConnection] = None) -> bool:
        conn = conn or g.request
        return conn.user is None

    @classmethod
    def authenticated(cls, conn: Optional[HTTPConnection] = None):
        conn = conn or g.request
        if conn is None or not conn.user:
            raise UnauthorizedException(detail="Not authenticated")
        return conn.user

    @classmethod
    def has_role(cls, role_name: str, conn: Optional[HTTPConnection] = None) -> bool:
        roles, _ = conn.auth.get_role_scope(conn)
        if role_name not in roles:
            raise ForbiddenException(detail=f"Role {role_name} required.")
        return True

    @classmethod
    def has_any_role(
        cls, role_names: typing.Sequence[str], conn: Optional[HTTPConnection] = None
    ) -> bool:
        roles, _ = conn.auth.get_role_scope(conn)
        if not any(role in roles for role in role_names):
            raise ForbiddenException(detail="权限不足")
        return True

    @classmethod
    def has_authority(
        cls, authority: str, conn: Optional[HTTPConnection] = None
    ) -> bool:
        conn = conn or g.request
        # TODO
        return False

    @classmethod
    def has_any_authority(
        cls, authority: typing.Sequence[str], conn: Optional[HTTPConnection] = None
    ) -> bool:
        conn = conn or g.request
        # TODO
        return False

    @classmethod
    def has_ip_address(cls, ip: str, conn: Optional[HTTPConnection] = None) -> bool:
        conn = conn or g.request
        # TODO
        return False
