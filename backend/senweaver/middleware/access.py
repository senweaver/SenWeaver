from config.settings import settings
from fastapi import Request, Response
from senweaver.exception.http_exception import ForbiddenException
from senweaver.utils.request import get_request_trace_id
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class AccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        get_request_trace_id(request)
        path = request.scope.get("path")
        if (
            settings.DEMO_MODE
            and request.method not in ["GET", "OPTIONS"]
            and (request.method, path) not in settings.DEMO_MODE_WHITE_ROUTES
        ):
            raise ForbiddenException("演示环境，禁止操作")
        return await call_next(request)
