import typer
from fastapi import FastAPI

from senweaver.helper import load_modules


def startup(app: FastAPI):
    # from app.system.system import initialize
    # initialize(app)
    load_modules(app, __package__)
    pass


def command(cli_app: typer.Typer):
    load_modules(cli_app, __package__, "concole")
