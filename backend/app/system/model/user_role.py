from sqlmodel import BigInteger, UniqueConstraint

from senweaver.core.models import PKMixin
from senweaver.db.models import Field


class UserRole(PKMixin, table=True):
    """用户角色表"""

    __tablename__ = "system_user_role"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id"),
        {"comment": "用户关联角色"},
    )
    user_id: int | None = Field(
        default=None, nullable=False, foreign_key="system_user.id", sa_type=BigInteger
    )
    role_id: int | None = Field(
        default=None, nullable=False, foreign_key="system_role.id", sa_type=BigInteger
    )
