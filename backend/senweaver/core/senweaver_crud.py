from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Sequence, Union

from fastcrud import FastCRUD, JoinConfig
from fastcrud.crud.helper import (
    JoinConfig,
    _auto_detect_join_condition,
    _handle_null_primary_key_multi_join,
    _nest_join_data,
)
from fastcrud.endpoint.helper import _get_primary_key, _get_primary_keys
from pydantic import BaseModel, ValidationError
from sqlalchemy import (
    Date,
    Time,
    and_,
    cast,
    extract,
    false,
    func,
    not_,
    or_,
    select,
    text,
    true,
)
from sqlalchemy.engine.row import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy.sql import Join
from sqlalchemy.sql.elements import BinaryExpression, ColumnElement
from sqlalchemy.sql.selectable import Select

from senweaver.auth.security import Authorizer
from senweaver.core.helper import FieldConfig, RelationConfig
from senweaver.core.schemas import SafeFormatMap
from senweaver.db.helper import detect_sql_injection
from senweaver.db.types import (
    CreateSchemaType,
    ModelType,
    SelectSchemaType,
    UpdateSchemaType,
)
from senweaver.exception.http_exception import NotFoundException
from senweaver.helper import get_nested_attribute
from senweaver.utils.globals import g


class SenweaverCRUD(FastCRUD):
    def __init__(
        self,
        model: type[ModelType],
        is_deleted_column: str = "is_deleted",
        deleted_at_column: str = "deleted_time",
        updated_at_column: str = "updated_time",
        created_by_id_column: str = "creator_id",
        updated_by_id_column: str = "modifier_id",
        relationships: Optional[Sequence[RelationConfig]] = None,
        extra_fields: Optional[Sequence[FieldConfig]] = None,
        allow_relationship: Optional[bool] = None,
        check_data_scope: Optional[bool] = None,
        check_field_scope: Optional[bool] = None,
    ) -> None:
        super().__init__(model, is_deleted_column, deleted_at_column, updated_at_column)
        if allow_relationship is None:
            allow_relationship = True if relationships else False
        if relationships and not allow_relationship:
            raise ValueError(
                "SenweaverCRUD relationship cannot be used without allow_relationship"
            )
        self.allow_relationship = allow_relationship
        self.check_data_scope = check_data_scope
        self.check_field_scope = check_field_scope
        self.relationships = relationships or []
        self.extra_fields = extra_fields or []
        self.created_by_id_column = created_by_id_column
        self.updated_by_id_column = updated_by_id_column

        relationship_dict = {}
        extra_field_dict = {}
        relationship_keys = set()
        relationship_paths = {}
        for relationship in self.relationships:
            relationship_dict[relationship.key] = relationship
            relationship_keys.add(relationship.key)
            relationship_paths.update(relationship._relationship_path or {})
        for extra_field in self.extra_fields:
            if extra_field.key in relationship_dict:
                raise ValueError(
                    f"SenweaverCRUD Key conflict : {
                                 extra_field.key}"
                )
            extra_field_dict[extra_field.key] = extra_field
        self._relationship_keys = relationship_keys
        self._relationship_dict = relationship_dict
        self._extra_field_dict = extra_field_dict
        self._field_config_dict = {**relationship_dict, **extra_field_dict}
        self._relationship_paths = relationship_paths

    # Now, add custom method

    def custom_method(self):
        pass

    def _get_sqlalchemy_filter(
        self,
        operator: str,
        value: Any,
    ) -> Optional[Callable[[str], Callable]]:
        if operator in {"in", "not_in", "between"}:
            if not isinstance(value, (tuple, list, set)):
                raise ValueError(f"<{operator}> filter must be tuple, list or set")
        self._SUPPORTED_FILTERS["eq"] = lambda column: column.__eq__
        self._SUPPORTED_FILTERS["year"] = lambda column: extract("year", column)
        self._SUPPORTED_FILTERS["month"] = lambda column: extract("month", column)
        self._SUPPORTED_FILTERS["day"] = lambda column: extract("day", column)
        self._SUPPORTED_FILTERS["hour"] = lambda column: extract("hour", column)
        self._SUPPORTED_FILTERS["minute"] = lambda column: extract("minute", column)
        self._SUPPORTED_FILTERS["second"] = lambda column: extract("second", column)
        self._SUPPORTED_FILTERS["quarter"] = lambda column: extract("quarter", column)
        self._SUPPORTED_FILTERS["weekday"] = lambda column: extract("dow", column)
        self._SUPPORTED_FILTERS["iso_weekday"] = lambda column: extract(
            "isodow", column
        )
        self._SUPPORTED_FILTERS["date"] = lambda column: cast(column, Date) == value
        self._SUPPORTED_FILTERS["time"] = lambda column: cast(column, Time) == value

        data = self._SUPPORTED_FILTERS.get(operator)
        return data

    def _parse_filters(
        self, model: Optional[Union[type[ModelType], AliasedClass]] = None, **kwargs
    ) -> list[ColumnElement]:
        model = model or self.model
        filters = []
        for key, value in kwargs.items():
            if key.startswith("__or"):
                """kwargs["__or_whatever"] = { "creator_id": 1, "is_active": True }"""
                if isinstance(value, list):
                    or_conditions = []
                    for sub_value in value:
                        parsed_sub_filters = self._parse_filters(model, **sub_value)
                        or_conditions.append(and_(*parsed_sub_filters))
                    filters.append(or_(*or_conditions))
                else:
                    or_filters_parsed = self._parse_filters(model, **value)
                    filters.append(or_(*or_filters_parsed))
            elif key.startswith("__and"):
                if isinstance(value, list):
                    and_conditions = []
                    for sub_value in value:
                        parsed_sub_filters = self._parse_filters(model, **sub_value)
                        and_conditions.append(and_(*parsed_sub_filters))
                    filters.append(and_(*and_conditions))
                else:
                    and_filters_parsed = self._parse_filters(model, **value)
                    filters.append(and_(*and_filters_parsed))
            elif key.startswith("__not"):
                """kwargs["__not_whatever"] = { "creator_id": 1, "is_active": True }"""
                not_filters_parsed = self._parse_filters(model, **value)
                filters.append(not_(*not_filters_parsed))
            elif key.startswith("__true"):
                filters.append(true())
            elif key.startswith("__false"):
                filters.append(false())
            elif key.startswith("__where"):
                filters.append(value)
            elif key.startswith("__text"):  # 支持 text 语句并绑定参数
                # 假设 value 是一个字典，其中 'sql' 是 SQL 语句，'params' 是绑定的参数
                if isinstance(value, dict):
                    sql = value.get("sql")
                    if detect_sql_injection(sql):  # 检测 SQL 注入
                        raise ValueError(f"<{sql}> SQL Injection detected!")
                    params = value.get("params", {})
                    filters.append(text(sql).params(**params))  # 绑定参数
                else:
                    if detect_sql_injection(value):  # 检测 SQL 注入
                        raise ValueError(f"<{value}> SQL Injection detected!")
                    filters.append(text(value))  # 如果没有参数，就直接插入 SQL 语句
            elif "." in key:
                relation_key, attr_name = key.rsplit(".", 1)
                relation: RelationConfig = self._relationship_paths.get(
                    relation_key, None
                )
                if relation is None or relation.alias is None:
                    filters.append(false())
                    continue
                relatioin_filters_parsed = self._parse_filters(
                    relation.alias, **{attr_name: value}
                )
                filters.append(and_(*relatioin_filters_parsed))
                continue
            else:
                if "__" in key:
                    field_name, op = key.rsplit("__", 1)
                    column = getattr(model, field_name, None)
                    if column is None:
                        raise ValueError(f"Invalid filter column: {field_name}")
                    if op == "or":
                        or_filters = [
                            sqlalchemy_filter(column)(or_value)
                            for or_key, or_value in value.items()
                            if (
                                sqlalchemy_filter := self._get_sqlalchemy_filter(
                                    or_key, or_value
                                )
                            )
                            is not None
                        ]
                        filters.append(or_(*or_filters))
                    elif op == "regex":
                        column = getattr(model, key, None)
                        request = g.request
                        if request is None or column is None:
                            continue
                        db = request.auth.db.session
                        if db.bind.dialect.name == "postgresql":
                            filters.append(column.op("~")(value))
                        elif db.bind.dialect.name in ["mysql", "mariadb", "sqlite"]:
                            filters.append(column.op("REGEXP")(value))
                        else:  # pragma: no cover
                            filters.append(false())
                    else:
                        sqlalchemy_filter = self._get_sqlalchemy_filter(op, value)
                        if sqlalchemy_filter:
                            filters.append(
                                sqlalchemy_filter(column)(value)
                                if op != "between"
                                else sqlalchemy_filter(column)(*value)
                            )
                else:
                    column = getattr(model, key, None)
                    if column is not None:
                        filters.append(column == value)

        return filters

    def _apply_sorting(
        self,
        stmt: Select,
        sort_columns: Union[str, list[str]],
        sort_orders: Optional[Union[str, list[str]]] = None,
    ) -> Select:
        """
        Applying descending sort on a single column:
        >>> stmt = _apply_sorting(stmt, 'age', 'desc')
        >>> stmt = _apply_sorting(stmt, '-age')
        Applying ascending sort on multiple columns:
        >>> stmt = _apply_sorting(stmt, ['name', '-age'])
        """
        # Parse sort_columns to determine sort orders
        if sort_columns and not sort_orders:
            if not isinstance(sort_columns, list):
                sort_columns = [sort_columns]

            sort_orders = []
            parsed_sort_columns = []
            for column in sort_columns:
                if isinstance(column, str) and column.startswith("-"):
                    sort_orders.append("desc")
                    parsed_sort_columns.append(column[1:])
                else:
                    sort_orders.append("asc")
                    parsed_sort_columns.append(column)

            sort_columns = parsed_sort_columns

        # Call the parent class's _apply_sorting method with the modified arguments
        return super()._apply_sorting(stmt, sort_columns, sort_orders)

    def _nest_multi_join_data(
        self,
        base_primary_key: str,
        data: list[Union[dict, BaseModel]],
        joins_config: Sequence[JoinConfig],
        return_as_model: bool = False,
        schema_to_select: Optional[type[BaseModel]] = None,
        nested_schema_to_select: Optional[dict[str, type[BaseModel]]] = None,
    ) -> Sequence[Union[dict, BaseModel]]:
        pre_nested_data = {}
        nested_row_key = {}
        join_primary_keys = {}
        for join_config in joins_config:
            join_primary_key = _get_primary_key(join_config.model)
            join_key = join_config.join_prefix.rstrip("_")
            join_primary_keys[join_key] = join_primary_key
        for row in data:
            if isinstance(row, BaseModel):
                new_row = {
                    key: (value[:] if isinstance(value, list) else value)
                    for key, value in row.model_dump().items()
                }
            else:
                new_row = {
                    key: (value[:] if isinstance(value, list) else value)
                    for key, value in row.items()
                }

            primary_key_value = new_row[base_primary_key]

            if primary_key_value not in pre_nested_data:
                for key, value in new_row.items():
                    join_primary_key = join_primary_keys.get(key, None)
                    if join_primary_key:
                        if isinstance(value, list) and any(
                            item[join_primary_key] is None for item in value
                        ):  # pragma: no cover
                            new_row[key] = []
                        elif (
                            isinstance(value, dict)
                            and join_primary_key in value
                            and value[join_primary_key] is None
                        ):  # pragma: no cover
                            new_row[key] = None
                        if new_row[key]:
                            for item in value:
                                nested_join_value_key = f"{primary_key_value}_{key}_{
                                    item[join_primary_key]}"
                                if (
                                    nested_row_key.get(nested_join_value_key, None)
                                    is None
                                ):
                                    nested_row_key[nested_join_value_key] = item[
                                        join_primary_key
                                    ]

                pre_nested_data[primary_key_value] = new_row
            else:
                existing_row = pre_nested_data[primary_key_value]
                for key, value in new_row.items():
                    join_primary_key = join_primary_keys.get(key, None)
                    if join_primary_key and isinstance(value, list):
                        new_values = []
                        for item in value:
                            if item[join_primary_key] is None:
                                existing_row[key] = []
                                break
                            nested_join_value_key = f"{primary_key_value}_{key}_{
                                item[join_primary_key]}"
                            if nested_row_key.get(nested_join_value_key, None) is None:
                                nested_row_key[nested_join_value_key] = item[
                                    join_primary_key
                                ]
                                new_values.append(item)
                        if new_values:
                            existing_row[key].extend(value)

        nested_data: list = list(pre_nested_data.values())

        if return_as_model:
            for i, item in enumerate(nested_data):
                if nested_schema_to_select:
                    for prefix, schema in nested_schema_to_select.items():
                        if prefix in item:
                            if isinstance(item[prefix], list):
                                item[prefix] = [
                                    schema(**nested_item)
                                    for nested_item in item[prefix]
                                ]
                            elif (
                                item[prefix] is not None
                            ):  # pragma: no cover  必须先判断是否none
                                item[prefix] = schema(**item[prefix])
                if schema_to_select:
                    nested_data[i] = schema_to_select(**item)

        return nested_data

    def _prepare_and_apply_joins(
        self,
        stmt: Select,
        joins_config: list[JoinConfig],
        use_temporary_prefix: bool = False,
    ):
        for join in joins_config:
            model = join.alias or join.model
            join_select = self._extract_matching_columns_from_schema(
                model,
                join.schema_to_select,
                join.join_prefix,
                join.alias,
                use_temporary_prefix,
            )
            joined_model_filters = self._parse_filters(
                model=model, **(join.filters or {})
            )
            if join.join_type == "left":
                stmt = stmt.outerjoin(model, join.join_on).add_columns(*join_select)
            elif join.join_type == "inner":
                stmt = stmt.join(model, join.join_on).add_columns(*join_select)
            else:  # pragma: no cover
                raise ValueError(f"Unsupported join type: {join.join_type}.")
            if joined_model_filters:
                stmt = stmt.filter(*joined_model_filters)

        return stmt

    def get_user_data(self, action: str):
        request = g.request
        updated_time = datetime.now(timezone.utc)
        user_data = {}
        if request and hasattr(request, "user"):
            user_data[self.updated_by_id_column] = request.user.id
            user_data[self.updated_at_column] = updated_time
            if action == "create":
                creator_data = request.auth.get_creator_data(self.model)
                user_data.update(creator_data)
        return user_data

    async def _save(
        self,
        action: str,
        db_object: ModelType,
        db: AsyncSession,
        data: dict[str, Any],
        **kwargs: Any,
    ):
        request = g.request
        relationship_dict = self._relationship_dict
        field_config_dict = self._field_config_dict
        user_data = self.get_user_data(action)
        data.update(user_data)
        for key, value in data.items():
            field_config: FieldConfig = field_config_dict.get(key, None)
            relationship: RelationConfig = relationship_dict.get(key, None)
            if relationship:
                pk_name = relationship._primary_key_names[0]
                rel_schema = data.get(relationship.key, None)
                if rel_schema is None:
                    setattr(
                        db_object,
                        relationship.key,
                        [] if relationship._rsp.uselist else None,
                    )
                    continue
                if relationship._rsp.uselist:
                    # one-to-many many-to-many
                    rel_objs = getattr(db_object, relationship.key, None) or []
                    existing_objs = {getattr(obj, pk_name): obj for obj in rel_objs}
                    existing_ids = [
                        (
                            item
                            if isinstance(item, relationship._primary_column_type)
                            else item.get(pk_name)
                        )
                        for item in rel_schema
                        if isinstance(
                            item, (relationship._primary_column_type, dict, BaseModel)
                        )
                    ]
                    existing_db_objs = {}
                    if existing_ids:
                        existing_db_objs_result = await db.execute(
                            select(relationship._model).where(
                                getattr(relationship._model, pk_name).in_(existing_ids)
                            )
                        )
                        existing_db_objs = {
                            getattr(obj, pk_name): obj
                            for obj in existing_db_objs_result.scalars().all()
                        }
                    new_rel_obj = []
                    for rel_item in rel_schema:
                        pk_value = (
                            rel_item
                            if isinstance(rel_item, relationship._primary_column_type)
                            else rel_item.get(pk_name)
                        )
                        rel_obj = existing_objs.get(
                            pk_value, None
                        ) or existing_db_objs.get(pk_value, None)
                        rel_item_data = {}
                        if isinstance(rel_item, (dict, BaseModel)):
                            rel_item_data = (
                                rel_item.model_dump()
                                if isinstance(rel_item, BaseModel)
                                else rel_item
                            )
                        rel_item_data.update(user_data)
                        if rel_obj:
                            for k, v in rel_item_data.items():
                                if hasattr(rel_obj, k):
                                    setattr(rel_obj, k, v)
                            new_rel_obj.append(rel_obj)
                        else:
                            rel_obj = relationship._model(**rel_item_data)
                            new_rel_obj.append(rel_obj)

                    setattr(db_object, relationship.key, new_rel_obj)
                else:
                    # one-to-one
                    exist_obj = getattr(db_object, relationship.key, None)
                    pk_value = (
                        rel_schema
                        if isinstance(rel_schema, relationship._primary_column_type)
                        else rel_schema.get(pk_name)
                    )
                    rel_obj = exist_obj
                    if pk_value:
                        exist_db_obj_result = await db.execute(
                            select(relationship._model).where(
                                getattr(relationship._model, pk_name) == pk_value
                            )
                        )
                        exist_db_obj = exist_db_obj_result.scalar_one_or_none()
                        if exist_db_obj is None:
                            setattr(db_object, relationship.key, None)
                            continue
                        rel_obj = exist_db_obj
                    rel_item_data = (
                        rel_schema.model_dump()
                        if isinstance(rel_schema, BaseModel)
                        else (rel_schema if isinstance(rel_schema, dict) else {})
                    )
                    rel_item_data.update(user_data)
                    if rel_obj:
                        for k, v in rel_item_data.items():
                            if hasattr(rel_obj, k):
                                setattr(rel_obj, k, v)
                    else:
                        rel_obj = relationship._model(**rel_item_data)
                    setattr(db_object, relationship.key, rel_obj)
            elif field_config and field_config.callbacks:
                callback = field_config.callbacks.get(action, None)
                if callback is None:
                    callback = field_config.callbacks.get("save", None)
                if callback:
                    await callback(
                        db=db,
                        obj=db_object,
                        key=key,
                        value=value,
                        request=request,
                        endpoint_creator=self,
                        **kwargs,
                    )
            elif hasattr(db_object, key):
                setattr(db_object, key, value)
        return data

    async def create(
        self, db: AsyncSession, object: CreateSchemaType, commit: bool = True
    ) -> ModelType:
        allow_field_scope, object_schema, allow_fields = (
            await Authorizer.get_allow_field_schema(
                self.model,
                self.check_field_scope,
                type(object),
                include_validator=False,
            )
        )
        if allow_field_scope and not allow_fields:
            return None
        object_dict = object.model_dump(exclude_unset=True)
        if allow_field_scope:
            object = object_schema.model_validate(object_dict)
            object_dict = object.model_dump(exclude_unset=True)
        if not self.allow_relationship:
            user_data = self.get_user_data("create")
            for k, v in user_data.items():
                if hasattr(object, k):
                    setattr(object, k, v)
            return await super().create(db=db, object=object, commit=commit)
        db_object = self.model()
        await self._save(action="create", db_object=db_object, db=db, data=object_dict)
        db.add(db_object)
        if commit:
            await db.commit()
        pk_data = self._get_pk_dict(db_object)
        object_dict.update(pk_data)
        return object_dict

    async def update(
        self,
        db: AsyncSession,
        object: Union[UpdateSchemaType, dict[str, Any]],
        allow_multiple: bool = False,
        commit: bool = True,
        return_columns: Optional[list[str]] = None,
        schema_to_select: Optional[type[SelectSchemaType]] = None,
        return_as_model: bool = False,
        one_or_none: bool = False,
        **kwargs: Any,
    ) -> Optional[Union[dict, SelectSchemaType]]:
        if isinstance(object, dict):
            update_data = object
            allow_field_scope = Authorizer.allow_field_permission(
                self.check_field_scope
            )
            if allow_field_scope:
                fields_dict: dict = await g.request.auth.get_allow_fields(self.model)
                allow_fields = list(fields_dict.keys())
                update_data = {
                    k: v for k, v in update_data.items() if k in allow_fields
                }
        else:
            allow_field_scope, object_schema, allow_fields = (
                await Authorizer.get_allow_field_schema(
                    self.model,
                    self.check_field_scope,
                    type(object),
                    include_validator=False,
                )
            )
            update_data = object.model_dump(exclude_unset=True)
            if allow_field_scope:
                object = object_schema.model_validate(update_data)
                update_data = object.model_dump(exclude_unset=True)
        if allow_field_scope and not allow_fields:
            return_columns = [_get_primary_key(self.model)]
        if not self.allow_relationship:
            user_data = self.get_user_data("update")
            if isinstance(object, dict):
                object.update(user_data)
            else:
                for k, v in user_data.items():
                    if hasattr(object, k):
                        setattr(object, k, v)
            return await super().update(
                db=db,
                object=object,
                allow_multiple=allow_multiple,
                commit=commit,
                return_columns=return_columns,
                schema_to_select=schema_to_select,
                return_as_model=return_as_model,
                one_or_none=one_or_none,
                **kwargs,
            )
        filters = self._parse_filters(**kwargs)
        stmt = select(self.model).filter(*filters)
        for relationship in self.relationships:
            if relationship.key in update_data:
                stmt = stmt.options(relationship.apply_options())
        db_result = await db.execute(stmt)
        db_object = db_result.scalars().first()
        if not db_object:
            raise NotFoundException(f"{self.model.__name__} not found")
        await self._save(
            action="update", db_object=db_object, db=db, data=update_data, **kwargs
        )
        # await db.flush()
        if commit:
            await db.commit()
        pk_data = self._get_pk_dict(db_object)
        update_data.update(pk_data)
        return update_data

    async def _build_filters(self, filters: dict[str, Any]) -> dict[str, Any]:
        tmp_filters = filters.copy()
        for key, value in tmp_filters.items():
            field_name = key
            if "_sw_dot_" in key:
                field_name = key.replace("_sw_dot_", ".")
                filters[field_name] = filters.pop(key)
            if "__" in field_name:
                field_name, _ = field_name.rsplit("__", 1)
            if callable(value):
                filters[field_name] = value()  # 执行回调获取实际的值
                continue
            relationship = self._relationship_dict.get(field_name)
            if not relationship or relationship._foreign_key_column_name is None:
                continue
            if relationship.key == key or key == relationship._foreign_key_column_name:
                relation_value = filters.pop(relationship.key, None)
                foreign_value = filters.pop(relationship._foreign_key_column_name, None)
                value = foreign_value or relation_value
                if value is None or value == 0:
                    filters[f"{relationship._foreign_key_column_name}__or"] = {
                        "is": None,
                        "eq": 0,
                    }
                else:
                    filters[relationship._foreign_key_column_name] = value
        # auth filter
        if not Authorizer.allow_data_permission(self.check_data_scope):
            return filters
        data_filter = await g.request.auth.get_data_filters(self.model)
        filters.update(data_filter)
        return filters

    async def _row_to_data(
        self,
        db: AsyncSession,
        action,
        obj,
        schema: Optional[type[BaseModel]] = None,
        return_as_model: bool = False,
        relation_item: Optional[RelationConfig] = None,
        relationships: Optional[Sequence[RelationConfig]] = None,
    ):
        if isinstance(obj, list):
            return [
                await self._row_to_data(
                    db,
                    action,
                    item,
                    schema=schema,
                    return_as_model=return_as_model,
                    relation_item=relation_item,
                    relationships=relationships,
                )
                for item in obj
            ]
        elif not hasattr(obj, "__table__"):
            return obj
        if return_as_model and schema == self.model:
            return obj
        data = {}
        obj_data = obj.__dict__
        if schema:
            for key, field in schema.model_fields.items():
                json_schema_extra = field.json_schema_extra or {}
                extra_field = json_schema_extra.get("sw_extra_field", None)
                sw_callback = json_schema_extra.get("sw_callback", {})
                callback = sw_callback.get(action, None)
                if callback is None:
                    callback = sw_callback.get("select", None)
                if callback:
                    data[key] = await callback(
                        db=db,
                        obj=obj,
                        key=key,
                        field=field,
                        schema=schema,
                        relationships=relationships,
                    )
                    continue
                if extra_field:
                    data[key] = extra_field.default
                    if "." in extra_field.key:
                        data[key] = get_nested_attribute(obj, extra_field.key, ".")
                    continue
                if "__" in key:
                    data[key] = get_nested_attribute(obj, key)
                    pass
                if key == "value" and not hasattr(obj, "value"):
                    data["value"] = obj_data[self._primary_keys[0].name]
                    pass
                if hasattr(obj, key):
                    data[key] = getattr(obj, key, None)
                if relation_item:
                    format = json_schema_extra.get("sw_format", None)
                    if format:
                        safe_format_map = SafeFormatMap(obj)
                        data[key] = format.format_map(safe_format_map)

        else:
            for column in obj.__table__.c:
                data[column.name] = getattr(obj, column.name, None)
        relation_schemas = {}
        if relationships:
            for relationship in relationships:
                key = relationship.key
                related_obj = getattr(obj, key)
                if relationship.callbacks is not None:
                    callback = relationship.callbacks.get(
                        action, relationship.callbacks.get("select", None)
                    )
                    if callback:
                        data[key] = await callback(
                            db=db, obj=obj, key=key, relation=relationship
                        )
                        relation_schemas[key] = data[key]
                        continue
                if related_obj is not None:
                    data[key] = await self._row_to_data(
                        db,
                        action,
                        obj=related_obj,
                        schema=relationship.schema_to_select,
                        return_as_model=relationship.return_as_model,
                        relation_item=relationship,
                        relationships=relationship.relationships,
                    )
                    relation_schemas[key] = data[key]
        if schema:
            if return_as_model:
                try:
                    model_data = schema(**data)
                    for key, schema_item in relation_schemas.items():
                        if hasattr(model_data, key):
                            setattr(model_data, key, schema_item)
                    return model_data
                except ValidationError as e:
                    raise ValueError(
                        f"Data validation error for schema {
                            schema.__name__}: {e}"
                    )
            elif "value" not in data and self._primary_keys:
                data["value"] = obj_data[self._primary_keys[0].name]

        return data

    def _extract_matching_columns_from_schema(
        self,
        model: Union[ModelType, AliasedClass],
        schema: Optional[type[SelectSchemaType]],
        prefix: Optional[str] = None,
        alias: Optional[AliasedClass] = None,
        use_temporary_prefix: Optional[bool] = False,
        temp_prefix: Optional[str] = "joined__",
    ) -> list[Any]:
        if not hasattr(model, "__table__"):  # pragma: no cover
            raise AttributeError(
                f"{model.__name__} does not have a '__table__' attribute."
            )

        model_or_alias = alias if alias else model
        columns = []
        temp_prefix = (
            temp_prefix if use_temporary_prefix and temp_prefix is not None else ""
        )
        if schema:
            for field in schema.model_fields.keys():
                if hasattr(model_or_alias, field):
                    column = getattr(model_or_alias, field)
                    if isinstance(column, property):
                        continue
                    if prefix is not None or use_temporary_prefix:
                        column_label = (
                            f"{temp_prefix}{prefix}{field}"
                            if prefix
                            else f"{temp_prefix}{field}"
                        )
                        column = column.label(column_label)
                    columns.append(column)
        else:
            for column in model.__table__.c:
                column = getattr(model_or_alias, column.key)
                if prefix is not None or use_temporary_prefix:
                    column_label = (
                        f"{temp_prefix}{prefix}{column.key}"
                        if prefix
                        else f"{temp_prefix}{column.key}"
                    )
                    column = column.label(column_label)
                columns.append(column)

        return columns

    async def select(
        self,
        schema_to_select: Optional[type[BaseModel]] = None,
        sort_columns: Optional[Union[str, list[str]]] = None,
        sort_orders: Optional[Union[str, list[str]]] = None,
        **kwargs: Any,
    ) -> Select:
        to_select = self._extract_matching_columns_from_schema(
            model=self.model, schema=schema_to_select
        )
        filters = self._parse_filters(**kwargs)
        stmt = select(*to_select).filter(*filters)

        if sort_columns:
            stmt = self._apply_sorting(stmt, sort_columns, sort_orders)
        return stmt

    async def get(
        self,
        db: AsyncSession,
        schema_to_select: Optional[type[SelectSchemaType]] = None,
        return_as_model: bool = False,
        one_or_none: bool = False,
        **kwargs: Any,
    ) -> Optional[Union[dict, SelectSchemaType]]:
        kwargs = await self._build_filters(kwargs)
        allow_field_scope, schema_to_select, allow_fields = (
            await Authorizer.get_allow_field_schema(
                self.model, self.check_field_scope, schema_to_select
            )
        )
        if allow_field_scope and not allow_fields:
            return None
        if not self.allow_relationship:
            return await super().get(
                db=db,
                schema_to_select=schema_to_select,
                return_as_model=return_as_model,
                one_or_none=one_or_none,
                **kwargs,
            )
        if not hasattr(self.model, "__table__"):  # pragma: no cover
            raise AttributeError(
                f"{self.model.__name__} does not have a '__table__' attribute."
            )
        if return_as_model:
            if not schema_to_select:
                raise ValueError(
                    "schema_to_select must be provided when return_as_model is True."
                )
        filters = self._parse_filters(**kwargs)
        stmt = select(self.model).filter(*filters)
        for relationship in self.relationships:
            stmt = stmt.options(relationship.apply_options())
        db_row = await db.execute(stmt)
        result = (
            db_row.scalars().one_or_none() if one_or_none else db_row.scalars().first()
        )
        if result is None:
            return None
        relation_item: RelationConfig = (
            getattr(schema_to_select, "sw_relation_config", None)
            if schema_to_select
            else None
        )
        data = await self._row_to_data(
            db,
            "read",
            result,
            schema=schema_to_select,
            return_as_model=return_as_model,
            relation_item=relation_item,
            relationships=self.relationships,
        )
        return data

    async def get_multi(
        self,
        db: AsyncSession,
        offset: int = 0,
        limit: Optional[int] = 100,
        schema_to_select: Optional[type[SelectSchemaType]] = None,
        sort_columns: Optional[Union[str, list[str]]] = None,
        sort_orders: Optional[Union[str, list[str]]] = None,
        return_as_model: bool = False,
        return_total_count: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        kwargs = await self._build_filters(kwargs)
        allow_field_scope, schema_to_select, allow_fields = (
            await Authorizer.get_allow_field_schema(
                self.model, self.check_field_scope, schema_to_select
            )
        )
        if allow_field_scope and not allow_fields:
            return (
                {"data": [], "total_count": 0} if return_total_count else {"data": []}
            )
        if not self.allow_relationship:
            return await super().get_multi(
                db=db,
                offset=offset,
                limit=limit,
                schema_to_select=schema_to_select,
                sort_columns=sort_columns,
                sort_orders=sort_orders,
                return_as_model=return_as_model,
                return_total_count=return_total_count,
                **kwargs,
            )

        if (limit is not None and limit < 0) or offset < 0:
            raise ValueError("Limit and offset must be non-negative.")
        if not hasattr(self.model, "__table__"):  # pragma: no cover
            raise AttributeError(
                f"{self.model.__name__} does not have a '__table__' attribute."
            )
        if return_as_model:
            if not schema_to_select:
                raise ValueError(
                    "schema_to_select must be provided when return_as_model is True."
                )
        filters = self._parse_filters(**kwargs)
        stmt = select(self.model).filter(*filters)
        relationships = []
        for relationship in self.relationships:
            if allow_field_scope and relationship.key not in allow_fields:
                continue
            stmt = stmt.options(relationship.apply_options())
            relationships.append(relationship)

        if sort_columns:
            stmt = self._apply_sorting(stmt, sort_columns, sort_orders)

        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        records = result.scalars().all()
        relation_item: RelationConfig = (
            getattr(schema_to_select, "sw_relation_config", None)
            if schema_to_select
            else None
        )
        data = [
            await self._row_to_data(
                db,
                "read_multi",
                item,
                schema=schema_to_select,
                return_as_model=return_as_model,
                relation_item=relation_item,
                relationships=relationships,
            )
            for item in records
        ]
        response: dict[str, Any] = {"data": data}
        if return_total_count:
            total_count = await self.count(db=db, relationships=relationships, **kwargs)
            response["total_count"] = total_count

        return response

    async def get_joined(
        self,
        db: AsyncSession,
        schema_to_select: Optional[type[SelectSchemaType]] = None,
        join_model: Optional[ModelType] = None,
        join_on: Optional[Union[Join, BinaryExpression]] = None,
        join_prefix: Optional[str] = None,
        join_schema_to_select: Optional[type[SelectSchemaType]] = None,
        join_type: str = "left",
        alias: Optional[AliasedClass] = None,
        join_filters: Optional[dict] = None,
        joins_config: Optional[list[JoinConfig]] = None,
        nest_joins: bool = False,
        relationship_type: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[dict[str, Any]]:
        kwargs = await self._build_filters(kwargs)
        return await super().get_joined(
            db=db,
            schema_to_select=schema_to_select,
            join_model=join_model,
            join_on=join_on,
            join_prefix=join_prefix,
            join_schema_to_select=join_schema_to_select,
            join_type=join_type,
            alias=alias,
            join_filters=join_filters,
            joins_config=joins_config,
            nest_joins=nest_joins,
            relationship_type=relationship_type,
            **kwargs,
        )

    async def get_multi_joined(
        self,
        db: AsyncSession,
        schema_to_select: Optional[type[SelectSchemaType]] = None,
        join_model: Optional[type[ModelType]] = None,
        join_on: Optional[Any] = None,
        join_prefix: Optional[str] = None,
        join_schema_to_select: Optional[type[SelectSchemaType]] = None,
        join_type: str = "left",
        alias: Optional[AliasedClass[Any]] = None,
        join_filters: Optional[dict] = None,
        nest_joins: bool = False,
        offset: int = 0,
        limit: Optional[int] = 100,
        sort_columns: Optional[Union[str, list[str]]] = None,
        sort_orders: Optional[Union[str, list[str]]] = None,
        return_as_model: bool = False,
        joins_config: Optional[list[JoinConfig]] = None,
        return_total_count: bool = True,
        relationship_type: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        kwargs = await self._build_filters(kwargs)
        if joins_config and (
            join_model
            or join_prefix
            or join_on
            or join_schema_to_select
            or alias
            or relationship_type
        ):
            raise ValueError(
                "Cannot use both single join parameters and joins_config simultaneously."
            )
        elif not joins_config and not join_model:
            raise ValueError("You need one of join_model or joins_config.")

        if (limit is not None and limit < 0) or offset < 0:
            raise ValueError("Limit and offset must be non-negative.")

        if relationship_type is None:
            relationship_type = "one-to-one"

        primary_select = self._extract_matching_columns_from_schema(
            model=self.model, schema=schema_to_select
        )
        stmt: Select = select(*primary_select)

        join_definitions = joins_config if joins_config else []
        if join_model:
            if join_on is None and joins_config is None:
                join_on = _auto_detect_join_condition(self.model, join_model)
            join_definitions.append(
                JoinConfig(
                    model=join_model,
                    join_on=join_on,
                    join_prefix=join_prefix,
                    schema_to_select=join_schema_to_select,
                    join_type=join_type,
                    alias=alias,
                    filters=join_filters,
                    relationship_type=relationship_type,
                )
            )

        stmt = self._prepare_and_apply_joins(
            stmt=stmt, joins_config=join_definitions, use_temporary_prefix=nest_joins
        )

        primary_filters = self._parse_filters(**kwargs)
        if primary_filters:
            stmt = stmt.filter(*primary_filters)

        if sort_columns:
            stmt = self._apply_sorting(stmt, sort_columns, sort_orders)

        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        data: list[Union[dict, BaseModel]] = []

        for row in result.mappings().all():
            row_dict = dict(row)

            if nest_joins:
                row_dict = _nest_join_data(
                    data=row_dict,
                    join_definitions=join_definitions,
                )

            if return_as_model:
                if schema_to_select is None:
                    raise ValueError(
                        "schema_to_select must be provided when return_as_model is True."
                    )
                try:
                    model_instance = schema_to_select(**row_dict)
                    data.append(model_instance)
                except ValidationError as e:
                    raise ValueError(
                        f"Data validation error for schema {
                            schema_to_select.__name__}: {e}"
                    )
            else:
                data.append(row_dict)
        # nest_joins = False
        if nest_joins and any(
            join.relationship_type == "one-to-many" for join in join_definitions
        ):
            nested_data = self._nest_multi_join_data(
                base_primary_key=self._primary_keys[0].name,
                data=data,
                joins_config=join_definitions,
                return_as_model=return_as_model,
                schema_to_select=schema_to_select if return_as_model else None,
                nested_schema_to_select={
                    (
                        join.join_prefix.rstrip("_")
                        if join.join_prefix
                        else join.model.__name__
                    ): join.schema_to_select
                    for join in join_definitions
                    if join.schema_to_select
                },
            )
        else:
            nested_data = _handle_null_primary_key_multi_join(data, join_definitions)

        response: dict[str, Any] = {"data": nested_data}

        if return_total_count:
            total_count: int = await self.count(
                db=db, joins_config=joins_config, **kwargs
            )
            response["total_count"] = total_count

        return response

    async def get_multi_by_cursor(
        self,
        db: AsyncSession,
        cursor: Any = None,
        limit: int = 100,
        schema_to_select: Optional[type[SelectSchemaType]] = None,
        sort_column: str = "id",
        sort_order: str = "asc",
        **kwargs: Any,
    ) -> dict[str, Any]:
        kwargs = await self._build_filters(kwargs)
        allow_field_scope, schema_to_select, allow_fields = (
            await Authorizer.get_allow_field_schema(
                self.model, self.check_field_scope, schema_to_select
            )
        )
        if allow_field_scope and not allow_fields:
            return {"data": [], "next_cursor": None}
        if not self.allow_relationship:
            pass
        # TODO
        return super().get_multi_by_cursor(
            db=db,
            cursor=cursor,
            limit=limit,
            schema_to_select=schema_to_select,
            sort_column=sort_column,
            sort_order=sort_order,
            **kwargs,
        )

    async def count(
        self,
        db: AsyncSession,
        joins_config: Optional[list[JoinConfig]] = None,
        relationships: Optional[Sequence[RelationConfig]] = None,
        **kwargs: Any,
    ) -> int:
        kwargs = await self._build_filters(kwargs)
        primary_filters = self._parse_filters(**kwargs)

        if joins_config is not None:
            primary_keys = [p.name for p in _get_primary_keys(self.model)]
            if not any(primary_keys):  # pragma: no cover
                raise ValueError(
                    f"The model '{
                        self.model.__name__}' does not have a primary key defined, which is required for counting with joins."
                )
            # to_select = [
            #     getattr(self.model, pk).label(f"distinct_{pk}") for pk in primary_keys
            # ]
            to_select = [
                func.distinct(getattr(self.model, pk)).label(f"distinct_{pk}")
                for pk in primary_keys
            ]
            base_query = select(*to_select)

            for relationship in relationships:
                base_query = base_query.options(relationship.apply_options())

            for join in joins_config:
                join_model = join.alias or join.model
                join_filters = (
                    self._parse_filters(model=join_model, **join.filters)
                    if join.filters
                    else []
                )

                if join.join_type == "inner":
                    base_query = base_query.join(join_model, join.join_on)
                else:
                    base_query = base_query.outerjoin(join_model, join.join_on)

                if join_filters:
                    base_query = base_query.where(*join_filters)

            if primary_filters:
                base_query = base_query.where(*primary_filters)

            subquery = base_query.subquery()
            count_query = select(func.count()).select_from(subquery)
        else:
            count_query = select(func.count()).select_from(self.model)
            if primary_filters:
                count_query = count_query.where(*primary_filters)

        total_count: Optional[int] = await db.scalar(count_query)
        if total_count is None:
            raise ValueError("Could not find the count.")

        return total_count

    async def db_delete(
        self,
        db: AsyncSession,
        allow_multiple: bool = False,
        commit: bool = True,
        **kwargs: Any,
    ) -> None:
        kwargs = await self._build_filters(kwargs)
        if not self.allow_relationship:
            pass
        # TODO
        return super().db_delete(
            db=db, allow_multiple=allow_multiple, commit=commit, **kwargs
        )

    async def delete(
        self,
        db: AsyncSession,
        db_row: Optional[Row] = None,
        allow_multiple: bool = False,
        commit: bool = True,
        **kwargs: Any,
    ) -> None:
        kwargs = await self._build_filters(kwargs)
        if not self.allow_relationship:
            pass
        # TODO
        return super().delete(
            db=db, db_row=db_row, allow_multiple=allow_multiple, commit=commit, **kwargs
        )
