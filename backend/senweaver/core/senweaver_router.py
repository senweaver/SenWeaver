from enum import Enum
from typing import Any, Callable, Optional, Sequence, Type, Union

from fastapi import APIRouter
from fastapi.routing import APIRoute
from sqlmodel import SQLModel

from senweaver.core.helper import SenweaverFilter
from senweaver.core.senweaver_creator import SenweaverEndpointCreator
from senweaver.core.senweaver_crud import SenweaverCRUD
from senweaver.db.helper import senweaver_model_serializer, senweaver_model_validator
from senweaver.db.types import (
    CreateSchemaType,
    DeleteSchemaType,
    SelectSchemaType,
    UpdateSchemaType,
)
from senweaver.module.base import Module


def senweaver_router(
    module: Module,
    model: type[SQLModel],
    create_schema: Optional[Type[CreateSchemaType]] = None,
    update_schema: Optional[Type[UpdateSchemaType]] = None,
    session: Callable = None,
    crud: Optional[SenweaverCRUD] = None,
    delete_schema: Optional[Type[DeleteSchemaType]] = None,
    path: str = "",
    title: Optional[str] = None,
    tags: Optional[list[Union[str, Enum]]] = None,
    include_in_schema: bool = True,
    create_deps: Sequence[Callable] = [],
    read_deps: Sequence[Callable] = [],
    read_multi_deps: Sequence[Callable] = [],
    update_deps: Sequence[Callable] = [],
    delete_deps: Sequence[Callable] = [],
    db_delete_deps: Sequence[Callable] = [],
    included_methods: Optional[list[str]] = None,
    deleted_methods: Optional[list[str]] = None,
    endpoint_creator: Optional[Type[SenweaverEndpointCreator]] = None,
    is_deleted_column: str = "is_deleted",
    deleted_at_column: str = "deleted_time",
    updated_at_column: str = "updated_time",
    created_by_id_column: str = "creator_id",
    updated_by_id_column: str = "modifier_id",
    endpoint_names: Optional[dict[str, str]] = None,
    filter_config: Optional[Union[SenweaverFilter, dict]] = None,
    select_schema: Optional[Type[SelectSchemaType]] = None,
    sort_columns: Optional[Union[str, list[str]]] = None,
    callbacks: dict[str, Callable[..., Any]] | None = None,
    check_data_scope: bool = True,
    check_field_scope: bool = True,
    read_validator: Callable[..., Any] = senweaver_model_serializer,
    write_validator: Callable[..., Any] = senweaver_model_validator,
    custom_router: Callable[..., Any] = None,
    route_class: Type[APIRoute] = None,
) -> APIRouter:
    crud = crud or SenweaverCRUD(
        model=model,
        is_deleted_column=is_deleted_column,
        deleted_at_column=deleted_at_column,
        updated_at_column=updated_at_column,
        created_by_id_column=created_by_id_column,
        updated_by_id_column=updated_by_id_column,
        relationships=filter_config.relationships if filter_config else None,
        extra_fields=filter_config.extra_fields if filter_config else None,
        allow_relationship=True,
        check_data_scope=check_data_scope,
        check_field_scope=check_field_scope,
    )

    endpoint_creator_class = endpoint_creator or SenweaverEndpointCreator
    endpoint_creator_instance = endpoint_creator_class(
        module=module,
        session=session,
        model=model,
        crud=crud,
        create_schema=create_schema,  # type: ignore
        update_schema=update_schema,  # type: ignore
        select_schema=select_schema,  # type: ignore
        include_in_schema=include_in_schema,
        delete_schema=delete_schema,
        path=path,
        title=title,
        tags=tags,
        is_deleted_column=is_deleted_column,
        deleted_at_column=deleted_at_column,
        updated_at_column=updated_at_column,
        endpoint_names=endpoint_names,
        filter_config=filter_config,
        created_by_id_column=created_by_id_column,
        updated_by_id_column=updated_by_id_column,
        sort_columns=sort_columns,
        callbacks=callbacks,
        check_data_scope=check_data_scope,
        check_field_scope=check_field_scope,
        read_validator=read_validator,
        write_validator=write_validator,
        route_class=route_class,
    )

    endpoint_creator_instance.add_routes_to_router(
        create_deps=create_deps,
        read_deps=read_deps,
        read_multi_deps=read_multi_deps,
        update_deps=update_deps,
        delete_deps=delete_deps,
        db_delete_deps=db_delete_deps,
        included_methods=included_methods,
        deleted_methods=deleted_methods,
    )
    if custom_router:
        custom_router(endpoint_creator_instance)
    return endpoint_creator_instance.router
