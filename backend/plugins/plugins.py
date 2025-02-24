import typer
from fastapi import FastAPI

from senweaver.helper import load_modules


def startup(app: FastAPI):
    # init router
    # from .example.router import init_router as example_init_router
    # example_init_router(app)
    load_modules(app, __package__)


def command(cli_app: typer.Typer):
    load_modules(cli_app, __package__, "concole")
