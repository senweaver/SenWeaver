from typing import Optional, Union

from sqlalchemy import JSON, BigInteger, Boolean, Column, Index, Integer, String, text

from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db.models import Field
from senweaver.utils.partial import optional


class DictTypeBase(BaseMixin):
    parent_id: Optional[Union[int, None]] = Field(
        default=None,
        nullable=True,
        index=True,
        title="父类型",
        sa_type=BigInteger,
        foreign_key="system_dict_type.id",
    )
    name: str = Field(
        sa_type=String(100),
        nullable=False,
        sa_column_kwargs={"server_default": text("''")},
        title="字典名称",
    )
    type: str = Field(
        sa_type=String(128),
        nullable=False,
        sa_column_kwargs={"server_default": text("''")},
        title="字典类型",
    )
    is_active: Optional[bool] = Field(default=True, title="激活状态")
    options: Optional[dict] = Field(default=None, sa_type=JSON, title="选项数据")
    rank: int = Field(sa_type=Integer, nullable=False, title="排序")


class DictType(AuditMixin, DictTypeBase, PKMixin, table=True):
    __tablename__ = "system_dict_type"
    __table_args__ = ({"comment": "字典类型"},)


@optional()
class DictTypeRead(AuditMixin, DictTypeBase, PKMixin):
    pass


class DictTypeCreate(DictTypeBase):
    pass


class DictTypeCreateInternal(DictTypeBase):
    pass


@optional()
class DictTypeUpdate(DictTypeBase):
    pass


class DictTypeUpdateInternal(DictTypeUpdate):
    pass
