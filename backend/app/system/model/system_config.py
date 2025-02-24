from typing import Optional, Union

from sqlalchemy import JSON, Boolean, String, text

from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db.models import Field
from senweaver.utils.partial import optional


class SystemConfigBase(BaseMixin):
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
    inherit: Optional[bool] = Field(default=False, sa_type=Boolean, title="用户继承")


class SystemConfig(AuditMixin, SystemConfigBase, PKMixin, table=True):
    __tablename__ = "system_system_config"
    __table_args__ = {"comment": "系统配置"}


@optional()
class SystemConfigRead(AuditMixin, SystemConfigBase, PKMixin):
    pass


class SystemConfigCreate(SystemConfigBase):
    pass


class SystemConfigCreateInternal(SystemConfigBase):
    pass


@optional()
class SystemConfigUpdate(SystemConfigBase):
    pass


class SystemConfigUpdateInternal(SystemConfigUpdate):
    pass
