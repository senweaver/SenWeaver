from fastapi import APIRouter

from senweaver import senweaver_router
from senweaver.core.helper import FieldConfig, RelationConfig, SenweaverFilter

from ..logic.notice_logic import NoticeLogic
from ..model.notice import Notice
from ..model.notice_user_read import NoticeUserRead
from ..notifications import module

router = APIRouter(tags=["notice-messages"], route_class=module.route_class)


filter_config = SenweaverFilter(
    # 查询
    filters={
        "id": None,
        "title__contains": None,
        "message__contains": None,
        "notice_type": None,
        "level": None,
        "publish": None,
    },
    fields=[
        "id",
        "title",
        "level",
        "publish",
        "notice_type",
        "notice_user",
        "notice_dept",
        "notice_role",
        "message",
        "created_time",
        "user_count",
        "read_user_count",
        "extra_json",
        "files",
    ],
    table_fields=[
        "id",
        "title",
        "notice_type",
        "read_user_count",
        "publish",
        "created_time",
    ],
    extra_kwargs={
        "extra_json": {"read_only": True},
    },
    ordering_fields=["updated_time", "created_time"],
    relationships=[
        RelationConfig(
            rel=Notice.notice_user,
            attrs=["id", "username"],
            format="{username}",
            many=True,
            label="被通知用户",
            read_only=False,
            required=True,
            write_only=False,
            input_type="api-search-user",
            callbacks={"select": NoticeLogic.get_notice_user},
            relationships=[
                RelationConfig(rel=NoticeUserRead.owner, attrs=["id", "username"])
            ],
        ),
        RelationConfig(
            rel=Notice.notice_dept,
            attrs=["id", "name"],
            format="{name}",
            label="被通知部门",
            many=True,
            input_type="api-search-dept",
        ),
        RelationConfig(
            rel=Notice.notice_role,
            attrs=["id", "name"],
            format="{name}",
            label="被通知角色",
            many=True,
            read_only=False,
            input_type="api-search-role",
        ),
    ],
    extra_fields=[
        FieldConfig(
            key="files",
            default=[],
            annotation=list,
            write_only=True,
            label="上传的附件",
            input_type="json",
        ),
        FieldConfig(
            key="user_count",
            default=0,
            label="用户数量",
            read_only=True,
            annotation=int,
            input_type="field",
            callbacks={"select": NoticeLogic.get_user_count},
        ),
        FieldConfig(
            key="read_user_count",
            default=0,
            annotation=int,
            read_only=True,
            label="已读用户数量",
            input_type="field",
            callbacks={"select": NoticeLogic.get_read_user_count},
        ),
    ],
)
_router = senweaver_router(
    module=module,
    model=Notice,
    path=f"/notice-messages",
    filter_config=filter_config,
    callbacks={"save": NoticeLogic.save},
)
router.include_router(_router)
