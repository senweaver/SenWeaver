from pydantic import BaseModel


class ISystemMsgSubscriptionUpdate(BaseModel):
    users: list[int]
