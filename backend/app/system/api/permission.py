from pathlib import Path as FilePath

from fastapi import APIRouter, Depends, Request

from senweaver import senweaver_router
from senweaver.core.helper import RelationConfig, SenweaverFilter

from ..logic.permission_logic import PermissionLogic
from ..model.data_permission import DataPermission
from ..model.menu import Menu
from ..system import module

path = FilePath(__file__)

router = APIRouter(tags=["data_permission"], route_class=module.route_class)
filter_config = SenweaverFilter(
    filters={
        "id": None,
        "name__contains": None,
        "mode_type": None,
        "is_active": None,
        "description": None,
    },
    fields=[
        "id",
        "name",
        "is_active",
        "mode_type",
        "menu",
        "description",
        "rules",
        "created_time",
    ],
    table_fields=[
        "id",
        "name",
        "mode_type",
        "is_active",
        "description",
        "created_time",
    ],
    relationships=[
        RelationConfig(
            rel=DataPermission.menu,
            attrs=["id", "name", "label", "meta__title", "parent_id", "value"],
            format="{name}",
            label="菜单",
            read_only=False,
            many=True,
            relationships=[RelationConfig(rel=Menu.meta, attrs=["title"])],
            description="若存在菜单权限，则该权限仅针对所选择的菜单权限生效",
        ),
    ],
    ordering_fields=["created_time"],
)
_router = senweaver_router(
    module=module,
    model=DataPermission,
    path=f"/permission",
    filter_config=filter_config,
)
router.include_router(_router)
