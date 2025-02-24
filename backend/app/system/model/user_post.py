from sqlmodel import BigInteger, UniqueConstraint

from senweaver.core.models import PKMixin
from senweaver.db.models import Field


class UserPost(PKMixin, table=True):
    """用户岗位"""

    __tablename__ = "system_user_post"
    __table_args__ = (
        UniqueConstraint("user_id", "post_id"),
        {"comment": "用户关联岗位"},
    )
    user_id: int | None = Field(
        default=None, nullable=False, foreign_key="system_user.id", sa_type=BigInteger
    )
    post_id: int | None = Field(
        default=None, nullable=False, foreign_key="system_post.id", sa_type=BigInteger
    )
