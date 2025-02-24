from sqlmodel import BigInteger, UniqueConstraint

from senweaver.core.models import PKMixin
from senweaver.db.models import Field


class NoticeFile(PKMixin, table=True):
    __tablename__ = "notifications_notice_file"
    __table_args__ = (
        UniqueConstraint("notice_id", "attachment_id"),
        {"comment": "消息附件"},
    )
    notice_id: int | None = Field(
        default=None,
        nullable=False,
        foreign_key="notifications_notice.id",
        sa_type=BigInteger,
    )
    attachment_id: int | None = Field(
        default=None,
        nullable=False,
        index=True,
        foreign_key="system_attachment.id",
        sa_type=BigInteger,
    )
