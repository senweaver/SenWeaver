from typing import Any, Optional

from sqlalchemy import JSON, String
from sqlmodel import Relationship

from senweaver.core.models import AuditMixin, BaseMixin, ModeTypeMixin, PKMixin
from senweaver.db.models import Field
from senweaver.utils.partial import optional

from .dept_rule import DeptRule
from .menu_rule import MenuRule
from .user_rule import UserRule


class DataPermissionBase(BaseMixin, ModeTypeMixin):
    name: str = Field(
        default=...,
        max_length=128,
        nullable=False,
        unique=True,
        sa_type=String(128),
        title="名称",
    )
    rules: Any = Field(default=..., nullable=False, sa_type=JSON, title="配置值")
    is_active: bool | None = Field(default=True, title="激活状态")


class DataPermission(AuditMixin, DataPermissionBase, PKMixin, table=True):
    __tablename__ = "system_data_permission"
    __table_args__ = {"comment": "数据权限"}
    users: list["User"] = Relationship(
        back_populates="rules",
        link_model=UserRule,
        sa_relationship_kwargs=dict(
            lazy="noload",
            primaryjoin="UserRule.datapermission_id==DataPermission.id",
            secondaryjoin="UserRule.user_id==User.id",
            foreign_keys="[UserRule.user_id,UserRule.datapermission_id]",
        ),
    )
    depts: list["Dept"] = Relationship(
        back_populates="rules",
        link_model=DeptRule,
        sa_relationship_kwargs=dict(
            lazy="noload",
            primaryjoin="DeptRule.datapermission_id==DataPermission.id",
            secondaryjoin="DeptRule.dept_id==Dept.id",
            foreign_keys="[DeptRule.dept_id,DeptRule.datapermission_id]",
        ),
    )
    menu: list["Menu"] = Relationship(
        back_populates="rules",
        link_model=MenuRule,
        sa_relationship_kwargs=dict(
            lazy="noload",
            primaryjoin="MenuRule.datapermission_id==DataPermission.id",
            secondaryjoin="MenuRule.menu_id==Menu.id",
            foreign_keys="[MenuRule.menu_id,MenuRule.datapermission_id]",
        ),
    )


@optional()
class DataPermissionRead(AuditMixin, DataPermissionBase, PKMixin):
    pass


class DataPermissionCreate(DataPermissionBase):
    pass


class DataPermissionCreateInternal(DataPermissionBase):
    pass


@optional()
class DataPermissionUpdate(DataPermissionBase):
    pass
