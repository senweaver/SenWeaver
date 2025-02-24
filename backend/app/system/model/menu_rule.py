from sqlmodel import BigInteger, ForeignKey, UniqueConstraint

from senweaver.core.models import PKMixin
from senweaver.db.models import Field, SQLModel
from senweaver.utils.partial import optional


class MenuRuleBase(SQLModel):
    menu_id: int | None = Field(
        default=None,
        nullable=False,
        index=True,
        foreign_key="system_menu.id",
        sa_type=BigInteger,
    )
    datapermission_id: int | None = Field(
        default=None,
        nullable=False,
        foreign_key="system_data_permission.id",
        sa_type=BigInteger,
    )


class MenuRule(MenuRuleBase, PKMixin, table=True):
    __tablename__ = "system_menu_rule"
    __table_args__ = (
        UniqueConstraint("menu_id", "datapermission_id"),
        {"comment": "菜单关联数据权限"},
    )
