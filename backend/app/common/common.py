# -*- coding: utf-8 -*-
from pathlib import Path

from fastapi import FastAPI
from senweaver.module.app import AppModule


class CommonApp(AppModule):
    async def run(self):
        pass


module = CommonApp(module_path=Path(__file__).parent, package=__package__)


def initialize(app: FastAPI):
    module.start(app)
