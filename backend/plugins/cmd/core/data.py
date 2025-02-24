import asyncio
import importlib
import importlib.util
import pkgutil

import typer
from typer import Typer

from senweaver.helper import import_string

sub_app = Typer()


def concole(app: typer.Typer):
    app.add_typer(sub_app, name="data")


def load_module(
    package_path: str, init_module_name: str = None, attr: str = "on_init_data"
):
    module = import_string(package_path)
    path = getattr(module, "__path__", None)
    if path is None:
        raise ValueError(f"{package_path!r} is not a package")
    basename = f"{module.__name__}"
    module_names = []
    for _, modname, ispkg in pkgutil.iter_modules(path):
        if init_module_name is not None and modname != init_module_name:
            continue
        if ispkg:
            module_name = f"{basename}.{modname}.{modname}"
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "module"):
                    module_obj = getattr(module, "module", None)
                    if hasattr(module_obj, attr):
                        func = getattr(module_obj, attr, None)
                        if callable(func):
                            asyncio.run(func())
            except ImportError as e:
                print(f"Error importing {module_name}: {e}")


@sub_app.command()
def init(module: str = typer.Option(None, "--module", "-m", help="module name")):
    load_module("app", module)
    load_module("plugins", module)


@sub_app.command()
def dump(module: str = typer.Option(None, "--module", "-m", help="module name")):
    load_module("app", module, "on_dump_data")
    load_module("plugins", module, "on_dump_data")
