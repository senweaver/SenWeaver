from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    name: str
    version: str
    title: str
    description: str
    author: str
    enabled: bool = True
    homepage: str
    url: str
    option: dict
    model_config = ConfigDict(populate_by_name=True, extra="allow")
