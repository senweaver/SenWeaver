from sqlmodel import BigInteger, UniqueConstraint

from senweaver.core.models import PKMixin
from senweaver.db.models import Field, SQLModel
from senweaver.utils.partial import optional


class DeptRuleBase(SQLModel):
    dept_id: int | None = Field(
        default=None, nullable=False, foreign_key="system_dept.id", sa_type=BigInteger
    )
    datapermission_id: int | None = Field(
        default=None,
        nullable=False,
        index=True,
        foreign_key="system_data_permission.id",
        sa_type=BigInteger,
    )


class DeptRule(DeptRuleBase, PKMixin, table=True):
    __tablename__ = "system_dept_rule"
    __table_args__ = (
        UniqueConstraint("dept_id", "datapermission_id"),
        {"comment": "部门关联数据权限"},
    )
