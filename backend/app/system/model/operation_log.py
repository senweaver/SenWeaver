from typing import Optional

from sqlmodel import Float, String, Text

from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db.models import Field
from senweaver.utils.partial import optional


class OperationLogBase(BaseMixin):
    module: Optional[str] = Field(default=None, max_length=64, title="模块")
    path: Optional[str] = Field(default=None, max_length=400, title="访问路径")
    body: Optional[str] = Field(default=None, sa_type=Text, title="请求参数")
    method: Optional[str] = Field(default=None, max_length=8, title="请求方式")
    ipaddress: Optional[str] = Field(
        default=None, sa_type=String(40), max_length=40, title="Ip地址"
    )
    country: Optional[str] = Field(
        default=None, sa_type=String(50), max_length=50, title="国家"
    )
    region: Optional[str] = Field(
        default=None, max_length=50, sa_type=String(50), title="地区"
    )
    city: Optional[str] = Field(
        default=None, max_length=50, sa_type=String(50), title="城市"
    )
    browser: Optional[str] = Field(default=None, max_length=64, title="浏览器")
    system: Optional[str] = Field(default=None, max_length=64, title="操作系统")
    response_code: Optional[int] = Field(default=None, title="响应码")
    response_result: Optional[str] = Field(default=None, sa_type=Text, title="响应内容")
    status_code: Optional[int] = Field(default=None, title="状态码")
    cost_time: Optional[float] = Field(
        default=0.0, sa_type=Float, title="请求耗时（ms）"
    )

    @property
    def location(self) -> str:
        # 将不为空的字段组成一个列表，并通过 '/' 连接
        parts = [self.country, self.region, self.city]
        # 去除列表中的 None 或空字符串
        location_parts = [part for part in parts if part]
        # 如果 location_parts 列表为空，则返回 '-'
        return "/".join(location_parts) if location_parts else "-"


class OperationLog(AuditMixin, OperationLogBase, PKMixin, table=True):
    __tablename__ = "system_operation_log"
    __table_args__ = {"comment": "操作日志"}


@optional()
class OperationLogRead(AuditMixin, OperationLogBase, PKMixin):
    pass


class OperationLogCreate(OperationLogBase):
    pass


@optional()
class OperationLogUpdate(OperationLogBase):
    pass
