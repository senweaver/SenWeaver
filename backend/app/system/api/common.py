from fastapi import APIRouter

from ..system import module

open_router = APIRouter(
    prefix="/common", tags=["common"], route_class=module.route_class
)
router = APIRouter(prefix="/common", tags=["common"], route_class=module.route_class)
