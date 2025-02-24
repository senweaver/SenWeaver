from pathlib import Path as FilePath

from fastapi import APIRouter, Depends, Request

from app.system.logic.dict_logic import DictLogic
from app.system.model.dict_data import (
    DictData,
    DictDataCreate,
    DictDataRead,
    DictDataUpdate,
)
from app.system.model.dict_type import (
    DictType,
    DictTypeCreate,
    DictTypeRead,
    DictTypeUpdate,
)
from senweaver import senweaver_router

from ..system import module

path = FilePath(__file__)

router = APIRouter(tags=["字典"], route_class=module.route_class)

type_router = senweaver_router(module=module, model=DictType, path=f"/dict/type")
router.include_router(type_router)

data_router = senweaver_router(module=module, model=DictData, path=f"/dict/data")
router.include_router(data_router)
