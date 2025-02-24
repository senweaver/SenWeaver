from typing import Any, Optional, Union

from sqlalchemy import JSON, TEXT, Boolean, String
from sqlmodel import BigInteger, Relationship, UniqueConstraint

from app.system.model.user import User
from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db.models import Field
from senweaver.utils.translation import _


class SystemMsgSubscriptionUser(PKMixin, table=True):
    __tablename__ = "notifications_system_subscription_user"
    __table_args__ = (
        UniqueConstraint("system_subscription_id", "user_id"),
        {"comment": "系统消息订阅人"},
    )
    system_subscription_id: int | None = Field(
        default=None,
        nullable=False,
        foreign_key="notifications_system_subscription.id",
        sa_type=BigInteger,
    )
    user_id: int | None = Field(
        default=None,
        nullable=False,
        index=True,
        foreign_key="system_user.id",
        sa_type=BigInteger,
    )


class SystemMsgSubscriptionBase(BaseMixin):
    message_type: str = Field(
        ..., title="消息类型", nullable=False, unique=True, sa_type=String(128)
    )
    receive_backends: Any = Field(
        default=list, sa_type=JSON, title="消息后端", nullable=False
    )


class SystemMsgSubscription(AuditMixin, SystemMsgSubscriptionBase, PKMixin, table=True):
    __tablename__ = "notifications_system_subscription"
    __table_args__ = ({"comment": "系统消息订阅"},)
    users: list["User"] = Relationship(
        link_model=SystemMsgSubscriptionUser,
        sa_relationship_kwargs=dict(
            primaryjoin="SystemMsgSubscriptionUser.system_subscription_id==SystemMsgSubscription.id",
            secondaryjoin="SystemMsgSubscriptionUser.user_id==User.id",
            foreign_keys="[SystemMsgSubscriptionUser.system_subscription_id,SystemMsgSubscriptionUser.user_id]",
        ),
    )


class UserMsgSubscriptionBase(BaseMixin):
    message_type: str = Field(
        ..., title="消息类型", nullable=False, sa_type=String(128)
    )
    receive_backends: Any = Field(
        default=list, sa_type=JSON, title="消息后端", nullable=False
    )
    user_id: int | None = Field(
        ..., nullable=False, foreign_key="system_user.id", sa_type=BigInteger
    )


class UserMsgSubscription(AuditMixin, UserMsgSubscriptionBase, PKMixin, table=True):
    __tablename__ = "notifications_user_subscription"
    __table_args__ = (
        UniqueConstraint("user_id", "message_type"),
        {"comment": "用户消息订阅"},
    )
    user: Optional["User"] = Relationship(
        sa_relationship_kwargs=dict(
            primaryjoin="UserMsgSubscription.user_id==User.id",
            foreign_keys="UserMsgSubscription.user_id",
        )
    )
