from typing import Optional

from pydantic import field_validator

from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db.models import Field
from senweaver.utils.partial import optional


class MenuMetaBase(BaseMixin):
    title: Optional[str] = Field(
        title="菜单名称",
        description="菜单名称（兼容国际化、非国际化，如果用国际化的写法就必须在根目录的`locales`文件夹下对应添加）",
        max_length=255,
        nullable=True,
    )
    icon: Optional[str] = Field(
        default=None, title="菜单图标", max_length=255, nullable=True
    )
    r_svg_name: Optional[str] = Field(
        default=None, title="菜单右图标", max_length=255, description="菜单右侧额外图标"
    )
    is_show_menu: bool = Field(default=True, title="显示菜单")
    is_show_parent: bool = Field(default=False, title="显示父级菜单")
    is_keepalive: bool = Field(
        default=True,
        title="页面缓存",
        description="开启后，会保存该页面的整体状态，刷新后会清空状态",
    )
    frame_url: Optional[str] = Field(
        title="Iframe地址",
        max_length=255,
        nullable=True,
        description="内嵌的Iframe地址",
    )
    frame_loading: bool = Field(
        default=False,
        title="Iframe页面加载动画",
        description="内嵌的`iframe`页面是否开启首次加载动画",
    )
    transition_enter: Optional[str] = Field(
        default=None, title="进场动画", max_length=255, nullable=True
    )
    transition_leave: Optional[str] = Field(
        default=None, title="离场动画", max_length=255, nullable=True
    )
    is_hidden_tag: bool = Field(
        title="隐藏标签",
        description="当前菜单名称或自定义信息禁止添加到标签页",
        default=False,
    )
    fixed_tag: bool = Field(
        default=False,
        title="固定标签",
        description="当前菜单名称是否固定显示在标签页且不可关闭",
    )
    dynamic_level: int = Field(
        default=0, title="标签显示数量", description="显示已打开标签页最大数量"
    )


class MenuMeta(AuditMixin, MenuMetaBase, PKMixin, table=True):
    __tablename__ = "system_menu_meta"
    __table_args__ = {"comment": "菜单元数据"}


@optional()
class MenuMetaRead(AuditMixin, MenuMetaBase, PKMixin):
    pass


class MenuMetaCreate(MenuMetaBase):
    pass


@optional()
class MenuMetaUpdate(MenuMetaBase):
    pass


class MenuMetaUpdateInternal(MenuMetaUpdate):
    pass
