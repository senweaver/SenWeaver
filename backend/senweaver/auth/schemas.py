from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field, SecretStr
from senweaver.auth.constants import LoginTypeChoices


class IToken(BaseModel):
    access: str
    token_type: str = "bearer"
    refresh: str
    access_token_lifetime: int
    refresh_token_lifetime: int


class IRefreshToken(BaseModel):
    refresh: str


class ITokenData(BaseModel):
    id: int


class IVerify(BaseModel):
    form_type: str
    token: str
    target: str
    captcha_key: str
    captcha_code: str


class IVerifyCategoryEnum(str, Enum):
    login = "login"
    bind_email = "bind_email"
    bind_phone = "bind_phone"
    register = "register"
    reset = "reset"


class ILogin(BaseModel):
    username: str
    password: Union[str, SecretStr]
    captcha_key: Optional[str]
    token: Optional[str]
    captcha_code: Optional[str]


class ILoginCode(BaseModel):
    password: str
    verify_code: str
    verify_token: str


class IUserProfile(BaseModel):
    username: str
    nickname: str
    gender: int


class IChangePassword(BaseModel):
    old_password: str
    sure_password: str


class IResetPassword(BaseModel):
    old_password: Union[str, SecretStr]
    new_password: Union[str, SecretStr]
    confirm_password: Union[str, SecretStr]


class IClient(BaseModel):
    user_agent: Optional[str] = ""
    device: Optional[str] = ""
    os: Optional[str] = ""
    browser: Optional[str] = ""
    ip: Optional[str] = ""
    country: Optional[str] = ""
    region: Optional[str] = ""
    city: Optional[str] = ""


class ILoginLog(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    status: bool = True
    login_type: Optional[LoginTypeChoices] = None
    client: Optional[IClient]


class IOperationLog(BaseModel):
    trace_id: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    method: str
    title: str
    path: str
    client: Optional[IClient] = None
    request_data: dict | None = None
    cost_time: float
    opera_time: datetime
    response_code: int
    status_code: int
    response_result: dict | None = None
