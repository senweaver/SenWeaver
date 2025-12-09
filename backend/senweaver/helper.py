import functools
import importlib
import importlib.util
import pkgutil
import random
import re
import string
from copy import copy
from datetime import datetime, timezone
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    Type,
    Union,
)

import typer
from fastapi import FastAPI
from fastapi._compat import ModelField
from fastapi.utils import create_cloned_field
from pydantic import (
    BaseModel,
    ConfigDict,
    SecretStr,
    create_model,
    field_serializer,
    field_validator,
    model_serializer,
    model_validator,
)
from pydantic.fields import FieldInfo
from sqlalchemy.ext.asyncio import AsyncEngine

from senweaver.db.helper import senweaver_model_serializer, senweaver_model_validator
from senweaver.logger import logger


def find_modules(
    import_path: str, include_packages: bool = False, recursive: bool = False
) -> Iterator[str]:
    module = import_string(import_path)
    path = getattr(module, "__path__", None)
    if path is None:
        raise ValueError(f"{import_path!r} is not a package")
    basename = f"{module.__name__}."
    for _importer, modname, ispkg in pkgutil.iter_modules(path):
        modname = basename + modname
        if ispkg:
            if include_packages:
                yield modname
            if recursive:
                yield from find_modules(modname, include_packages, True)
        else:
            yield modname


def import_string(import_name: str, silent: bool = False) -> Any:
    import_name = import_name.replace(":", ".")
    try:
        module_spec = importlib.util.find_spec(import_name)
        if module_spec is None:
            raise ImportError(f"Cannot find module {import_name}")

        module = importlib.import_module(import_name)
        return module

    except ImportError as e:
        logger.error(e)
        if not silent:
            raise e

    return None


def import_class_module(import_name: str, silent: bool = False, **kwargs) -> Any:
    try:
        # 分离模块路径和类名
        module_path, class_name = import_name.rsplit(".", 1)
        # 动态导入模块
        module = importlib.import_module(module_path)
        # 获取类
        cls = getattr(module, class_name)(**kwargs)
        return cls
    except (ImportError, AttributeError) as e:
        if not silent:
            raise e
    return None


def load_routers(
    app: FastAPI,
    package_path: str,
    prefix: str = "",
    api_name="api",
    depend_router_name="router",
    open_router_name="open_router",
    depends: list = None,
):
    depends = [] if depends is None else depends
    modules = find_modules(
        f"{package_path}.{api_name}", include_packages=True, recursive=True
    )
    for name in modules:
        module = import_string(name)
        if hasattr(module, depend_router_name):
            router_obj = getattr(module, depend_router_name)
            kwargs = dict(router=router_obj)
            if "dependencies" in kwargs:
                kwargs["dependencies"].extend(depends)
            else:
                kwargs["dependencies"] = depends
            if prefix:
                kwargs.update(prefix=prefix)
            app.include_router(**kwargs)
        if hasattr(module, open_router_name):
            open_router_obj = getattr(module, open_router_name)
            app.include_router(open_router_obj, prefix=prefix)


def load_modules(
    app: Union[FastAPI, typer.Typer], package_path: str, attr: str = "initialize"
):
    module = import_string(package_path)
    path = getattr(module, "__path__", None)
    if path is None:
        raise ValueError(f"{package_path!r} is not a package")
    basename = f"{module.__name__}"
    for _importer, modname, ispkg in pkgutil.iter_modules(path):
        if ispkg:
            module_name = f"{basename}.{modname}.{modname}"
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, attr):
                    init_obj = getattr(module, attr)
                    if callable(init_obj):
                        init_obj(app)
            except ImportError as e:
                print(f"Error importing {module_name}: {e}")


def make_field_optional(field: FieldInfo, default: Any = None) -> tuple[Any, FieldInfo]:
    new = copy(field)
    new.default = default
    new.annotation = field.annotation | None
    if new.json_schema_extra:
        new.json_schema_extra = {**new.json_schema_extra}
    return new.annotation, new


def create_schema_by_schema(
    schema: Type[BaseModel],
    name: str,
    *,
    include: Set[str] = None,
    exclude: Set[str] = None,
    include_validator: bool = True,
    validators: dict[str, Callable[..., Any]] | None = None,
    set_optional: bool = False,
    allow_read_validator: Optional[bool] = None,
    allow_write_validator: Optional[bool] = None,
    extra: str = "ignore",
    extra_fields: Dict[str, FieldInfo] = None,
    **kwargs,
) -> Type[BaseModel]:
    fields = {}
    for field_name, field in schema.model_fields.items():
        fields[field_name] = ModelField(field_info=field, name=field_name)
    property_fields = {}
    keys = set(fields.keys())
    if include:
        property_keys = include - keys
        keys = keys & include  # 交集操作
        for key in property_keys:  # 添加属性
            attr_obj = getattr(schema, key, None)
            if isinstance(attr_obj, property):
                extra_fields = extra_fields or {}
                property_fields[key] = attr_obj
                extra_fields[key] = FieldInfo(
                    annotation=Any,
                    nullable=True,
                    json_schema_extra={"sw_property_field": True},
                )
    if exclude:
        keys = keys - exclude  # 差集操作
    fields = {
        name: create_cloned_field(field)
        for name, field in fields.items()
        if name in keys
    }
    model_fields = list(fields.values())
    # 获取模型中的所有验证器
    field_params = {
        f.name: (
            (f.field_info.annotation, f.field_info)
            if set_optional is None
            else make_field_optional(f.field_info)
        )
        for f in model_fields
    }
    # 如果有 extra_fields，动态追加字段
    if extra_fields:
        for extra_field_name, field_info in extra_fields.items():
            # 这里使用 create_field 或自定义方式来添加额外字段
            field_params[extra_field_name] = (
                (field_info.annotation, field_info)
                if set_optional is None
                else make_field_optional(field_info)
            )
    if validators is None:
        validators = {}
    if include_validator:
        # 将原始模型的验证器复制到新模型
        if allow_read_validator:
            validators["_senweaver_model_serializer"] = model_serializer(mode="wrap")(
                senweaver_model_serializer
            )
        if allow_write_validator:
            validators["_senweaver_model_validator"] = model_validator(mode="before")(
                senweaver_model_validator
            )
        field_keys = set(field_params.keys())
        decorators = schema.__pydantic_decorators__
        for key, decorator in decorators.field_validators.items():
            intersection_fields = tuple(field_keys & set(decorator.info.fields))
            if not intersection_fields:
                continue
            wrapped_func = functools.partial(decorator.func)
            validators[key] = field_validator(
                *intersection_fields,
                mode=decorator.info.mode,
                check_fields=decorator.info.check_fields,
                json_schema_input_type=decorator.info.json_schema_input_type,
            )(wrapped_func)
        for key, decorator in decorators.model_validators.items():
            wrapped_func = functools.partial(decorator.func)
            validators[key] = model_validator(mode=decorator.info.mode)(wrapped_func)
        for key, decorator in decorators.field_serializers.items():
            intersection_fields = tuple(field_keys & set(decorator.info.fields))
            if not intersection_fields:
                continue
            wrapped_func = functools.partial(decorator.func)
            validators[key] = field_serializer(
                *intersection_fields,
                mode=decorator.info.mode,
                return_type=decorator.info.return_type,
                when_used=decorator.info.when_used,
            )(wrapped_func)
        for key, decorator in decorators.model_serializers.items():
            wrapped_func = functools.partial(decorator.func)
            validators[key] = model_serializer(
                mode=decorator.info.mode,
                return_type=decorator.info.return_type,
                when_used=decorator.info.when_used,
            )(wrapped_func)
    schema_config = ConfigDict(extra=extra, **kwargs)
    new_model = create_model(
        name, __config__=schema_config, __validators__=validators, **field_params
    )
    if property_fields:
        # for pkey, pvalue in property_fields.items():
        #     setattr(new_model, pkey, pvalue)
        new_model.sw_property_fields = list(property_fields.keys())
    return new_model


# 自动将字段变为可选的工具函数


def make_optional(model: BaseModel):
    optional_fields = {k: (Optional[v], None) for k, v in model.__annotations__.items()}
    return type(f"Partial{model.__name__}", (model,), optional_fields)


def build_tree(
    items: List[Union[Dict[str, Any], BaseModel]],
    id_field="id",
    parent_field: str = "parent_id",
) -> List[Dict[str, Any]]:
    if items is None or len(items) == 0:
        return []
    # 创建一个字典，用于快速查找每个id对应的菜单项
    node_dict = {}
    nodes = []
    # 在一次循环中完成所有操作
    for item in items:
        # 转换为字典格式
        node = item.model_dump() if isinstance(item, BaseModel) else item
        # 将节点添加到节点字典中
        node_dict[node[id_field]] = node
        nodes.append(node)
    # 初始化一个空列表来存储所有的树（顶级菜单项）
    trees = []
    # 遍历每个菜单项
    for item in nodes:
        # 检查当前项是否有父项
        parent_id = item[parent_field]

        # 如果当前项是顶级菜单项（即没有父项，或者父项为None/0，具体取决于你的设计）
        if parent_id is None or (parent_id not in node_dict):
            # 直接将其添加到树列表中
            trees.append(item)
        else:
            # 否则，尝试找到其父项，并将当前项作为子项添加到父项中
            # 注意：这里假设item_dict中一定存在parent_id对应的项
            parent_item = node_dict[parent_id]

            # 如果父项还没有'children'键，则创建一个空列表
            if "children" not in parent_item:
                parent_item["children"] = []

            # 将当前项添加到父项的'children'列表中
            parent_item["children"].append(item)

    # 返回所有顶级菜单项组成的树形结构列表
    return trees


def now_utc():
    return datetime.now(timezone.utc)


async def get_table_info(table_name, engine: AsyncEngine = None):
    """获取表信息"""
    if not engine:
        from senweaver.db.session import async_engine

        engine = async_engine
    from sqlalchemy import Inspector, inspect

    try:
        async with engine.connect() as conn:

            def fetch_table_info(sync_conn):
                inspector: Inspector = inspect(sync_conn)
                columns = inspector.get_columns(table_name)
                primary_keys = inspector.get_pk_constraint(table_name)
                foreign_keys = inspector.get_foreign_keys(table_name)
                unique_constraints = inspector.get_unique_constraints(table_name)
                check_constraints = inspector.get_check_constraints(table_name)
                for column in columns:
                    column["primary_key"] = (
                        column["name"] in primary_keys["constrained_columns"]
                    )
                return {
                    "name": table_name,
                    "columns": columns,
                    "comment": inspector.get_table_comment(table_name).get("text"),
                    "primary_keys": primary_keys,
                    "foreign_keys": foreign_keys,
                    "indexes": inspector.get_indexes(table_name),
                    "unique_constraints": unique_constraints,
                    "check_constraints": check_constraints,
                }

            info = await conn.run_sync(fetch_table_info)
            return info
    except Exception as e:
        print(f"Error get columns {table_name}: {e}")
    return None


async def get_table_names(engine: AsyncEngine = None):
    """获取所有表名"""
    if not engine:
        from senweaver.db.session import async_engine

        engine = async_engine
    from sqlalchemy import inspect

    try:
        async with engine.connect() as conn:
            tables = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
            return tables
    except Exception as e:
        print(f"Error db connect: {e}")
    return None


async def get_table_columns(table_name: str, engine: AsyncEngine = None):
    """获取指定表的所有字段信息"""
    try:
        if not engine:
            from senweaver.db.session import async_engine

            engine = async_engine
        from sqlalchemy import inspect

        async with engine.connect() as conn:
            columns = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_columns(table_name)
            )
            return columns
    except Exception as e:
        print(f"Error get columns {table_name}: {e}")
        return None


def is_module_name(name: str) -> bool:
    """
    验证给定的字符串是否符合 PEP 8 的包和模块命名规则。

    参数:
    name (str): 需要验证的字符串。

    返回:
    bool: 如果符合规则，返回 True；否则返回 False。
    """
    # 检查是否符合全小写字母、数字和下划线的组合且不以数字开头
    if re.match(r"^[a-z][a-z0-9_]*$", name):
        return True
    return False


def get_secret_value(secret: Union[str, SecretStr]) -> str:
    if isinstance(secret, SecretStr):
        return secret.get_secret_value()
    return secret


def generate_string(
    length: int,
    digits: bool = True,
    uppercase: bool = True,
    lowercase: bool = True,
    special: bool = False,
    exclude_chars: str = "0O1lI",
) -> str:
    # 初始化字符集
    char_set = ""

    # 添加需要的字符集
    if digits:
        char_set += string.digits
    if uppercase:
        char_set += string.ascii_uppercase
    if lowercase:
        char_set += string.ascii_lowercase
    if special:
        char_set += string.punctuation

    # 排除指定的字符
    if exclude_chars:
        char_set = "".join(c for c in char_set if c not in exclude_chars)

    # 确保字符集非空
    if not char_set:
        raise ValueError(
            "Character set is empty. Please adjust your options or excluded characters."
        )

    # 生成随机字符串
    return "".join(random.choice(char_set) for _ in range(length))


def format_path_to_pascal_case(s: str) -> str:
    # 去除首尾的指定字符并替换中间的 `/` 和 `-` 为 `_`
    cleaned_str = re.sub(r"^[\s/,-]+|[\s/,-]+$", "", s)
    underscored_str = re.sub(r"[\s/,-]+", "_", cleaned_str)

    # 转换为PascalCase
    pascal_case_str = "".join(word.capitalize() for word in underscored_str.split("_"))
    return pascal_case_str


def get_nested_attribute(obj, attr_path: str, separator="__"):
    """
    从给定的对象实例中根据属性路径获取嵌套属性的值。

    :param obj: 要从中获取属性的对象实例。
    :param attr_path: 包含属性路径的字符串，各层属性之间用指定的分隔符分隔。
    :param separator: 分隔符，默认为 '__'。
    :return: 属性值或 None 如果路径无效。
    """
    attrs = attr_path.split(separator)
    for attr in attrs:
        try:
            # 尝试通过 getattr 获取属性值
            obj = getattr(obj, attr)
        except AttributeError:
            # 如果在任何层级上找不到属性，则返回 None
            return None
    return obj
