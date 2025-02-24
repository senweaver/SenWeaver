from typing import Union

from fastapi import status
from fastcrud.exceptions.http_exceptions import CustomException as BaseCustomException


class CustomException(BaseCustomException):
    def __init__(
        self,
        detail: Union[str, None] = None,
        code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        super().__init__(detail=detail, status_code=status_code)
        self.code = code


class BadRequestException(CustomException):
    def __init__(self, detail: Union[str, None] = None):
        super().__init__(
            detail=detail if detail is not None else "Bad request",
            status_code=status.HTTP_400_BAD_REQUEST,
            code=status.HTTP_400_BAD_REQUEST,
        )


class NotFoundException(CustomException):
    def __init__(self, detail: Union[str, None] = None):
        super().__init__(
            detail=detail if detail is not None else "Not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code=status.HTTP_404_NOT_FOUND,
        )


class ForbiddenException(CustomException):
    def __init__(self, detail: Union[str, None] = None):
        super().__init__(
            detail=detail if detail is not None else "Forbidden",
            status_code=status.HTTP_403_FORBIDDEN,
            code=status.HTTP_403_FORBIDDEN,
        )


class UnauthorizedException(CustomException):
    def __init__(self, detail: Union[str, None] = None):
        super().__init__(
            detail=detail if detail is not None else "Unauthorized",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=status.HTTP_401_UNAUTHORIZED,
        )


class DuplicateValueException(CustomException):
    def __init__(self, detail: Union[str, None] = None):
        super().__init__(
            detail=detail if detail is not None else "Duplicate value",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class AuthException(CustomException):
    def __init__(self, detail: Union[str, None] = None):
        super().__init__(
            detail=detail if detail is not None else "Authentication required",
            status_code=status.HTTP_511_NETWORK_AUTHENTICATION_REQUIRED,
            code=status.HTTP_511_NETWORK_AUTHENTICATION_REQUIRED,
        )


class PermissionException(CustomException):

    def __init__(self, detail: Union[str, None] = None):
        super().__init__(
            detail=detail if detail is not None else "Permission denied",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=status.HTTP_401_UNAUTHORIZED,
        )


class InvalidIDException(CustomException):
    def __init__(self, detail: Union[str, None] = None):
        super().__init__(
            detail=detail if detail is not None else "Invalid ID",
            status_code=status.HTTP_400_BAD_REQUEST,
            code=status.HTTP_400_BAD_REQUEST,
        )
