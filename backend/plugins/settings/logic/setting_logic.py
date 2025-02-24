from datetime import datetime, timezone
from typing import Any, Optional, Union, get_args, get_origin

import annotated_types
from fastapi import Request
from pydantic import BaseModel, EmailStr, HttpUrl, SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from senweaver import SenweaverCRUD
from senweaver.core.schemas import IFormItem
from senweaver.db.models import Choices
from senweaver.db.models.helper import get_choices_dict
from senweaver.utils.pydantic import parse_annotation_type

from ..core.schemas import ISettingData
from ..model.setting import Setting


class SettingLogic:
    @classmethod
    def get_input_type(cls, field_type: Any, annotation_type: Any) -> str:

        TYPE_MAPPING = {
            HttpUrl: "url",
            EmailStr: "email",
            SecretStr: "password",
            bool: "boolean",
            int: "integer",
            str: "string",
            float: "float",
            Choices: "choice",
        }
        if issubclass(annotation_type, Choices):
            if cls.is_list_type(field_type):
                return "multiple choice"
            return "choice"
        return TYPE_MAPPING.get(annotation_type, "string")

    @classmethod
    def is_optional(cls, field_type):
        """判断字段类型是否是 Optional[...]"""
        return get_origin(field_type) is Union and type(None) in get_args(field_type)

    @classmethod
    def is_list_type(cls, field_type):
        """判断字段是否是 List[...] 或 Optional[List[...]]"""
        origin = get_origin(field_type)
        if origin is list:
            return True
        if origin is Union:
            args = get_args(field_type)
            return any(get_origin(arg) is list for arg in args)
        return False

    @classmethod
    def get_form_by_model(cls, model: type[BaseModel]) -> list[dict[str, Any]]:
        """从 Pydantic 模型自动生成 JSON 结构"""
        data = []
        for field_name, field_info in model.model_fields.items():

            extra_info = field_info.json_schema_extra or {}
            annotation_type = parse_annotation_type(field_info.annotation)
            input_type = extra_info.get("input_type") or cls.get_input_type(
                field_info.annotation, annotation_type
            )

            is_optional = cls.is_optional(field_info.annotation)
            default_value = (
                field_info.default if field_info.default is not None else None
            )
            if default_value is None and field_info.examples:
                default_value = field_info.examples[0]
            max_length = None
            min_length = None
            min_value = None
            max_value = None
            choices = None
            if issubclass(annotation_type, Choices):
                choices = get_choices_dict(annotation_type.choices)
            for metadata in field_info.metadata:
                if isinstance(metadata, annotated_types.MaxLen):
                    max_length = metadata.max_length
                    break
                if isinstance(metadata, annotated_types.MinLen):
                    min_length = metadata.min_length
                    break
                if isinstance(metadata, annotated_types.Ge):
                    min_value = metadata.ge
                    break
                if isinstance(metadata, annotated_types.Le):
                    max_value = metadata.le
                    break
            item = IFormItem(
                key=field_name,
                required=field_info.is_required() or not is_optional,
                default=default_value,
                label=field_info.title or field_name,
                help_text=field_info.description or "",
                max_length=max_length,
                min_length=min_length,
                min_value=min_value,
                max_value=max_value,
                input_type=input_type,
                read_only=False,
                write_only=False,
                choices=choices,
                table_show=1,  # 默认值，依据需求可调整
            )
            item = item.model_copy(update=extra_info)
            data.append(item)
        return data

    @classmethod
    async def get_model_list(
        cls, request: Request, model: type[BaseModel], default: dict = {}
    ):
        keys = list(model.model_fields.keys())
        db: AsyncSession = request.auth.db.session
        crud = SenweaverCRUD(Setting)
        result = await crud.get_multi(
            db,
            limit=None,
            schema_to_select=ISettingData,
            return_total_count=False,
            name__in=keys,
        )
        list_data = result["data"]
        data = {}
        for item in list_data:
            data[item["name"]] = item["value"]
        default.update(data)
        return model(**default)

    @classmethod
    async def save(cls, request: Request, category: str, object: BaseModel):
        update_data = {}
        import orjson

        updated_time = datetime.now(timezone.utc)
        if request and hasattr(request, "user"):
            update_data["modifier_id"] = request.user.id
            update_data["updated_time"] = updated_time
        creator_data = request.auth.get_creator_data(Setting)
        db: AsyncSession = request.auth.db.session
        crud = SenweaverCRUD(Setting)
        object_data = object.model_dump(exclude_unset=True)
        model_class = type(object)

        for field_name, field_value in object_data.items():
            data = {"name": field_name, "value": field_value, "category": category}
            data.update(update_data)
            db_instance = await crud.get(db, return_as_model=False, name=field_name)
            if db_instance is None:
                data.update(creator_data)
                await crud.create(db, object=Setting(**data))
            else:
                await crud.update(db, object=data, name=field_name)
        return await cls.get_model_list(request, model_class)


setting_logic = SettingLogic()
