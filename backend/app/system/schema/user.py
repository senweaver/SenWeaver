from typing import List

from pydantic import BaseModel, Field, field_validator

from senweaver.core.models import ModeTypeMixin, PKMixin


class IUserResetPassword(BaseModel):
    password: str = Field(min_length=5, max_length=128, title="密码")


class IUpdateUserRoles(BaseModel):
    roles: list[int]


class IUpdateUserPosts(BaseModel):
    posts: list[int]


class IRoleItem(BaseModel):
    id: int
    name: str


class IRuleItem(BaseModel):
    id: int
    name: str


class IUserEmpower(ModeTypeMixin):
    roles: List[IRoleItem]
    rules: List[IRuleItem]

    @field_validator("mode_type", mode="before")
    def check_mode_type(cls, v):
        if v is None:
            return ModeTypeMixin.ModeChoices.OR
        if isinstance(v, dict) and "value" in v:
            return ModeTypeMixin.ModeChoices(v["value"])
        return v


class IUserUploadAvatar(BaseModel):
    pass
