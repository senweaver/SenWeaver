# -*- coding: utf-8 -*-
from pathlib import Path

import typer
from fastapi import FastAPI

from senweaver.module.app import AppModule


class CommonApp(AppModule):

    def run(self):
        pass


module = CommonApp(module_path=Path(__file__).parent, package=__package__)


def initialize(app: FastAPI):
    module.start(app)


def concole(app: typer.Typer):
    pass
