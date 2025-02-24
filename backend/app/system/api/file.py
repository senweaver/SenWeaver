from pathlib import Path as FilePath
from typing import List, Optional

from fastapi import APIRouter, File, Form, Request, UploadFile

from app.system.model.attachment import Attachment
from senweaver import senweaver_router
from senweaver.core.helper import SenweaverFilter
from senweaver.utils.response import ResponseBase, success_response

from ..logic.common_logic import CommonLogic
from ..system import module

path = FilePath(__file__)

router = APIRouter(tags=["文件"], route_class=module.route_class)

filter_config = SenweaverFilter(
    filters={
        "filename": None,
        "mime_type": None,
        "hash": None,
        "description": None,
        "is_upload": None,
        "is_tmp": None,
    },
    ordering_fields=["created_time", "filesize"],
    read_only_fields=["id", "is_upload", "storage", "bucket", "category", "filepath"],
    fields=[
        "id",
        "filename",
        "filesize",
        "mime_type",
        "hash",
        "file_url",
        "access_url",
        "is_tmp",
        "is_upload",
        "filepath",
    ],
    table_fields=[
        "id",
        "filename",
        "filesize",
        "mime_type",
        "access_url",
        "is_tmp",
        "is_upload",
        "hash",
    ],
)
_router = senweaver_router(
    module=module, model=Attachment, path=f"/{path.stem}", filter_config=filter_config
)


@_router.get("/file/config", summary="获取上传配置")
async def notice_unread(request: Request) -> ResponseBase:
    # TODO 获取系统配置和用户配置中最小的
    data = {"file_upload_size": await CommonLogic.get_upload_max_size(request.user.id)}
    return success_response(data)


@_router.post("/file/upload", summary="上传文件")
async def upload(
    request: Request,
    category: Optional[str] = Form(
        default="public",
        description="文件类型，如 'public','image', 'document', 'video'",
        examples=["public"],
    ),
    file: List[UploadFile] = File(...),
):
    data = await CommonLogic.upload(request, request.user.id, category, "", file)
    return success_response(data)


router.include_router(_router)
