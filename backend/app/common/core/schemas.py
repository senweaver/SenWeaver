# -*- coding: utf-8 -*-
from typing import List

from pydantic import BaseModel


class IResourceCache(BaseModel):
    resources: List[str]
