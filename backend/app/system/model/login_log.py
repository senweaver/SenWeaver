from typing import Optional, Union

from sqlmodel import String

from senweaver.auth.constants import LoginTypeChoices
from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db.models import ChoiceType, Field
from senweaver.utils.partial import optional


class LoginLogBase(BaseMixin):
    # class LoginTypeChoices(models.IntegerChoices):
    #     USERNAME = 0, "用户名和密码"
    #     SMS = 1, "短信验证"
    #     EMAIL = 2, "邮箱验证"
    #     WECHAT = 4, "微信扫码"
    #     UNKNOWN = 9, "未知"

    status: bool = Field(title="登录状态", default=True)
    ipaddress: Optional[str] = Field(
        default=None, sa_type=String(40), max_length=40, nullable=True, title="Ip地址"
    )
    country: Optional[str] = Field(
        default=None, sa_type=String(50), max_length=50, nullable=True, title="国家"
    )
    region: Optional[str] = Field(
        default=None, max_length=50, sa_type=String(50), nullable=True, title="地区"
    )
    city: Optional[str] = Field(
        default=None, max_length=50, sa_type=String(50), nullable=True, title="城市"
    )
    browser: Optional[str] = Field(
        default=None, max_length=64, nullable=True, title="浏览器"
    )
    system: Optional[str] = Field(
        default=None, max_length=64, nullable=True, title="操作系统"
    )
    agent: Optional[str] = Field(
        default=None, max_length=128, nullable=True, title="用户代理"
    )
    login_type: Union[LoginTypeChoices, int] = Field(
        default=LoginTypeChoices.USERNAME,
        sa_type=ChoiceType(LoginTypeChoices),
        title="登录类型",
    )


class LoginLog(AuditMixin, LoginLogBase, PKMixin, table=True):
    __tablename__ = "system_login_log"
    __table_args__ = {"comment": "登录日志"}


@optional()
class LoginLogRead(AuditMixin, LoginLogBase, PKMixin):
    pass


class LoginLogCreate(LoginLogBase):
    pass


@optional()
class LoginLogUpdate(LoginLogBase):
    pass
