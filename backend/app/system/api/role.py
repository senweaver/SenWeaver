from pathlib import Path as FilePath
from typing import Annotated, Any, List, Optional, Union

from fastapi import APIRouter, Depends, Path
from fastapi.requests import Request

from app.system.logic.role_logic import RoleLogic
from app.system.model.role import Role
from senweaver import senweaver_router
from senweaver.core.helper import FieldConfig, SenweaverFilter

from ..system import module

path = FilePath(__file__)
router = APIRouter(tags=["角色"], route_class=module.route_class)

filter_config = SenweaverFilter(
    filters={
        "name__contains": None,
        "code": None,
        "is_active": None,
        "description": None,
    },
    fields=[
        "id",
        "name",
        "code",
        "is_active",
        "description",
        "menu",
        "updated_time",
        "field",
        "fields",
    ],
    table_fields=["id", "name", "code", "is_active", "description", "updated_time"],
    read_only_fields=["id"],
    ordering_fields=["updated_time", "name", "created_time"],
    extra_fields=[
        FieldConfig(
            key="menu",
            default=[],
            label="菜单",
            annotation=Union[List[int], List[dict]],
            input_type="input",
            required=True,
            read_only=False,
            many=True,
        ),
        FieldConfig(
            key="field", default=[], label="字段", read_only=True, input_type="field"
        ),
        FieldConfig(
            key="fields",
            default={},
            write_only=True,
            annotation=dict[int, List[int]],
            label="字段",
            input_type="nested object",
            required=True,
            extra_kwargs={
                "child": {
                    "type": "field",
                    "required": True,
                    "read_only": False,
                    "write_only": False,
                }
            },
        ),
    ],
)
_router = senweaver_router(
    module=module,
    model=Role,
    path=f"/{path.stem}",
    filter_config=filter_config,
    callbacks={
        "create": RoleLogic.create,
        "update": RoleLogic.update,
        "read": RoleLogic.read,
    },
)
router.include_router(_router)
