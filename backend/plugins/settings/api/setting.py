from fastapi import APIRouter

from senweaver import senweaver_router
from senweaver.core.helper import SenweaverFilter

from ..model import Setting
from ..settings import module

router = APIRouter(tags=["系统设置"], route_class=module.route_class)

filter_config = SenweaverFilter(
    filters={"id": None, "is_active": None, "name__contains": None, "category": None},
    fields=[
        "id",
        "name",
        "value",
        "category",
        "is_active",
        "encrypted",
        "created_time",
    ],
    read_only_fields=["id"],
    ordering_fields=["created_time", "category"],
)
_router = senweaver_router(
    module=module, model=Setting, path=f"/setting", filter_config=filter_config
)
router.include_router(_router)
