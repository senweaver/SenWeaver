from pathlib import Path

import typer
from fastapi import FastAPI

from senweaver.module.plugin import PluginModule


class CmdPlugin(PluginModule):

    def run(self):
        pass


module = CmdPlugin(module_path=Path(__file__).parent, package=__package__)


def initialize(app: FastAPI):
    module.start(app)


def concole(app: typer.Typer):
    from .core import build, create, createsuperuser, crud, data

    build.concole(app)
    crud.concole(app)
    create.concole(app)
    data.concole(app)
    createsuperuser.concole(app)
