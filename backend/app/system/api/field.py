from pathlib import Path as FilePath

from fastapi import APIRouter

from app.system.model.modelfield import ModelField
from senweaver import senweaver_router
from senweaver.core.helper import RelationConfig, SenweaverFilter

from ..logic.field_logic import FieldLogic
from ..system import module

path = FilePath(__file__)


router = APIRouter(tags=["字段/模型"], route_class=module.route_class)

filter_config = SenweaverFilter(
    filters={
        "id": None,
        "name": None,
        "label": None,
        "parent": None,
        "field_type": None,
        "created_time": None,
    },
    fields=[
        "id",
        "name",
        "label",
        "parent",
        "field_type",
        "created_time",
        "updated_time",
    ],
    ordering_fields=["created_time", "updated_time"],
    relationships=[
        RelationConfig(
            rel=ModelField.parent,
            attrs=["id", "name", "label"],
            format="{label}({id})",
            label="字段类型",
        )
    ],
)
_router = senweaver_router(
    module=module,
    model=ModelField,
    # included_methods=['create', 'read', 'update', 'delete'],
    deleted_methods=["choices"],
    path=f"/{path.stem}",
    filter_config=filter_config,
    sort_columns="-created_time",
    custom_router=FieldLogic.add_custom_router,
)
router.include_router(_router)
