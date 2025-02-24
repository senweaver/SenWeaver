from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, model_serializer


class IFormItem(BaseModel):
    key: str
    label: str
    help_text: Optional[str] = None
    default: Any = None
    input_type: str
    required: Optional[bool] = None
    read_only: Optional[bool] = None
    write_only: Optional[bool] = None
    multiple: Optional[bool] = None
    max_length: Optional[int] = None
    table_show: Optional[int] = None
    choices: Optional[List[dict]] = None
    model_config = ConfigDict(extra="allow")

    @model_serializer(mode="wrap")
    def item_serialize_model(self, handler):
        result = handler(self)
        data = {}
        for key, item in result.items():
            if item is None:
                continue
            data[key] = item
        return data


class SafeFormatMap:
    def __init__(self, obj: BaseModel):
        self.obj = obj
        self.missing_keys = set()

    def __getitem__(self, key: str) -> Any:
        try:
            value = getattr(self.obj, key)
            return "" if value is None else value
        except AttributeError:
            self.missing_keys.add(key)
            return ""

    def get_missing_keys(self):
        return self.missing_keys
