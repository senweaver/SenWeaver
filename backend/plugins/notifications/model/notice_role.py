from sqlmodel import BigInteger, UniqueConstraint

from senweaver.core.models import PKMixin
from senweaver.db.models import Field


class NoticeRole(PKMixin, table=True):
    __tablename__ = "notifications_notice_role"
    __table_args__ = (
        UniqueConstraint("notice_id", "role_id"),
        {"comment": "消息通知角色"},
    )
    notice_id: int | None = Field(
        default=None,
        nullable=False,
        foreign_key="notifications_notice.id",
        sa_type=BigInteger,
    )
    role_id: int | None = Field(
        default=None,
        nullable=False,
        index=True,
        foreign_key="system_role.id",
        sa_type=BigInteger,
    )
