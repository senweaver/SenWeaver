from typing import Optional, Union

from sqlmodel import BigInteger, Relationship, UniqueConstraint

from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db import models
from senweaver.db.models import ChoiceType
from senweaver.utils.partial import optional
from senweaver.utils.translation import _

from .fieldpermission_field import FieldPermissionField
from .menu_model import MenuModel


class ModelFieldBase(BaseMixin):
    class KeyChoices(models.TextChoices):
        TEXT = "value.text", "文本"
        JSON = "value.json", "Json"
        ALL = "value.all", "所有数据"
        DATETIME = "value.datetime", "日期时间"
        DATETIME_RANGE = "value.datetime.range", _("日期时间去选择器")
        DATE = "value.date", _("距离当前时间多少秒")
        OWNER = "value.user.id", _("本人ID")
        OWNER_DEPARTMENT = "value.user.dept.id", _("本部门ID")
        OWNER_DEPARTMENTS = "value.user.dept.ids", _("本部门ID及部门以下数据")
        DEPARTMENTS = "value.dept.ids", _("部门ID及部门以下数据")
        TABLE_USER = "value.table.user.ids", _("选择用户ID")
        TABLE_MENU = "value.table.menu.ids", _("选择菜单ID")
        TABLE_ROLE = "value.table.role.ids", _("选择角色ID")
        TABLE_DEPT = "value.table.dept.ids", _("选择部门ID")

    class FieldChoices(models.IntegerChoices):
        ROLE = 0, _("角色权限")
        DATA = 1, _("字段权限")

    field_type: Union[FieldChoices, int] = models.Field(
        default=FieldChoices.DATA,
        nullable=False,
        sa_type=ChoiceType(FieldChoices),
        title=_("字段类型"),
    )
    name: Optional[str] = models.Field(
        default=None, nullable=True, max_length=128, title=_("模型/字段数值")
    )
    label: Optional[str] = models.Field(
        default=None, nullable=True, max_length=128, title=_("模型/字段数值")
    )


class ModelField(AuditMixin, ModelFieldBase, PKMixin, table=True):
    __tablename__ = "system_modelfield"
    __table_args__ = (
        UniqueConstraint("name", "parent_id"),
        {"comment": "模型/字段名称"},
    )

    parent_id: Optional[Union[int, None]] = models.Field(
        default=None,
        nullable=True,
        index=True,
        title="上级节点",
        sa_type=BigInteger,
        foreign_key="system_modelfield.id",
    )
    parent: Optional["ModelField"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs=dict(
            # notice the uppercase "N" to refer to this table class
            remote_side=lambda: ModelField.id
        ),
    )
    children: list["ModelField"] = Relationship(back_populates="parent")

    menus: list["Menu"] = Relationship(
        back_populates="model",
        link_model=MenuModel,
        sa_relationship_kwargs=dict(
            lazy="noload",
            primaryjoin="MenuModel.modelfield_id==ModelField.id",
            secondaryjoin="MenuModel.menu_id==Menu.id",
            foreign_keys="[MenuModel.modelfield_id,MenuModel.menu_id]",
        ),
    )
    fieldpermissions: list["FieldPermission"] = Relationship(
        back_populates="fields",
        link_model=FieldPermissionField,
        sa_relationship_kwargs=dict(
            primaryjoin="FieldPermissionField.modelfield_id==ModelField.id",
            secondaryjoin="FieldPermissionField.fieldpermission_id==FieldPermission.id",
            foreign_keys="[FieldPermissionField.fieldpermission_id,FieldPermissionField.modelfield_id]",
        ),
    )


@optional()
class ModelFieldRead(AuditMixin, ModelFieldBase, PKMixin):
    pass


class ModelFieldCreate(ModelFieldBase):
    pass


@optional()
class ModelFieldUpdate(ModelFieldBase):
    pass


class ModelFieldUpdateInternal(ModelFieldUpdate):
    pass
