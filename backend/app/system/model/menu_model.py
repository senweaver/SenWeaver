from sqlmodel import BigInteger, ForeignKey, UniqueConstraint

from senweaver.core.models import PKMixin
from senweaver.db.models import Field


class MenuModel(PKMixin, table=True):
    """菜单模型表"""

    __tablename__ = "system_menu_model"
    __table_args__ = (
        UniqueConstraint("menu_id", "modelfield_id"),
        {"comment": "菜单模型"},
    )
    menu_id: int | None = Field(
        default=None, nullable=False, foreign_key="system_menu.id", sa_type=BigInteger
    )
    modelfield_id: int | None = Field(
        default=None,
        nullable=False,
        index=True,
        foreign_key="system_modelfield.id",
        sa_type=BigInteger,
    )
