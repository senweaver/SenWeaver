from typing import Optional

from fastapi import APIRouter, Body, Query, Request

from senweaver.utils.response import ResponseBase, success_response

from ..core.schemas import ISmsConfigModel, ISmsSet
from ..settings import module

router = APIRouter(prefix="/sms", tags=["SmsSettings"], route_class=module.route_class)


@router.get("/backends", summary="获取详情")
async def get_sms_value(request: Request) -> ResponseBase:
    data = [{"value": "alibaba", "label": "阿里云"}]
    return success_response(data)


@router.get("", summary="获取详情")
async def get_sms(request: Request) -> ResponseBase:
    data = {"SMS_ENABLED": False, "SMS_BACKEND": "alibaba"}
    return success_response(data)


@router.patch("", summary="更新")
async def patch_sms(request: Request, data: ISmsSet) -> ResponseBase:
    # TODO
    return success_response()


@router.patch("/config", summary="更新")
async def patch_sms_config(
    request: Request, data: ISmsConfigModel, category: str = Query()
) -> ResponseBase:
    # TODO
    return success_response()


@router.post("/config", summary="更新")
async def post_sms_config(
    request: Request, data: ISmsConfigModel, category: str = Query()
) -> ResponseBase:
    # TODO
    return success_response()


@router.get("/config", summary="配置")
async def get_sms_config(request: Request, category: str = Query()) -> ResponseBase:
    data = {
        "SMS_TEST_PHONE": {"code": "+86", "phone": ""},
        "ALIBABA_ACCESS_KEY_ID": "1",
        "ALIBABA_VERIFY_SIGN_NAME": "1",
        "ALIBABA_VERIFY_TEMPLATE_CODE": "1",
    }
    return success_response(data)


@router.get("/config/search-columns", summary="获取列表和创建更新字段")
async def get_sms_search_columns(
    request: Request, category: str = Query()
) -> ResponseBase:
    data = [
        {
            "required": False,
            "read_only": False,
            "label": "手机",
            "help_text": "手机用于测试短信服务器的连通性",
            "write_only": False,
            "key": "SMS_TEST_PHONE",
            "input_type": "phone",
            "table_show": 1,
        },
        {
            "required": True,
            "read_only": False,
            "label": "Access Key ID",
            "max_length": 256,
            "write_only": False,
            "key": "ALIBABA_ACCESS_KEY_ID",
            "input_type": "string",
            "table_show": 1,
        },
        {
            "required": False,
            "read_only": False,
            "label": "Access Key Secret",
            "max_length": 256,
            "write_only": True,
            "key": "ALIBABA_ACCESS_KEY_SECRET",
            "input_type": "string",
            "table_show": 1,
        },
        {
            "required": True,
            "read_only": False,
            "label": "签名",
            "max_length": 256,
            "write_only": False,
            "key": "ALIBABA_VERIFY_SIGN_NAME",
            "input_type": "string",
            "table_show": 1,
        },
        {
            "required": True,
            "read_only": False,
            "label": "模板",
            "max_length": 256,
            "write_only": False,
            "key": "ALIBABA_VERIFY_TEMPLATE_CODE",
            "input_type": "string",
            "table_show": 1,
        },
    ]
    return success_response(data)


@router.get("/search-columns", summary="获取列表和创建更新字段")
async def get_sms_search_columns(request: Request) -> ResponseBase:
    data = [
        {
            "required": False,
            "default": False,
            "read_only": False,
            "label": "短信",
            "help_text": "启用短信服务 (SMS)",
            "write_only": False,
            "key": "SMS_ENABLED",
            "input_type": "boolean",
            "table_show": 1,
        },
        {
            "required": False,
            "default": "alibaba",
            "read_only": False,
            "label": "提供商",
            "help_text": "短信服务 (SMS) 提供商或协议",
            "write_only": False,
            "choices": [{"value": "alibaba", "label": "阿里云"}],
            "key": "SMS_BACKEND",
            "input_type": "choice",
            "table_show": 1,
        },
    ]
    return success_response(data)
