from typing import Optional

from sqlmodel import BigInteger, Boolean, Index, Relationship, UniqueConstraint

from app.system.model.user import User
from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db.models import Field


class NoticeUserReadBase(BaseMixin):
    unread: Optional[bool] = Field(default=True, sa_type=Boolean, title="未读")
    notice_id: int | None = Field(
        default=None,
        nullable=False,
        index=True,
        foreign_key="notifications_notice.id",
        sa_type=BigInteger,
    )
    owner_id: int | None = Field(
        default=None,
        nullable=False,
        index=True,
        foreign_key="system_user.id",
        sa_type=BigInteger,
    )

    @property
    def username(self):
        """用户名"""
        return self.owner.username if self.owner is not None else None

    @property
    def notice_type(self):
        """通知类型"""
        return self.notice.notice_type.label if self.notice is not None else ""


class NoticeUserRead(AuditMixin, NoticeUserReadBase, PKMixin, table=True):
    __tablename__ = "notifications_notice_user_read"
    __table_args__ = (
        UniqueConstraint("notice_id", "owner_id"),
        Index("ix_notice_owner_unread", "owner_id", "unread"),
        {"comment": "消息通知用户"},
    )
    owner: Optional["User"] = Relationship(
        sa_relationship_kwargs=dict(
            primaryjoin="NoticeUserRead.owner_id==User.id",
            foreign_keys="NoticeUserRead.owner_id",
        )
    )
    notice: Optional["Notice"] = Relationship(
        sa_relationship_kwargs=dict(
            back_populates="notice_user",
            primaryjoin="NoticeUserRead.notice_id==Notice.id",
            foreign_keys="NoticeUserRead.notice_id",
        )
    )
