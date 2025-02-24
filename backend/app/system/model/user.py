from datetime import datetime, timezone
from typing import Optional

from sqlmodel import BigInteger, Relationship

from senweaver.core.models import (
    AuditMixin,
    BaseMixin,
    PKMixin,
    SoftDeleteMixin,
    UserMixin,
)
from senweaver.db.models import Field
from senweaver.utils.partial import optional

from .data_permission import DataPermission
from .user_post import UserPost
from .user_role import UserRole
from .user_rule import UserRule


class UserBase(UserMixin, BaseMixin):
    pass


class User(SoftDeleteMixin, AuditMixin, UserBase, PKMixin, table=True):
    __tablename__ = "system_user"
    __table_args__ = {"comment": "用户信息"}
    posts: list["Post"] = Relationship(
        back_populates="users",
        link_model=UserPost,
        sa_relationship_kwargs=dict(
            primaryjoin="User.id==UserPost.user_id",
            secondaryjoin="UserPost.post_id==Post.id",
            foreign_keys="[UserPost.user_id,UserPost.post_id]",
        ),
    )
    # primaryjoin="and_(UserRole.user_id==User.id, UserRole.is_active==True)"
    roles: list["Role"] = Relationship(
        back_populates="users",
        link_model=UserRole,
        sa_relationship_kwargs=dict(
            primaryjoin="UserRole.user_id==User.id",
            secondaryjoin="UserRole.role_id==Role.id",
            foreign_keys="[UserRole.user_id,UserRole.role_id]",
        ),
    )
    rules: list["DataPermission"] = Relationship(
        back_populates="users",
        link_model=UserRule,
        sa_relationship_kwargs=dict(
            primaryjoin="UserRule.user_id==User.id",
            secondaryjoin="UserRule.datapermission_id==DataPermission.id",
            foreign_keys="[UserRule.user_id,UserRule.datapermission_id]",
        ),
    )
    dept: Optional["Dept"] = Relationship(
        back_populates="users",
        sa_relationship_kwargs=dict(
            primaryjoin="User.dept_id==Dept.id", foreign_keys="User.dept_id"
        ),
    )


@optional()
class UserRead(AuditMixin, UserBase, PKMixin):
    pass


class UserCreate(UserBase):
    pass


class UserCreateInternal(UserBase):
    pass


@optional()
class UserUpdate(UserBase):
    dept: int = Field(default=None, sa_type=BigInteger, nullable=True, title="所属部门")


class UserUpdateInternal(UserUpdate):
    updated_time: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
