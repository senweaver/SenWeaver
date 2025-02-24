import importlib
import inspect
import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Sequence, Set, Type

import orjson
import yaml
from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastcrud import FastCRUD, FilterConfig
from pydantic import model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from senweaver.auth.security import get_current_user
from senweaver.core.senweaver_crud import SenweaverCRUD
from senweaver.core.senweaver_route import SenweaverRoute
from senweaver.db.helper import senweaver_model_validator
from senweaver.db.session import get_session
from senweaver.helper import create_schema_by_schema, find_modules, load_routers
from senweaver.module.settings import Settings


class Module(ABC):
    app: FastAPI = None
    type: str
    name: str
    ready: bool = False
    package: str
    module_path: Path
    settings: Settings
    config_path: str
    depends: list = None
    prefix: str = None
    table_models: dict[str, SQLModel] = None
    module_models: dict[str, SQLModel] = None
    module_filters: dict[str, Any] = None

    def __init__(
        self,
        type: str,
        module_path: Path,
        package: str,
        name: str = None,
        depends: list = [Depends(get_current_user)],
        route_class: Type[APIRoute] = SenweaverRoute,
    ):
        self.type = type
        self.module_path = module_path
        self.package = package
        self.table_models = {}
        self.module_models = {}
        self.module_filters = {}
        self.settings = None
        self.name = name
        self.depends = depends
        self.route_class = route_class
        if name is None:
            self.name = self.module_path.stem
        self.config_path = None
        if (self.module_path / "config.yaml").exists():
            self.config_path = (self.module_path / "config.yaml").as_posix()
            self.load_from_yaml()
        self.prefix = f"/{self.name}"
        self.load_models()

    def load_models(self):
        if self.settings is None or not self.settings.enabled:
            return
        modules = find_modules(
            f"{self.package}.model", include_packages=False, recursive=True
        )
        for name in modules:
            module = importlib.import_module(name)
            for name, cls in inspect.getmembers(module, inspect.isclass):
                if issubclass(cls, SQLModel) and hasattr(cls, "__table__"):
                    if not cls.__module__.startswith(self.package):
                        continue
                    self.table_models[cls.__tablename__] = cls
                    if not cls.__tablename__.startswith(f"{self.name}_"):
                        raise ValueError(
                            f"{cls.__tablename__} must start with {self.name}_"
                        )
                    cls.__senweaver_name__ = f"{self.name}.{
                        cls.__name__.lower()}"
                    self.module_models[cls.__senweaver_name__] = cls

    def load_from_yaml(self):

        with open(self.config_path, "r", encoding="utf-8") as open_yaml:
            settings_dict = yaml.safe_load(open_yaml)
        self.settings = Settings(**settings_dict)
        pattern = rf"^\/{self.name}(?:\/[\w.-]*)?$"
        if not re.match(pattern, self.settings.url):
            raise ValueError(
                f'url must be in the format "/{self.name}" or "/{self.name}/xxx"'
            )

    def save_to_yaml(self):
        with open(self.config_path, "w", encoding="utf-8") as write_yaml:
            settings_dict = self.settings.model_dump()
            yaml.safe_dump(
                settings_dict, write_yaml, allow_unicode=True, sort_keys=False
            )

    def get_resource_name(self, path: str):
        # 去掉开头和结尾可能存在的斜杠，并以斜杠和连字符作为分隔符分割字符串
        words = path.strip("/").replace("-", "/").split("/")
        # 将每个单词首字母大写，其余字母小写，然后拼接起来
        path_name = "".join(word.capitalize() or "_" for word in words)
        new_name = self.name[0].upper() + self.name[1:]
        return f"{new_name}{path_name}"

    def get_auth_str(self, resource_name: str, actions: str | Sequence[str]):
        if resource_name is None:
            raise ValueError("resource_name can not be empty")
        if isinstance(actions, str) and "," in actions:
            actions = actions.split(",")
        if not actions:
            raise ValueError("actions can not be empty")
        actions_list = [actions] if isinstance(actions, str) else list(actions)
        # new_name = self.name[0].upper() + self.name[1:]
        return ",".join([f"{action}:{resource_name}" for action in actions_list])

    def get_path_auth_str(self, path: str, actions: str | Sequence[str]):
        resource_name = self.get_resource_name(path)
        return self.get_auth_str(resource_name, actions)

    def install(self):
        pass

    def uninstall(self):
        pass

    def add_filter(
        self, path: str, model: Type[SQLModel], filter: FilterConfig, router: APIRouter
    ):
        if model != filter.model:  # type: ignore
            raise ValueError(
                f"The model of filter {path} must be the same as the model of the table {model.__name__}"
            )
        self.module_filters[path] = filter

    def add_path_router(self, path: str, router: APIRouter):
        resource_name = self.get_resource_name(path)
        self.add_resource_router(resource_name, router)

    def add_resource_router(self, resource_name: str, router: APIRouter):
        router.sw_module = self
        from .manager import module_manager

        module_manager._add_router(resource_name, router)

    async def on_init_data(self):
        async for db in get_session():
            self.init_data(db)

    async def on_dump_data(self):
        async for db in get_session():
            self.dump_data(db)

    async def init_data(self, db: AsyncSession, path: str = None, models: list = None):
        if not self.settings.enabled:
            return
        if path is None:
            path = self.module_path / "resource/data"
        if models is None:
            models = []
            for file_path in path.glob("*.json"):
                file_stem = file_path.stem  # 获取文件名（不含扩展名）
                model = self.module_models.get(f"{self.name}.{file_stem}", None)
                if model is None:
                    continue
                models.append(model)
        for model in models:
            file_path = path.joinpath(f"{model.__name__.lower()}.json")
            with open(file_path, "r", encoding="utf-8") as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError as e:
                    print(
                        f"Failed to decode JSON from {
                        file_path}: {e}"
                    )
                    continue
            if len(data) == 0:
                print(f"Empty JSON file: {file_path}")
                continue
            create_schema = create_schema_by_schema(
                model,
                name=f"{self.name}{model.__name__}InitDataCreate",
                validators={
                    "_senweaver_model_validator": model_validator(mode="before")(
                        senweaver_model_validator
                    )
                },
            )
            crud = SenweaverCRUD(model)
            pk_name = crud._primary_keys[0].name
            for item in data:
                # exists = await crud.exists(db, pk_name=item[pk_name])
                # if exists:
                #     continue
                try:
                    object = create_schema(**item)
                    await crud.create(db, object)
                except Exception as e:
                    print(e)

    async def dump_data(
        self,
        db: AsyncSession,
        path: str = None,
        include: Set[str] = None,
        exclude: Set[str] = None,
    ):
        if not self.settings.enabled:
            return
        if path is None:
            path = self.module_path / "resource/data"
        path.mkdir(parents=True, exist_ok=True)
        for key, model in self.module_models.items():
            name = key.replace(f"{self.name}.", "")
            if include is not None and name not in include:
                continue
            if exclude is not None and name in exclude:
                continue
            try:
                ret = await FastCRUD(model).get_multi(
                    db, return_total_count=False, limit=None
                )
                items = ret["data"]
                if not items:
                    continue
                data_json = orjson.dumps(
                    items, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE
                )
                file_path = path.joinpath(f"{name}.json")
                with file_path.open("wb") as f:
                    f.write(data_json)
            except Exception as e:
                print(e)

    def on_before_start(self):
        pass

    def on_after_start(self):
        pass

    def start(self, app: FastAPI):
        from .manager import module_manager

        self.app = app
        if self.app is None:
            raise ValueError(f"module {self.name} app is None")
        if not self.settings.enabled:
            return
        self.on_before_start()
        load_routers(
            app=self.app,
            package_path=self.package,
            prefix=self.prefix,
            depends=self.depends,
        )
        # 挂载子应用
        # subapp = FastAPI(title=self.settings.title,
        #                  description=self.settings.description, version=self.settings.version)
        # load_routers(subapp, self.package, f'/{self.name}')
        # self.app.mount(f'/{self.settings.name}', subapp)

        static_path = self.module_path / "public"
        if static_path.exists():
            static_file_path = static_path.as_posix()
            self.app.mount(
                self.settings.url,
                StaticFiles(directory=static_file_path, html=True),
                name=f"{self.type}_{self.name}_web",
            )
        self.run()
        self.ready = True
        module_manager.add(self.name, self)
        self.on_after_start()

    @abstractmethod
    def run(self):
        raise NotImplementedError()  # pragma: no cover
