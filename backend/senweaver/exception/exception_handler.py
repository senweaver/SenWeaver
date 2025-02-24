from typing import Union

from config.settings import EnvironmentEnum, settings
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from pydantic import ValidationError
from pydantic.errors import PydanticUserError
from senweaver.exception.helper import _validation_exception_handler, get_error_response
from senweaver.exception.http_exception import BaseCustomException, CustomException
from senweaver.logger import logger
from sqlalchemy.exc import SQLAlchemyError
from starlette import status


def register_exception(app: FastAPI):
    """
    全局异常处理器注册
    """

    @app.exception_handler(BaseCustomException)
    async def custom_exception_handler(request: Request, exc: BaseCustomException):
        logger.exception(exc)
        if isinstance(exec, CustomException):
            content = get_error_response(code=exc.code, detail=exc.detail)
        else:
            content = get_error_response(
                code=exc.status_code,
                detail=exc.detail,
            )
        return ORJSONResponse(content=content, status_code=exc.status_code)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.exception(exc)
        content = get_error_response(code=exc.status_code, detail=exc.detail)
        return ORJSONResponse(content=content, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(
        request: Request, exc: Union[RequestValidationError, ValidationError]
    ):
        return await _validation_exception_handler(request, exc)

    @app.exception_handler(PydanticUserError)
    async def pydantic_user_error_handler(request: Request, exc: PydanticUserError):
        """
        Pydantic 用户异常处理
        """
        content = get_error_response(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="模型验证配置错误"
        )
        return ORJSONResponse(
            content=content, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    @app.exception_handler(ValueError)
    async def value_exception_handler(request: Request, exc: ValueError):
        logger.exception(exc)
        content = get_error_response(
            code=status.HTTP_400_BAD_REQUEST, detail=exc.__str__()
        )
        return ORJSONResponse(
            content=content,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.error(f"数据库错误: {exc}")
        content = get_error_response(
            code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "服务器开小差啦,请稍后重试"
                if settings.ENVIRONMENT == EnvironmentEnum.PRODUCTION
                else str(exc)
            ),
        )
        return ORJSONResponse(
            content=content,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    @app.exception_handler(Exception)
    async def all_exception_handler(request: Request, exc: Exception):
        logger.exception(exc)
        code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(exc, CustomException):
            code = exc.code
        elif isinstance(exc, BaseCustomException):
            code = exc.status_code
        content = get_error_response(
            code=code,
            detail=(
                "服务器开小差啦,请稍后重试"
                if settings.ENVIRONMENT == EnvironmentEnum.PRODUCTION
                else str(exc)
            ),
        )
        return ORJSONResponse(
            content=content, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
