import re

from datetime import datetime
from pathlib import Path

import typer

from typer import Typer

from config.settings import settings

from ..helper import create_module

sub_app = Typer()


@sub_app.command()
def app(
    name: str = typer.Option(..., '--name', '-n', help='app name'),
    title: str = typer.Option(None, '--title', '-t', help='app title'),
    description: str = typer.Option(None, '--description', '-d', help='app description'),
    author: str = typer.Option('senweaver', '--author', '-a', help='app author'),
    version: str = typer.Option('0.1.0', '--version', '-v', help='app version'),
    homepage: str = typer.Option('https://www.senweaver.com', '--homepage', help='app homepage'),
):
    template_dir = Path(__file__).resolve().parent.parent.joinpath('resource/template/module/base')
    # 定义要替换的变量
    variables = {
        'module_type': 'app',
        'module_type_name': 'App',
        'title': title or name,
        'description': description or f'{name} app',
        'author': author,
        'version': version,
        'homepage': homepage,
        'year': str(datetime.now().year),
    }
    module_path = settings.APP_PATH.joinpath(name)
    create_module(module_path, name, template_dir, variables)
    # asyncio.run(showtable())


@sub_app.command()
def plugin(
    name: str = typer.Option(..., '--name', '-n', help='plugin name'),
    title: str = typer.Option(None, '--title', '-t', help='plugin title'),
    description: str = typer.Option(None, '--description', '-d', help='plugin description'),
    author: str = typer.Option('senweaver', '--author', '-a', help='plugin author'),
    version: str = typer.Option('0.1.0', '--version', '-v', help='plugin version'),
    homepage: str = typer.Option('https://www.senweaver.com', '--homepage', help='plugin homepage'),
):
    template_dir = Path(__file__).resolve().parent.parent.joinpath('resource/template/module/base')
    # 定义要替换的变量
    variables = {
        'module_type': 'plugin',
        'module_type_name': 'Plugin',
        'title': title or name,
        'description': description or f'{name} plugin',
        'author': author,
        'version': version,
        'homepage': homepage,
        'year': str(datetime.now().year),
    }
    module_path = settings.PLUGIN_PATH.joinpath(name)
    create_module(module_path, name, template_dir, variables)


@sub_app.command()
def vendor(
    name: str = typer.Option(..., '--name', '-n', help='package name'),
    package_name: str = typer.Option(None, '--package-name', '-p', help='PyPI package name'),
    description: str = typer.Option(None, '--description', '-d', help='package description'),
    author: str = typer.Option('senweaver', '--author', '-a', help='package author'),
    author_email: str = typer.Option('', '--author-email', '-e', help='author email'),
    homepage: str = typer.Option('https://www.senweaver.com', '--homepage', help='project homepage'),
    version: str = typer.Option('0.1.0', '--version', '-v', help='package version'),
):
    # 验证 name 格式：必须为 xxxx_yyyy 的形式
    if not re.match(r'^[a-z][a-z0-9]*_[a-z0-9_]+$', name):
        raise typer.BadParameter("name must be in format 'prefix_name' (e.g., 'my_package', 'data_processor')")
    # 定义要替换的变量
    package_name = package_name or name.replace('_', '-')
    variables = {
        'module_name': name,
        'package_name': package_name,
        'description': description or f'A Python package: {name}',
        'author': author,
        'author_email': author_email,
        'homepage': homepage,
        'version': version,
        'year': str(datetime.now().year),
        'model_class_name': ''.join(word.capitalize() for word in name.split('_')),
    }
    template_dir = Path(__file__).resolve().parent.parent.joinpath('resource/template/module/vendor')
    module_path = settings.VENDOR_PATH.joinpath(package_name)
    create_module(module_path, name, template_dir, variables)


def concole(app: typer.Typer):
    app.add_typer(sub_app, name='create')
    pass
