import json
from typing import Any, Optional

from pydantic import field_serializer, field_validator
from sqlalchemy import JSON, TEXT, Boolean, String

from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db.models import Field
from senweaver.utils.partial import optional


class SettingBase(BaseMixin):
    name: Optional[str] = Field(default=None, title="名称", sa_type=String(128))
    value: Any = Field(default=None, sa_type=JSON, title="值")
    category: str = Field(sa_type=String(128), nullable=False, title="类别")
    encrypted: Optional[bool] = Field(default=False, sa_type=Boolean, title="加密的")
    is_active: Optional[bool] = Field(default=True, sa_type=Boolean, title="激活状态")


class Setting(AuditMixin, SettingBase, PKMixin, table=True):
    __tablename__ = "settings_setting"
    __table_args__ = ({"comment": "系统设置"},)

    # @field_serializer("value")
    # def serialize_value(self, v: Any, info) -> str:
    #     """
    #     在保存数据到数据库之前，将 value 序列化成 JSON 字符串。
    #     """
    #     return json.dumps(v)

    # @field_validator("value", mode="before")
    # def deserialize_value(cls, v: Any) -> Any:
    #     """
    #     在从数据库加载数据时，如果是字符串则尝试反序列化为 Python 对象。
    #     """
    #     if isinstance(v, str):
    #         try:
    #             return json.loads(v)
    #         except json.JSONDecodeError:
    #             # 如果不是有效的 JSON 字符串，则直接返回原值
    #             return v
    #     return v


@optional()
class SettingRead(AuditMixin, SettingBase, PKMixin):
    pass


class SettingCreate(SettingBase):
    pass


class SettingCreateInternal(SettingBase):
    pass


@optional()
class SettingUpdate(SettingBase):
    pass


class SettingUpdateInternal(SettingUpdate):
    pass
