from typing import Optional, Type

from fastapi import Depends, Request
from fastapi.routing import APIRoute

from app.system.model.user import User
from config.settings import settings
from senweaver.auth.auth import Auth
from senweaver.auth.router import AuthRouter
from senweaver.auth.security import oauth2_scheme, requires_user
from senweaver.core.senweaver_route import SenweaverRoute
from senweaver.db.models.helper import choices_dict
from senweaver.utils.response import ResponseBase, success_response


class SystemAuthRouter(AuthRouter):
    router_prefix: Optional[str] = "/system/auth"
    title: Optional[str] = "系统用户认证"

    def __init__(self, auth: Auth = None, route_class: Type[APIRoute] = SenweaverRoute):
        super().__init__(auth, route_class)

    def user_choices(self):
        @requires_user()
        async def endpoint(request: Request) -> ResponseBase:
            data = choices_dict(User)
            return success_response(choices_dict=data)

        return endpoint

    def add_routes(self):
        super().add_routes()
        oauth2_depend = [Depends(oauth2_scheme)] if settings.DOCS_URL else None
        self.router.add_api_route(
            f"/system/userinfo/choices",
            self.user_choices(),
            summary="获取用户的字段选择",
            methods=["GET"],
            tags=["current user"],
            dependencies=oauth2_depend,
            description="获取用户的字段选择",
        )
