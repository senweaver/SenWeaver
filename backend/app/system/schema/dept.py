from typing import List

from pydantic import BaseModel, field_validator

from senweaver.core.models import ModeTypeMixin, PKMixin


class IRoleItem(BaseModel):
    id: int
    name: str


class IRuleItem(BaseModel):
    id: int
    name: str


class IDeptEmpower(ModeTypeMixin):
    roles: List[IRoleItem]
    rules: List[IRuleItem]

    @field_validator("mode_type", mode="before")
    def check_mode_type(cls, v):
        if v is None:
            return ModeTypeMixin.ModeChoices.OR
        if isinstance(v, dict) and "value" in v:
            return ModeTypeMixin.ModeChoices(v["value"])
        return v
