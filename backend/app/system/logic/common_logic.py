import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import Request, UploadFile

from config.settings import settings
from senweaver.core.senweaver_crud import SenweaverCRUD
from senweaver.exception.http_exception import CustomException

from ..model.attachment import Attachment


class CommonLogic:
    @classmethod
    async def get_upload_max_size(cls, user_id: int):
        return 10485760

    @classmethod
    async def upload(
        cls,
        request: Request,
        user_id: int,
        category: str,
        upload_id: str,
        files: List[UploadFile],
    ):
        result = []
        file_upload_max_size = await cls.get_upload_max_size(user_id)
        # 使用条件语句来构建路径
        bucket_name = "default"
        for file in files:
            if file.size > file_upload_max_size:
                raise CustomException(
                    detail=f"文件大小不能超过 {file_upload_max_size}", code=1003
                )
            current_date = datetime.now().strftime("%Y%m%d")
            if upload_id and upload_id.strip():  # 检查upload_id非空且非仅空白字符
                path = f"{bucket_name}/{category}/{upload_id}/{current_date}"
            else:
                path = f"{bucket_name}/{category}/{current_date}"
            upload_path = settings.UPLOAD_PATH / path

            if not upload_path.exists():
                upload_path.mkdir(parents=True, exist_ok=True)
            file_obj = file.file
            sha_hash = hashlib.sha1()
            file_obj.seek(0)
            while chunk := file_obj.read(4096):
                sha_hash.update(chunk)
            hash = sha_hash.hexdigest()
            file_obj.seek(0)
            suffix = Path(file.filename).suffix
            # if category == "avatar":
            #     avatar_hash = hashlib.sha256()
            #     avatar_hash.update(f"{user_id}_{hash}".encode('utf-8'))
            #     filename = avatar_hash.hexdigest()
            # else:
            filename = f"{uuid.uuid4().hex}{suffix}"
            filepath = upload_path / filename
            with open(filepath, "wb") as f:
                while chunk := file_obj.read(4096):
                    f.write(chunk)
            file_obj = Attachment(
                hash=hash,
                filename=file.filename,
                bucket=bucket_name,
                category=category,
                filepath=f"{path}/{filename}",
                suffix=suffix,
                filesize=file.size,
                mime_type=file.content_type,
                storage="local",
                creator_id=request.user.id,
                modifier_id=request.user.id,
                is_tmp=True,
                is_upload=True,
            )
            db = request.auth.db.session
            crud = SenweaverCRUD(Attachment, allow_relationship=True)
            ret = await crud.create(db, file_obj)
            file_data = {
                "id": ret["id"],
                "access_url": file_obj.access_url,
                "file_url": file_obj.file_url,
                "filename": file_obj.filename,
                "filesize": file_obj.filesize,
                "is_tmp": file_obj.is_tmp,
                "is_upload": file_obj.is_upload,
                "hash": file_obj.hash,
                "mime_type": file_obj.mime_type,
            }
            result.append(file_data)

        return result


common_logic = CommonLogic()
