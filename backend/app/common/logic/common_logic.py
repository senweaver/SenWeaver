from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from senweaver import SenweaverCRUD


class CommonLogic:
    crud: SenweaverCRUD

    def __init__(self) -> None:
        # self.crud = SenweaverCRUD[]
        pass


common_logic = CommonLogic()
