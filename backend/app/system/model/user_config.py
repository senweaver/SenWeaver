from typing import Optional, Union

from sqlalchemy import JSON, BigInteger, Boolean, String

from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db.models import Field
from senweaver.utils.partial import optional


class UserConfigBase(BaseMixin):
    key: str = Field(default=None, sa_type=String(255), unique=True, title="配置名称")
    value: Union[str, bool, dict, int] = Field(
        default=None, sa_type=JSON, title="配置值"
    )
    is_active: Optional[bool] = Field(default=True, sa_type=Boolean, title="激活状态")
    access: Optional[bool] = Field(
        default=False,
        sa_type=Boolean,
        title="接口访问",
        description="允许API接口访问访问该配置",
    )
    owner_id: Optional[int] = Field(
        title="用户ID", default=None, nullable=True, index=True, sa_type=BigInteger
    )


class UserConfig(AuditMixin, UserConfigBase, PKMixin, table=True):
    __tablename__ = "system_user_config"
    __table_args__ = {"comment": "用户配置"}


@optional()
class UserConfigRead(AuditMixin, UserConfigBase, PKMixin):
    pass


class UserConfigCreate(UserConfigBase):
    pass


class UserConfigCreateInternal(UserConfigBase):
    pass


@optional()
class UserConfigUpdate(UserConfigBase):
    pass


class UserConfigUpdateInternal(UserConfigUpdate):
    pass
