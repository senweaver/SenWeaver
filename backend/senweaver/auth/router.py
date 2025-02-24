import uuid
from datetime import timedelta
from enum import Enum
from typing import Annotated, Optional, Type, Union

import orjson
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.routing import APIRoute

from config.settings import EnvironmentEnum, settings
from senweaver.auth import models
from senweaver.auth.auth import Auth
from senweaver.auth.schemas import (
    IChangePassword,
    ILogin,
    ILoginCode,
    IRefreshToken,
    IUserProfile,
    IVerify,
    IVerifyCategoryEnum,
)
from senweaver.auth.security import (
    CustomOAuth2PasswordRequestForm,
    oauth2_scheme,
    oauth_token_url,
    requires_user,
)
from senweaver.constants import TokenTypeEnum
from senweaver.core.senweaver_route import SenweaverRoute
from senweaver.exception.http_exception import (
    BadRequestException,
    CustomException,
    UnauthorizedException,
)
from senweaver.helper import generate_string
from senweaver.utils.request import get_request_ident
from senweaver.utils.response import (
    ResponseBase,
    TokenResponse,
    error_response,
    success_response,
)


class AuthRouter:
    auth: Auth = None
    router: APIRouter = None
    title: Optional[str] = None
    router_prefix: Optional[str] = None
    router_tags: Optional[list[Union[str, Enum]]] = None
    register_schema: Type[models.UserRegProtocolType] = None
    resource_name: Optional[str] = None

    def __init__(self, auth: Auth = None, route_class: Type[APIRoute] = SenweaverRoute):
        self.auth = auth or self.auth
        assert self.auth, "auth is None"
        self.router_prefix = self.router_prefix or "/auth"
        self.router_tags = self.router_tags or ["auth"]
        # prefix=self.router_prefix,
        self.router = self.router or APIRouter(
            tags=self.router_tags, route_class=route_class
        )
        if self.resource_name is None:
            words = self.router_prefix.strip("/").replace("-", "/").split("/")
            self.resource_name = "".join(word.capitalize() or "_" for word in words)
        self.router.sw_auth = auth
        self.router.sw_title = self.title or self.resource_name

    def auth_temp_token(self):

        async def endpoint(request: Request) -> TokenResponse:
            force_new = False
            key = get_request_ident(request)
            make_token_key = "senweaver:make_token"
            cache_key = f"{make_token_key}:{key}"
            token = await request.app.state.redis.get(f"{cache_key}")
            if token and not force_new:
                return TokenResponse(token=token)
            random_str = uuid.uuid1().__str__().split("-")[0:-1]
            user_ran_str = uuid.uuid5(uuid.NAMESPACE_DNS, key).__str__().split("-")
            user_ran_str.extend(random_str)
            token = f"tmp_token_{''.join(user_ran_str)}"
            await request.app.state.redis.set(
                f"{cache_key}", token, ex=timedelta(seconds=60)
            )
            return TokenResponse(token=token)

        return endpoint

    def auth_get_verify(self):
        async def endpoint(
            request: Request,
            category: Optional[IVerifyCategoryEnum] = Query(
                None, description="Select a category"
            ),
        ) -> ResponseBase:
            if category == "login":
                data = {
                    "access": True,
                    "captcha": settings.CAPTCHA_ENABLE,
                    "token": True,
                    "encrypted": False,
                    "email": True,
                    "sms": False,
                    "basic": True,
                    "rate": 60,
                    "lifetime": 15,
                    "reset": True,
                    "register": True,
                }
            if category == "bind_phone":
                data = {
                    "access": True,
                    "captcha": settings.CAPTCHA_ENABLE,
                    "token": True,
                    "encrypted": False,
                    "rate": 60,
                    "sms": True,
                }
            if category == "bind_email":
                data = {
                    "access": True,
                    "captcha": settings.CAPTCHA_ENABLE,
                    "token": True,
                    "encrypted": False,
                    "rate": 60,
                    "email": True,
                }
            return success_response(data)

        return endpoint

    def auth_post_verify(self):
        async def endpoint(
            request: Request,
            item: IVerify = Body(...),  # type: ignore
            category: Optional[IVerifyCategoryEnum] = Query(
                None, description="Select a category"
            ),
        ) -> ResponseBase:
            auth: Auth = request.auth
            # TODO
            if item.form_type != "username":
                raise BadRequestException()
            # 验证临时token
            key = get_request_ident(request)
            make_token_key = "senweaver:make_token"
            cache_key = f"{make_token_key}:{key}"
            temp_token = await request.app.state.redis.get(f"{cache_key}")
            if item.token != temp_token:
                raise CustomException("临时Token校验失败，请重新登录")
            # 验证验证码
            if settings.CAPTCHA_ENABLE:
                check_captcha = await auth.captcha_helper.check_captcha(
                    request, item.captcha_key, item.captcha_code
                )
                if not check_captcha:
                    raise UnauthorizedException("验证码错误")

            user = await auth.get_user(is_active=True, username=item.target)
            if not user:
                return error_response("用户不存在", code=1001)
            code = generate_string(6)
            cache_data = {
                "target": item.target,
                "form_type": item.form_type,
                "query_key": item.form_type,
                "code": code,
            }
            verify_token = generate_string(50)
            verify_token_key = "senweaver:verify_token"
            cache_key = f"{verify_token_key}:{verify_token}"
            data = {"verify_token": verify_token, "extra": {}}
            if item.form_type == "username":
                # 用户名登录的直接返回
                data["verify_code"] = code
            await request.app.state.redis.set(
                f"{cache_key}", orjson.dumps(cache_data), ex=timedelta(seconds=60)
            )
            return success_response(data, "验证码已发送")

        return endpoint

    def captcha(self):
        async def endpoint(request: Request) -> ResponseBase:
            auth: Auth = request.auth
            data = await auth.captcha_helper.get_captcha(request)
            return success_response(**data)

        return endpoint

    def register(self):
        async def endpoint(
            request: Request,
            response: Response,
            item: self.register_schema = Body(...),  # type: ignore
        ) -> ResponseBase:
            auth: Auth = request.auth
            data = await auth.register(request, response, item)
            return success_response(data)

        return endpoint

    def login_basic(self):
        async def endpoint(
            request: Request, response: Response, param: ILogin
        ) -> ResponseBase:
            auth: Auth = request.auth
            key = get_request_ident(request)
            make_token_key = "senweaver:make_token"
            cache_key = f"{make_token_key}:{key}"
            temp_token = await request.app.state.redis.get(f"{cache_key}")
            if param.token != temp_token:
                raise CustomException("临时Token校验失败，请重新登录")
            data, msg = await auth.login(
                request=request,
                response=response,
                param=param,
                captcha_enabled=settings.CAPTCHA_ENABLE,
            )
            return success_response(data, msg)

        return endpoint

    def get_login_basic(self):
        async def endpoint(request: Request, response: Response) -> ResponseBase:
            data = {
                "access": True,
                "captcha": settings.CAPTCHA_ENABLE,
                "token": True,
                "encrypted": False,
                "lifetime": 15,
                "reset": True,
                "basic": True,
            }
            return success_response(data)

        return endpoint

    def login_code(self):
        async def endpoint(
            request: Request, response: Response, param: ILoginCode
        ) -> ResponseBase:
            auth: Auth = request.auth
            verify_token_key = "senweaver:verify_token"
            cache_key = f"{verify_token_key}:{param.verify_token}"
            cache_data = await request.app.state.redis.get(f"{cache_key}")
            if not cache_data:
                raise CustomException("已过期或存在错误")
            verify_data = orjson.loads(cache_data)
            if verify_data["code"] != param.verify_code:
                raise CustomException("校验码错误")
            if not verify_data or verify_data["query_key"] != "username":
                raise CustomException("暂不支持")
            username = verify_data["target"]
            login_param = ILogin(
                username=username,
                password=param.password,
                captcha_key="",
                captcha_code="",
                token="",
            )
            data, msg = await auth.login(
                request=request,
                response=response,
                param=login_param,
                captcha_enabled=False,
            )
            return success_response(data, msg)

        return endpoint

    def oauth_token_login(self):
        async def endpoint(
            request: Request,
            response: Response,
            form_data: Annotated[CustomOAuth2PasswordRequestForm, Depends()],
        ):
            param = ILogin(
                **dict(
                    username=form_data.username,
                    password=form_data.password,
                    captcha_code=form_data.captcha,
                    captcha_key=form_data.captcha_key,
                    token="",
                )
            )
            auth: Auth = request.auth
            # 这里不要校验验证码
            data, _ = await auth.login(
                request=request,
                response=response,
                param=param,
                captcha_enabled=settings.ENVIRONMENT == EnvironmentEnum.PRODUCTION,
            )
            return {"access_token": data.access}

        return endpoint

    def refresh_token(self):
        async def endpoint(request: Request, param: IRefreshToken) -> ResponseBase:
            if not param.refresh:
                raise UnauthorizedException("Refresh token missing.")
            auth: Auth = request.auth
            user = await auth.channel.read_token(param.refresh, TokenTypeEnum.refresh)
            if not user:
                raise UnauthorizedException("Refresh token error.")
            data = await auth.manager.create_token(request, user)
            return success_response(data)

        return endpoint

    def logout(self):
        @requires_user()
        async def endpoint(request: Request, response: Response) -> ResponseBase:
            auth: Auth = request.auth
            data = await auth.logout(request, response)
            return success_response(data)

        return endpoint

    def get_current_user_info(self):
        @requires_user()
        async def endpoint(request: Request) -> ResponseBase:
            auth: Auth = request.auth
            data = await auth.get_current_user_info(request)
            return success_response(data)

        return endpoint

    def change_password(self):
        @requires_user()
        async def endpoint(request: Request, data: IChangePassword) -> ResponseBase:
            auth: Auth = request.auth
            data = await auth.change_password(request, data)
            return success_response(data)

        return endpoint

    def upload_avatar(self):
        @requires_user()
        async def endpoint(
            request: Request,
            path: Optional[str] = Form(None),
            file: Optional[UploadFile] = File(None),
        ) -> ResponseBase:
            auth: Auth = request.auth
            data = await auth.upload_avatar(request, path, file)
            return success_response(data)

        return endpoint

    def reset_password(self):
        async def endpoint(request: Request) -> ResponseBase:
            auth: Auth = request.auth
            data = await auth.reset_password(request)
            return success_response(data=data)

        return endpoint

    def update_profile(self):
        @requires_user()
        async def endpoint(request: Request, profile: IUserProfile) -> ResponseBase:
            auth: Auth = request.auth
            data = await auth.update_profile(request, profile)
            return success_response(data=data)

        return endpoint

    def add_routes(self):
        oauth2_depend = [Depends(oauth2_scheme)] if settings.DOCS_URL else None
        self.router.add_api_route(
            f"{self.router_prefix}/captcha",
            self.captcha(),
            summary="captcha",
            methods=["GET"],
            description=f"captcha",
        )
        self.router.add_api_route(
            f"{self.router_prefix}/token",
            self.auth_temp_token(),
            summary="获取临时token",
            methods=["GET"],
            description=f"获取临时token",
        )
        self.router.add_api_route(
            f"{self.router_prefix}/verify",
            self.auth_get_verify(),
            summary="获取verify",
            methods=["GET"],
            description=f"获取verify",
        )
        self.router.add_api_route(
            f"{self.router_prefix}/verify",
            self.auth_post_verify(),
            summary="获取verify",
            methods=["POST"],
            description=f"获取verify",
        )
        if self.register_schema is not None:
            self.router.add_api_route(
                f"{self.router_prefix}/register",
                self.register(),
                summary="register",
                methods=["POST"],
                description=f"register",
            )
        self.router.add_api_route(
            f"/system/login/code",
            self.login_code(),
            summary="login by code",
            methods=["POST"],
            description=f"login by code",
        )
        self.router.add_api_route(
            f"/system/login/basic",
            self.get_login_basic(),
            summary="login basic",
            methods=["GET"],
            description=f"login basic",
        )
        self.router.add_api_route(
            f"/system/login/basic",
            self.login_basic(),
            summary="login",
            methods=["POST"],
            description=f"login",
        )
        if settings.DOCS_URL:
            self.router.add_api_route(
                oauth_token_url,
                self.oauth_token_login(),
                summary="token login",
                methods=["POST"],
                dependencies=oauth2_depend,
                description=f"token login",
            )
        self.router.add_api_route(
            f"/system/refresh",
            self.refresh_token(),
            summary="刷新token",
            methods=["POST"],
            description=f"token refresh",
        )

        self.router.add_api_route(
            f"/system/userinfo",
            self.get_current_user_info(),
            summary="获取当前用户信息",
            methods=["GET"],
            tags=["current user"],
            dependencies=oauth2_depend,
            description=f"current user info",
        )
        self.router.add_api_route(
            f"/system/userinfo/upload",
            self.upload_avatar(),
            summary="上传用户头像",
            methods=["POST"],
            tags=["current user"],
            dependencies=oauth2_depend,
            description=f"upload avatar",
        )
        self.router.add_api_route(
            f"/system/userinfo/reset-password",
            self.change_password(),
            summary="修改当前用户密码",
            methods=["POST"],
            tags=["current user"],
            dependencies=oauth2_depend,
            description=f"change current user password",
        )
        self.router.add_api_route(
            f"/system/userinfo/forgot-password",
            self.reset_password(),
            summary="重置当前用户密码",
            methods=["POST"],
            tags=["current user"],
            dependencies=oauth2_depend,
            description=f"reset current user password",
        )
        self.router.add_api_route(
            f"/system/userinfo",
            self.update_profile(),
            summary="更新当前用户信息",
            methods=["POST"],
            tags=["current user"],
            dependencies=oauth2_depend,
            description=f"change current user avatar",
        )

        self.router.add_api_route(
            f"/system/logout",
            self.logout(),
            summary="退出登录",
            methods=["POST"],
            dependencies=oauth2_depend,
            description=f"logout",
        )
