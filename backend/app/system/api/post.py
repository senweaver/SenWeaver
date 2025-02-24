from pathlib import Path as FilePath

from fastapi import APIRouter

from app.system.model.post import Post, PostCreate, PostRead, PostUpdate
from senweaver import senweaver_router

from ..system import module

path = FilePath(__file__)

router = APIRouter(tags=["岗位"], route_class=module.route_class)

_router = senweaver_router(module=module, model=Post, path=f"/{path.stem}")
router.include_router(_router)
