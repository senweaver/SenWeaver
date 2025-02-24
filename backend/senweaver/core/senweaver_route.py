from asyncio import create_task
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict

import orjson
from fastapi import Request, Response, UploadFile, status
from fastapi.routing import APIRoute
from senweaver.auth.schemas import IClient, IOperationLog
from senweaver.exception.http_exception import BaseCustomException, CustomException
from senweaver.utils.data import DataSanitizer
from senweaver.utils.request import get_request_trace_id, parse_client_info


class SenweaverRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            if request.method not in ["POST", "PUT", "PATCH", "DELETE"]:
                return await original_route_handler(request)
            start_time = datetime.now(timezone.utc)
            response = None
            status_code = status.HTTP_200_OK
            response_code = 1000
            response_except = None
            try:
                response = await original_route_handler(request)
            except BaseCustomException as e:
                status_code = e.status_code
                response_code = e.status_code
                response_except = e
            except CustomException as e:
                status_code = e.status_code
                response_code = e.code
                response_except = e
            except Exception as e:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                response_code = status_code
                response_except = e
            end_time = datetime.now(timezone.utc)
            cost_time = (end_time - start_time).total_seconds() * 1000.0
            request_data = await self._collect_request_data(request)
            _route = request.scope.get("route")
            client: IClient = await parse_client_info(request)
            response_data = await self._collect_response_data(
                response, status_code, response_code
            )
            try:
                log = IOperationLog(
                    trace_id=get_request_trace_id(request),
                    method=request.method,
                    title=getattr(_route, "summary", None) or "",
                    path=request.url.path,
                    client=client,
                    request_data=request_data,
                    response_code=response_data["code"],
                    cost_time=cost_time,
                    opera_time=start_time,
                    status_code=response_data["status_code"],
                    response_result=response_data["body"],
                )
                if hasattr(request, "user") and request.user is not None:
                    log.user_id = request.user.id
                    log.username = request.user.username
                create_task(request.auth.add_oper_log(log=log))
            except Exception as e:
                pass
            if response_except is not None:
                raise response_except
            return response

        return custom_route_handler

    async def _collect_request_data(self, request: Request) -> Dict[str, Any]:
        data = {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "form_data": {},
            "body": None,
            "files": [],
        }
        content_type = request.headers.get("content-type", "")
        try:
            if content_type.startswith("multipart/form-data"):
                form = await request.form()
                form_data = {}
                files = []
                for key, value in form.items():
                    if isinstance(value, UploadFile):
                        files.append({"field": key, "filename": value.filename})
                    else:
                        form_data[key] = value
                data["form_data"] = form_data
                data["files"] = files
            elif content_type.startswith("application/x-www-form-urlencoded"):
                form = await request.form()
                data["form_data"] = dict(form)
            else:
                body = await request.body()
                if body:
                    data["body"] = orjson.loads(body.decode("utf-8"))
        except Exception:
            pass
        data["form_data"] = DataSanitizer.sanitize(data["form_data"])
        data["query_params"] = DataSanitizer.sanitize(data["query_params"])
        data["body"] = DataSanitizer.sanitize(data["body"])
        return data

    async def _collect_response_data(
        self, response: Response, status_code: int, response_code: int
    ) -> Dict[str, Any]:
        if response is None:
            return {"status_code": status_code, "code": response_code, "body": {}}
        body = b""
        if hasattr(response, "body"):
            body = response.body
        elif hasattr(response, "body_iterator"):
            async for chunk in response.body_iterator:
                body += chunk
            response = Response(content=body, status_code=response.status_code)
        try:
            body = orjson.loads(body.decode())
            response_code = body.get("code", response_code)
        except:
            body = body.decode("utf-8", errors="replace")
            response_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        return {
            "status_code": response.status_code,
            "code": response_code,
            "body": body,
        }
