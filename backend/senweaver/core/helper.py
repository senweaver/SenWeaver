import inspect
from enum import Enum
from typing import Annotated, Any, Callable, List, Optional, Sequence, Union
from urllib.parse import urljoin

from config.settings import settings
from fastapi import FastAPI, Query
from fastcrud import FilterConfig
from fastcrud.endpoint.helper import _get_primary_keys, _get_python_type
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_pascal
from pydantic.fields import FieldInfo
from senweaver.helper import create_schema_by_schema
from senweaver.utils.globals import g
from sqlalchemy import Column
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import (
    InstrumentedAttribute,
    RelationshipProperty,
    aliased,
    class_mapper,
    contains_eager,
    defaultload,
    joinedload,
    lazyload,
    noload,
    raiseload,
    selectinload,
    subqueryload,
)
from sqlalchemy.orm.util import AliasedClass
from sqlmodel import SQLModel

LOAD_STRATEGIES = {
    "selectin": selectinload,
    "joined": joinedload,
    "subquery": subqueryload,
    "contains_eager": contains_eager,
    "noload": noload,
    "lazy": lazyload,
    "raise": raiseload,
    "raise": raiseload,
    "default": defaultload,
}


class FieldConfig(BaseModel):
    default: Optional[Any] = None
    key: Optional[str] = None
    name: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None
    input_type: Optional[str] = ""
    required: Optional[bool] = False
    read_only: Optional[bool] = False
    write_only: Optional[bool] = False
    many: Optional[bool] = None
    format: Optional[str] = None
    annotation: Optional[Any] = None
    callbacks: dict[str, Callable[..., Any]] | None = None
    extra_kwargs: Optional[dict[str, Any]] = {}
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def set_name_from_key(self) -> "FieldConfig":
        if self.name is None and self.key is not None:
            self.name = self.key
        return self


class RelationConfig(FieldConfig):
    rel: InstrumentedAttribute
    filters: Annotated[dict[str, Any], Field(default={})]
    strategy: Optional[str] = None
    attrs: Optional[Sequence[str]] = None
    exclude: Optional[Sequence[str]] = None
    schema_to_select: Optional[type[BaseModel]] = None
    return_as_model: bool = True
    relationships: Optional[Sequence["RelationConfig"]] = None
    extra_fields: Optional[Sequence[FieldConfig]] = None
    alias: Optional[Union[AliasedClass, str, bool]] = None
    _model: Optional[type[SQLModel]] = None
    _base_model: Optional[type[SQLModel]] = None
    _link_model: Optional[type[SQLModel]] = None
    _foreign_key_names: Optional[Sequence[str]] = None
    _foreign_key_columns: Optional[Column] = None
    _foreign_key_column: Optional[Column] = None
    _foreign_key_column_name: Optional[str] = None
    _foreign_column_type: Optional[type] = None
    _primary_key_names: Optional[Sequence[str]] = None
    _is_tree: Optional[bool] = None
    _rsp: Optional[RelationshipProperty] = None
    _relationship_type: Optional[str] = None
    _relationship_path: Optional[dict[str, "RelationConfig"]] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def check_relation_config(self):
        if self.required is None:
            self.required = not self.read_only
        self.key = self.rel.key
        self._base_model = self.rel.class_
        self._model = self.rel.mapper.class_
        inspector = sa_inspect(self._model)
        rsp = class_mapper(self._base_model).get_property(self.rel.key)
        self._rsp = rsp
        foreign_key_columns = rsp._calculated_foreign_keys
        self._foreign_key_columns = foreign_key_columns
        foreign_key_column = next(iter(foreign_key_columns), None)
        self._foreign_key_column = foreign_key_column
        self._foreign_key_column_name = (
            foreign_key_column.name if foreign_key_column is not None else None
        )
        self._foreign_column_type = _get_python_type(foreign_key_column)
        self._foreign_key_names = [fk.name for fk in foreign_key_columns]
        label_str = (
            rsp.target.comment
            if rsp.target.comment and rsp.target.comment != ""
            else self.key.capitalize()
        )
        self.label = self.label if self.label else label_str
        primary_key_columns = inspector.mapper.primary_key
        primary_key_names = [pk.name for pk in primary_key_columns]
        self._primary_column_type = _get_python_type(primary_key_columns[0])
        self._primary_key_names = primary_key_names
        column_names = list(self._model.model_fields.keys())
        pk_format_list = []
        pk_format = None
        for pk_name in primary_key_names:
            pk_format_list.append(f"{{{pk_name}}}")
        if pk_format_list:
            pk_format = "-".join(pk_format_list)
        if self.format is None:
            if "label" in column_names:
                self.format = "{label}"
            else:
                self.format = pk_format
        self.relationships = self.relationships or []
        relationship_dict = {}
        for relationship in self.relationships:
            relationship_dict[relationship.key] = relationship

        self._relationship_dict = relationship_dict
        if self.schema_to_select is None:
            extra_fieslds = {}
            if "label" not in column_names:
                extra_fieslds["label"] = FieldInfo(
                    annotation=str,
                    default="",
                    title="标题",
                    nullable=True,
                    json_schema_extra={
                        "sw_format": self.format,
                        "sw_relation_field": True,
                    },
                )
            old_attrs = self.attrs or []
            diff_attrs = set(old_attrs) - set(column_names)
            for attr_name in diff_attrs:
                if "__" in attr_name:
                    extra_fieslds.update(self.get_nested_extra_fields(attr_name))
                    continue
                attr_obj = getattr(self._model, attr_name, None)
                if attr_obj is None:
                    if attr_name == "value":
                        pk_field = self._model.model_fields.get(
                            self._primary_key_names[0], None
                        )
                        if pk_field:
                            extra_fieslds["value"] = FieldInfo(
                                annotation=pk_field.annotation,
                                default=pk_field.default,
                                title=pk_field.title,
                                nullable=True,
                                json_schema_extra={"sw_relation_field": True},
                            )
                    continue
                if isinstance(attr_obj, property):
                    extra_fieslds[attr_name] = FieldInfo(
                        annotation=Any,
                        default="",
                        nullable=True,
                        json_schema_extra={
                            "sw_relation_field": True,
                            "sw_property_field": True,
                        },
                    )
            if self.attrs is None and self.exclude is None:
                # only primary key
                self.attrs = primary_key_names
            self.schema_to_select = create_schema_by_schema(
                self._model,
                name=f"{self._base_model.__name__}{
                    to_pascal(self.key)}Relation",
                include=set(self.attrs) if self.attrs else None,
                exclude=set(self.exclude) if self.exclude else None,
                extra_fields=extra_fieslds,
                set_optional=True,
            )
        self.attrs = list(self.schema_to_select.model_fields.keys())
        self.schema_to_select.sw_relation_config = self

        if rsp.uselist:
            self.strategy = self.strategy or "selectin"
            self.many = True if self.many is None else self.many
            self.annotation = (
                self.annotation
                or Union[List[self.schema_to_select], List[self._primary_column_type]]
            )
            if rsp.secondary is not None:
                # many-to-many
                self._relationship_type = "many-to-many"
                relatoinship = self._base_model.__sqlmodel_relationships__[self.key]
                self._link_model = relatoinship.link_model
                self.input_type = self.input_type or "m2m_related_field"
            else:
                # one-to-many
                self._relationship_type = "one-to-many"
                self.input_type = self.input_type or "o2m_related_field"
        else:
            # one-to-one
            self._relationship_type = "one-to-one"
            self.strategy = self.strategy or "joined"
            self.annotation = (
                self.annotation
                or Union[self.schema_to_select, self._primary_column_type, None]
            )
            self.input_type = "object_related_field"
            self.many = False if self.many is None else self.many
            if self._base_model == self._model:
                self._is_tree = True

        if self.strategy == "joined":
            if self.alias and isinstance(self.alias, str):
                self.alias = aliased(self._model, name=self.alias)
            self.alias = self.alias or aliased(self._model, name=f"sw_{self.key}")
        self._strategy = LOAD_STRATEGIES.get(self.strategy)
        self.relationships = self.relationships or []
        self._relationship_path = self.build_path_map()
        return self

    # 构建路径映射

    def build_path_map(self, parent_path: str = "") -> dict[str, "RelationConfig"]:
        path_map = {}
        full_path = f"{parent_path}.{self.key}" if parent_path else self.key
        # 如果当前有attrs，则加入映射
        if self.attrs:
            path_map[full_path] = self
        # 如果有子关系，则递归构建路径映射
        for rel in self.relationships:
            path_map.update(rel.build_path_map(full_path))
        return path_map

    def get_nested_extra_fields(self, attr_name: str) -> dict:
        """处理具有多个'__'分隔符的嵌套属性"""
        extra_fields = {}
        attr_parts = attr_name.split("__")
        relation_key = attr_parts[0]
        relation_attr_name = attr_parts[-1]
        relationship_dict = self._relationship_dict
        relation_child: RelationConfig = relationship_dict.get(relation_key, None)
        if not relation_child:
            return extra_fields

        for part in attr_parts[1:-1]:
            relation_child = next(
                (r for r in relation_child.relationships if r.key == part), None
            )
            if not relation_child:
                return extra_fields

        if relation_child:
            relation_attr = relation_child._model.model_fields.get(
                relation_attr_name, None
            )
            if relation_attr:
                extra_fields[attr_name] = FieldInfo(
                    annotation=relation_attr.annotation,
                    default=relation_attr.default,
                    title=relation_attr.title,
                    description=relation_attr.description,
                    nullable=True,
                    sw_relation_field=True,
                )

        return extra_fields

    def apply_options(self):
        # 默认创建一个加载选项
        base_option = self._strategy(
            self.rel.of_type(self.alias) if self.alias else self.rel
        )
        # 对每个子关系，调用 apply_options，生成嵌套的选项
        for relationship in self.relationships:
            # 为当前关系创建 `.options()` 调用，并递归添加子关系的选项
            base_option = base_option.options(relationship.apply_options())
        return base_option


class SenweaverFilter(FilterConfig):
    backend_filters: Annotated[dict[str, Any], Field(default={})]
    model: Optional[type[SQLModel]] = None
    module: Any = None
    ordering_fields: Optional[list[str]] = None
    fields: Optional[list[str]] = None
    table_fields: Optional[list[str]] = None
    read_only_fields: Optional[Union[str, list[str]]] = None
    extra_kwargs: Optional[dict[str, Any]] = None
    extra_fields: Optional[Sequence[FieldConfig]] = None
    relationships: Optional[Sequence[RelationConfig]] = None
    _relationship_dict: Optional[dict[str, RelationConfig]] = None
    _extra_field_dict: Optional[dict[str, FieldConfig]] = None
    _relationship_paths: Optional[dict[str, RelationConfig]] = None
    _column_fields: Optional[dict[str, Any]] = None
    _field_configs: Optional[Sequence[FieldConfig]] = None
    _field_configs_dict: Optional[dict[str, FieldConfig]] = None

    def __init__(self, **kwargs: Any) -> None:
        ordering_fields = kwargs.pop("ordering_fields", None)
        backend_filters = kwargs.pop("backend_filters", {})
        table_fields = kwargs.pop("table_fields", None)
        fields = kwargs.pop("fields", None)
        read_only_fields = kwargs.pop("read_only_fields", None)
        kwargs.pop("_column_fields", None)  # 移除
        model = kwargs.pop("model", None)  # 移除
        relationships = kwargs.pop("relationships", None) or []
        extra_kwargs = kwargs.pop("extra_kwargs", None)
        extra_fields = kwargs.pop("extra_fields", [])
        super().__init__(**kwargs)
        self.backend_filters = backend_filters
        self.ordering_fields = ordering_fields
        self.table_fields = table_fields
        self.fields = fields
        self.model = model
        self.read_only_fields = read_only_fields
        self.extra_kwargs = extra_kwargs
        self.extra_fields = extra_fields
        self.relationships = relationships
        relationship_dict = {}
        relationship_paths = {}
        extra_fields_dict = {}
        field_configs_dict = {}
        field_configs = []
        for relationship in self.relationships:
            relationship_dict[relationship.key] = relationship
            relationship_paths.update(relationship._relationship_path or {})
            field_configs.append(relationship)
            field_configs_dict[relationship.key] = relationship
        for extra_field in self.extra_fields:
            if extra_field.key in relationship_dict:
                raise ValueError(
                    f"Key conflict : {
                                 extra_field.key}"
                )
            field_configs.append(extra_field)
            extra_fields_dict[extra_field.key] = extra_field
            field_configs_dict[extra_field.key] = extra_field
        self._field_configs = field_configs
        self._field_configs_dict = field_configs_dict
        self._extra_field_dict = extra_fields_dict
        self._relationship_dict = relationship_dict
        self._relationship_paths = relationship_paths

    # 简化的检查函数
    def check_attr_in_filter(self, key: str) -> bool:
        key, attr_name = key.rsplit(".", 1)
        if key not in self._relationship_paths:
            return False
        _model = self._relationship_paths[key]._model
        return attr_name in _model.model_fields.keys()


def _create_dynamic_filters(
    filter_config: Optional[SenweaverFilter], column_types: dict[str, type]
) -> Callable[..., dict[str, Any]]:
    if filter_config is None:
        return lambda: {}

    def filters(
        **kwargs: Any,
    ) -> dict[str, Any]:
        filtered_params = {}
        for key, value in kwargs.items():
            if value is not None:
                filtered_params[key] = value
        return filtered_params

    params = []
    for key, value in filter_config.filters.items():
        column_type = column_types.get(key, inspect._empty)
        alias_key = key
        if "." in key:
            key = key.replace(".", "_sw_dot_")
        params.append(
            inspect.Parameter(
                key,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=Query(value, alias=alias_key),
                annotation=column_type,
            )
        )

    sig = inspect.Signature(params)
    setattr(filters, "__signature__", sig)

    return filters


def get_file_url(path: str | None):
    if path is None or path == "":
        return None
    if path.startswith("http"):
        return path
    if g.request and hasattr(g.request, "base_url"):
        base_url = str(g.request.base_url)
        return urljoin(base_url, f"{settings.UPLOAD_URL}/{path.lstrip('/')}")
    return path
