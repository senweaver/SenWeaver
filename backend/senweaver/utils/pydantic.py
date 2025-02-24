from typing import Any, Dict

from fastapi._compat import sequence_annotation_to_type  # noqa: F401
from pydantic import BaseModel
from pydantic.v1.typing import is_literal_type, is_none_type, is_union
from pydantic.v1.utils import lenient_issubclass
from typing_extensions import Annotated, get_args, get_origin


def parse_annotation_type(annotation: Any) -> Any:
    if annotation is Ellipsis:
        return Any
    origin = get_origin(annotation)
    if origin is None:
        return annotation
    elif is_union(origin) or origin is Annotated:
        pass
    elif origin in sequence_annotation_to_type:
        return sequence_annotation_to_type[origin]
    elif origin in {Dict, dict}:
        return dict
    elif lenient_issubclass(origin, BaseModel):
        return origin
    args = get_args(annotation)
    for arg in args:
        if is_literal_type(annotation):
            arg = type(arg)
        if is_none_type(arg):
            continue
        return parse_annotation_type(arg)
    return annotation
