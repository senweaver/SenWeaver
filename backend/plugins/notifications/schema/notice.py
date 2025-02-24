from pydantic import BaseModel


class IStateUpdate(BaseModel):
    unread: bool


class INoticeBatchRead(BaseModel):
    ids: list[int]
