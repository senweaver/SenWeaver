from typing import Any, TypeVar

from fastcrud.types import *
from pydantic import BaseModel

CreateSchemaInternalType = TypeVar("CreateSchemaInternalType", bound=BaseModel)
