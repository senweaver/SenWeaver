from typing import Annotated, List

from fastapi import Depends, Path, Query, Request, routing
from fastcrud import FastCRUD
from sqlalchemy.ext.asyncio import AsyncSession

from senweaver import SenweaverCRUD
from senweaver.auth.security import (
    Authorizer,
    get_permission_list,
    get_route_permission,
    requires_permissions,
)
from senweaver.core.helper import RelationConfig
from senweaver.core.senweaver_creator import SenweaverEndpointCreator
from senweaver.exception.http_exception import NotFoundException
from senweaver.helper import build_tree
from senweaver.module.manager import module_manager
from senweaver.utils.response import ResponseBase, error_response, success_response

from ..model.menu import Menu
from ..model.menu_meta import MenuMeta
from ..model.menu_model import MenuModel
from ..model.modelfield import ModelField
from ..model.role_menu import RoleMenu
from ..schema.menu import IMenuPermission


class MenuLogic:

    @classmethod
    async def get_routes(cls, request: Request):
        # 查询按钮之外的数据
        user_roles, role_ids = request.auth.get_role_scope(request)
        # 显示0目录和1菜单
        # menu_type = [Menu.MenuChoices.DIRECTORY.value,
        #              Menu.MenuChoices.MENU.value]
        # menu_type__in=menu_type
        filters = {"is_active": True}
        db: AsyncSession = request.auth.db.session
        if not Authorizer.is_superuser(request):
            result = await FastCRUD(RoleMenu).get_multi(
                db, role_id__in=role_ids, limit=None, return_total_count=False
            )
            menu_ids = [rm["menu_id"] for rm in result["data"]]
            filters["id__in"] = menu_ids
        menus = await SenweaverCRUD(
            Menu,
            relationships=[RelationConfig(rel=Menu.meta, schema_to_select=MenuMeta)],
            check_data_scope=False,
            check_field_scope=False,
        ).get_multi(
            db,
            schema_to_select=Menu,
            sort_columns="rank",
            limit=None,
            return_total_count=False,
            return_as_model=True,
            **filters,
        )
        routes, auths = cls.build_menu_tree(user_roles, menus["data"])
        if Authorizer.is_superuser(request):
            auths = ["*"]
        return routes, auths

    @classmethod
    def build_menu_tree(cls, user_roles: set[str], items: List[Menu]):
        # 创建所有节点的字典，键为节点id，值为包含子节点的字典
        node_list = []
        auths = []
        for item in items:
            if item.auths and item.auths != "":
                auths.extend(item.auths.split(","))
            if item.menu_type == Menu.MenuChoices.PERMISSION.value:
                continue
            meta = item.meta
            meta_data = {
                "title": meta.title,
                "icon": meta.icon,
                "showParent": meta.is_show_parent,
                "showLink": meta.is_show_menu,
                "extraIcon": meta.r_svg_name,
                "keepAlive": meta.is_keepalive,
                "frameSrc": meta.frame_url,
                "frameLoading": meta.frame_loading,
                "transition": {
                    "enterTransition": meta.transition_enter,
                    "leaveTransition": meta.transition_leave,
                },
                "hiddenTag": meta.is_hidden_tag,
                "dynamicLevel": meta.dynamic_level,
                "fixedTag": meta.fixed_tag,
                # "icon": item.icon,
                # "title": item.title,
                # "extraIcon": item.extra_icon,
                # "showLink": item.show_link,
                # "showParent": item.show_parent,
                # "transition": {
                #     "enterTransition": item.enter_transition,
                #     "leaveTransition": item.leave_transition,
                # },
                # "keepAlive": item.keep_alive,
                # "frameSrc": item.frame_src,
                # "frameLoading": item.frame_loading,
                # "hiddenTag": item.hidden_tag,
                # "fixedTag": item.fixed_tag,
                # "activePath": item.active_path,
            }

            node_list.append(
                {
                    "id": item.id,
                    "parent_id": item.parent_id,
                    "menuType": item.menu_type,
                    "name": item.name,
                    "path": item.path,
                    "rank": item.rank,
                    "component": item.component,
                    # "redirect": item.redirect,
                    "meta": meta_data,
                }
            )
        return build_tree(node_list, id_field="id"), auths

    @classmethod
    def add_custom_router(cls, endpoint_creator: SenweaverEndpointCreator):
        self = endpoint_creator
        router = self.router

        @router.get(f"{self.path}/perms", summary="获取所有权限标识")
        async def get_menu_perms(request: Request) -> ResponseBase:
            permission_list = get_permission_list(request.app)
            return success_response(permission_list)

        @router.get(f"{self.path}/api-url", summary="获取Api地址")
        async def get_menu_api_url(request: Request) -> ResponseBase:
            data = [{"name": "#", "method": "#", "url": "#", "label": "#", "view": "#"}]
            resource_routers = module_manager.resource_routers
            for resource_name, router in resource_routers.items():
                label_name = getattr(router, "sw_title", resource_name)
                for route in router.routes:
                    ignore_paths = [
                        "/choices",
                        "/search-fields",
                        "/search-columns",
                        "/cursor",
                    ]
                    if any(route.path.endswith(p) for p in ignore_paths):
                        continue
                    url_path = module_manager.endpoints[route.endpoint].path
                    for method in route.methods:
                        data.append(
                            {
                                "name": resource_name,
                                "method": method,
                                "url": url_path,
                                "label": label_name,
                                "view": resource_name,
                            }
                        )
            return success_response(data)

        @router.post(f"{self.path}" + "/{id}/permissions", summary="自动添加API权限")
        @requires_permissions(
            f"{self.module.get_auth_str(self.resource_name, "permissions")}"
        )
        async def save_menu_permissions(
            request: Request,
            id: Annotated[int, Path(...)],
            data: IMenuPermission,
        ) -> ResponseBase:
            if not data.views:
                return error_response(code=1001)
            db: AsyncSession = request.auth.db.session
            menu_object = await SenweaverCRUD(Menu).get(db, id=id)
            if not menu_object:
                raise NotFoundException()
            for resource_name in data.views:
                resource_router = module_manager.resource_routers.get(resource_name)
                if resource_router is None:
                    continue
                model_names = []
                filter_config = getattr(resource_router, "sw_filter", None)
                if filter_config:
                    for relationship in filter_config.relationships:
                        model_names.append(relationship._model.__senweaver_name__)
                rank = 10000
                for route in resource_router.routes:
                    ignore_paths = [
                        "/choices",
                        "/search-fields",
                        "/search-columns",
                        "/cursor",
                    ]
                    if any(route.path.endswith(p) for p in ignore_paths):
                        continue
                    auth_set = get_route_permission(route)
                    auth_str = ",".join(auth_set)
                    name_suffix = resource_name
                    url_path = module_manager.endpoints[route.endpoint].path
                    if len(data.views) == 1 and data.component:
                        name_suffix = data.component
                    menu_name = f"{route.name}:{name_suffix}"
                    for method in route.methods:
                        permission_menu = await SenweaverCRUD(Menu).get(
                            db, menu_type=Menu.MenuChoices.PERMISSION, name=menu_name
                        )
                        if permission_menu:  # and data.skip_existing:
                            continue
                        # 1.先保存meta
                        meta = MenuMeta(
                            title=(route.summary or route.description)[:250]
                        )
                        await SenweaverCRUD(MenuMeta).create(db, meta, commit=False)
                        # 2.保存菜单
                        rank += 1
                        menu = Menu(
                            rank=rank,
                            is_active=True,
                            menu_type=Menu.MenuChoices.PERMISSION,
                            name=menu_name,
                            parent_id=id,
                            path=url_path,
                            auths=auth_str,
                            method=method,
                            meta_id=meta.id,
                        )
                        await SenweaverCRUD(Menu).create(db, menu, commit=False)
                        # 3.保存关联模型
                        if model_names:
                            result = await SenweaverCRUD(ModelField).get_multi(
                                db,
                                field_type=ModelField.FieldChoices.ROLE,
                                name__in=model_names,
                                return_total_count=False,
                                limit=None,
                            )
                            for model in result["data"]:
                                await SenweaverCRUD(MenuModel).create(
                                    db,
                                    MenuModel(
                                        menu_id=menu.id, modelfield_id=model["id"]
                                    ),
                                    commit=False,
                                )
                await db.commit()
            return success_response()


menu_logic = MenuLogic()
