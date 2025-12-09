# -*- coding: utf-8 -*-
from pathlib import Path

from fastapi import FastAPI
from senweaver.db.session import get_session
from senweaver.module.app import AppModule


class SystemApp(AppModule):
    async def on_init_data(self):
        async for db in get_session():
            return await self.init_data(db)

    async def on_dump_data(self):
        async for db in get_session():
            await self.dump_data(
                db=db, exclude=("operationlog", "loginlog", "attachment")
            )

    async def run(self):
        pass


module = SystemApp(module_path=Path(__file__).parent, package=__package__)


def initialize(app: FastAPI):
    module.start(app)
