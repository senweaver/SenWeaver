import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, Query, Request
from senweaver import SenweaverCRUD
from senweaver.auth.security import requires_permissions
from senweaver.core.helper import SenweaverFilter
from senweaver.core.models import AuditMixin, BaseMixin
from senweaver.core.senweaver_creator import SenweaverEndpointCreator
from senweaver.db.helper import get_field_lookup_info
from senweaver.db.models.helper import get_choices_dict
from senweaver.module.manager import module_manager
from senweaver.utils.response import ResponseBase, error_response, success_response
from senweaver.utils.translation import _
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, InstrumentedAttribute, RelationshipProperty
from sqlmodel import delete, select

from ..model.modelfield import ModelField


class FieldLogic:
    @classmethod
    async def update_or_create(
        cls,
        db: AsyncSession,
        model: type[DeclarativeBase],
        defaults: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> tuple[Any, bool]:
        """
        异步的 update_or_create 实现，返回 (obj, created)。

        :param db: 异步数据库会话 (AsyncSession)
        :param model: SQLModel 模型类
        :param defaults: 默认值 (用于创建或更新记录)
        :param kwargs: 查询条件 (用于过滤记录)
        :return: 元组 (obj, created)，其中 obj 是创建或更新的对象，created 表示是否是新创建的
        """
        if defaults is None:
            defaults = {}
        now_time = datetime.now(timezone.utc)
        # 查询记录
        stmt = select(model).filter_by(**kwargs)
        result = await db.execute(stmt)
        obj = result.scalars().first()
        defaults["updated_time"] = now_time
        # 如果记录不存在，则创建新记录
        if obj is None:
            defaults["created_time"] = now_time
            obj = model(**kwargs, **defaults)
            db.add(obj)
            created = True
        else:
            # 如果记录存在，则更新记录
            for key, value in defaults.items():
                setattr(obj, key, value)
            created = False

        await db.flush()
        await db.refresh(obj)  # 刷新对象以获取最新数据
        return obj, created

    @classmethod
    async def sync_model_fields(cls, request: Request):
        await cls.sync_data_model_fields(request)
        await cls.sync_role_model_fields(request)

    @classmethod
    async def sync_role_model_fields(cls, request: Request):
        db: AsyncSession = request.auth.db.session
        delete_flag = False
        model_field_labels = {}
        field_type = ModelField.FieldChoices.ROLE
        filters = module_manager.get_filters()
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        async def process_filter(filter: SenweaverFilter, parent_id=None):
            nonlocal delete_flag, count, model_field_labels
            if filter.model is None:
                return
            delete_flag = True
            # 处理当前 filter
            mapper = inspect(filter.model)  # 获取模型的映射器
            table = mapper.local_table
            table_comment = table.comment or filter.model.__name__
            obj, created = await cls.update_or_create(
                db,
                ModelField,
                name=filter.model.__senweaver_name__,
                field_type=field_type,
                parent_id=parent_id,
                defaults={"label": table_comment},
            )
            count[int(not created)] += 1

            # 处理当前 filter 的字段
            for name in filter.fields:
                field_label = None
                field = filter._field_configs_dict.get(name, None)
                if field is None:
                    field_obj = getattr(filter.model, name, None)
                    if isinstance(field_obj, property):
                        field_label = (
                            field_obj.__doc__
                            if field_obj.__doc__
                            else name.capitalize()
                        )
                    else:
                        field = filter.model.model_fields.get(name, None)
                        if field is None:
                            if isinstance(field_obj, InstrumentedAttribute):
                                fk_column = next(
                                    iter(field_obj.property.local_columns), None
                                )
                                if fk_column is not None:
                                    field = filter.model.model_fields.get(
                                        fk_column.name, None
                                    )
                                    if field is None:
                                        continue
                                    field_label = getattr(field, "title", name)
                                    field_label = re.compile(r"id", re.IGNORECASE).sub(
                                        "", field_label
                                    )
                        else:
                            field_label = getattr(field, "title", name)
                else:
                    field_label = field.label
                if field_label is not None:
                    model_field_labels[
                        f"{filter.model.__senweaver_name__}_{
                        name}"
                    ] = field_label
                field_label = (
                    field_label
                    or model_field_labels.get(
                        f"{filter.model.__senweaver_name__}_{name}", None
                    )
                    or name.capitalize()
                )

                _, created = await cls.update_or_create(
                    db,
                    ModelField,
                    name=name,
                    parent_id=obj.id,
                    field_type=field_type,
                    defaults={"label": field_label},
                )
                count[int(not created)] += 1

        relation_models = {}
        filter_models = {}
        for filter in filters:
            filter_models[filter.model.__senweaver_name__] = filter.model
            count = [0, 0]  # 用于统计 created 和 updated 的数量
            await process_filter(filter)
            for relationship in filter.relationships:
                if (
                    relationship._relationship_type == "one-to-one"
                    and relationship._model.__senweaver_name__ not in filter_models
                ):
                    relation_models[relationship._model.__senweaver_name__] = (
                        relationship._model
                    )
            print(
                f"{filter.model.__senweaver_name__}: created:{
                  count[0]} updated:{count[1]}"
            )
        for item_name, item_model in relation_models.items():
            if item_name in filter_models:
                continue
            count = [0, 0]  # 用于统计 created 和 updated 的数量
            filter = SenweaverFilter(
                model=item_model,
                read_only_fields=["creator", "modifier", "dept_belong", "id"],
                fields=[
                    field
                    for field in item_model.__mapper__.all_orm_descriptors.keys()
                    if field
                    not in {
                        "creator",
                        "modifier",
                        "creator_id",
                        "modifier_id",
                        "dept_belong_id",
                    }
                ],
            )
            await process_filter(filter)
            print(
                f"{filter.model.__senweaver_name__}: created:{
                  count[0]} updated:{count[1]}"
            )

        if delete_flag:
            result = await db.execute(
                delete(ModelField).where(
                    ModelField.field_type == field_type, ModelField.updated_time < now
                )
            )
            deleted = result.rowcount
            print(f"Sync Role permission end - deleted success, deleted:{deleted}")
        await db.commit()

    @classmethod
    async def sync_data_model_fields(cls, request: Request):
        db: AsyncSession = request.auth.db.session
        delete_flag = False
        field_type = ModelField.FieldChoices.DATA
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        m2m_models = {}
        for name, model_class in module_manager.module_models.items():
            inspector = inspect(model_class)
            relationships = inspector.mapper.relationships
            for rel in relationships:
                if rel.secondary is not None:
                    rel_model_class = module_manager.table_models.get(rel.secondary.key)
                    if rel_model_class:
                        m2m_models[rel_model_class.__senweaver_name__] = rel_model_class
                    continue
        obj, created = await cls.update_or_create(
            db,
            ModelField,
            defaults={"label": "全部表"},
            name="*",
            field_type=field_type,
            parent_id=None,
        )
        await cls.update_or_create(
            db,
            ModelField,
            defaults={"label": "全部字段"},
            name="*",
            field_type=field_type,
            parent_id=obj.id,
        )
        for key, field in BaseMixin.__fields__.items():
            await cls.update_or_create(
                db,
                ModelField,
                name=key,
                field_type=field_type,
                parent_id=obj.id,
                defaults={"label": getattr(field, "title", key)},
            )
        for key, field in AuditMixin.__fields__.items():
            label = getattr(field, "title", key)
            if "_id" in key:
                key, _ = key.rsplit("_id", 1)
                label = re.compile(r"id", re.IGNORECASE).sub("", label)
            await cls.update_or_create(
                db,
                ModelField,
                name=key,
                field_type=field_type,
                parent_id=obj.id,
                defaults={"label": label},
            )
        for name, model_class in module_manager.module_models.items():
            if name in m2m_models:
                continue
            delete_flag = True
            count = [0, 0]
            mapper = inspect(model_class)  # 获取模型的映射器
            table = mapper.local_table
            table_comment = table.comment or model_class.__name__
            obj, created = await cls.update_or_create(
                db,
                ModelField,
                name=name,
                field_type=field_type,
                parent_id=None,
                defaults={"label": table_comment},
            )
            count[int(not created)] += 1
            relationships = {}  # 触发关系映射的解析
            for relationship in mapper.relationships:
                if relationship.uselist:
                    continue
                foreign_key_column = next(iter(relationship.local_columns), None)
                if foreign_key_column is not None:
                    relationships[foreign_key_column.name] = relationship.key
            for key, field in model_class.__fields__.items():
                if key in relationships:
                    continue
                label = getattr(field, "title", key)
                if key in relationships.keys():
                    label = re.compile(r"id", re.IGNORECASE).sub("", label)
                    key = relationships[key]
                _, created = await cls.update_or_create(
                    db,
                    ModelField,
                    name=key,
                    field_type=field_type,
                    parent_id=obj.id,
                    defaults={"label": label},
                )
                count[int(not created)] += 1

            print(f"{name}:created:{count[0]} updated:{count[1]}")
        if delete_flag:
            result = await db.execute(
                delete(ModelField).where(
                    ModelField.field_type == field_type, ModelField.updated_time < now
                )
            )
            deleted = result.rowcount
            print(f"Sync Data permission end - deleted success, deleted:{deleted}")
        await db.commit()

    @classmethod
    def add_custom_router(cls, endpoint_creator: SenweaverEndpointCreator):
        self = endpoint_creator
        router = self.router
        module = self.module
        filter_config = self.filter_config

        @router.get(f"{self.path}/lookups", summary="获取字段名")
        @requires_permissions(f"{module.get_auth_str(self.resource_name, "lookups")}")
        async def field_lookups(
            request: Request, table: str, field: Optional[str] = None
        ) -> ResponseBase:
            if not (table and field):
                return error_response(code=1001)
            if table == "*":
                table = "system.user"
            data = await SenweaverCRUD(
                ModelField, relationships=filter_config.relationships
            ).get(request.auth.db.session, limit=1, name=table)
            if not data:
                return error_response(code=1001)
            model_class = module_manager.get_model(table)
            if model_class is None:
                return error_response(code=1001)
            data = get_field_lookup_info(model_class, field)
            return success_response(data)

        @router.get(f"{self.path}/sync", summary="同步字段")
        @requires_permissions(f"{module.get_auth_str(self.resource_name, "sync")}")
        async def field_sync(request: Request) -> ResponseBase:
            await FieldLogic.sync_model_fields(request)
            return success_response()

        @router.get(f"{self.path}/choices", summary="获取字段选择")
        @requires_permissions(f"{module.get_auth_str(self.resource_name, "sync")}")
        async def field_choices(request: Request) -> ResponseBase:
            disabled_choices = [
                ModelField.KeyChoices.TEXT,
                ModelField.KeyChoices.JSON,
                ModelField.KeyChoices.DATE,
                ModelField.KeyChoices.DEPARTMENTS,
            ]
            result = get_choices_dict(
                ModelField.KeyChoices.choices, disabled_choices=disabled_choices
            )
            return success_response(choices_dict={"choices": result})


field_logic = FieldLogic()
