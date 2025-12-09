import importlib
import inspect
import os
from pathlib import Path
from typing import List

from config.settings import settings
from sqlmodel import SQLModel

from senweaver.helper import find_modules


def get_modules(base_package: str, module_path: Path) -> List[str]:
    module_names = []
    # 确保路径存在
    if not module_path.exists() or not module_path.is_dir():
        print(
            f"Warning: module path {module_path} does not exist or is not a directory"
        )
        return module_names

    for modname in os.listdir(module_path):
        item_path = module_path / modname

        # 检查是否为目录
        if not item_path.is_dir():
            continue

        # 检查是否包含__init__.py文件
        if not (item_path / "__init__.py").exists():
            continue

        # 检查是否存在同名Python文件（module_name/module_name.py）
        module_file = item_path / f"{modname}.py"
        if not module_file.exists():
            continue

        # 构造完整模块名
        module_name = f"{base_package}.{modname}"
        module_names.append(module_name)

    return module_names


def get_module_models(module_package: str):
    model_classes = {}
    modules = find_modules(
        f"{module_package}.model", include_packages=False, recursive=True
    )
    for name in modules:
        module = importlib.import_module(name)
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, SQLModel) and hasattr(cls, "__table__"):
                if not cls.__module__.startswith(module_package):
                    continue
                model_classes[cls.__name__] = cls
    return model_classes


def get_all_modules():
    app_modules = get_modules("app", settings.APP_PATH)
    plugin_modules = get_modules("plugins", settings.PLUGIN_PATH)
    all_modules = app_modules + plugin_modules
    return all_modules


def get_all_models():
    all_modules = get_all_modules()
    model_classes = {}
    for module_package in all_modules:
        model_classes.update(get_module_models(module_package))
    return model_classes
