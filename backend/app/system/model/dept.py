from typing import List, Optional, Union

from pydantic import field_validator, model_validator
from sqlmodel import BigInteger, Relationship, String

from senweaver.core.models import AuditMixin, BaseMixin, ModeTypeMixin, PKMixin
from senweaver.db.models import Field
from senweaver.utils.partial import optional

from .data_permission import DataPermission
from .dept_role import DeptRole
from .dept_rule import DeptRule


class DeptBase(BaseMixin, ModeTypeMixin):
    name: str = Field(
        default=..., max_length=128, sa_type=String(128), title="部门名称"
    )
    code: str = Field(
        default=..., sa_type=String(128), max_length=128, title="部门标识", unique=True
    )
    parent_id: Optional[Union[int, None]] = Field(
        default=None,
        nullable=True,
        index=True,
        title="上级部门",
        sa_type=BigInteger,
        foreign_key="system_dept.id",
    )
    rank: int = Field(default=0, title="排序")
    auto_bind: bool | None = Field(
        default=False,
        title="自动绑定",
        description="注册参数channel的值和该部门code一致，则该用户会自动和该部门绑定",
    )
    is_active: bool | None = Field(default=True, title="激活状态")


class Dept(AuditMixin, DeptBase, PKMixin, table=True):
    __tablename__ = "system_dept"
    __table_args__ = {"comment": "部门"}
    parent: Optional["Dept"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs=dict(
            # notice the uppercase "N" to refer to this table class
            remote_side=lambda: Dept.id
        ),
    )
    children: list["Dept"] = Relationship(back_populates="parent")

    users: Optional[List["User"]] = Relationship(
        back_populates="dept",
        sa_relationship_kwargs=dict(
            primaryjoin="Dept.id==User.dept_id", foreign_keys="User.dept_id"
        ),
    )
    rules: list["DataPermission"] = Relationship(
        back_populates="depts",
        link_model=DeptRule,
        sa_relationship_kwargs=dict(
            primaryjoin="DeptRule.dept_id==Dept.id",
            secondaryjoin="DeptRule.datapermission_id==DataPermission.id",
            foreign_keys="[DeptRule.dept_id,DeptRule.datapermission_id]",
        ),
    )
    roles: list["Role"] = Relationship(
        back_populates="depts",
        link_model=DeptRole,
        sa_relationship_kwargs=dict(
            primaryjoin="DeptRole.dept_id==Dept.id",
            secondaryjoin="DeptRole.role_id==Role.id",
            foreign_keys="[DeptRole.dept_id,DeptRole.role_id]",
        ),
    )


@optional()
class DeptRead(AuditMixin, DeptBase, PKMixin):
    pass


class DeptCreate(DeptBase):
    pass


@optional()
class DeptUpdate(DeptBase):
    pass
