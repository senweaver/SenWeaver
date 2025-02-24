from typing import Any, Optional

from sqlalchemy import JSON, Boolean, Column, Index, Integer, String, text

from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db.models import Field
from senweaver.utils.partial import optional


class DictDataBase(BaseMixin):
    type: str = Field(
        sa_type=String(128),
        index=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("''")},
        title="字典类型",
    )
    label: str = Field(
        sa_type=String(100),
        nullable=False,
        sa_column_kwargs={"server_default": text("'string'")},
        title="字典标签",
    )
    value: str = Field(
        sa_type=String(100),
        nullable=False,
        sa_column_kwargs={"server_default": text("'string'")},
        title="字典键值",
    )
    value_type: Optional[str] = Field(
        default=None,
        sa_type=String(50),
        sa_column_kwargs={"server_default": text("'string'")},
        title="数据类型",
        description="数据类型:string,int,bool,datetime,date",
    )
    icon: Optional[str] = Field(
        default=None,
        sa_type=String(255),
        sa_column_kwargs={"server_default": text("''")},
        title="图标",
    )
    css_class: Optional[str] = Field(
        default=None, sa_type=String(100), title="样式属性（其他样式扩展）"
    )
    list_class: Optional[str] = Field(
        default=None, sa_type=String(100), title="表格回显样式"
    )
    is_default: Optional[bool] = Field(default=False, sa_type=Boolean, title="是否默认")
    is_active: Optional[bool] = Field(default=True, title="激活状态")
    options: Any = Field(default=None, sa_type=JSON, title="选项数据")
    rank: Optional[int] = Field(default=0, sa_type=Integer, title="字典排序")


class DictData(AuditMixin, DictDataBase, PKMixin, table=True):
    __tablename__ = "system_dict_data"
    __table_args__ = ({"comment": "字典数据表"},)


@optional()
class DictDataRead(AuditMixin, DictDataBase, PKMixin):
    pass


class DictDataCreate(DictDataBase):
    pass


class DictDataCreateInternal(DictDataBase):
    pass


@optional()
class DictDataUpdate(DictDataBase):
    pass


class DictDataUpdateInternal(DictDataUpdate):
    pass
