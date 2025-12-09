from typing import Union

from config.settings import settings
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from sqlmodel import SQLModel

from senweaver.auth import models
from senweaver.auth.manager import AuthManager
from senweaver.module.base import Module


class ModuleManager:
    """
    Manages modules.
    """

    def __init__(self):
        self.app = None
        self.modules: dict[str, Module] = {}
        self.table_models: dict[str, SQLModel] = {}
        self.module_models: dict[str, SQLModel] = {}
        self.resource_routers: dict[str, APIRouter] = {}
        self.endpoints: dict = {}
        self.auth_module: AuthManager[models.UserProtocolType, models.ID] = None

    def add(self, module_name: str, module_instance: Module):
        if module_instance is None:  # pragma: no cover
            raise ValueError("Module instance cannot be None.")
        if module_instance.app is None:
            raise ValueError("Module instance must have an app.")
        if module_name != module_instance.name:
            raise ValueError(f"Module name does not match module instance name.")
        if not module_instance.settings.enabled:
            return
        if module_instance.ready:
            if module_name in self.modules:
                raise ValueError(f"Module with name {module_name} already exists.")
            self.modules[module_name] = module_instance
            self.table_models.update(module_instance.table_models)
            self.module_models.update(module_instance.module_models)

    def get(self, module_name: str) -> Union[Module, None]:
        return self.modules.get(module_name)

    def get_model(self, name: str) -> Union[SQLModel, None]:
        if "." in name:
            return self.module_models.get(name)
        return self.table_models.get(name)

    def get_filters(self):
        filters = []
        for _, module_instance in self.modules.items():
            values = list(module_instance.module_filters.values())
            filters = filters + values
        return filters

    def _add_router(self, resource_name: str, router: APIRouter):
        if resource_name in self.resource_routers:  # pragma: no cover
            _router = self.resource_routers[resource_name]
            if _router != router:
                raise ValueError(
                    f"Resource router with name {resource_name} already exists."
                )
        self.resource_routers[resource_name] = router

    def start(self, app: FastAPI):
        if app is None:  # pragma: no cover
            raise ValueError("App cannot be None.")
        self.app = app
        # Lazy load auth module to avoid circular imports
        if self.auth_module is None:
            from senweaver.helper import import_class_module

            self.auth_module = import_class_module(settings.AUTH_ENGINE)
        self.modules[self.auth_module.name] = self.auth_module

    async def run(self):
        # 初始化完成
        routes = self.app.routes
        for route in routes:
            if isinstance(route, APIRoute):
                if route.endpoint in self.endpoints:
                    pass
                self.endpoints[route.endpoint] = route

        # routes
        for module in self.modules.values():
            await module.run()


module_manager = ModuleManager()
