from fastapi import Request
from pydantic import model_serializer, model_validator
from pydantic.fields import FieldInfo
from sqlalchemy.ext.asyncio import AsyncSession

from senweaver import SenweaverCRUD
from senweaver.core.helper import RelationConfig
from senweaver.db.helper import senweaver_model_serializer, senweaver_model_validator
from senweaver.helper import create_schema_by_schema

from ..model.notification import SystemMsgSubscription, UserMsgSubscription
from ..schema.notification import ISystemMsgSubscriptionUpdate


class NotificationLogic:
    @classmethod
    async def get_backends(cls, request: Request):
        return [{"value": "site_msg", "label": "站内信"}]

    @classmethod
    async def save_system_msg_subscription(
        cls, request: Request, message_type: str, data: ISystemMsgSubscriptionUpdate
    ):
        db: AsyncSession = request.auth.db.session
        crud = SenweaverCRUD(
            SystemMsgSubscription,
            relationships=[RelationConfig(rel=SystemMsgSubscription.users)],
        )
        await crud.update(db, data, message_type=message_type)
        children = await cls.get_system_msg_subscription_data(
            db, message_type=message_type
        )
        return children[0] if children else None

    @classmethod
    async def get_system_msg_subscription_data(cls, db: AsyncSession, **kwargs):
        relationship = RelationConfig(
            rel=SystemMsgSubscription.users,
            attrs=["id", "username", "nickname"],
            format="{nickname}({username})",
        )
        crud = SenweaverCRUD(SystemMsgSubscription, relationships=[relationship])
        read_extra_fields = {}
        json_schema_extra = {"sw_is_relationship": True}
        read_extra_fields["users"] = FieldInfo(
            annotation=relationship.annotation,
            default=None,
            title=relationship.label,
            description=relationship.description,
            nullable=True,
            json_schema_extra=json_schema_extra,
        )
        select_schema = create_schema_by_schema(
            SystemMsgSubscription,
            name=f"{SystemMsgSubscription.__name__}Read",
            include=set(["id", "users", "message_type", "receive_backends"]),
            set_optional=True,
            extra_fields=read_extra_fields,
            validators={
                "_senweaver_model_serializer": model_serializer(mode="wrap")(
                    senweaver_model_serializer
                )
            },
        )
        result = await crud.get_multi(
            db=db,
            limit=None,
            schema_to_select=select_schema,
            return_as_model=True,
            **kwargs,
        )
        children = []
        subscriptions = result["data"]
        for sub in subscriptions:
            users = []
            receivers = []
            for user in sub.users:
                users.append(user.id)
                receivers.append(user)
            children.append(
                {
                    "message_type": sub.message_type,
                    "message_type_label": "监控告警",
                    "receive_backends": sub.receive_backends,
                    "users": users,
                    "receivers": receivers,
                }
            )
        return children

    @classmethod
    async def get_system_msg_subscription(cls, request: Request):
        db: AsyncSession = request.auth.db.session
        crud = SenweaverCRUD(SystemMsgSubscription)
        result = await crud.get_multi(db, limit=None, return_total_count=False)
        if not result["data"]:
            object = SystemMsgSubscription(
                message_type="ServerPerformanceMessage", receive_backends=["email"]
            )
            await crud.create(db, object)
        children = await cls.get_system_msg_subscription_data(db)
        data = [
            {"category": "Monitor", "category_label": "资源监控", "children": children}
        ]
        return data

    @classmethod
    async def get_user_msg_subscription(cls, request: Request):
        db: AsyncSession = request.auth.db.session
        crud = SenweaverCRUD(UserMsgSubscription)
        current_user = request.user
        result = await crud.get_multi(db, limit=None, return_total_count=False)
        if not result["data"]:
            await crud.create(
                db,
                UserMsgSubscription(
                    message_type="ImportDataMessage",
                    receive_backends=[],
                    user_id=current_user.id,
                ),
            )
            await crud.create(
                db,
                UserMsgSubscription(
                    message_type="BatchDeleteDataMessage",
                    receive_backends=[],
                    user_id=current_user.id,
                ),
            )
            await crud.create(
                db,
                UserMsgSubscription(
                    message_type="DifferentCityLoginMessage",
                    receive_backends=[],
                    user_id=current_user.id,
                ),
            )
            await crud.create(
                db,
                UserMsgSubscription(
                    message_type="ResetPasswordSuccessMsg",
                    receive_backends=[],
                    user_id=current_user.id,
                ),
            )
        user_data = {
            "nickname": current_user.nickname,
            "id": current_user.id,
            "username": current_user.username,
            "label": f"{current_user.nickname}({current_user.username})",
        }
        data = [
            {
                "category": "Task Message",
                "category_label": "任务通知",
                "children": [
                    {
                        "message_type": "ImportDataMessage",
                        "message_type_label": "导入数据通知",
                        "user": 1,
                        "receive_backends": [],
                        "receivers": user_data,
                    },
                    {
                        "message_type": "BatchDeleteDataMessage",
                        "message_type_label": "批量删除数据通知",
                        "user": 1,
                        "receive_backends": [],
                        "receivers": user_data,
                    },
                ],
            },
            {
                "category": "AccountSecurity",
                "category_label": "账号安全",
                "children": [
                    {
                        "message_type": "DifferentCityLoginMessage",
                        "message_type_label": "异地登录提醒",
                        "user": 1,
                        "receive_backends": [],
                        "receivers": user_data,
                    },
                    {
                        "message_type": "ResetPasswordSuccessMsg",
                        "message_type_label": "重置密码提醒",
                        "user": 1,
                        "receive_backends": [],
                        "receivers": user_data,
                    },
                ],
            },
        ]
        return data


notification_logic = NotificationLogic()
