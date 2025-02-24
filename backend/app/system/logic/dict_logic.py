from fastapi import Request

from ..model.dict_type import DictType, DictTypeCreate


class DictLogic:

    @classmethod
    async def create(cls, request: Request, user: DictTypeCreate) -> DictType:
        # TODO
        return None


dict_logic = DictLogic()
