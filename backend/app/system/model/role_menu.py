from sqlmodel import BigInteger, UniqueConstraint

from senweaver.core.models import PKMixin
from senweaver.db.models import Field


class RoleMenu(PKMixin, table=True):
    """角色菜单表"""

    __tablename__ = "system_role_menu"
    __table_args__ = (UniqueConstraint("role_id", "menu_id"), {"comment": "角色菜单"})
    role_id: int | None = Field(
        default=None, nullable=False, foreign_key="system_role.id", sa_type=BigInteger
    )
    menu_id: int | None = Field(
        default=None,
        nullable=False,
        index=True,
        foreign_key="system_menu.id",
        sa_type=BigInteger,
    )
