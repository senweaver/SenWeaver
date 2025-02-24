from typing import List

from pydantic import BaseModel, Field, field_validator

from senweaver.core.models import PKMixin


class IMenuPermission(BaseModel):
    views: List[str]  # views 是一个字符串列表
    skip_existing: bool  # skip_existing 是一个布尔值
    component: str  # component 是一个字符串
