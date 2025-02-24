import uuid
from datetime import datetime
from typing import Any, Optional, Protocol, TypeVar

from senweaver.exception.http_exception import InvalidIDException

ID = TypeVar("ID")


class UserProtocol(Protocol[ID]):
    id: ID
    username: str
    phone: Optional[str]
    email: Optional[str]
    password: str
    password_time: Optional[datetime]
    last_login: Optional[datetime]
    is_active: bool


class UserRegProtocol(Protocol):
    username: str
    nickname: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    password: Optional[str]


UserProtocolType = TypeVar("UserProtocolType", bound=UserProtocol)
UserRegProtocolType = TypeVar("UserRegProtocolType", bound=UserRegProtocol)


class UUIDIDMixin:
    def parse_id(self, value: Any) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(value)
        except Exception:
            raise InvalidIDException()


class IntegerIDMixin:
    def parse_id(self, value: Any) -> int:
        if isinstance(value, float):
            raise InvalidIDException()
        try:
            return int(value)
        except Exception:
            raise InvalidIDException


class StringIDMixin:
    def parse_id(self, value: Any) -> str:
        if not isinstance(value, str):
            raise InvalidIDException()
        if not value.strip():
            raise InvalidIDException()
        return value
