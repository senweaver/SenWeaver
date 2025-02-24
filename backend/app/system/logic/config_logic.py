from typing import Any, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from senweaver import SenweaverCRUD

from ..model.system_config import SystemConfig
from ..model.user_config import UserConfig


class ConfigLogic:
    @classmethod
    async def get_config(
        cls, request: Request, key: str
    ) -> UserConfig | SystemConfig | None:
        db: AsyncSession = request.auth.db.session
        auth = "AnonymousUser"
        config = None
        if request.user:
            auth = f"{request.user.nickname}({request.user.username})"
            config = await SenweaverCRUD(
                UserConfig, check_data_scope=False, check_field_scope=False
            ).get(db, key=key, owner_id=request.user.id, one_or_none=True)
        if config is None:
            config = await SenweaverCRUD(SystemConfig).get(
                db, key=key, one_or_none=True
            )
        data = {}
        if config is not None:
            data = config["value"]
        return {"config": data, "auth": auth}

    @classmethod
    async def save_config(cls, request: Request, key: str, data: Any):
        if data is not None:
            db: AsyncSession = request.auth.db.session
            crud = SenweaverCRUD(UserConfig, check_field_scope=False)
            config = await crud.get(
                db, key=key, owner_id=request.user.id, one_or_none=True
            )
            if config is not None:
                config.update({"value": data})
                await crud.update(db, config)
            else:
                await crud.create(
                    db, UserConfig(key=key, owner_id=request.user.id, value=data)
                )
        return await cls.get_config(request, key)


config_logic = ConfigLogic()
