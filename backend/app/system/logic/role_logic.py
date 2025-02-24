from typing import Any, List

from fastapi import Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from senweaver.exception.http_exception import NotFoundException

from ..model import Role, RoleMenu
from ..model.fieldpermission import FieldPermission
from ..model.menu import Menu
from ..model.modelfield import ModelField


class RoleLogic:

    @classmethod
    async def get_field(cls, db: AsyncSession, obj: Role, key: str, **kwargs):
        role_id = getattr(obj, "id", None)
        stmt = (
            select(FieldPermission)
            .options(selectinload(FieldPermission.fields))
            .where(FieldPermission.role_id == role_id)
        )
        result = await db.execute(stmt)
        records = result.scalars().all()
        data = {}
        for record in records:
            field_ids = [field.id for field in record.fields]
            data[record.menu_id] = field_ids
        return data

    @classmethod
    async def read(cls, db: AsyncSession, schema_to_select: type[BaseModel], **kwargs):
        role_id = kwargs.get("id", None)
        if not role_id:
            raise ValueError("参数错误")
        stmt = (
            select(Role)
            .options(
                selectinload(Role.menus),
                selectinload(Role.fields).options(selectinload(FieldPermission.fields)),
            )
            .where(Role.id == role_id)
        )
        result = await db.execute(stmt)
        obj = result.scalars().first()
        data = {}
        menus = []
        for menu in obj.menus:
            menus.append({"id": menu.id, "name": menu.name, "label": menu.id})
        data["menu"] = menus
        field_dict = {}
        for record in obj.fields:
            field_ids = [field.id for field in record.fields]
            field_dict[record.menu_id] = field_ids
        data["field"] = field_dict
        for key, _ in schema_to_select.model_fields.items():
            if key == "field" or key == "menu":
                continue
            data[key] = getattr(obj, key, None)
        return schema_to_select(**data)

    @classmethod
    async def create(cls, db: AsyncSession, item: BaseModel, **kwargs):
        role = Role()
        # request = kwargs.pop("request", None)
        data = item.model_dump()
        field = data.pop("field", None)
        fields = data.pop("fields", None) or {}
        menu = data.pop("menu", None)
        if menu is None:
            raise ValueError("Menu can't be empty")
        menu_result = await db.execute(select(Menu, Menu.id).where(Menu.id.in_(menu)))
        menus = menu_result.scalars().all()
        menu_objs = {obj.id: obj for obj in menus}
        model_field_ids = []
        for k, v in fields.items():
            model_field_ids += v
        model_field_result = await db.execute(
            select(ModelField, ModelField.id).where(ModelField.id.in_(model_field_ids))
        )
        model_fields = model_field_result.scalars().all()
        model_field_objs = {obj.id: obj for obj in model_fields}
        role = Role(**data)
        field_permissions: List[FieldPermission] = []
        for k, v in fields.items():
            model_fields = [
                model_field_objs.get(m)
                for m in v
                if model_field_objs.get(m, None) is not None
            ]
            menu_item = menu_objs.get(k, None)
            if menu_item is None:
                continue
            field_permissions.append(
                FieldPermission(menu=menu_item, fields=model_fields, role=role)
            )
        role.menus = menus
        role.fields = field_permissions
        db.add(role)
        await db.commit()
        data["id"] = role.id
        return role

    @classmethod
    async def update(cls, db: AsyncSession, item: BaseModel, **kwargs):
        role_id = kwargs.get("id", None)
        if not role_id:
            raise ValueError("参数错误")
        data = item.model_dump()
        field = data.pop("field", None)
        fields = data.pop("fields", None) or {}
        menu = data.pop("menu", None)
        if menu is None:
            raise ValueError("Menu can't be empty")
        stmt = (
            select(Role)
            .options(
                selectinload(Role.menus),
                selectinload(Role.fields).options(selectinload(FieldPermission.fields)),
            )
            .where(Role.id == role_id)
        )
        result = await db.execute(stmt)
        role = result.scalars().first()
        if not role:
            raise NotFoundException("角色不存在")
        current_menus = {obj.id: obj for obj in role.menus}
        current_field_permissions = {}
        current_model_fields = {}
        for obj in role.fields:
            current_field_permissions[f"{obj.role_id}_{obj.menu_id}"] = obj
            for obj_field in obj.fields:
                current_model_fields[obj_field.id] = obj_field

        menu_result = await db.execute(select(Menu, Menu.id).where(Menu.id.in_(menu)))
        menu_records = menu_result.scalars().all()
        existing_db_menu_objs = {obj.id: obj for obj in menu_records}
        model_field_ids = []
        existing_db_model_field_objs = {}
        if fields:
            for _, v in fields.items():
                model_field_ids += v
            model_field_result = await db.execute(
                select(ModelField, ModelField.id).where(
                    ModelField.id.in_(model_field_ids)
                )
            )
            model_field_records = model_field_result.scalars().all()
            existing_db_model_field_objs = {obj.id: obj for obj in model_field_records}
            new_field_permissions: List[FieldPermission] = []
            for menu_id, v in fields.items():
                model_fields: List[ModelField] = []
                for m in v:
                    model_field_item = current_model_fields.get(
                        m, None
                    ) or existing_db_model_field_objs.get(m, None)
                    if model_field_item:
                        model_fields.append(model_field_item)
                menu_item = current_menus.get(
                    menu_id, None
                ) or existing_db_menu_objs.get(menu_id, None)
                if menu_item is None:
                    continue
                field_permission = current_field_permissions.get(
                    f"{role.id}_{menu_item.id}", None
                ) or FieldPermission(menu=menu_item, fields=model_fields, role=role)
                field_permission.fields = model_fields
                field_permission.menu = menu_item
                new_field_permissions.append(field_permission)
            role.fields = new_field_permissions
        new_menus: List[Menu] = []
        for menu_obj in menu_records:
            new_menus.append(current_menus.get(menu_obj.id, None) or menu_obj)
        role.menus = new_menus
        await db.flush()
        await db.commit()
        return data


role_logic = RoleLogic()
