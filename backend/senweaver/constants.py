from enum import Enum


class TokenTypeEnum(str, Enum):
    """
    Enum for token type.
    """

    access = "access"
    refresh = "refresh"
