from typing import Annotated, Optional

from fastapi import APIRouter, Body, Path, Query, Request

from senweaver.utils.response import ResponseBase, success_response

from ..logic.notification_logic import NotificationLogic
from ..notifications import module
from ..schema.notification import ISystemMsgSubscriptionUpdate

router = APIRouter(tags=["SystemMsgSubscription"], route_class=module.route_class)


@router.get("/system-msg-subscription/backends", summary="获取消息通知后端")
async def get_system_backends(request: Request) -> ResponseBase:
    data = await NotificationLogic.get_backends(request)
    return success_response(data)


@router.get("/system-msg-subscription", summary="获取系统消息订阅")
async def get_system_msg_subscription(request: Request) -> ResponseBase:
    data = await NotificationLogic.get_system_msg_subscription(request)
    return success_response(data)


@router.post("/system-msg-subscription/{message_type}", summary="获取系统消息订阅列表")
async def save_system_msg_subscription(
    request: Request,
    message_type: Annotated[str, Path(...)],
    data: ISystemMsgSubscriptionUpdate,
) -> ResponseBase:
    result = await NotificationLogic.save_system_msg_subscription(
        request, message_type, data
    )
    return success_response(result)


@router.get("/user-msg-subscription/backends", summary="获取消息通知后端")
async def get_user_backends(request: Request) -> ResponseBase:
    data = await NotificationLogic.get_backends(request)
    return success_response(data)


@router.get("/user-msg-subscription", summary="获取用户消息订阅")
async def get_user_msg_subscription(request: Request) -> ResponseBase:
    data = await NotificationLogic.get_user_msg_subscription(request)
    return success_response(data)
