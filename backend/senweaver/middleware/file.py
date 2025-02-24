import re

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from config.settings import settings
from senweaver.exception.http_exception import ForbiddenException


class FileMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method != "GET" or not request.url.path.startswith(
            f"{settings.UPLOAD_URL}/"
        ):
            return await call_next(request)
        path = request.url.path
        if (
            not re.match(r"^[\w\-\u4e00-\u9fff\/]+(\.[a-zA-Z0-9]+)?$", path)
            or "/./" in path
            or "//" in path
        ):
            raise ForbiddenException("Invalid path")
        if request.url.path.startswith(f"{settings.UPLOAD_PUBLIC_URL}/"):
            # 公开文件访问
            return await call_next(request)
        # 判断文件访问权限
        await request.auth.check_file_permission(request)

        return await call_next(request)
