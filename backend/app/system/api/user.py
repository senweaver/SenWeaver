from pathlib import Path as FilePath
from typing import Annotated

from fastapi import APIRouter, Depends, File, Path, UploadFile
from fastapi.requests import Request

from app.system.logic.user_logic import UserLogic
from app.system.model.user import User
from app.system.schema.user import IUserEmpower, IUserResetPassword
from senweaver import senweaver_router
from senweaver.auth.security import requires_permissions
from senweaver.core.helper import RelationConfig, SenweaverFilter
from senweaver.utils.response import ResponseBase, success_response

from ..system import module

path = FilePath(__file__)

router = APIRouter(tags=["用户"], route_class=module.route_class)

filter_config = SenweaverFilter(
    filters={
        "id": None,
        "username": None,
        "nickname": None,
        "phone": None,
        "is_active": None,
        "gender": None,
        "mode_type": None,
        "dept": None,
    },
    fields=[
        "id",
        "avatar",
        "username",
        "nickname",
        "phone",
        "email",
        "gender",
        "block",
        "is_active",
        "password",
        "dept",
        "description",
        "last_login",
        "created_time",
        "roles",
        "rules",
        "mode_type",
    ],
    read_only_fields=[
        "last_login",
        "created_time",
        "rules",
        "id",
        "avatar",
        "roles",
        "password_time",
        "group_id",
    ],
    table_fields=[
        "id",
        "avatar",
        "username",
        "nickname",
        "gender",
        "block",
        "is_active",
        "dept",
        "phone",
        "last_login",
        "created_time",
        "roles",
        "rules",
    ],
    extra_kwargs={
        "last_login": {"read_only": True},
        "created_time": {"read_only": True},
        "avatar": {"read_only": True},
        "dept": {"required": True},
        "password": {"write_only": True},
    },
    ordering_fields=["created_time", "last_login"],
    relationships=[
        RelationConfig(
            rel=User.dept,
            attrs=["id", "name", "parent_id", "label"],
            format="{name}",
            label="所属部门",
        ),
        RelationConfig(
            rel=User.roles,
            attrs=["id", "name", "code", "label"],
            format="{name}",
            label="角色权限",
            read_only=False,
        ),
        RelationConfig(
            rel=User.rules,
            attrs=["id", "name", "label", "get_mode_type_display"],
            format="{name}",
            label="数据权限",
            read_only=False,
        ),
    ],
)
_router = senweaver_router(
    module=module,
    model=User,
    path=f"/user",
    filter_config=filter_config,
    custom_router=UserLogic.add_custom_router,
)

router.include_router(_router)
