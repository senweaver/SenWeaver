from fastapi import APIRouter, Request

from senweaver.utils.response import ResponseBase, success_response

from ..settings import module

router = APIRouter(
    prefix="/ip", tags=["IpBlockSettings"], route_class=module.route_class
)
module.add_path_router("/block", router)


@router.get("/block", summary="获取详情")
async def get_ip_block(request: Request, size: int, page: int) -> ResponseBase:
    data = {"total": 0, "results": []}
    return success_response(data)


@router.get("/block/search-columns", summary="获取列表和创建更新字段")
async def get_ip_block_search_columns(request: Request) -> ResponseBase:
    data = [
        {
            "required": False,
            "read_only": False,
            "label": "主键ID",
            "write_only": False,
            "key": "id",
            "input_type": "string",
            "table_show": 1,
        },
        {
            "required": False,
            "read_only": False,
            "label": "拦截的IP",
            "max_length": 1024,
            "write_only": False,
            "key": "ip",
            "input_type": "string",
            "table_show": 1,
        },
        {
            "required": True,
            "read_only": False,
            "label": "创建时间",
            "write_only": False,
            "key": "created_time",
            "input_type": "datetime",
            "table_show": 1,
        },
    ]
    return success_response(data)
