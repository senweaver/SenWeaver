from typing import Any, Optional, Union

from pydantic import field_serializer, field_validator, model_validator
from sqlmodel import BigInteger, Relationship
from typing_extensions import Self

from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db import models
from senweaver.db.models import ChoiceType, SQLModel
from senweaver.utils.partial import optional
from senweaver.utils.translation import _

from .data_permission import DataPermission
from .fieldpermission import FieldPermission
from .menu_meta import MenuMeta, MenuMetaCreate
from .menu_model import MenuModel
from .menu_rule import MenuRule
from .modelfield import ModelField
from .role_menu import RoleMenu


class MenuBase(BaseMixin):
    class MenuChoices(models.IntegerChoices):
        DIRECTORY = 0, "目录"
        MENU = 1, "菜单"
        PERMISSION = 2, "权限"

    class MethodChoices(models.TextChoices):
        GET = "GET", "GET"
        POST = "POST", "POST"
        PUT = "PUT", "PUT"
        DELETE = "DELETE", "DELETE"
        PATCH = "PATCH", "PATCH"

    menu_type: Union[MenuChoices, int] = models.Field(
        default=MenuChoices.DIRECTORY,
        index=True,
        nullable=False,
        sa_type=ChoiceType(MenuChoices),
        title="菜单类型",
        description="`0`代表目录、`1`代表菜单、`2`代表按钮）",
    )  #
    name: Optional[str] = models.Field(
        default=None,
        unique=True,
        nullable=True,
        max_length=128,
        title="组件英文名称 或 权限标识",
        description="路由名称（必须唯一并且和当前路由`component`字段对应的页面里用`defineOptions`包起来的`name`保持一致）",
    )  # 组件英文名称或权限标识
    rank: int = models.Field(
        default=9999,
        title="排序",
        description="规定只有`home`路由的`rank`才能为`0`，所以后端在返回`rank`的时候需要从非`0`开始",
    )  # 菜单顺序
    path: Optional[str] = models.Field(
        default=None,
        nullable=True,
        index=True,
        max_length=255,
        title="路由地址 或 后端权限路由",
        description="路由路径或后端权限路由",
    )
    component: Optional[str] = models.Field(
        default=None,
        max_length=255,
        nullable=True,
        title="组件路径",
        description="组件路径（传`component`组件路径，那么`path`可以随便写，如果不传，`component`组件路径会跟`path`保持一致）",
    )
    is_active: bool = models.Field(title="激活状态", default=True)

    method: Optional[Union[MethodChoices, str]] = models.Field(
        default=None,
        sa_type=ChoiceType(MethodChoices),
        max_length=10,
        nullable=True,
        title="请求方式",
        description="请求方式GET POST PUT DELETE PATCH",
    )
    auths: Optional[str] = models.Field(
        default=None,
        title="权限标识",
        description="权限标识（按钮级别权限设置）",
        max_length=255,
        nullable=True,
    )
    meta_id: Optional[Union[int, None]] = models.Field(
        default=None, nullable=True, unique=True, title="菜单元数据", sa_type=BigInteger
    )
    parent_id: Optional[Union[int, None]] = models.Field(
        default=None,
        nullable=True,
        index=True,
        title="上级菜单",
        sa_type=BigInteger,
        foreign_key="system_menu.id",
    )

    @field_validator("method", mode="before")
    def validate_method(cls, v):
        if v == "":
            return None
        return v

    @property
    def title(self):
        """菜单名称"""
        return self.meta.title if self.meta else None


class Menu(AuditMixin, MenuBase, PKMixin, table=True):
    __tablename__ = "system_menu"
    __table_args__ = {"comment": "菜单信息"}

    parent: Optional["Menu"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs=dict(
            # notice the uppercase "N" to refer to this table class
            remote_side=lambda: Menu.id
        ),
    )
    children: list["Menu"] = Relationship(back_populates="parent")

    roles: list["Role"] = Relationship(
        back_populates="menus",
        link_model=RoleMenu,
        sa_relationship_kwargs=dict(
            lazy="noload",
            primaryjoin="RoleMenu.menu_id==Menu.id",
            secondaryjoin="RoleMenu.role_id==Role.id",
            foreign_keys="[RoleMenu.menu_id,RoleMenu.role_id]",
        ),
    )
    model: list["ModelField"] = Relationship(
        back_populates="menus",
        link_model=MenuModel,
        sa_relationship_kwargs=dict(
            lazy="noload",
            primaryjoin="MenuModel.menu_id==Menu.id",
            secondaryjoin="MenuModel.modelfield_id==ModelField.id",
            foreign_keys="[MenuModel.modelfield_id,MenuModel.menu_id]",
        ),
    )
    meta: Optional[MenuMeta] = Relationship(
        sa_relationship_kwargs=dict(
            uselist=False,
            primaryjoin="Menu.meta_id==MenuMeta.id",
            foreign_keys="Menu.meta_id",
        )
    )
    fields: Optional[list["FieldPermission"]] = Relationship(
        back_populates="menu",
        sa_relationship_kwargs=dict(
            primaryjoin="Menu.id==FieldPermission.menu_id",
            foreign_keys="FieldPermission.menu_id",
        ),
    )
    rules: list["DataPermission"] = Relationship(
        back_populates="menu",
        link_model=MenuRule,
        sa_relationship_kwargs=dict(
            primaryjoin="MenuRule.menu_id==Menu.id",
            secondaryjoin="MenuRule.datapermission_id==DataPermission.id",
            foreign_keys="[MenuRule.menu_id,MenuRule.datapermission_id]",
        ),
    )


class MenuParent(SQLModel):
    id: int = models.Field(
        default=None,
        primary_key=True,
        nullable=False,
        sa_type=BigInteger,
        sa_column_kwargs={"name": "id"},
    )
    name: str = models.Field(default=None, nullable=False, max_length=128)
    label: Optional[str] = models.Field(default=None, nullable=False, max_length=128)

    @model_validator(mode="after")
    def _set_default_label(self) -> Self:
        if not self.label:
            self.label = f"{self.name}({self.id})"
        return self


@optional()
class MenuRead(AuditMixin, MenuBase, PKMixin):
    meta: Optional[Union[MenuMeta, dict[str, Any]]] = None
    parent: Optional[Union["MenuParent", dict[str, Any]]] = None
    model: list[MenuParent] | None = None

    @field_serializer("parent")
    def serializer_parent(self, v):
        if isinstance(v, dict):
            return MenuParent(**v)
        return v

    @field_serializer("meta")
    def serializer_meta(self, v):
        if isinstance(v, dict):
            return MenuMeta(**v)
        return v


class MenuCreate(MenuBase):
    meta: MenuMetaCreate

    @model_validator(mode="before")
    def handle(cls, values):
        if "parent" in values and isinstance(values["parent"], int):
            values["parent_id"] = values["parent"]
            values.pop("parent")
        if "rank" in values and values["rank"] == 0:
            values.pop("rank")
        return values


class MenuCreateInternal(MenuCreate):
    pass


@optional()
class MenuUpdate(MenuBase):
    meta: MenuMeta

    @model_validator(mode="before")
    def handle(cls, values):
        if "parent" in values and isinstance(values["parent"], int):
            values["parent_id"] = values["parent"]
            values.pop("parent")
        return values


class MenuUpdateInternal(MenuUpdate):
    pass
