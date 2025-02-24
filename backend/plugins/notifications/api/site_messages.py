from fastapi import APIRouter, Request
from sqlalchemy.orm import aliased

from senweaver import senweaver_router
from senweaver.auth.security import requires_permissions
from senweaver.core.helper import FieldConfig, RelationConfig, SenweaverFilter
from senweaver.utils.response import ResponseBase, success_response

from ..logic.notice_logic import NoticeLogic
from ..model.notice import Notice
from ..model.notice_user_read import NoticeUserRead
from ..notifications import module
from ..schema.notice import INoticeBatchRead

router = APIRouter(tags=["site-messages"], route_class=module.route_class)


filter_config = SenweaverFilter(
    # 查询
    filters={
        "id": None,
        "title__contains": None,
        "message__contains": None,
        "notice_type": None,
        "level": None,
        "unread": None,
    },
    backend_filters={"publish": True},
    fields=["id", "level", "title", "message", "created_time", "unread", "notice_type"],
    table_fields=["id", "title", "unread", "notice_type", "created_time"],
    read_only_fields=["id", "notice_user", "notice_type"],
    ordering_fields=["created_time"],
    extra_fields=[
        FieldConfig(
            key="unread",
            default=None,
            label="是否已读",
            read_only=True,
            annotation=bool,
            input_type="boolean",
        )
    ],
)
_router = senweaver_router(
    module=module,
    model=Notice,
    path=f"/site-messages",
    filter_config=filter_config,
    included_methods=["read_multi", "search_columns", "search_fields"],
    callbacks={"read_multi": NoticeLogic.get_site_message_list},
    custom_router=NoticeLogic.add_custom_router,
)
router.include_router(_router)


@router.post(f"/site-messages/batch-read", summary="批量已读消息")
@requires_permissions(f"{module.get_auth_str("UserNotice", "batchRead")}")
async def batch_read(
    request: Request,
    batch_read: INoticeBatchRead,
) -> ResponseBase:
    await NoticeLogic.read_message(request, batch_read.ids)
    return success_response()


@router.post(f"/site-messages/all-read", summary="全部已读消息")
@requires_permissions(f"{module.get_auth_str("UserNotice", "allRead")}")
async def all_read(request: Request) -> ResponseBase:
    await NoticeLogic.read_all_message(request)
    return success_response()
