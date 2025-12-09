import copy
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Literal, Optional, Sequence, Type, Union

from fastapi import APIRouter, Body, Depends, Query
from fastapi.requests import Request
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRoute
from fastcrud.endpoint.helper import (
    _apply_model_pk,
    _extract_unique_columns,
    _get_column_types,
    _get_primary_keys,
    _get_python_type,
    _inject_dependencies,
)
from fastcrud.paginated.helper import compute_offset
from pydantic import ValidationError, model_serializer, model_validator
from pydantic.alias_generators import to_pascal
from pydantic.fields import FieldInfo
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from senweaver.auth.security import Authorizer, requires_permissions
from senweaver.core.helper import SenweaverFilter, _create_dynamic_filters
from senweaver.core.models import AuditMixin
from senweaver.core.senweaver_crud import SenweaverCRUD
from senweaver.db.helper import (
    create_pks_schema,
    senweaver_model_serializer,
    senweaver_model_validator,
)
from senweaver.db.models.helper import (
    choices_dict,
    get_search_columns,
    get_search_fields,
)
from senweaver.db.types import (
    CreateSchemaType,
    DeleteSchemaType,
    SelectSchemaType,
    UpdateSchemaType,
)
from senweaver.exception.http_exception import (
    BadRequestException,
    DuplicateValueException,
    NotFoundException,
)
from senweaver.helper import (
    build_tree,
    create_schema_by_schema,
    format_path_to_pascal_case,
)
from senweaver.module.base import Module
from senweaver.utils.response import PageResponse, ResponseBase, success_response


class SenweaverEndpointCreator:
    def __init__(
        self,
        module: Module,
        session: Callable,
        model: type[SQLModel],
        create_schema: Optional[Type[CreateSchemaType]] = None,
        update_schema: Optional[Type[UpdateSchemaType]] = None,
        select_schema: Optional[Type[SelectSchemaType]] = None,
        crud: Optional[SenweaverCRUD] = None,
        include_in_schema: bool = True,
        delete_schema: Optional[Type[DeleteSchemaType]] = None,
        path: str = "",
        tags: Optional[list[Union[str, Enum]]] = None,
        title: Optional[str] = None,
        is_deleted_column: str = "is_deleted",
        deleted_at_column: str = "deleted_time",
        created_at_column: str = "created_time",
        updated_at_column: str = "updated_time",
        created_by_id_column: str = "creator_id",
        updated_by_id_column: str = "modifier_id",
        endpoint_names: Optional[dict[str, str]] = None,
        filter_config: Optional[Union[SenweaverFilter, dict]] = None,
        sort_columns: Optional[Union[str, list[str]]] = None,
        callbacks: dict[str, Callable[..., Any]] | None = None,
        check_data_scope: bool = True,
        check_field_scope: bool = True,
        read_validator: Callable[..., Any] = senweaver_model_serializer,
        write_validator: Callable[..., Any] = senweaver_model_validator,
        route_class: Type[APIRoute] = None,
    ) -> None:
        self._primary_keys = _get_primary_keys(model)
        self._primary_keys_types = {
            pk.name: _get_python_type(pk) for pk in self._primary_keys
        }
        self.primary_key_names = [pk.name for pk in self._primary_keys]
        self.session = session
        self.model = model
        self.include_in_schema = include_in_schema
        self.path = path
        self.title = (
            title or model.__table__.comment or (tags[0] if tags else model.__name__)
        )
        self.tags = tags or []
        self.router = APIRouter(route_class=route_class or module.route_class)
        self.is_deleted_column = is_deleted_column
        self.deleted_at_column = deleted_at_column
        self.updated_at_column = updated_at_column

        self.default_endpoint_names = {
            "create": "add",
            "read": "get",
            "update": "edit",
            "delete": "del",
            "batch_delete": "batch-delete",
            "db_delete": "destroy",
            "read_multi": "",
            "read_multi_cursor": "cursor",
            "import": "import-data",
            "export": "export-data",
            "recyclebin": "recyclebin",
            "restore": "restore",
            "tree": "tree",
            "tree_parent": "list-parent",
            "choices": "choices",
            "search_columns": "search-columns",
            "search_fields": "search-fields",
        }
        self.endpoint_names = {**self.default_endpoint_names, **(endpoint_names or {})}
        self.resource_name = module.get_resource_name(path)
        self.module = module
        self.callbacks = callbacks or {}
        filter_config = filter_config or SenweaverFilter()
        if isinstance(filter_config, dict):
            filter_config = SenweaverFilter(**filter_config)
        filter_config.module = module
        filter_config.model = model
        module.add_filter(self.path, model, filter_config, self.router)
        self.created_by_id_column = created_by_id_column
        self.updated_by_id_column = updated_by_id_column
        self.sort_columns = sort_columns
        select_schema = select_schema or model
        inspector = sa_inspect(model)
        # 遍历所有字段，寻找是否存在自引用外键
        tree_parent_column = None
        filter_config._column_fields = {}
        for column in inspector.columns:
            filter_config._column_fields[column.name] = column
            if column.foreign_keys:
                for fk in column.foreign_keys:
                    # 检查外键是否引用了自身
                    if fk.column.table == model.__table__:
                        tree_parent_column = column.name
        self.tree_parent_column = tree_parent_column
        self.default_included_methods = list(self.default_endpoint_names.keys())
        self.primary_key_name = (
            self.primary_key_names[0] if self.primary_key_names else "id"
        )

        read_only_fields = [
            self.primary_key_name,
            deleted_at_column,
            updated_at_column,
            created_at_column,
            is_deleted_column,
        ]
        if issubclass(self.model, AuditMixin):
            for audit_key in list(AuditMixin.model_fields.keys()):
                read_only_fields.append(audit_key)
        column_names = list(select_schema.model_fields.keys())
        if filter_config.read_only_fields:
            read_only_fields.extend(filter_config.read_only_fields)

        filter_config.read_only_fields = read_only_fields
        # all_keys = model.__mapper__.all_orm_descriptors.keys()
        if filter_config.table_fields is None:
            filter_config.table_fields = (
                [name for name in column_names if name not in read_only_fields]
                if filter_config.fields is None
                else filter_config.fields
            )
        if filter_config.fields is None:
            filter_config.fields = [name for name in column_names if name]
        write_fields = set()
        read_extra_fields = {}
        write_extra_fields = {}
        extra_column_types = {}
        for field_name in filter_config.fields:
            field_extra = (
                filter_config.extra_kwargs.get(field_name, {})
                if filter_config.extra_kwargs
                else {}
            )
            if field_extra.get("read_only"):
                read_only_fields.append(field_name)
                continue
            if field_name in read_only_fields:
                continue
            write_fields.add(field_name)
        filter_config.read_only_fields = list(set(read_only_fields))

        for relationship in filter_config.relationships:
            json_schema_extra = {"sw_is_relationship": True}
            extra_column_types[relationship.key] = relationship._foreign_column_type
            read_extra_fields[relationship.key] = FieldInfo(
                annotation=relationship.annotation,
                default=None,
                title=relationship.label,
                description=relationship.description,
                nullable=True,
                json_schema_extra=json_schema_extra,
            )
            if relationship.key not in read_only_fields:
                write_extra_fields[relationship.key] = FieldInfo(
                    annotation=relationship.annotation,
                    default=None,
                    title=relationship.label,
                    description=relationship.description,
                    nullable=True,
                    json_schema_extra=json_schema_extra,
                )
            if relationship._is_tree:
                write_extra_fields[relationship.key] = FieldInfo(
                    annotation=relationship._foreign_column_type,
                    default=None,
                    title=relationship.label,
                    description=relationship.description,
                    nullable=True,
                    json_schema_extra=json_schema_extra,
                )
                write_extra_fields[f"{relationship.key}_ids"] = FieldInfo(
                    annotation=list[relationship._foreign_column_type],
                    default=None,
                    title="父ids",
                    nullable=True,
                    json_schema_extra=json_schema_extra,
                )

        for extra_field in filter_config.extra_fields:
            extra_column_types[extra_field.key] = extra_field.annotation or Any
            if not extra_field.write_only:
                json_schema_extra = {"sw_extra_field": extra_field}
                json_schema_extra["sw_callback"] = extra_field.callbacks or {}
                read_extra_fields[extra_field.name] = FieldInfo(
                    annotation=extra_field.annotation or Any,
                    json_schema_extra=json_schema_extra,
                    default=None,
                    title=extra_field.label,
                    description=extra_field.description,
                    nullable=True,
                )
            if (extra_field.key not in read_only_fields) or extra_field.write_only:
                write_extra_fields[extra_field.name] = FieldInfo(
                    annotation=extra_field.annotation or Any,
                    default=None,
                    title=extra_field.label,
                    description=extra_field.description,
                    nullable=True,
                )
        path_name = format_path_to_pascal_case(path)
        schema_suffix = (
            path_name if path_name != to_pascal(model.__name__) else "Schema"
        )
        self.filter_config = filter_config
        # self.select_schema = create_model(
        #     f"{select_schema.__name__}ReadSchema", __base__=select_schema)
        self.select_schema = create_schema_by_schema(
            select_schema,
            name=f"{select_schema.__name__}Read{schema_suffix}",
            include=set(filter_config.fields),
            extra_fields=read_extra_fields,
            set_optional=True,
            validators=(
                {
                    "_senweaver_model_serializer": model_serializer(mode="wrap")(
                        read_validator
                    )
                }
                if read_validator
                else None
            ),
        )
        self.select_schema.sw_filter = filter_config
        create_schema = (
            create_schema
            if create_schema
            else create_schema_by_schema(
                model,
                name=f"{model.__name__}Create{schema_suffix}",
                include=write_fields,
                extra_fields=write_extra_fields,
                validators=(
                    {
                        "_senweaver_model_validator": model_validator(mode="before")(
                            write_validator
                        )
                    }
                    if write_validator
                    else None
                ),
            )
        )
        create_schema.sw_filter = filter_config
        self.create_schema = create_schema
        update_schema = (
            update_schema
            if update_schema
            else create_schema_by_schema(
                model,
                name=f"{model.__name__}Update{schema_suffix}",
                include=write_fields,
                extra_fields=write_extra_fields,
                validators=(
                    {
                        "_senweaver_model_validator": model_validator(mode="before")(
                            write_validator
                        )
                    }
                    if write_validator
                    else None
                ),
            )
        )
        update_schema.sw_filter = filter_config
        self.update_schema = update_schema
        self.check_data_scope = check_data_scope
        self.check_field_scope = check_field_scope
        self.crud = crud or SenweaverCRUD(
            model=model,
            is_deleted_column=is_deleted_column,
            deleted_at_column=deleted_at_column,
            updated_at_column=updated_at_column,
            created_by_id_column=created_by_id_column,
            updated_by_id_column=updated_by_id_column,
            relationships=filter_config.relationships,
            extra_fields=filter_config.extra_fields,
            allow_relationship=True,
            check_data_scope=check_data_scope,
            check_field_scope=check_field_scope,
        )
        self.router.sw_filter = filter_config
        self.router.sw_endpoint_creator = self
        self.router.sw_title = self.title
        self.router.sw_model = model
        self.router.sw_module = module
        module.add_resource_router(self.resource_name, self.router)
        self.delete_schema = delete_schema
        self.filter_config = filter_config
        self.column_types = _get_column_types(model)
        self.column_types.update(extra_column_types)
        self._validate_filter_config(filter_config)

    def _validate_filter_config(self, filter_config: SenweaverFilter) -> None:
        model_columns = self.crud.model_col_names
        model_columns += list(filter_config._relationship_dict.keys())
        model_columns += list(self.select_schema.model_fields.keys())
        for key in filter_config.filters.keys():
            if "__" in key:
                key, _ = key.rsplit("__", 1)
            if "." in key and filter_config.check_attr_in_filter(key):
                continue
            if key not in model_columns:
                raise ValueError(
                    f"Invalid filter column '{key}': not found in model '{
                        self.model.__name__
                    }' columns"
                )

    async def get_session(self, request: Request):
        return request.auth.db.session if self.session is None else self.session

    def permission(self, actions: str | Sequence[str]):
        data = {
            "value": f"{self.module.get_auth_str(self.resource_name, actions)}",
            "check_data_scope": self.check_data_scope,
            "check_field_scope": self.check_field_scope,
        }
        return data

    def _create_item(self):
        """Creates an endpoint for creating items in the database."""

        @requires_permissions(
            f"{self.module.get_auth_str(self.resource_name, 'create')}"
        )
        async def create(
            request: Request,
            db: AsyncSession = Depends(self.get_session),
            item: self.create_schema = Body(...),  # type: ignore
        ) -> ResponseBase:
            unique_columns = _extract_unique_columns(self.model)
            for column in unique_columns:
                col_name = column.name
                if hasattr(item, col_name):
                    value = getattr(item, col_name)
                    if value is None:  # pragma: no cover
                        continue
                    exists = await self.crud.exists(db, **{col_name: value})
                    if exists:  # pragma: no cover
                        raise DuplicateValueException(
                            f"Value {value} is already registered"
                        )
            callback = self.callbacks.get("create", self.callbacks.get("save"))
            if callback:
                return success_response(
                    await callback(
                        endpoint_creator=self,
                        action="create",
                        request=request,
                        db=db,
                        item=item,
                    )
                )
            data = await self.crud.create(db, item)
            return success_response(data)

        return create

    def _read_item(self):
        """Creates an endpoint for reading a single item from the database."""

        @_apply_model_pk(**self._primary_keys_types)
        @requires_permissions(
            f"{self.module.get_auth_str(self.resource_name, 'detail,list')}"
        )
        async def read_item(
            request: Request, db: AsyncSession = Depends(self.get_session), **pkeys
        ) -> ResponseBase:
            callback = self.callbacks.get("read")
            if callback:
                return success_response(
                    await callback(
                        endpoint_creator=self,
                        request=request,
                        db=db,
                        schema_to_select=self.select_schema,
                        **pkeys,
                    )
                )
            filters = {}
            if hasattr(self.model, self.is_deleted_column):
                filters[self.is_deleted_column] = False
            item = await self.crud.get(
                db,
                return_as_model=True,
                schema_to_select=self.select_schema,
                **pkeys,
                **filters,
            )
            if not item:  # pragma: no cover
                raise NotFoundException("Item not found")
            return success_response(item)  # pragma: no cover

        return read_item

    def _read_choices(self, choices):
        @requires_permissions(
            f"{self.module.get_auth_str(self.resource_name, 'detail,list')}"
        )
        async def read_choices(
            request: Request, db: AsyncSession = Depends(self.get_session)
        ) -> ResponseBase:
            callback = self.callbacks.get("choices")
            if callback:
                return success_response(
                    await callback(endpoint_creator=self, request=request, db=db)
                )
            return success_response(choices_dict=choices)

        return read_choices

    def _import_data(self):
        @requires_permissions(
            f"{self.module.get_auth_str(self.resource_name, 'import')}"
        )
        async def import_data(
            request: Request,
            db: AsyncSession = Depends(self.get_session),
            action: Literal["create", "update"] = Query(
                "create", description="import data"
            ),
        ) -> ResponseBase:
            callback = self.callbacks.get("import")
            if callback:
                return success_response(
                    await callback(
                        endpoint_creator=self, request=request, db=db, action=action
                    )
                )
            return success_response()

        return import_data

    def _search_columns(self):
        results = get_search_columns(self.model, self.select_schema, self.filter_config)

        @requires_permissions(f"{self.module.get_auth_str(self.resource_name, 'list')}")
        async def search_columns(
            request: Request, db: AsyncSession = Depends(self.get_session)
        ) -> ResponseBase:
            callback = self.callbacks.get("search_columns")
            if callback:
                return success_response(
                    await callback(endpoint_creator=self, request=request, db=db)
                )
            data = []
            result_dict = results
            if self.filter_config.relationships:
                result_dict = copy.deepcopy(results)
            allow_field_scope = Authorizer.allow_field_permission()
            if allow_field_scope:
                fields_dict = await request.auth.get_allow_fields(self.model)
                allow_fields = list(fields_dict.keys())
            for key, info in result_dict.items():
                if allow_field_scope and key not in allow_fields:
                    continue
                if info.read_only:
                    info.choices = []
                    data.append(info)
                    continue
                item = self.filter_config._relationship_dict.get(key, None)
                if item:
                    relation_crud = SenweaverCRUD(
                        item._model,
                        relationships=item.relationships,
                        extra_fields=item.extra_fields,
                        check_data_scope=self.check_data_scope,
                        check_field_scope=self.check_field_scope,
                        allow_relationship=True,
                    )
                    if item.input_type == "object_related_field":
                        ret = await relation_crud.get_multi(
                            db,
                            return_total_count=False,
                            return_as_model=False,
                            limit=None,
                            schema_to_select=item.schema_to_select,
                        )
                        info.choices = ret["data"]
                    elif item.input_type == "m2m_related_field":
                        info.read_only = item.read_only
                        info.multiple = item.many
                        ret = await relation_crud.get_multi(
                            db,
                            return_total_count=False,
                            return_as_model=False,
                            limit=None,
                            schema_to_select=item.schema_to_select,
                        )
                        info.choices = ret["data"]
                data.append(info)
            return success_response(data)

        return search_columns

    def _search_fields(self):
        results = (
            get_search_fields(self.model, self.filter_config)
            if self.filter_config
            else {}
        )

        @requires_permissions(f"{self.module.get_auth_str(self.resource_name, 'list')}")
        async def search_fields(
            request: Request, db: AsyncSession = Depends(self.get_session)
        ) -> ResponseBase:
            callback = self.callbacks.get("search_fields")
            if callback:
                return success_response(
                    await callback(endpoint_creator=self, request=request, db=db)
                )
            data = []
            result_dict = results
            if self.filter_config.relationships:
                result_dict = copy.deepcopy(results)
            allow_field_scope = Authorizer.allow_field_permission()
            if allow_field_scope:
                fields_dict = await request.auth.get_allow_fields(self.model)
                allow_fields = list(fields_dict.keys())
            for key, info in result_dict.items():
                if allow_field_scope and key not in allow_fields:
                    continue
                item = self.filter_config._relationship_dict.get(key, None)
                if item:
                    relation_crud = SenweaverCRUD(
                        item._model,
                        relationships=item.relationships,
                        extra_fields=item.extra_fields,
                        check_data_scope=self.check_data_scope,
                        check_field_scope=self.check_field_scope,
                        allow_relationship=True,
                    )
                    if item.input_type == "object_related_field":
                        info.input_type = "select"
                        ret = await relation_crud.get_multi(
                            db,
                            return_total_count=False,
                            return_as_model=False,
                            limit=None,
                            schema_to_select=item.schema_to_select,
                        )
                        info.choices = ret["data"]
                    elif item.input_type == "m2m_related_field":
                        info.input_type = "select"
                        info.read_only = item.read_only
                        info.multiple = item.many
                        ret = await relation_crud.get_multi(
                            db,
                            return_total_count=False,
                            return_as_model=False,
                            limit=None,
                            schema_to_select=item.schema_to_select,
                        )
                        info.choices = ret["data"]
                data.append(info)
            return success_response(data)

        return search_fields

    def _export_data(self):
        """Creates an endpoint for reading multiple items from the database."""
        dynamic_filters = _create_dynamic_filters(self.filter_config, self.column_types)

        @requires_permissions(
            f"{self.module.get_auth_str(self.resource_name, 'export')}"
        )
        async def export_data(
            request: Request,
            db: AsyncSession = Depends(self.get_session),
            type: Literal["csv", "xlsx"] = Query(None, description="Select a category"),
            filters: dict = Depends(dynamic_filters),
            ordering: Optional[list[str]] = Query([]),
        ) -> StreamingResponse:
            if self.filter_config.backend_filters:
                filters.update(self.filter_config.backend_filters)
            if ordering is None or len(ordering) == 0:
                ordering = self.sort_columns if self.sort_columns else []
            callback = self.callbacks.get("export")
            if callback:
                return await callback(
                    endpoint_creator=self,
                    request=request,
                    db=db,
                    type=type,
                    filters=filters,
                    ordering=ordering,
                )
            # StreamingResponse | ResponseBase
            from io import BytesIO, StringIO

            import pandas as pd

            crud_data = await self.crud.get_multi(
                db,
                sort_columns=ordering,
                return_total_count=False,
                return_as_model=True,
                schema_to_select=self.select_schema,
                **filters,
            )
            data_df = pd.DataFrame([s.__dict__ for s in crud_data["data"]])
            if type == "xlsx":
                stream = BytesIO()
                with pd.ExcelWriter(stream) as writer:
                    data_df.to_excel(writer, index=False)
                media_type = (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                filename = f"export_{self.model.__name__}_{
                    datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                }.xlsx"
            else:
                stream = StringIO()
                data_df.to_csv(stream, index=False)
                media_type = "text/csv"
                filename = f"export_{self.model.__name__}_{
                    datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                }.csv"

            response = StreamingResponse(
                iter([stream.getvalue()]),
                media_type=media_type,
                headers={
                    "Content-Disposition": f"attachment;filename={filename}",
                    "Access-Control-Expose-Headers": "Content-Disposition",
                },
            )
            return response

        return export_data

    def _read_items(self, is_tree=False):
        dynamic_filters = _create_dynamic_filters(self.filter_config, self.column_types)

        @requires_permissions(f"{self.module.get_auth_str(self.resource_name, 'list')}")
        async def read_items(
            request: Request,
            db: AsyncSession = Depends(self.get_session),
            offset: Optional[int] = Query(
                None, description="Offset for unpaginated queries"
            ),
            limit: Optional[int] = Query(
                None, description="Limit for unpaginated queries"
            ),
            page: Optional[int] = Query(None, alias="page", description="Page number"),
            items_per_page: Optional[int] = Query(
                None, alias="size", description="Number of items per page"
            ),
            filters: dict = Depends(dynamic_filters),
            ordering: Optional[list[str]] = Query([]),
        ) -> ResponseBase:
            if self.filter_config.backend_filters:
                filters.update(self.filter_config.backend_filters)
            if ordering is None or len(ordering) == 0:
                ordering = self.sort_columns if self.sort_columns else []
            if hasattr(self.model, self.is_deleted_column):
                filters[self.is_deleted_column] = False
            callback = self.callbacks.get("read_multi")
            if callback:
                return await callback(
                    endpoint_creator=self,
                    is_tree=is_tree,
                    request=request,
                    db=db,
                    offset=offset,
                    limit=limit,
                    filters=filters,
                    page=page,
                    items_per_page=items_per_page,
                    ordering=ordering,
                )

            is_paginated = (page is not None) and (items_per_page is not None)
            has_offset_limit = (offset is not None) and (limit is not None)

            if is_paginated and has_offset_limit:
                raise BadRequestException(
                    detail="Conflicting parameters: Use either 'page' and 'itemsPerPage' for paginated results or 'offset' and 'limit' for specific range queries."
                )
            if is_paginated:
                offset = compute_offset(page=page, items_per_page=items_per_page)  # type: ignore
                limit = items_per_page
                crud_data = await self.crud.get_multi(
                    db,
                    offset=offset,
                    limit=limit,
                    sort_columns=ordering,
                    return_as_model=True,
                    schema_to_select=self.select_schema,
                    **filters,
                )
                list_data = crud_data["data"]
                if is_tree:
                    list_data = build_tree(list_data)
                return PageResponse.create(
                    results=list_data,
                    total=crud_data["total_count"],
                    page=page,
                    page_size=items_per_page,
                )

            if not has_offset_limit:
                offset = 0
                limit = 10
            crud_data = await self.crud.get_multi(
                db,
                offset=offset,
                limit=limit,
                sort_columns=ordering,
                return_as_model=True,
                schema_to_select=self.select_schema,
                **filters,
            )
            if is_tree:
                crud_data["data"] = build_tree(crud_data["data"])
            return success_response(
                {"results": crud_data["data"], "total": crud_data["total_count"]}
            )  # pragma: no cover

        return read_items

    def _read_items_cursor(self):
        dynamic_filters = _create_dynamic_filters(self.filter_config, self.column_types)

        @requires_permissions(f"{self.module.get_auth_str(self.resource_name, 'list')}")
        async def read_items_cursor(
            request: Request,
            db: AsyncSession = Depends(self.get_session),
            cursor: Any = None,
            limit: int = Query(10),
            filters: dict = Depends(dynamic_filters),
            ordering: Optional[list[str]] = Query([]),
        ) -> ResponseBase:
            if self.filter_config.backend_filters:
                filters.update(self.filter_config.backend_filters)
            if ordering is None or len(ordering) == 0:
                ordering = self.sort_columns if self.sort_columns else []
            if hasattr(self.model, self.is_deleted_column):
                filters[self.is_deleted_column] = False
            callback = self.callbacks.get("read_multi_cursor")
            if callback:
                return success_response(
                    await callback(
                        endpoint_creator=self,
                        request=request,
                        db=db,
                        cursor=cursor,
                        limit=limit,
                        filters=filters,
                        ordering=ordering,
                        schema_to_select=self.select_schema,
                    )
                )
            crud_data = await self.crud.get_multi_by_cursor(
                db,
                cursor=cursor,
                limit=limit,
                sort_columns=ordering,
                return_as_model=True,
                schema_to_select=self.select_schema,
                **filters,
            )

            return success_response(crud_data)

        return read_items_cursor

    def _update_item(self):
        @_apply_model_pk(**self._primary_keys_types)
        @requires_permissions(
            f"{self.module.get_auth_str(self.resource_name, 'update')}"
        )
        async def update_item(
            request: Request,
            item: self.update_schema = Body(...),  # type: ignore
            db: AsyncSession = Depends(self.get_session),
            **pkeys,
        ) -> ResponseBase:
            callback = self.callbacks.get("update", self.callbacks.get("save"))
            if callback:
                return success_response(
                    await callback(
                        endpoint_creator=self,
                        request=request,
                        action="update",
                        db=db,
                        item=item,
                        **pkeys,
                    )
                )
            ret = await self.crud.update(db, item, **pkeys)
            return success_response(ret)

        return update_item

    def _delete_item(self):
        @_apply_model_pk(**self._primary_keys_types)
        @requires_permissions(
            f"{self.module.get_auth_str(self.resource_name, 'delete')}"
        )
        async def delete_item(
            request: Request, db: AsyncSession = Depends(self.get_session), **pkeys
        ) -> ResponseBase:
            callback = self.callbacks.get("delete")
            if callback:
                return success_response(
                    await callback(
                        endpoint_creator=self, request=request, db=db, **pkeys
                    )
                )
            filters = self.crud._parse_filters(**pkeys)
            stmt = select(self.model).filter(*filters)
            for relationship in self.filter_config.relationships:
                stmt = stmt.options(relationship.apply_options())
            db_row = await db.execute(stmt)
            obj_data = db_row.scalars().first()
            if not obj_data:
                raise NotFoundException(f"{self.model.__name__} not found")
            await db.delete(obj_data)
            await db.commit()
            return success_response()

        return delete_item

    def _batch_delete_items(self):
        pk_name = self._primary_keys[0].name
        pk_type = self._primary_keys_types[pk_name]
        pks_schema = create_pks_schema(
            f"{self.model.__name__}_PksModel", pk_name, pk_type, pk_name
        )

        @requires_permissions(
            f"{self.module.get_auth_str(self.resource_name, 'batchDelete')}"
        )
        async def batch_delete_items(
            request: Request,
            db: AsyncSession = Depends(self.get_session),
            item: Union[pks_schema, list[pk_type]] = Body(...),
        ) -> ResponseBase:
            callback = self.callbacks.get("batch_delete")
            if callback:
                return success_response(
                    await callback(
                        endpoint_creator=self, request=request, db=db, item=item
                    )
                )
            if isinstance(item, pks_schema):
                ids = getattr(item, f"{pk_name}s")
                if ids is None or len(ids) <= 0:  # pragma: no cover
                    raise BadRequestException(detail=f"{pk_name}s error or empty")
            else:
                ids = item
            kwargs = dict()
            kwargs[f"{pk_name}__in"] = ids
            filters = self.crud._parse_filters(**kwargs)
            stmt = select(self.model).filter(*filters)
            for relationship in self.filter_config.relationships:
                stmt = stmt.options(relationship.apply_options())
            db_row = await db.execute(stmt)
            records = db_row.scalars().all()
            for item in records:
                await db.delete(item)
            await db.commit()
            return success_response()

        return batch_delete_items

    def _db_delete(self):
        """
        Creates an endpoint for hard deleting an item from the database.
        """

        @_apply_model_pk(**self._primary_keys_types)
        @requires_permissions(
            f"{self.module.get_auth_str(self.resource_name, 'destroy')}"
        )
        async def destroy(
            request: Request, db: AsyncSession = Depends(self.get_session), **pkeys
        ) -> ResponseBase:
            callback = self.callbacks.get("db_delete")
            if callback:
                return success_response(
                    await callback(
                        endpoint_creator=self, request=request, db=db, **pkeys
                    )
                )
            return success_response(await self.crud.db_delete(db, **pkeys))

        return destroy

    def add_routes_to_router(
        self,
        create_deps: Sequence[Callable] = [],
        read_deps: Sequence[Callable] = [],
        read_multi_deps: Sequence[Callable] = [],
        update_deps: Sequence[Callable] = [],
        delete_deps: Sequence[Callable] = [],
        db_delete_deps: Sequence[Callable] = [],
        included_methods: Optional[Sequence[str]] = None,
        deleted_methods: Optional[Sequence[str]] = None,
    ):
        """override add_routes_to_router to also add the custom routes"""
        if (included_methods is not None) and (deleted_methods is not None):
            raise ValueError(
                "Cannot use both 'included_methods' and 'deleted_methods' simultaneously."
            )
        if included_methods is None:
            included_methods = self.default_included_methods
        else:
            try:
                for v in included_methods:
                    if v not in self.default_included_methods:
                        raise ValueError(f"Invalid CRUD method: {v}")
            except ValidationError as e:
                raise ValueError(f"Invalid CRUD methods in included_methods: {e}")

        if deleted_methods is None:
            deleted_methods = []
        else:
            try:
                for v in deleted_methods:
                    if v not in self.default_included_methods:
                        raise ValueError(f"Invalid CRUD method: {v}")
            except ValidationError as e:
                raise ValueError(f"Invalid CRUD methods in deleted_methods: {e}")

        delete_description = "Delete a"
        if self.delete_schema:
            delete_description = "Soft delete a"

        if ("create" in included_methods) and ("create" not in deleted_methods):
            self.router.add_api_route(
                self._get_endpoint_path(operation="create"),
                self._create_item(),
                name="create",
                methods=["POST"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=_inject_dependencies(create_deps),
                summary=f"添加{self.title}",
                description=f"Create a new {self.model.__name__} row in the database.",
            )
        if ("read" in included_methods) and ("read" not in deleted_methods):
            self.router.add_api_route(
                self._get_endpoint_path(operation="read"),
                self._read_item(),
                name="detail",
                methods=["GET"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=_inject_dependencies(read_deps),
                summary=f"获取{self.title}详情",
                description=f"Read a single {
                    self.model.__name__
                } row from the database by its primary keys",
            )
        if ("read_multi" in included_methods) and ("read_multi" not in deleted_methods):
            self.router.add_api_route(
                self._get_endpoint_path(operation="read_multi"),
                self._read_items(),
                name="list",
                methods=["GET"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=_inject_dependencies(read_multi_deps),
                summary=f"获取{self.title}列表",
                description=f"Read multiple {
                    self.model.__name__
                } rows from the database with a limit and an offset.",
            )
        if ("read_multi_cursor" in included_methods) and (
            "read_multi_cursor" not in deleted_methods
        ):
            self.router.add_api_route(
                self._get_endpoint_path(operation="read_multi_cursor"),
                self._read_items_cursor(),
                methods=["GET"],
                name="cursor",
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=_inject_dependencies(read_multi_deps),
                summary=f"通过游标获取{self.title}列表",
                description="Implements cursor-based pagination for fetching records.",
            )

        if (
            ("tree" in included_methods)
            and ("tree" not in deleted_methods)
            and self.tree_parent_column
        ):
            self.router.add_api_route(
                self._get_endpoint_path(operation="tree"),
                self._read_items(is_tree=True),
                methods=["GET"],
                name="tree",
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=_inject_dependencies(read_multi_deps),
                summary=f"获取树状结构的{self.title}数据",
                description=f"Read {self.model.__name__} tree.",
            )
        if ("choices" in included_methods) and ("choices" not in deleted_methods):
            choices = choices_dict(self.model)
            if choices:
                self.router.add_api_route(
                    self._get_endpoint_path(operation="choices"),
                    self._read_choices(choices),
                    name="choices",
                    methods=["GET"],
                    include_in_schema=self.include_in_schema,
                    tags=self.tags,
                    dependencies=_inject_dependencies(read_deps),
                    summary=f"获取 {self.title}字段选择",
                    description=f"Read {self.model.__name__} choices.",
                )
        if ("export" in included_methods) and ("export" not in deleted_methods):
            self.router.add_api_route(
                self._get_endpoint_path(operation="export"),
                self._export_data(),
                name="export",
                methods=["GET"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=_inject_dependencies(read_deps),
                summary=f"导出{self.title}数据",
                description=f"Export {self.model.__name__} Data.",
            )
        if ("import" in included_methods) and ("import" not in deleted_methods):
            self.router.add_api_route(
                self._get_endpoint_path(operation="import"),
                self._import_data(),
                name="import",
                methods=["POST"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=_inject_dependencies(read_deps),
                summary=f"导入{self.title}数据",
                description=f"Import {self.model.__name__} Data.",
            )
        if ("search_columns" in included_methods) and (
            "search_columns" not in deleted_methods
        ):
            self.router.add_api_route(
                self._get_endpoint_path(operation="search_columns"),
                self._search_columns(),
                name="search_columns",
                methods=["GET"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=_inject_dependencies(read_deps),
                summary=f"获取{self.title}的展示字段",
                description=f"Search {self.model.__name__} columns",
            )
        if ("search_fields" in included_methods) and (
            "search_fields" not in deleted_methods
        ):
            self.router.add_api_route(
                self._get_endpoint_path(operation="search_fields"),
                self._search_fields(),
                name="search_fields",
                methods=["GET"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=_inject_dependencies(read_deps),
                summary=f"获取{self.title}的查询字段",
                description=f"Search {self.model.__name__} columns",
            )

        if ("update" in included_methods) and ("update" not in deleted_methods):
            self.router.add_api_route(
                self._get_endpoint_path(operation="update"),
                self._update_item(),
                name="update",
                methods=["POST"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=_inject_dependencies(update_deps),
                summary=f"更新{self.title}",
                description=f"Update an existing {
                    self.model.__name__
                } row in the database by its primary keys: {self.primary_key_names}.",
            )
        if ("delete" in included_methods) and ("delete" not in deleted_methods):
            path = self._get_endpoint_path(operation="delete")
            self.router.add_api_route(
                path,
                self._delete_item(),
                name="delete",
                methods=["POST"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=_inject_dependencies(delete_deps),
                summary=f"删除{self.title}",
                description=f"{delete_description} {
                    self.model.__name__
                } row from the database by its primary keys: {self.primary_key_names}.",
            )

        if (
            ("batch_delete" in included_methods)
            and ("batch_delete" not in deleted_methods)
            and (len(self._primary_keys) == 1)
        ):
            path = self._get_endpoint_path(operation="batch_delete")
            self.router.add_api_route(
                path,
                self._batch_delete_items(),
                name="batchDelete",
                methods=["POST"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=_inject_dependencies(delete_deps),
                summary=f"批量删除{self.title}",
                description=f"{delete_description} {
                    self.model.__name__
                } rows from the database by its primary keys",
            )

        if (
            ("db_delete" in included_methods)
            and ("db_delete" not in deleted_methods)
            and self.delete_schema
        ):
            self.router.add_api_route(
                self._get_endpoint_path(operation="db_delete"),
                self._db_delete(),
                name="destroy",
                methods=["POST"],
                include_in_schema=self.include_in_schema,
                tags=self.tags,
                dependencies=_inject_dependencies(db_delete_deps),
                summary=f"物理删除{self.title}",
                description=f"Permanently delete a {
                    self.model.__name__
                } row from the database by its primary keys: {self.primary_key_names}.",
            )

    def get_openapi_extra(self):
        return {
            "senweaver_extra": {"title": self.title, "resource": self.resource_name}
        }

    def _get_endpoint_path(self, operation: str):
        endpoint_name = self.endpoint_names.get(
            operation, self.default_endpoint_names.get(operation, operation)
        )
        path = f"{self.path}/{endpoint_name}" if endpoint_name else self.path

        if operation in {"read", "update", "delete", "db_delete"}:
            _primary_keys_path_suffix = "/".join(
                f"{{{n}}}" for n in self.primary_key_names
            )
            path = f"{path}/{_primary_keys_path_suffix}"

        return path

    def add_custom_route(
        self,
        endpoint: Callable,
        methods: Optional[Union[set[str], list[str]]],
        path: Optional[str] = None,
        dependencies: Optional[Sequence[Callable]] = None,
        include_in_schema: bool = True,
        tags: Optional[list[Union[str, Enum]]] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        response_description: str = "Successful Response",
    ) -> None:
        path = self.path if path is None else path
        full_path = f"{self.path}{path}"
        self.router.add_api_route(
            path=full_path,
            endpoint=endpoint,
            methods=methods,
            dependencies=_inject_dependencies(dependencies) or [],
            include_in_schema=include_in_schema,
            tags=tags or self.tags,
            summary=summary,
            description=description,
            response_description=response_description,
        )
