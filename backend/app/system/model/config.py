from typing import Optional

from pydantic import field_validator
from sqlalchemy import (
    JSON,
    TEXT,
    BigInteger,
    Boolean,
    Column,
    Index,
    Integer,
    String,
    text,
)
from sqlmodel import Relationship

from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db.models import Field
from senweaver.utils.partial import optional


class ConfigBase(BaseMixin):
    parent_id: Optional[int] = Field(default=None, sa_type=BigInteger)
    group: str = Field(sa_type=String(128), nullable=False, title="配置分组")
    key: Optional[str] = Field(
        default=None,
        title="参数键名",
        sa_type=String(100),
        sa_column_kwargs={"server_default": text("''")},
    )
    name: Optional[str] = Field(default=None, title="参数名称", sa_type=String(100))
    type: str = Field(
        sa_type=String(32),
        nullable=False,
        title="参数类型",
        description="参数类型:string,text,int,bool,array,datetime,date,file",
    )
    value: Optional[str] = Field(default=None, sa_type=TEXT, title="参数值")
    default_value: str = Field(sa_type=String(500), nullable=False, title="默认值")
    rule: str = Field(
        sa_type=String(100),
        nullable=False,
        sa_column_kwargs={"server_default": text("''")},
        title="验证规则",
    )
    tip: Optional[str] = Field(default=None, sa_type=String(500), title="参数描述")
    is_default: Optional[bool] = Field(
        default=False, sa_type=Boolean, title="是否为系统默认"
    )
    is_active: Optional[bool] = Field(default=None, sa_type=Boolean, title="激活状态")
    rank: int = Field(default=0, sa_type=Integer, nullable=False, title="排序")
    options: Optional[dict] = Field(default=None, sa_type=JSON, title="选项配置")

    @field_validator("options")
    def validate_json(v):
        if not v:
            return v
        if not isinstance(v, dict):
            raise ValueError("Options must be a valid JSON")

        return v


class Config(AuditMixin, ConfigBase, PKMixin, table=True):
    __tablename__ = "system_config"
    __table_args__ = ({"comment": "配置"},)
    children: list["Config"] = Relationship(
        sa_relationship_kwargs=dict(
            primaryjoin="Config.parent_id==Config.id", foreign_keys="Config.parent_id"
        )
    )


@optional()
class ConfigRead(AuditMixin, ConfigBase, PKMixin):
    pass


class ConfigCreate(ConfigBase):
    pass


class ConfigCreateInternal(ConfigBase):
    pass


@optional()
class ConfigUpdate(ConfigBase):
    pass


class ConfigUpdateInternal(ConfigUpdate):
    pass
