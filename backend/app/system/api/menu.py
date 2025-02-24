from pathlib import Path as FilePath

from app.system.model.menu import Menu
from app.system.model.menu_meta import MenuMeta
from fastapi import APIRouter
from senweaver import senweaver_router
from senweaver.core.helper import RelationConfig, SenweaverFilter

from ..logic.menu_logic import MenuLogic
from ..system import module

path = FilePath(__file__)

router = APIRouter(tags=["菜单"], route_class=module.route_class)
open_router = APIRouter(tags=["菜单"], route_class=module.route_class)
filter_config = SenweaverFilter(
    filters={"name": None},
    fields=[
        "id",
        "name",
        "rank",
        "path",
        "component",
        "meta",
        "parent",
        "menu_type",
        "is_active",
        "model",
        "method",
    ],
    extra_kwargs={"rank": {"read_only": True}},
    ordering_fields=["updated_time", "name", "created_time", "rank"],
    relationships=[
        RelationConfig(rel=Menu.parent, attrs=["id", "name"], label="上级菜单"),
        RelationConfig(
            rel=Menu.meta,
            exclude=["creator", "modifier", "id"],
            label="菜单元数据",
            is_filter=True,
        ),
        RelationConfig(rel=Menu.model, attrs=["id", "name", "label"], label="模型名称"),
    ],
)
_router = senweaver_router(
    module=module,
    model=Menu,
    path=f"/{path.stem}",
    filter_config=filter_config,
    sort_columns="rank",
    custom_router=MenuLogic.add_custom_router,
)
"""
推荐使用custom_router=MenuLogic.add_custom_router的方式添加自定义路由
如果有其他特殊的自定义路由，注意前面用_router
@_router.post("/menu/other", summary="other")
@requires_permissions(f"{module.get_path_auth_str("/menu/other", "other")}")
"""
router.include_router(_router)
