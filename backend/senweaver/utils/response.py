from abc import ABC
from math import ceil
from time import time
from typing import Any, Generic, Optional, Sequence, TypeVar

from fastapi import status
from pydantic import BaseModel, ConfigDict, Field, field_serializer
from pydantic.alias_generators import to_camel
from senweaver.utils.request import get_request_trace_id

T = TypeVar("T")


class ResponseBase(BaseModel, Generic[T]):
    code: Optional[int] = 1000
    detail: Optional[str] = "操作成功"
    time: Optional[int] = Field(default_factory=lambda: int(time()))
    requestId: Optional[str] = Field(default_factory=lambda: get_request_trace_id())
    # 使用alias_generator来转换字段名为小驼峰命名
    model_config = ConfigDict(
        #  alias_generator=to_camel,
        populate_by_name=True,
        extra="allow",
    )


class PageBase(BaseModel, Generic[T], ABC):
    results: Sequence[T]
    total: int
    page: int
    size: int
    pages: int
    has_more: bool
    previous: Optional[int] = Field(
        default=None, description="Page number of the previous page"
    )
    next: Optional[int] = Field(
        default=None, description="Page number of the next page"
    )
    requestId: Optional[str] = Field(default_factory=lambda: get_request_trace_id())


class SuccessResponse(ResponseBase[T]):
    def __init__(self, data: T | None = None, detail: str = "操作成功", **kwargs):
        if data is not None:
            kwargs["data"] = data
        super().__init__(detail=detail, code=1000, **kwargs)


class TokenResponse(ResponseBase[T]):
    token: Optional[str] = None


class ErrorResponse(ResponseBase[T]):
    def __init__(
        self,
        detail: str = "操作失败",
        code: int = status.HTTP_400_BAD_REQUEST,
        **kwargs
    ):
        super().__init__(detail=detail, code=code, **kwargs)


class PageResponse(ResponseBase[PageBase[T]], Generic[T]):
    @classmethod
    def create(
        cls,
        results: Sequence[T],
        total: int,
        page: int = 1,
        page_size: int = 10,
        code: int = 1000,
        detail: str = "操作成功",
        **kwargs
    ) -> Optional["PageResponse[T]"]:
        pages = ceil(total / page_size)
        page_data = PageBase[T](
            results=results,
            total=total,
            page=page,
            size=page_size,
            has_more=(page * page_size) < total,
            pages=pages,
            next=page + 1 if page < pages else None,
            previous=page - 1 if page > 1 else None,
        )
        return cls(code=code, detail=detail, data=page_data, time=int(time()), **kwargs)


success_response = SuccessResponse
error_response = ErrorResponse
page_response = PageResponse
