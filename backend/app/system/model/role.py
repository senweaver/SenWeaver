from typing import Optional

from sqlmodel import Relationship

from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db.models import Field
from senweaver.utils.partial import optional

from .dept_role import DeptRole
from .fieldpermission import FieldPermission
from .role_menu import RoleMenu
from .user_role import UserRole


class RoleBase(BaseMixin):
    name: str = Field(max_length=64, nullable=False, unique=True, title="角色名称")
    code: str = Field(
        max_length=64, nullable=False, unique=True, index=True, title="角色编码"
    )
    is_active: bool = Field(title="激活状态", default=True)


class Role(AuditMixin, RoleBase, PKMixin, table=True):
    """角色"""

    __tablename__ = "system_role"
    __table_args__ = {"comment": "角色"}
    users: list["User"] = Relationship(
        back_populates="roles",
        link_model=UserRole,
        sa_relationship_kwargs=dict(
            lazy="noload",
            primaryjoin="UserRole.role_id==Role.id",
            secondaryjoin="UserRole.user_id==User.id",
            foreign_keys="[UserRole.user_id,UserRole.role_id]",
        ),
    )
    depts: list["Dept"] = Relationship(
        back_populates="roles",
        link_model=DeptRole,
        sa_relationship_kwargs=dict(
            lazy="noload",
            primaryjoin="DeptRole.role_id==Role.id",
            secondaryjoin="DeptRole.dept_id==Dept.id",
            foreign_keys="[DeptRole.dept_id,DeptRole.role_id]",
        ),
    )
    menus: list["Menu"] = Relationship(
        back_populates="roles",
        link_model=RoleMenu,
        sa_relationship_kwargs=dict(
            lazy="noload",
            primaryjoin="RoleMenu.role_id==Role.id",
            secondaryjoin="RoleMenu.menu_id==Menu.id",
            foreign_keys="[RoleMenu.menu_id,RoleMenu.role_id]",
        ),
    )
    fields: Optional[list["FieldPermission"]] = Relationship(
        back_populates="role",
        sa_relationship_kwargs=dict(
            primaryjoin="Role.id==FieldPermission.role_id",
            foreign_keys="FieldPermission.role_id",
        ),
    )


@optional()
class RoleRead(AuditMixin, RoleBase, PKMixin):
    pass


class RoleCreate(RoleBase):
    pass


@optional()
class RoleUpdate(RoleBase):
    pass
