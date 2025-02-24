import asyncio
from pathlib import Path

import typer
from typer import Option, Typer

from config.settings import settings

from ..helper import create_module

sub_app = Typer()


@sub_app.command()
def app(name: str = typer.Option(..., "--name", "-n", help="app name")):
    template_dir = (
        Path(__file__).resolve().parent.parent.joinpath("resource/template/module/app")
    )
    # 定义要替换的变量
    variables = {}
    module_path = settings.APP_PATH.joinpath(name)
    create_module(module_path, name, template_dir, variables)
    # asyncio.run(showtable())


@sub_app.command()
def plugin(name: str = typer.Option(..., "--name", "-n", help="plugin name")):
    template_dir = (
        Path(__file__)
        .resolve()
        .parent.parent.joinpath("resource/template/module/plugin")
    )
    # 定义要替换的变量
    variables = {}
    module_path = settings.PLUGIN_PATH.joinpath(name)
    create_module(module_path, name, template_dir, variables)


@sub_app.command()
def vendor(
    name: str = typer.Option(..., "--name", "-n", help="vendor name"),
    provider: str = typer.Option("senweaver", "--provider", "-p", help="provider name"),
):
    template_dir = (
        Path(__file__)
        .resolve()
        .parent.parent.joinpath("resource/template/module/vendor")
    )
    # 定义要替换的变量
    variables = {"provider": provider}
    module_path = settings.VENDOR_PATH.joinpath(provider).joinpath(name)
    create_module(module_path, name, template_dir, variables)


def concole(app: typer.Typer):
    app.add_typer(sub_app, name="create")
    pass
