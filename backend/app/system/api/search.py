from fastapi import APIRouter
from fastcrud import aliased

from app.system.model.dept import Dept
from app.system.model.menu import Menu
from app.system.model.role import Role
from app.system.model.user import User
from senweaver import senweaver_router
from senweaver.core.helper import FieldConfig, RelationConfig, SenweaverFilter

from ..system import module

router = APIRouter(tags=["查询信息"], route_class=module.route_class)


user_router = senweaver_router(
    module=module,
    model=User,
    path=f"/search/user",
    included_methods=["read_multi", "search_columns", "search_fields"],
    filter_config=SenweaverFilter(
        filters={
            "username": None,
            "nickname": None,
            "phone": None,
            "is_active": None,
            "gender": None,
            "dept": None,
            "id": None,
        },
        read_only_fields=list(User.__mapper__.all_orm_descriptors.keys()),
        fields=[
            "id",
            "avatar",
            "username",
            "nickname",
            "phone",
            "email",
            "gender",
            "is_active",
            "password",
            "dept",
            "description",
            "last_login",
            "created_time",
        ],
        table_fields=[
            "id",
            "avatar",
            "username",
            "nickname",
            "gender",
            "is_active",
            "dept",
            "phone",
            "last_login",
            "created_time",
        ],
        relationships=[
            RelationConfig(
                rel=User.dept,
                attrs=["id", "name", "parent_id", "label"],
                format="{name}",
                label="所属部门",
            )
        ],
    ),
)
router.include_router(user_router)

dept_router = senweaver_router(
    module=module,
    model=Dept,
    path=f"/search/dept",
    included_methods=["read_multi", "search_columns", "search_fields"],
    filter_config=SenweaverFilter(
        filters={
            "name__contains": None,
            "is_active": None,
            "code": None,
            "description": None,
        },
        read_only_fields=list(Dept.__mapper__.all_orm_descriptors.keys()),
        fields=[
            "name",
            "id",
            "code",
            "parent",
            "is_active",
            "user_count",
            "auto_bind",
            "description",
            "created_time",
        ],
        table_fields=[
            "name",
            "code",
            "is_active",
            "user_count",
            "auto_bind",
            "description",
            "created_time",
            "id",
        ],
        ordering_fields=["created_time", "rank"],
    ),
)
router.include_router(dept_router)

role_router = senweaver_router(
    module=module,
    model=Role,
    path=f"/search/role",
    included_methods=["read_multi", "search_columns", "search_fields"],
    filter_config=SenweaverFilter(
        filters={
            "name__contains": None,
            "code__contains": None,
            "is_active": None,
            "description": None,
        },
        read_only_fields=list(Role.__mapper__.all_orm_descriptors.keys()),
        fields=["id", "name", "code", "is_active", "description", "updated_time"],
        ordering_fields=["updated_time", "name", "created_time"],
    ),
)
router.include_router(role_router)

menu_router = senweaver_router(
    module=module,
    model=Menu,
    path=f"/search/menu",
    included_methods=["read_multi", "search_columns", "search_fields"],
    filter_config=SenweaverFilter(
        filters={
            "meta.title": None,
            "path__contains": None,
            "component__contains": None,
        },
        read_only_fields=list(Menu.__mapper__.all_orm_descriptors.keys()),
        fields=[
            "title",
            "id",
            "rank",
            "path",
            "component",
            "parent",
            "menu_type",
            "is_active",
            "method",
        ],
        table_fields=["title", "menu_type", "path", "component", "is_active", "method"],
        ordering_fields=["-rank", "updated_time", "created_time"],
        relationships=[
            RelationConfig(rel=Menu.parent, attrs=["id", "name"], label="上级菜单"),
            RelationConfig(rel=Menu.meta, attr=["id", "title"], label="菜单元数据"),
        ],
        extra_fields=[
            FieldConfig(key="meta.title", name="title", label="菜单标题"),
        ],
    ),
)
router.include_router(menu_router)
