from typing import Optional

from fastapi import APIRouter, Body, Query, Request

from senweaver.utils.response import ResponseBase, success_response

from ..core.schemas import IEmailSet
from ..logic.setting_logic import SettingLogic
from ..settings import module

router = APIRouter(tags=["EmailSettings"], route_class=module.route_class)


@router.get("/email", summary="获取邮件配置")
async def get_basic_list(request: Request) -> ResponseBase:
    data = await SettingLogic.get_model_list(request, IEmailSet)
    return success_response(data)


@router.post("/email", summary="更新邮件配置")
async def post_basic(request: Request, data: IEmailSet) -> ResponseBase:
    result = await SettingLogic.save(request, "basic", data)
    return success_response(result)


@router.get("/email/search-columns", summary="获取邮件配置的展示字段")
async def get_basic_search_columns(request: Request) -> ResponseBase:
    data = SettingLogic.get_form_by_model(IEmailSet)
    return success_response(data)
