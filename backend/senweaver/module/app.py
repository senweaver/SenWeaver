from pathlib import Path
from typing import Type

from fastapi import Depends
from fastapi.routing import APIRoute

from senweaver.auth.security import get_current_user
from senweaver.core.senweaver_route import SenweaverRoute
from senweaver.module.base import Module


class AppModule(Module):

    def __init__(
        self,
        module_path: Path,
        package: str,
        name=None,
        depends: list = [Depends(get_current_user)],
        route_class: Type[APIRoute] = SenweaverRoute,
    ):
        super().__init__("app", module_path, package, name, depends, route_class)
