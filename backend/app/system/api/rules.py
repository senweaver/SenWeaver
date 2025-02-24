from fastapi import APIRouter, Request

from senweaver.utils.response import ResponseBase, success_response

from ..system import module

router = APIRouter(prefix="/rules", tags=["密码规则"], route_class=module.route_class)


@router.get("/password", summary="获取密码规则配置")
async def password(
    request: Request,
) -> ResponseBase:

    return success_response(
        data={"password_rules": [{"key": "SECURITY_PASSWORD_MIN_LENGTH", "value": 6}]}
    )
