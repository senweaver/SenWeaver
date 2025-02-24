from typing import Optional, Union

from sqlmodel import BigInteger, Relationship

from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db.models import Field
from senweaver.utils.partial import optional

from .user_post import UserPost


class PostBase(BaseMixin):
    parent_id: Optional[Union[int, None]] = Field(
        default=None, nullable=True, index=True, description="父ID", sa_type=BigInteger
    )
    name: str = Field(max_length=64, nullable=False, title="岗位名称")
    code: str = Field(max_length=64, nullable=False, title="岗位编码")
    rank: int = Field(title="排序", default=None, sa_column_kwargs={"comment": "排序"})
    is_active: bool = Field(title="激活状态", default=True)


class Post(AuditMixin, PostBase, PKMixin, table=True):
    """岗位信息"""

    __tablename__ = "system_post"
    __table_args__ = {"comment": "岗位信息"}
    users: list["User"] = Relationship(
        back_populates="posts",
        link_model=UserPost,
        sa_relationship_kwargs=dict(
            lazy="selectin",
            primaryjoin="UserPost.post_id==Post.id",
            secondaryjoin="UserPost.user_id==User.id",
            foreign_keys="[UserPost.user_id,UserPost.post_id]",
        ),
    )


@optional()
class PostRead(AuditMixin, PostBase, PKMixin):
    pass


class PostCreate(PostBase):
    pass


@optional()
class PostUpdate(PostBase):
    pass
