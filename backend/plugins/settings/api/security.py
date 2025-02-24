from enum import Enum
from typing import Optional, Union

from fastapi import APIRouter, Body, Request
from pydantic import BaseModel

from senweaver.utils.response import ResponseBase, success_response

from ..core.schemas import (
    IBasicSet,
    IBindEmailSet,
    IBindPhoneSet,
    ICaptchaSet,
    ILoginAuthSet,
    ILoginLimitSet,
    IPasswordSet,
    IRegisterAuthSet,
    IResetAuthSet,
    ISettingData,
    ISmsConfigModel,
    ISmsSet,
    IVerifySet,
)
from ..logic.setting_logic import SettingLogic
from ..settings import module

router = APIRouter(tags=["BasicSettings"], route_class=module.route_class)


def register_router(
    path: str,
    schema: type[BaseModel],
    category: str,
    tags: Optional[list[Union[str, Enum]]] = None,
    title: Optional[str] = None,
    default: dict = {},
):
    route = APIRouter(tags=tags, route_class=module.route_class)

    @route.get(path, summary=f"获取{title}")
    async def get_list(request: Request) -> ResponseBase:
        data = await SettingLogic.get_model_list(request, schema, default)
        return success_response(data)

    @route.post(path, summary=f"更新{title}")
    async def save_setting(
        request: Request, data: schema = Body(...)  # type: ignore
    ) -> ResponseBase:
        result = await SettingLogic.save(request, category, data)
        return success_response(result)

    @route.get(f"{path}/search-columns", summary=f"获取{title}的展示字段")
    async def get_search_columns(request: Request) -> ResponseBase:
        data = SettingLogic.get_form_by_model(schema)
        return success_response(data)

    return route


router.include_router(
    register_router(
        "/password",
        category="security_password",
        schema=IPasswordSet,
        tags=["PasswordSettings"],
        title="密码规则",
    )
)
router.include_router(
    register_router(
        "/login/limit",
        category="security_login_limit",
        schema=ILoginLimitSet,
        tags=["LoginLimitSettings"],
        title="登录限制",
    )
)
router.include_router(
    register_router(
        "/login/auth",
        category="security_login_auth",
        schema=ILoginAuthSet,
        tags=["LoginAuthSettings"],
        title="登录安全",
    )
)

router.include_router(
    register_router(
        "/register/auth",
        category="security_register_auth",
        schema=IRegisterAuthSet,
        tags=["RegisterAuthSettings"],
        title="注册安全",
    )
)

router.include_router(
    register_router(
        "/reset/auth",
        category="security_reset_password_auth",
        schema=IResetAuthSet,
        tags=["ResetAuthSettings"],
        title="重置密码",
    )
)

router.include_router(
    register_router(
        "/bind/email",
        category="security_bind_email_auth",
        schema=IBindEmailSet,
        tags=["BindEmailSettings"],
        title="绑定邮件",
    )
)

router.include_router(
    register_router(
        "/bind/phone",
        category="security_bind_phone_auth",
        schema=IBindPhoneSet,
        tags=["BindPhoneSettings"],
        title="绑定手机",
    )
)

router.include_router(
    register_router(
        "/verify",
        category="verify",
        tags=["VerifySettings"],
        schema=IVerifySet,
        title="验证码规则",
    )
)

router.include_router(
    register_router(
        "/captcha",
        category="captcha",
        tags=["CaptchaSettings"],
        schema=ICaptchaSet,
        title="图片验证码",
    )
)
