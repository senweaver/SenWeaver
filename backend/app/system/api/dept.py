from pathlib import Path as FilePath

from fastapi import APIRouter

from app.system.model.dept import Dept
from senweaver import senweaver_router
from senweaver.core.helper import FieldConfig, RelationConfig, SenweaverFilter

from ..logic.dept_logic import DeptLogic
from ..system import module

path = FilePath(__file__)


router = APIRouter(tags=["部门"], route_class=module.route_class)
filter_config = SenweaverFilter(
    filters={
        "id": None,
        "is_active": None,
        "name": None,
        "code": None,
        "mode_type": None,
        "auto_bind": None,
        "description": None,
    },
    fields=[
        "id",
        "name",
        "code",
        "parent",
        "rank",
        "is_active",
        "roles",
        "user_count",
        "rules",
        "mode_type",
        "auto_bind",
        "description",
        "created_time",
    ],
    table_fields=[
        "name",
        "id",
        "code",
        "user_count",
        "rank",
        "mode_type",
        "auto_bind",
        "is_active",
        "roles",
        "rules",
        "created_time",
    ],
    ordering_fields=["created_time", "rank"],
    relationships=[
        RelationConfig(rel=Dept.parent, attrs=["id", "name", "parent_id", "label"]),
        RelationConfig(
            rel=Dept.rules,
            attrs=["id", "name", "label", "get_mode_type_display"],
            format="{name}",
            label="数据权限",
            read_only=False,
        ),
        RelationConfig(
            rel=Dept.roles,
            attrs=["id", "name", "code", "label"],
            format="{name}",
            label="角色权限",
            read_only=False,
        ),
    ],
    extra_fields=[
        FieldConfig(
            key="user_count",
            default=0,
            label="人员数量",
            annotation=int,
            input_type="field",
            callbacks={"select": DeptLogic.get_user_count},
            read_only=True,
        ),
    ],
)

_router = senweaver_router(
    module=module,
    model=Dept,
    path=f"/{path.stem}",
    sort_columns="rank",
    filter_config=filter_config,
    custom_router=DeptLogic.add_custom_router,
)
router.include_router(_router)
