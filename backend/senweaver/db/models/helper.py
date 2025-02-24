import datetime
from typing import Optional, Union

from fastcrud import FastCRUD
from fastcrud.endpoint.helper import _extract_unique_columns, _get_primary_keys
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from sqlalchemy import Column
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import JSON, Boolean

from senweaver.core.helper import FieldConfig, RelationConfig, SenweaverFilter
from senweaver.core.schemas import IFormItem
from senweaver.db.models import BaseChoicesType, Choices, SQLModel
from senweaver.exception.http_exception import DuplicateValueException
from senweaver.utils.pydantic import parse_annotation_type


def choices_dict(model: type[SQLModel]):
    result = {}
    inspector = sa_inspect(model)
    for column in inspector.columns:
        if isinstance(column.type, BaseChoicesType):
            result[column.name] = get_choices_dict(column.type.choices.choices)
    return result


def get_choices_dict(choices, disabled_choices=None):
    result = []
    for value, label in choices:
        val = {"value": value, "label": label}
        if (
            disabled_choices
            and isinstance(disabled_choices, list)
            and value in disabled_choices
        ):
            val["disabled"] = True
        result.append(val)
    return result


def get_input_type(column: Column) -> str:
    try:
        if hasattr(column.type, "impl"):
            return column.type.impl.__class__.__name__.lower()
        ret = column.type.__class__.__name__.lower()
        if ret == "biginteger":
            ret = "integer"
        return ret
    except NotImplementedError:
        return "string"


def get_search_fields(
    model: type[SQLModel], filter_config: Optional[Union[SenweaverFilter, dict]] = None
) -> dict[str, IFormItem]:
    if filter_config is None:
        return {}
    results = {}
    inspector = sa_inspect(model)
    fields = model.__fields__
    fields_infos = {}
    for column in inspector.columns:
        info = get_field_info(column.name, column, fields.get(column.name))
        fields_infos[column.name] = info
    for key, value in filter_config.filters.items():
        if key == "unread":
            pass
        if "." in key:
            relation_key, attr_name = key.rsplit(".", 1)
            relation: RelationConfig = filter_config._relationship_paths.get(
                relation_key, None
            )
            if relation is None:
                continue
            relation_field_infos = get_search_fields(
                relation._model,
                SenweaverFilter(
                    filters={attr_name: None}, relationships=relation.relationships
                ),
            )
            for _, rv in relation_field_infos.items():
                rv.key = key
                if attr_name in relation._primary_key_names:
                    rv.label = f"{relation.label}{rv.label}"
                results[key] = rv
            continue
        field_name = key
        if "__" in key:
            field_name, _ = key.rsplit("__", 1)
        field_extra = (
            filter_config.extra_kwargs.get(field_name, {})
            if filter_config.extra_kwargs
            else {}
        )
        relation: RelationConfig = filter_config._relationship_dict.get(
            field_name, None
        )
        if relation:
            info = IFormItem(
                input_type=relation.input_type,
                key=key,
                label=relation.label,
                read_only=relation.read_only,
                required=relation.required,
                write_only=relation.write_only,
            )
            info = info.model_copy(update=field_extra)
            results[key] = info
            continue
        extra_field = filter_config._extra_field_dict.get(field_name, None)
        if extra_field:
            info = IFormItem(
                input_type=extra_field.input_type,
                key=key,
                label=extra_field.label,
                read_only=extra_field.read_only,
                required=extra_field.required,
                write_only=extra_field.write_only,
            )
            if info.input_type == "boolean":
                info.input_type = "select"
                info.choices = [
                    {"value": True, "label": "是"},
                    {"value": False, "label": "否"},
                ]
            info = info.model_copy(update=field_extra)
            results[key] = info
            continue
        field_info: IFormItem = fields_infos.get(field_name)
        if field_info is None:
            continue

        result_item = IFormItem(
            key=key,
            label=field_info.label,
            help_text=field_info.help_text,
            input_type=field_info.input_type,
            choices=field_info.choices or [],
            default=value or "",
        )
        if result_item.input_type == "boolean":
            result_item.input_type = "select"
            result_item.choices = [
                {"value": True, "label": "是"},
                {"value": False, "label": "否"},
            ]
        if result_item.input_type == "labeled_choice":
            result_item.input_type = "select"
        result_item = result_item.model_copy(update=field_extra)
        results[key] = result_item
    if filter_config.ordering_fields is None:
        return results
    order_choices = []
    for choice in filter_config.ordering_fields:
        is_desc = False
        if choice.startswith("-"):
            choice = choice[1:]
            is_desc = True
        desc = (f"-{choice}", f"{choice} descending")
        asc = (choice, f"{choice} ascending")
        if is_desc:
            desc, asc = asc, desc
        order_choices.extend([desc, asc])
    if order_choices:
        results["ordering"] = IFormItem(
            label="ordering",
            key="ordering",
            input_type="select-ordering",
            choices=get_choices_dict(order_choices),
            default=order_choices[0][0],
        )
    return results


def get_schema_relations(model: type[SQLModel], schema=type[BaseModel]):
    results = {}
    inspector = sa_inspect(model)
    relationships = inspector.relationships.items()
    for key, rel in relationships:
        if key not in schema.__fields__:
            continue
        field_info = schema.__fields__[key]
        if rel.uselist:
            if rel.secondary is not None:
                relation_type = "many-to-many"
            else:
                relation_type = "one-to-many"
        else:
            relation_type = "one-to-one"
            primary_keys = _get_primary_keys(rel.mapper.class_)
            primary_key_names = [pk.name for pk in primary_keys]
            foreign_key_column = next(iter(rel._calculated_foreign_keys), None)
            if foreign_key_column is None:
                continue
            results[key] = {
                "type": relation_type,
                "schema": field_info.annotation,
                "model": rel.mapper.class_,
                "pkeys": primary_keys,
                "pkeys_name": primary_key_names,
                "fk_column": foreign_key_column,
                "crud": FastCRUD(rel.mapper.class_),
            }
    return results


def get_search_columns(
    model: type[SQLModel],
    select_schema: type[BaseModel],
    filter_config: Optional[Union[SenweaverFilter, dict]] = None,
):
    results = {}
    if filter_config is None or filter_config.table_fields is None:
        return results
    fields = select_schema.model_fields
    table_shows = {
        field_show_name: index + 1
        for index, field_show_name in enumerate(filter_config.table_fields)
    }
    for field_name in filter_config.fields:
        table_index = table_shows.get(field_name, None)
        attr_obj = getattr(model, field_name, None)
        field_extra = (
            filter_config.extra_kwargs.get(field_name, {})
            if filter_config.extra_kwargs
            else {}
        )
        if isinstance(attr_obj, property):
            info = IFormItem(
                input_type="field",
                key=field_name,
                label=attr_obj.__doc__ if attr_obj.__doc__ else field_name.capitalize(),
                read_only=True,
                required=False,
                write_only=False,
            )
            if table_index:
                info.table_show = table_index
            info = info.model_copy(update=field_extra)
            results[field_name] = info
            continue
        relation: RelationConfig = filter_config._relationship_dict.get(
            field_name, None
        )
        if relation:
            info = IFormItem(
                input_type=relation.input_type,
                key=field_name,
                label=relation.label,
                read_only=relation.read_only,
                required=relation.required,
                write_only=relation.write_only,
                multiple=relation.many,
                help_text=relation.description or "",
            )
            if table_index:
                info.table_show = table_index
            info = info.model_copy(update=field_extra)
            results[field_name] = info
            continue
        extra_field = filter_config._extra_field_dict.get(field_name, None)
        if extra_field:
            info = IFormItem(
                input_type=extra_field.input_type,
                key=extra_field.name,
                label=extra_field.label,
                multiple=extra_field.many,
                help_text=extra_field.description or "",
                read_only=extra_field.read_only,
                required=extra_field.required,
                write_only=extra_field.write_only,
                **extra_field.extra_kwargs,
            )
            if table_index:
                info.table_show = table_index
            info = info.model_copy(update=field_extra)
            results[extra_field.name] = info
            continue
        column: Column = filter_config._column_fields.get(field_name)
        field = fields.get(field_name)
        info = get_field_info(field_name, column, field)
        if info is None:
            continue
        is_readonly = info.key in filter_config.read_only_fields
        if is_readonly:
            info.read_only = True
            info.required = False
        if table_index:
            info.table_show = table_index
        info = info.model_copy(update=field_extra)
        results[field_name] = info
    if filter_config.extra_kwargs:
        diff_keys = (
            set(filter_config.extra_kwargs.keys())
            - set(results.keys())
            - set(filter_config.filters.keys())
        )
        if diff_keys:
            pass
    return results


def get_field_info(
    field_name: str, column: Column, field: Optional[FieldInfo] = None
) -> IFormItem:
    if column is None and field is None:
        return None
    info = IFormItem(
        input_type="input",
        key=field_name,
        label=field_name.replace("_", " ").capitalize(),
        read_only=False,
        required=False,
        write_only=False,
    )
    if column is not None:
        if column.default is not None:
            if isinstance(
                column.default.arg, (str, int, bool, float, datetime.datetime, list)
            ):
                info.default = column.default.arg
        comment = column.comment
        if comment and comment != "":
            info.label = comment
        info.required = not column.nullable
        info.input_type = get_input_type(column)
        max_length = getattr(column.type, "length", None)
        if max_length:
            info.max_length = max_length
        if isinstance(column.type, BaseChoicesType):
            info.input_type = "labeled_choice"
            info.choices = get_choices_dict(column.type.choices.choices)
        elif isinstance(column.type, Boolean):
            info.input_type = "boolean"
        elif isinstance(column.type, JSON):
            info.input_type = "json"
    if field is None:
        return info
    extra_info = (field.json_schema_extra or {}) if field else {}
    input_type = extra_info.get("sw_input_type")
    if input_type:
        info.input_type = input_type
    else:
        annotation = parse_annotation_type(field.annotation)
        if isinstance(annotation, type) and issubclass(annotation, Choices):
            info.input_type = "labeled_choice"
            info.choices = get_choices_dict(annotation.choices)
        elif isinstance(annotation, Boolean):
            info.input_type = "boolean"
        elif isinstance(annotation, JSON):
            info.input_type = "json"
    if info.help_text is None and field.description:
        info.help_text = field.description
    else:
        info.help_text = ""
    alias_key = field.alias
    if alias_key and alias_key != field_name:
        info.key = alias_key
    if field_name.replace("_", " ").capitalize() == info.label and field.title:
        info.label = field.title
    return info
