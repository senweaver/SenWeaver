# -*- coding: utf-8 -*-
from pathlib import Path

from fastapi import FastAPI
from senweaver.module.app import AppModule


class NotificationsApp(AppModule):
    async def run(self):
        pass


module = NotificationsApp(module_path=Path(__file__).parent, package=__package__)


def initialize(app: FastAPI):
    module.start(app)
