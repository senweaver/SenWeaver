from collections import defaultdict
from typing import List, Optional

from fastcrud import FastCRUD
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, joinedload, selectinload
from starlette.requests import HTTPConnection

from app.system.logic.dept_logic import DeptLogic
from app.system.model.data_permission import DataPermission
from app.system.model.dept import Dept
from app.system.model.dept_rule import DeptRule
from app.system.model.fieldpermission import FieldPermission
from app.system.model.menu import Menu
from app.system.model.menu_rule import MenuRule
from app.system.model.modelfield import ModelField
from app.system.model.user import User
from app.system.model.user_rule import UserRule
from senweaver.auth.constants import SENWEAVER_REQ_MENU
from senweaver.auth.filter import get_filter_attrs
from senweaver.auth.security import Authorizer
from senweaver.db.types import ModelType
from senweaver.utils.globals import g


async def parse_filters(
    model: type[ModelType],
    permissions: List[DataPermission],
    user_obj: User = None,
    dept_obj: Dept = None,
):
    import json
    from datetime import datetime, timedelta, timezone

    # from sqlalchemy.sql import and_, or_, not_, true, false
    from sqlalchemy import func

    from senweaver.core.models import ModeTypeMixin

    results = []
    for obj in permissions:
        rules = []
        if len(obj.rules) == 1:
            obj.mode_type = ModeTypeMixin.ModeChoices.OR
        for rule in obj.rules:
            if rule.get("table") in [model.__senweaver_name__, "*"]:
                if rule.get("type") == ModelField.KeyChoices.ALL:
                    if (
                        obj.mode_type == ModeTypeMixin.ModeChoices.AND
                    ):  # 且模式，存在*，则忽略该规则
                        continue
                    else:  # 或模式，存在* 则该规则表仅*生效
                        rules = [rule]
                        break
                rules.append(rule)
        if rules:
            results.append({"mode": obj.mode_type, "rules": rules})
    if not results:
        return {"__false": None}
    or_filters = []
    for result in results:
        for rule in result["rules"]:
            type_name = rule.get("type")
            field_name = rule.get("field")
            field_obj = getattr(model, field_name, None)
            if isinstance(field_obj, InstrumentedAttribute):
                fk_column = next(iter(field_obj.property.local_columns), None)
                if fk_column is not None:
                    rule["field"] = fk_column.name

            if type_name == ModelField.KeyChoices.OWNER:
                rule["value"] = user_obj.id if user_obj else "0"

            elif type_name == ModelField.KeyChoices.OWNER_DEPARTMENT:
                rule["value"] = str(user_obj.dept_id) if user_obj else "0"

            elif type_name == ModelField.KeyChoices.OWNER_DEPARTMENTS:
                rule["match"] = "in"
                rule["value"] = (
                    await DeptLogic.get_dept_tree_ids(dept_obj.id) if dept_obj else []
                )

            elif type_name == ModelField.KeyChoices.DEPARTMENTS:
                rule["match"] = "in"
                rule["value"] = (
                    await DeptLogic.get_dept_tree_ids(json.loads(rule["value"]))
                    if dept_obj
                    else []
                )

            elif type_name == ModelField.KeyChoices.ALL:
                rule["match"] = "all"
                if result["mode"] == ModeTypeMixin.ModeChoices.OR:
                    if (
                        dept_obj and dept_obj.mode_type == ModeTypeMixin.ModeChoices.OR
                    ) or not dept_obj:
                        print(f"{model.__senweaver_name__}: all query")
                        return {}  # 直接全部返回

            elif type_name == ModelField.KeyChoices.DATE:
                val = json.loads(rule["value"])
                if val < 0:
                    rule["value"] = datetime.now(timezone.utc) - timedelta(
                        seconds=abs(val)
                    )
                else:
                    rule["value"] = datetime.now(timezone.utc) + timedelta(seconds=val)

            elif type_name == ModelField.KeyChoices.DATETIME_RANGE:
                if isinstance(rule["value"], list) and len(rule["value"]) == 2:
                    rule["value"] = [
                        func.from_unixtime(rule["value"][0]),
                        func.from_unixtime(rule["value"][1]),
                    ]

            elif type_name == ModelField.KeyChoices.DATETIME:
                if isinstance(rule["value"], str):
                    rule["value"] = func.from_unixtime(rule["value"])

            elif type_name in [
                ModelField.KeyChoices.TABLE_USER,
                ModelField.KeyChoices.TABLE_MENU,
                ModelField.KeyChoices.TABLE_ROLE,
                ModelField.KeyChoices.TABLE_DEPT,
            ]:
                value = []
                for item in json.loads(rule["value"]):
                    if isinstance(item, dict) and "id" in item:
                        value.append(item["id"])
                    else:
                        value.append(item)
                rule["value"] = value
            elif type_name == ModelField.KeyChoices.JSON:
                rule["value"] = json.loads(rule["value"])
            rule.pop("type", None)

        #  ((0, '或模式'), (1, '且模式'))
        filter_list = get_filter_attrs(result.get("rules"))
        rule_filters = defaultdict(list)
        for filter in filter_list:
            if result["mode"] == ModeTypeMixin.ModeChoices.AND:
                if not filter:
                    continue
                rule_filters["__and"].append(filter)
            else:
                if not filter:
                    rule_filters = filter
                    break
                rule_filters["__or"].append(filter)
        or_filters.append(rule_filters)
    filters = defaultdict(list)
    if not dept_obj:
        for filter in or_filters:
            filters["__or"].append(filter)
    else:
        for filter in or_filters:
            if dept_obj.mode_type == ModeTypeMixin.ModeChoices.AND:
                if not filter:
                    continue
                filters["__and"].append(filter)
            else:
                if not filter:
                    return filter
                filters["__or"].append(filter)
        if dept_obj.mode_type == ModeTypeMixin.ModeChoices.AND and not filters:
            return {"__false": None}
    return filters


async def get_request_menu(db: AsyncSession, conn: Optional[HTTPConnection] = None):
    conn = conn or g.request
    menu_id = getattr(conn.state, SENWEAVER_REQ_MENU, 0)
    if menu_id > 0:
        return menu_id
    scope_method = conn.scope.get("method")
    if not scope_method:
        return 0
    route_path = conn.scope["route"].path
    paths = [conn.url.path, route_path]
    menu_scopes = await conn.auth.get_menu_scope(conn)
    auth_menus = await FastCRUD(Menu).get_multi(
        db,
        return_total_count=False,
        is_active=True,
        limit=None,
        id__in=menu_scopes,
        menu_type=Menu.MenuChoices.PERMISSION.value,
        method=conn.scope["method"],
        path__in=paths,
    )
    url_path_menu = []
    route_path_menu = []
    for menu in auth_menus["data"]:
        if conn.url.path == menu["path"]:
            url_path_menu.append(menu["id"])
        elif route_path == menu["path"]:
            route_path_menu.append(menu["id"])
    if url_path_menu:
        menu_id = url_path_menu[0]
    elif route_path_menu:
        menu_id = route_path_menu[0]
    setattr(conn.state, SENWEAVER_REQ_MENU, menu_id)
    return menu_id


async def get_allow_fields(conn: Optional[HTTPConnection] = None):
    conn = conn or g.request
    db: AsyncSession = conn.auth.db.session
    menu_id = await get_request_menu(db, conn)
    fields = {}
    # 判断字段权限
    if menu_id > 0:
        _, role_id_scope = conn.auth.get_role_scope(conn)
        result = await db.execute(
            select(FieldPermission)
            .options(
                selectinload(FieldPermission.fields).options(
                    joinedload(ModelField.parent)
                )
            )
            .filter(
                and_(
                    FieldPermission.role_id.in_(role_id_scope),
                    FieldPermission.menu_id == menu_id,
                )
            )
        )
        records = result.scalars().all()
        for record in records:
            for field in record.fields:
                field_item = fields.get(field.parent.name, defaultdict(list))
                field_item[field.name] = field
                fields[field.parent.name] = field_item
    return fields


async def get_data_filters(
    model: type[ModelType], conn: Optional[HTTPConnection] = None
):
    """
    1.获取所有数据权限规则
    2.循环判断规则
    a.循环判断最内层规则，根据模式和全部数据进行判断【如果规则数量为一个，则模式该规则链为或模式】
        如果模式为或模式，并存在全部数据，则该规则链其他规则失效，仅保留该规则
        如果模式为且模式，并且存在全部数据，则该改则失效
    b.判断外层规则 【如果规则数量为一个，则模式该规则链为或模式】
        若模式为或模式，并存在全部数据，则直接返回filer
        若模式为且模式，则 返回filter(规则)
    """
    conn = conn or g.request
    user_obj: User = conn.user
    if Authorizer.is_superuser(conn):
        # 超管
        return {}

    db: AsyncSession = conn.auth.db.session
    menu_id = await get_request_menu(db, conn)
    has_dept = False
    dept_obj = user_obj.dept
    filters = {}
    dept_filters = {}
    if dept_obj:
        # 获取部门id列表
        dept_pks = await DeptLogic.get_dept_tree_ids(
            db, user_obj.dept_id, is_parent=True
        )
        result = await db.execute(
            (
                select(DataPermission, DeptRule.dept_id)
                .outerjoin(DeptRule, DeptRule.datapermission_id == DataPermission.id)
                .outerjoin(MenuRule, MenuRule.datapermission_id == DataPermission.id)
                .where(
                    DataPermission.is_active == True,
                    DeptRule.dept_id.in_(dept_pks),
                    or_(MenuRule.menu_id == None, MenuRule.menu_id == menu_id),
                )
            )
        )
        dept_rules = defaultdict(list)
        for permission, dept_id in result:
            dept_rules[dept_id].append(permission)
        for dept_id, permissions in dept_rules.items():
            dept_filters.update(
                await parse_filters(model, permissions, user_obj, dept_obj)
            )
            has_dept = True
        if not has_dept and not dept_filters:
            dept_filters = {"__false": None}
        if has_dept and not dept_filters:
            return filters
    # 获取个人单独授权规则
    result = await db.execute(
        (
            select(DataPermission)
            .outerjoin(UserRule, UserRule.datapermission_id == DataPermission.id)
            .outerjoin(MenuRule, MenuRule.datapermission_id == DataPermission.id)
            .where(
                DataPermission.is_active == True,
                UserRule.user_id == user_obj.id,
                or_(MenuRule.menu_id == None, MenuRule.menu_id == menu_id),
            )
        )
    )
    user_permissions = result.scalars().all()
    # 不存在个人单独授权，则返回部门规则授权
    if not user_permissions:
        print("不存在个人单独授权，则返回部门规则授权")
        if has_dept:
            return filters
        else:
            return {}  # 没有任何授权
    user_filters = await parse_filters(model, user_permissions, user_obj, dept_obj)
    if user_filters:
        # 存在部门规则和个人规则，或操作
        filters["__or"] = [user_filters, dept_filters]
    return filters
