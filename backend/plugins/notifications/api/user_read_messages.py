from typing import Annotated

from fastapi import APIRouter, Body, Path, Request

from senweaver import senweaver_router
from senweaver.auth.security import requires_permissions
from senweaver.core.helper import FieldConfig, RelationConfig, SenweaverFilter
from senweaver.utils.response import ResponseBase, success_response

from ..logic.notice_logic import NoticeLogic
from ..model.notice_user_read import NoticeUserRead
from ..notifications import module
from ..schema.notice import IStateUpdate

router = APIRouter(tags=["user-read-messages"], route_class=module.route_class)


filter_config = SenweaverFilter(
    # 查询
    filters={
        "notice.id": None,
        "notice.title__contains": None,
        "owner.username": None,
        "owner_id": None,
        "notice.notice_type": None,
        "notice.level": None,
        "unread": None,
    },
    fields=["id", "notice_info", "notice_type", "owner", "unread", "updated_time"],
    read_only_fields=list(NoticeUserRead.__mapper__.all_orm_descriptors.keys()),
    ordering_fields=["updated_time", "created_time"],
    relationships=[
        RelationConfig(
            rel=NoticeUserRead.notice,
            attrs=["id", "level", "title", "notice_type", "message", "publish"],
            label="公告",
            read_only=True,
        ),
        RelationConfig(
            rel=NoticeUserRead.owner,
            attrs=["id", "username"],
            label="被通知用户",
            read_only=True,
        ),
    ],
    extra_fields=[
        FieldConfig(
            key="notice_info",
            default=0,
            label="用户数量",
            read_only=True,
            input_type="nested object",
            callbacks={"select": NoticeLogic.get_notice_info},
        )
    ],
)
_router = senweaver_router(
    module=module,
    model=NoticeUserRead,
    path="/user-read-messages",
    included_methods=["read_multi", "delete", "batch_delete", "search_fields"],
    filter_config=filter_config,
)
router.include_router(_router)


@router.get("/user-read-messages/search-columns", summary="已读消息列")
async def get_search_columns(request: Request) -> ResponseBase:
    data = [
        {
            "required": False,
            "read_only": True,
            "label": "ID",
            "write_only": False,
            "key": "id",
            "input_type": "integer",
            "table_show": 1,
        },
        {
            "required": False,
            "read_only": True,
            "label": "通知内容",
            "write_only": False,
            "children": {
                "id": {
                    "type": "integer",
                    "required": False,
                    "read_only": True,
                    "label": "ID",
                    "write_only": False,
                },
                "title": {
                    "type": "string",
                    "required": True,
                    "read_only": False,
                    "label": "通知标题",
                    "max_length": 255,
                    "write_only": False,
                },
                "level": {
                    "type": "labeled_choice",
                    "required": False,
                    "default": "info",
                    "read_only": False,
                    "label": "通知级别",
                    "write_only": False,
                    "choices": [
                        {"value": "info", "label": "普遍通知"},
                        {"value": "primary", "label": "一般通知"},
                        {"value": "success", "label": "成功通知"},
                        {"value": "danger", "label": "重要通知"},
                    ],
                },
                "publish": {
                    "type": "boolean",
                    "required": False,
                    "default": True,
                    "read_only": False,
                    "label": "发布",
                    "write_only": False,
                },
                "notice_type": {
                    "type": "labeled_choice",
                    "required": False,
                    "default": 2,
                    "read_only": False,
                    "label": "通知类型",
                    "write_only": False,
                    "choices": [
                        {"value": 0, "label": "系统通知"},
                        {"value": 1, "label": "系统公告"},
                        {"value": 2, "label": "用户通知"},
                        {"value": 3, "label": "部门通知"},
                        {"value": 4, "label": "角色通知"},
                    ],
                },
                "message": {
                    "type": "string",
                    "required": False,
                    "read_only": False,
                    "label": "通知内容",
                    "write_only": False,
                },
            },
            "key": "notice_info",
            "help_text": "",
            "input_type": "nested object",
            "table_show": 1,
        },
        {
            "required": False,
            "read_only": True,
            "label": "通知类型",
            "write_only": False,
            "key": "notice_type",
            "input_type": "string",
            "table_show": 1,
        },
        {
            "required": False,
            "read_only": True,
            "label": "用户",
            "write_only": False,
            "key": "owner",
            "help_text": "",
            "choices": [],
            "input_type": "object_related_field",
            "table_show": 1,
        },
        {
            "required": False,
            "read_only": True,
            "label": "未读",
            "write_only": False,
            "key": "unread",
            "help_text": "",
            "input_type": "boolean",
            "table_show": 1,
        },
        {
            "required": False,
            "read_only": True,
            "label": "更新时间",
            "write_only": False,
            "key": "updated_time",
            "help_text": "",
            "input_type": "datetime",
            "table_show": 1,
        },
    ]
    return success_response(data)


@router.post("/user-read-messages/{id}/state", summary="设置已读")
@requires_permissions(f"{module.get_auth_str(NoticeUserRead.__name__, "state")}")
async def set_read_state(
    request: Request, id: Annotated[int, Path(...)], state: IStateUpdate
) -> ResponseBase:
    await NoticeLogic.set_read_state(request, id, state)
    return success_response()
