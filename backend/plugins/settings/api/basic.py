from fastapi import APIRouter, Request

from senweaver.utils.response import ResponseBase, success_response

from ..core.schemas import IBasicSet
from ..logic.setting_logic import SettingLogic
from ..settings import module

router = APIRouter(tags=["BasicSettings"], route_class=module.route_class)
module.add_path_router("/basic", router)


@router.get("/basic", summary="获取基础配置")
async def get_basic_list(request: Request) -> ResponseBase:
    data = await SettingLogic.get_model_list(request, IBasicSet)
    return success_response(data)


@router.post("/basic", summary="更新基础配置")
async def post_basic(request: Request, data: IBasicSet) -> ResponseBase:
    result = await SettingLogic.save(request, "basic", data)
    return success_response(result)


@router.get("/basic/search-columns", summary="获取基础配置的展示字段")
async def get_basic_search_columns(request: Request) -> ResponseBase:
    data = SettingLogic.get_form_by_model(IBasicSet)
    return success_response(data)
