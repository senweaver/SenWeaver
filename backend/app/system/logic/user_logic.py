from datetime import datetime, timezone
from typing import Annotated

from fastapi import File, Path, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.system.core.auth.auth import SystemAuth
from senweaver import SenweaverCRUD
from senweaver.auth.security import requires_permissions
from senweaver.core.senweaver_creator import SenweaverEndpointCreator
from senweaver.exception.http_exception import (
    DuplicateValueException,
    NotFoundException,
)
from senweaver.utils.response import ResponseBase, success_response

from ..model.data_permission import DataPermission
from ..model.role import Role
from ..model.user import User, UserCreate, UserCreateInternal
from ..schema.user import IUserEmpower, IUserResetPassword
from .common_logic import CommonLogic


class UserLogic:

    @classmethod
    async def create(cls, request: Request, user: UserCreate) -> User:
        async_session: AsyncSession = request.auth.db.session
        crud = SenweaverCRUD(User)
        username_row = await crud.exists(db=async_session, username=user.username)
        if username_row:
            raise DuplicateValueException("Username not available")

        auth: SystemAuth = request.auth
        user_internal_dict = user.model_dump()
        user_internal_dict["password"] = auth.password_helper.hash(
            password=user_internal_dict["password"]
        )

        user_internal = UserCreateInternal(**user_internal_dict)
        return await crud.create(db=async_session, object=user_internal)

    @classmethod
    async def set_empower_data(cls, request: Request, user_id: int, data: IUserEmpower):
        db: AsyncSession = request.auth.db.session
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .options(selectinload(User.rules))
            .where(User.id == user_id)
        )
        db_row = await db.execute(stmt)
        user = db_row.scalars().first()
        if not user:
            raise NotFoundException(f"{User.__name__}{user_id} not found")
        role_ids = [role.id for role in data.roles]
        rule_ids = [rule.id for rule in data.rules]
        role_result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
        rule_result = await db.execute(
            select(DataPermission).where(DataPermission.id.in_(rule_ids))
        )
        user.roles = role_result.scalars().all()
        user.rules = rule_result.scalars().all()
        user.mode_type = data.mode_type
        await db.flush()
        await db.commit()

    @classmethod
    async def reset_user_password(
        cls, request: Request, user_id: int, data: IUserResetPassword
    ) -> User:
        crud = SenweaverCRUD(User)
        db: AsyncSession = request.auth.db.session
        user = await crud.get(db, id=user_id, is_active=True, one_or_none=True)
        if not user:
            raise NotFoundException("user not found")
        new_password_hash = request.auth.get_hash_password(
            value=data.password, key=user["username"]
        )
        new_password_time = datetime.now(timezone.utc)
        await crud.update(
            db,
            {"password": new_password_hash, "password_time": new_password_time},
            id=user_id,
        )

    @classmethod
    async def upload_avatar(cls, request: Request, user_id: int, file: UploadFile):
        data = await CommonLogic.upload(request, user_id, "avatar", "", [file])
        path = data[0].filepath
        await SenweaverCRUD(User).update(
            request.auth.db.session, {"avatar": path}, id=user_id
        )

    @classmethod
    def add_custom_router(cls, endpoint_creator: SenweaverEndpointCreator):
        self = endpoint_creator
        router = self.router
        module = self.module

        @router.post(self.path + "/{id}/reset-password", summary="管理员重置用户密码")
        @requires_permissions(f"{module.get_auth_str(self.resource_name, "reset")}")
        async def reset_user_password(
            id: Annotated[int, Path(...)],
            data: IUserResetPassword,
            request: Request,
        ) -> ResponseBase:
            await UserLogic.reset_user_password(request, id, data)
            return success_response()

        @router.post(self.path + "/{id}/empower", summary="分配用户角色-数据权限")
        @requires_permissions(f"{module.get_auth_str(self.resource_name, "empower")}")
        async def set_empower_data(
            id: Annotated[int, Path(...)],
            data: IUserEmpower,
            request: Request,
        ) -> ResponseBase:
            await UserLogic.set_empower_data(request, id, data)
            return success_response()

        @router.post(self.path + "/{id}/upload", summary="上传用户头像")
        @requires_permissions(f"{module.get_auth_str(self.resource_name, "upload")}")
        async def upload_user_avatar(
            request: Request,
            id: Annotated[int, Path(...)],
            file: UploadFile = File(None),
        ) -> ResponseBase:
            await UserLogic.upload_avatar(request, id, file)
            return success_response()

        @router.post(self.path + "/{id}/unblock", summary="解禁用户")
        @requires_permissions(f"{module.get_auth_str(self.resource_name, "unBlock")}")
        async def unblock_user(
            request: Request, id: Annotated[int, Path(...)]
        ) -> ResponseBase:

            return success_response()


user_logic = UserLogic()
