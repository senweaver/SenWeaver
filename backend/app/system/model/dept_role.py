from sqlmodel import BigInteger, UniqueConstraint

from senweaver.core.models import PKMixin
from senweaver.db.models import Field


class DeptRole(PKMixin, table=True):
    """部门角色表"""

    __tablename__ = "system_dept_role"
    __table_args__ = (
        UniqueConstraint("dept_id", "role_id"),
        {"comment": "部门关联角色"},
    )
    dept_id: int | None = Field(
        default=None, nullable=False, foreign_key="system_dept.id", sa_type=BigInteger
    )
    role_id: int | None = Field(
        default=None,
        nullable=False,
        index=True,
        foreign_key="system_role.id",
        sa_type=BigInteger,
    )
