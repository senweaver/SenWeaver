from sqlmodel import BigInteger, UniqueConstraint

from senweaver.core.models import PKMixin
from senweaver.db.models import Field


class FieldPermissionField(PKMixin, table=True):
    """字段权限表"""

    __tablename__ = "system_fieldpermission_field"
    __table_args__ = (
        UniqueConstraint("fieldpermission_id", "modelfield_id"),
        {"comment": "字段权限表"},
    )
    fieldpermission_id: int | None = Field(
        default=None,
        nullable=False,
        foreign_key="system_fieldpermission.id",
        sa_type=BigInteger,
    )
    modelfield_id: int | None = Field(
        default=None,
        nullable=False,
        index=True,
        foreign_key="system_modelfield.id",
        sa_type=BigInteger,
    )
