from sqlmodel import BigInteger, UniqueConstraint

from senweaver.core.models import PKMixin
from senweaver.db.models import Field


class NoticeDept(PKMixin, table=True):
    __tablename__ = "notifications_notice_dept"
    __table_args__ = (
        UniqueConstraint("notice_id", "dept_id"),
        {"comment": "消息通知部门"},
    )
    notice_id: int | None = Field(
        default=None,
        nullable=False,
        foreign_key="notifications_notice.id",
        sa_type=BigInteger,
    )
    dept_id: int | None = Field(
        default=None,
        nullable=False,
        index=True,
        foreign_key="system_dept.id",
        sa_type=BigInteger,
    )
