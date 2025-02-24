import re
from datetime import date, datetime, timezone
from urllib.parse import urljoin

import pytz
from fastapi import Request
from fastcrud.endpoint.helper import _get_python_type
from pydantic import BaseModel, Field
from sqlalchemy.orm import DeclarativeBase, RelationshipProperty

from config.settings import settings
from senweaver.db.models import Choices
from senweaver.utils.globals import g
from senweaver.utils.pydantic import parse_annotation_type
from senweaver.utils.translation import _


def create_pks_schema(model_name: str, pk_name: str, pk_type: type, pk_alias: str):
    # 动态创建类的字段定义
    annotations = {f"{pk_name}s": list[pk_type]}
    fields = {
        f"{pk_name}s": Field(..., alias=f"{pk_alias}s", example=[pk_type.__name__])
    }
    # 动态创建 BaseModel 子类
    return type(model_name, (BaseModel,), {"__annotations__": annotations, **fields})


def get_field_type(model: type[DeclarativeBase], field: str):
    field_type = None
    for key, item in model.__mapper__.all_orm_descriptors.items():
        if key == field:
            if isinstance(item.property, RelationshipProperty):
                foreign_key_column = next(iter(item.property.local_columns), None)
                if foreign_key_column is not None:
                    field_type = _get_python_type(foreign_key_column)
            else:
                field_type = _get_python_type(item.property.columns[0])
            break
    return field_type


def get_field_lookups(model: type[DeclarativeBase], field: str):
    field_type = get_field_type(model, field)
    if field_type is None:
        return ["eq"]
    if field_type == str:
        return [
            "eq",
            "ieq",
            "like",
            "ilike",
            "contains",
            "startswith",
            "istartswith",
            "endswith",
            "iendswith",
            "regex",
            "iregex",
        ]
    elif field_type in (int, float):
        return ["eq", "gt", "gte", "lt", "lte", "between", "in"]
    elif field_type == bool:
        return ["eq", "is", "is_not", "isnull"]
    elif field_type in (date, datetime):
        return [
            "eq",
            "gt",
            "gte",
            "lt",
            "lte",
            "between",
            "date",
            "year",
            "iso_year",
            "month",
            "day",
            "week",
            "week_day",
            "iso_week_day",
            "quarter",
            "time",
            "hour",
            "minute",
            "second",
        ]
    elif field_type == dict:
        return ["eq", "contains", "has_any", "has_all", "has_key", "contained_by"]
    return ["eq"]


def get_field_lookup_info(model: type[DeclarativeBase], field: str):
    fields = get_field_lookups(model, field)
    field_info = {
        "eq": _("精确匹配，字段值必须与给定值完全相同。"),
        "ieq": _("不区分大小写的精确匹配。"),
        "like": _("字段值必须包含给定的子字符串（区分大小写）。"),
        "ilike": _(
            "不区分大小写的包含，字段值必须包含给定的子字符串（不区分大小写）。"
        ),
        "contains": _("字段值必须包含给定的子字符串"),
        "in": _("字段值必须在给定的列表、元组或查询集中。"),
        "gt": _("大于，字段值必须大于给定值。"),
        "gte": _("大于或等于，字段值必须大于或等于给定值。"),
        "lt": _("小于，字段值必须小于给定值。"),
        "lte": _("小于或等于，字段值必须小于或等于给定值。"),
        "startswith": _("字段值必须以给定字符串开头（区分大小写）。"),
        "istartswith": _(
            "不区分大小写的开头匹配，字段值必须以给定字符串开头（不区分大小写）。"
        ),
        "endswith": _("字段值必须以给定字符串结尾（区分大小写）。"),
        "iendswith": _(
            "不区分大小写的结尾匹配，字段值必须以给定字符串结尾（不区分大小写）。"
        ),
        "between": _("在范围内，字段值必须在两个给定值之间（包含边界值）。"),
        "date": _("仅过滤日期部分（忽略时间部分）。"),
        "year": _("按年份过滤。"),
        "iso_year": _("按ISO年份过滤（可能与公历年份不同）。"),
        "month": _("按月份过滤。"),
        "day": _("按月份中的天数过滤。"),
        "week": _("按年份中的周数过滤。"),
        "week_day": _("按星期几过滤（1 = 星期一，7 = 星期日）。"),
        "iso_week_day": _("按ISO星期几过滤（1 = 星期一，7 = 星期日）。"),
        "quarter": _("按季度过滤（1, 2, 3, 4）。"),
        "time": _("仅过滤时间部分（忽略日期部分）。"),
        "hour": _("按小时过滤。"),
        "minute": _("按分钟过滤。"),
        "second": _("按秒过滤。"),
        "is": _("检查字段值是否为NULL，可以设置为True或False。"),
        "is_not": _("检查字段值是否非NULL，可以设置为True或False。"),
        "isnull": _("检查字段值是否为NULL，可以设置为True或False。"),
        "regex": _("字段值必须匹配给定的正则表达式（区分大小写）。"),
        "iregex": _("字段值必须匹配给定的正则表达式（不区分大小写）。"),
        "contained_by": _("字段值必须是给定值的子集，通常用于数组或JSON字段。"),
        "has_any": _("字段值必须包含至少一个给定的键，通常用于JSON字段。"),
        "has_all": _("字段值必须包含所有给定的键，通常用于JSON字段。"),
        "has_key": _("字段值必须包含给定的单个键，通常用于JSON字段。"),
    }
    return [{"value": field, "label": field_info.get(field, field)} for field in fields]


def senweaver_model_serializer(self, handler):
    result = handler(self)
    filter = getattr(self, "sw_filter", None)
    allow_fields = getattr(self, "sw_allow_fields", None)
    filter_fields = list(result.keys())
    field_configs_dict = filter._field_configs_dict if filter else {}
    if allow_fields is not None:
        filter_fields = allow_fields
    elif filter:
        filter_fields = filter.fields or []

    data = {}
    fields = self.model_fields
    model_class = type(self)
    for key in filter_fields:
        if allow_fields and key not in allow_fields:
            continue
        v = getattr(self, key, None)
        attr_obj = getattr(model_class, key, None)
        if isinstance(attr_obj, property):
            data[key] = v
            continue
        item = result.get(key, v)
        field = fields.get(key, None)
        field_config = field_configs_dict.get(key, None)
        if item is None and field is None and field_config:
            if field_config.write_only:
                continue
            item = field_config.default
        extra_info = (field.json_schema_extra or {}) if field else {}
        input_type = extra_info.get("sw_input_type", None)
        if input_type:
            if input_type == "image upload" and v and isinstance(v, str):
                if v is None or v == "":
                    item = None
                elif not v.startswith("http") and g.request:
                    base_url = str(g.request.base_url)
                    item = urljoin(base_url, f"{settings.UPLOAD_URL}/{v}")
            if input_type == "password":
                # 密码不返回
                continue

        if isinstance(v, Choices):
            item = {"value": v.value, "label": v.label}
        elif isinstance(v, datetime):
            _time = v.replace(tzinfo=timezone.utc).astimezone(
                pytz.timezone("Asia/Shanghai")
            )
            item = _time.isoformat()
        data[key] = item
    return data


def senweaver_model_validator(cls, values):
    fields = getattr(cls, "model_fields", {})
    filter = getattr(cls, "sw_filter", None)
    extra_field_dict = filter._extra_field_dict if filter else {}
    request: Request = g.request
    for key, v in values.items():
        field = fields.get(key, None)
        if field is None:
            continue
        field_config = extra_field_dict.get(key, None)
        field_config_callback = field_config.callbacks if field_config else None
        if field_config_callback:
            callback = field_config_callback.get("validate", None)
            if callback:
                values[key] = callback(key, values)
                continue

        extra_info = (field.json_schema_extra or {}) if field else {}
        input_type = extra_info.get("sw_input_type")
        is_relationship = extra_info.get("sw_is_relationship")
        if is_relationship and v in (None, "", 0, False):
            values[key] = None
            continue

        if input_type is not None:
            if input_type == "image upload":
                if v is None or v == "":
                    values[key] = None
                elif v.startswith("http") and g.request:  # 兼容本地文件
                    base_url = str(g.request.base_url)
                    values[key] = v.replace(
                        urljoin(base_url, f"{settings.UPLOAD_URL}/"), ""
                    )
            if request:
                if input_type == "password" and v and request.method != "GET":
                    username = values.get("username", g.request.user.username)
                    values[key] = request.auth.get_hash_password(value=v, key=username)
        annotation = parse_annotation_type(field.annotation)
        if isinstance(annotation, type) and v is not None:
            if issubclass(annotation, Choices) and isinstance(v, dict) and "value" in v:
                values[key] = annotation(v["value"])
            elif isinstance(annotation, datetime) and isinstance(v, str):
                values[key] = datetime.fromisoformat(v)
            elif isinstance(annotation, dict):
                pass
    return values


def detect_sql_injection(input_string: str):
    if not input_string:
        return True
    # 检测常见的 SQL 注入关键字或模式
    patterns = [
        r"\b(union|select|insert|delete|update|drop|alter|exec|execute|create)\b",
        r"--",  # SQL 单行注释
        r"/\*",
        r"\*/",  # SQL 多行注释
        r";",  # 分号
        r"\'",  # 单引号
        r'"',  # 双引号
        r"\bOR\b.*=\b1\b",  # OR 1=1
        r"\bAND\b.*=\b0\b",  # AND 1=0
        r"\badmin\b|--",  # admin 或者以 -- 开头的注释
        r"\bxor\b",
        r"\band\b",
        r"\bor\b",
        r"\bnot\b",
    ]

    for pattern in patterns:
        if re.search(pattern, input_string, re.IGNORECASE | re.UNICODE):
            return True
    return False
