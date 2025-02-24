from pathlib import Path as FilePath

from fastapi import APIRouter
from sqlmodel import Field

from app.system.model.login_log import LoginLog
from app.system.model.operation_log import OperationLog
from senweaver import senweaver_router
from senweaver.auth.security import Authorizer
from senweaver.core.helper import FieldConfig, RelationConfig, SenweaverFilter

from ..system import module

path = FilePath(__file__)

router = APIRouter(tags=["日志管理"], route_class=module.route_class)

login_filter_config = SenweaverFilter(
    filters={
        "login_type": None,
        "ipaddress": None,
        "city": None,
        "system": None,
        "browser": None,
        "created_time": None,
    },
    fields=[
        "id",
        "creator",
        "ipaddress",
        "city",
        "login_type",
        "browser",
        "system",
        "agent",
        "status",
        "created_time",
    ],
    table_fields=[
        "id",
        "creator",
        "ipaddress",
        "city",
        "login_type",
        "browser",
        "system",
        "status",
        "created_time",
    ],
    read_only_fields=["id", "creator"],
    ordering_fields=["created_time"],
)
login_router = senweaver_router(
    module=module,
    model=LoginLog,
    deleted_methods=["create", "update"],
    path=f"/logs/login",
    filter_config=login_filter_config,
)
oper_filter_config = SenweaverFilter(
    filters={
        "module": None,
        "ipaddress": None,
        "system": None,
        "browser": None,
        "creator_id": None,
    },
    fields=[
        "id",
        "module",
        "creator",
        "ipaddress",
        "path",
        "method",
        "browser",
        "system",
        "cost_time",
        "response_code",
        "status_code",
        "body",
        "response_result",
        "created_time",
    ],
    table_fields=[
        "id",
        "module",
        "creator",
        "ipaddress",
        "path",
        "method",
        "browser",
        "system",
        "cost_time",
        "status_code",
        "created_time",
    ],
    read_only_fields=list(OperationLog.__mapper__.all_orm_descriptors.keys()),
    ordering_fields=["created_time", "updated_time", "cost_time"],
    relationships=[
        RelationConfig(
            rel=OperationLog.creator,
            attrs=["id", "username"],
            read_only=True,
            label="用户",
        )
    ],
    extra_kwargs={"creator_id": {"input_type": "api-search-user"}},
)
oper_router = senweaver_router(
    module=module,
    model=OperationLog,
    deleted_methods=["create", "update"],
    filter_config=oper_filter_config,
    path=f"/logs/operation",
)

user_login_router = senweaver_router(
    module=module,
    model=LoginLog,
    included_methods=["read_multi", "search_columns"],
    path=f"/user/log",
    filter_config=SenweaverFilter(
        backend_filters={"creator_id": Authorizer.get_current_user_id},
        fields=[
            "created_time",
            "status",
            "agent",
            "city",
            "login_type",
            "system",
            "browser",
            "ipaddress",
        ],
        table_fields=[
            "id",
            "creator",
            "ipaddress",
            "city",
            "login_type",
            "browser",
            "system",
            "status",
            "created_time",
        ],
        read_only_fields=list(LoginLog.__mapper__.all_orm_descriptors.keys()),
        ordering_fields=["created_time"],
    ),
)

router.include_router(login_router)
router.include_router(user_login_router)
router.include_router(oper_router)
