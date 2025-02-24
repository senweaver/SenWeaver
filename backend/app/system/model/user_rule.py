from sqlmodel import BigInteger, UniqueConstraint

from senweaver.core.models import PKMixin
from senweaver.db.models import Field, SQLModel


class UserRuleBase(SQLModel):
    user_id: int | None = Field(
        default=None, nullable=False, foreign_key="system_user.id", sa_type=BigInteger
    )
    datapermission_id: int | None = Field(
        default=None,
        nullable=False,
        foreign_key="system_data_permission.id",
        sa_type=BigInteger,
    )


class UserRule(UserRuleBase, PKMixin, table=True):
    __tablename__ = "system_user_rule"
    __table_args__ = (
        UniqueConstraint("user_id", "datapermission_id"),
        {"comment": "用户关联数据权限"},
    )
