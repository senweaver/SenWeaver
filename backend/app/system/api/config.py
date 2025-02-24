from pathlib import Path as FilePath
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Path, Request

from app.system.model.config import Config
from app.system.model.system_config import SystemConfig
from app.system.model.user_config import UserConfig
from senweaver import senweaver_router
from senweaver.auth.security import requires_permissions
from senweaver.core.helper import SenweaverFilter
from senweaver.utils.response import ResponseBase, success_response

from ..logic.config_logic import ConfigLogic
from ..system import module

path = FilePath(__file__)

router = APIRouter(tags=["配置"], route_class=module.route_class)
open_router = APIRouter(tags=["配置"], route_class=module.route_class)

filter_config = SenweaverFilter(
    filters={"name": None, "key": None, "group": None, "is_active": None, "id": None}
)
_router = senweaver_router(
    module=module, model=Config, path=f"/{path.stem}", filter_config=filter_config
)
router.include_router(_router)

system_filter_config = SenweaverFilter(
    filters={
        "id": None,
        "is_active": None,
        "key__contains": None,
        "inherit": None,
        "access": None,
        "description": None,
    },
    fields=[
        "id",
        "key",
        "value",
        "cache_value",
        "is_active",
        "inherit",
        "access",
        "description",
        "created_time",
    ],
    read_only_fields=["id"],
    ordering_fields=["created_time"],
)
system_router = senweaver_router(
    module=module,
    model=SystemConfig,
    path=f"/{path.stem}/system",
    filter_config=system_filter_config,
)
router.include_router(system_router)
user_filter_config = SenweaverFilter(
    filters={
        "id": None,
        "is_active": None,
        "key__contains": None,
        "access": None,
        "owner_id": None,
        "description": None,
    },
    fields=[
        "id",
        "config_user",
        "owner_id",
        "key",
        "value",
        "cache_value",
        "is_active",
        "access",
        "description",
        "created_time",
    ],
    read_only_fields=["id", "owner_id"],
    extra_kwargs={"owner_id": {"input_type": "api-search-user"}},
    ordering_fields=["created_time"],
)
user_router = senweaver_router(
    module=module,
    model=UserConfig,
    path=f"/{path.stem}/user",
    filter_config=user_filter_config,
)
router.include_router(user_router)


@open_router.get("/configs/{key}", summary="配置信息")
async def get_config(
    key: Annotated[str, Path(...)],
    request: Request,
) -> ResponseBase:
    data = await ConfigLogic.get_config(request, key)
    return success_response(**data)


@router.post("/configs/{key}", summary="配置信息")
async def save_config(
    request: Request,
    key: Annotated[str, Path(...)],
    data: Any = Body(...),  # type: ignore
) -> ResponseBase:
    result = await ConfigLogic.save_config(request, key, data)
    return success_response(**result)


@router.post("/config/system/{id}/invalid", summary="使配置值缓存失效")
@requires_permissions(f"{module.get_auth_str(SystemConfig.__name__, "invalid")}")
async def invalid_system_config(
    id: Annotated[int, Path(...)],
    request: Request,
) -> ResponseBase:
    return success_response()


@router.post("/config/user/{id}/invalid", summary="使配置值缓存失效")
@requires_permissions(f"{module.get_auth_str(UserConfig.__name__, "invalid")}")
async def invalid_user_config(
    id: Annotated[int, Path(...)],
    request: Request,
) -> ResponseBase:
    return success_response()
