from typing import Any, Optional

from sqlalchemy import JSON, String
from sqlmodel import BigInteger, Relationship, UniqueConstraint

from senweaver.core.models import AuditMixin, BaseMixin, ModeTypeMixin, PKMixin
from senweaver.db.models import Field
from senweaver.utils.partial import optional

from .fieldpermission_field import FieldPermissionField


class FieldPermissionBase(BaseMixin):
    role_id: int | None = Field(
        default=None, nullable=False, foreign_key="system_role.id", sa_type=BigInteger
    )
    menu_id: int | None = Field(
        default=None,
        nullable=False,
        foreign_key="system_menu.id",
        index=True,
        sa_type=BigInteger,
    )


class FieldPermission(AuditMixin, FieldPermissionBase, PKMixin, table=True):
    __tablename__ = "system_fieldpermission"
    __table_args__ = (UniqueConstraint("role_id", "menu_id"), {"comment": "字段权限"})
    role: Optional["Role"] = Relationship(
        back_populates="fields",
        sa_relationship_kwargs=dict(
            primaryjoin="FieldPermission.role_id==Role.id",
            foreign_keys="FieldPermission.role_id",
        ),
    )
    menu: Optional["Menu"] = Relationship(
        back_populates="fields",
        sa_relationship_kwargs=dict(
            primaryjoin="FieldPermission.menu_id==Menu.id",
            foreign_keys="FieldPermission.menu_id",
        ),
    )
    fields: list["ModelField"] = Relationship(
        back_populates="fieldpermissions",
        link_model=FieldPermissionField,
        sa_relationship_kwargs=dict(
            primaryjoin="FieldPermissionField.fieldpermission_id==FieldPermission.id",
            secondaryjoin="FieldPermissionField.modelfield_id==ModelField.id",
            foreign_keys="[FieldPermissionField.fieldpermission_id,FieldPermissionField.modelfield_id]",
        ),
    )


@optional()
class FieldPermissionRead(AuditMixin, FieldPermissionBase, PKMixin):
    pass


class FieldPermissionCreate(FieldPermissionBase):
    pass


class FieldPermissionCreateInternal(FieldPermissionBase):
    pass


@optional()
class FieldPermissionUpdate(FieldPermissionBase):
    pass
