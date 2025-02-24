from datetime import datetime, timezone
from typing import Any, Optional, Sequence
from urllib.parse import urljoin

from fastapi import Depends, Query, Request
from fastcrud import FastCRUD
from fastcrud.paginated.helper import compute_offset
from pydantic import BaseModel
from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload, selectinload

from app.system.model.attachment import Attachment
from app.system.model.dept import Dept
from app.system.model.role import Role
from app.system.model.user import User
from app.system.model.user_role import UserRole
from config.settings import settings
from senweaver import SenweaverCRUD
from senweaver.auth.security import Authorizer, requires_permissions
from senweaver.core.helper import RelationConfig
from senweaver.core.senweaver_creator import SenweaverEndpointCreator
from senweaver.exception.http_exception import BadRequestException, NotFoundException
from senweaver.utils.response import PageResponse, ResponseBase, success_response

from ..model import Notice, NoticeDept, NoticeRole, NoticeUserRead
from ..schema.notice import IStateUpdate


class NoticeLogic:

    @classmethod
    async def read_all_message(cls, request: Request):
        db: AsyncSession = request.auth.db.session
        crud = SenweaverCRUD(Notice)
        _, role_ids = request.auth.get_role_scope()
        current_user = request.user
        filters = {"publish": True}
        filters["__where"] = or_(
            Notice.notice_type == Notice.NoticeChoices.NOTICE,
            and_(
                Notice.notice_type == Notice.NoticeChoices.DEPT,
                (
                    NoticeDept.dept_id.is_(None)
                    if current_user.dept_id is None
                    else NoticeDept.dept_id == current_user.dept_id
                ),
            ),
            and_(
                Notice.notice_type == Notice.NoticeChoices.ROLE,
                NoticeRole.id.in_(role_ids),
            ),
            and_(
                Notice.notice_type.in_(Notice.get_user_choices()),
                and_(
                    NoticeUserRead.owner_id == current_user.id,
                    NoticeUserRead.unread.is_(True),
                ),
            ),
        )
        kwargs = await crud._build_filters(filters)
        sa_filters = crud._parse_filters(**kwargs)
        stmt = (
            select(Notice.id)
            .distinct()
            .outerjoin(NoticeDept, Notice.id == NoticeDept.dept_id)
            .outerjoin(NoticeRole, Notice.id == NoticeRole.notice_id)
            .outerjoin(NoticeUserRead, Notice.id == NoticeUserRead.notice_id)
            .filter(*sa_filters)
        )
        result = await db.execute(stmt)
        list_ids = result.scalars().all()
        await cls.read_message(request, list_ids)

    @classmethod
    async def read_message(cls, request: Request, ids: list[int]):
        db: AsyncSession = request.auth.db.session
        crud = SenweaverCRUD(NoticeUserRead)
        await crud.update(
            db,
            object={"unread": False},
            notice_id__in=ids,
            owner_id=request.user.id,
            unread=True,
            allow_multiple=True,
        )
        for id in ids:
            db_instance = await crud.get(
                db, return_as_model=False, notice_id=id, owner_id=request.user.id
            )
            data = {"notice_id": id, "owner_id": request.user.id, "unread": False}
            user_data = {}
            updated_time = datetime.now(timezone.utc)
            if request and hasattr(request, "user"):
                user_data["modifier_id"] = request.user.id
                user_data["updated_time"] = updated_time
                if db_instance is None:
                    creator_data = request.auth.get_creator_data(NoticeUserRead)
                    user_data.update(creator_data)
            data.update(user_data)
            if db_instance is None:
                await crud.create(db, object=NoticeUserRead(**data))
            else:
                await crud.update(
                    db, object=data, notice_id=id, owner_id=request.user.id
                )

    @classmethod
    async def get_user_count(cls, db: AsyncSession, obj: Notice, key: str, **kwargs):
        if obj.notice_type == Notice.NoticeChoices.DEPT:
            ids = [item.id for item in obj.notice_dept]
            return await FastCRUD(User).count(db, dept_id__in=ids, is_deleted=False)
        elif obj.notice_type == Notice.NoticeChoices.ROLE:
            ids = [item.id for item in obj.notice_role]
            return await FastCRUD(UserRole).count(db, Role_id__in=ids)
        return len(obj.notice_user)

    @classmethod
    async def get_read_user_count(
        cls, db: AsyncSession, obj: Notice, key: str, **kwargs
    ):
        if obj.notice_type in Notice.get_user_choices():
            ids = [owner.id for owner in obj.notice_user]
            return await FastCRUD(NoticeUserRead).count(
                db, notice_id=obj.id, unread=False, owner_id__in=ids
            )
        elif obj.notice_type in Notice.get_notice_choices():
            return len(obj.notice_user)
        return 0

    @classmethod
    async def get_notice_user(
        cls, db: AsyncSession, obj: Notice, key: str, relation: RelationConfig, **kwargs
    ):
        notice_user = getattr(obj, key, None)
        data = []
        if notice_user:
            for user in notice_user:
                user_data = {
                    "id": user.owner_id,
                    "username": user.username,
                    "label": user.username,
                }
                if relation.schema_to_select and relation.return_as_model:
                    data.append(relation.schema_to_select(**user_data))
                else:
                    data.append(user_data)
        return data

    @classmethod
    async def get_notice_info(
        cls,
        db: AsyncSession,
        obj: NoticeUserRead,
        key: str,
        schema: Optional[BaseModel] = None,
        relationships: Optional[Sequence[RelationConfig]] = None,
        **kwargs,
    ):
        notice = getattr(obj, "notice", None)
        if notice is None:
            return None
        filter = getattr(schema, "sw_filter", None)
        if filter:
            relation: RelationConfig = filter._relationship_dict.get("notice", None)
            if relation is None:
                return notice
            data = notice.model_dump()
            notice_data = {}
            for key, value in data.items():
                if key not in relation.attrs:
                    continue
                notice_data[key] = value
            rel_obj = relation.schema_to_select(**notice_data)
            rel_obj.label = notice.title
            return rel_obj
        return notice

    @classmethod
    async def set_read_state(cls, request: Request, id: int, state: IStateUpdate):
        db: AsyncSession = request.auth.db.session
        crud = SenweaverCRUD(NoticeUserRead)
        obj = await crud.get_joined(
            db, join_model=Notice, join_prefix="notice_", nest_joins=True, id=id
        )
        if obj is None:
            raise NotFoundException()
        notice_type = obj["notice"]["notice_type"]
        if notice_type in Notice.get_user_choices():
            await crud.update(db, {"unread": state.unread}, id=id)
        elif notice_type in Notice.get_notice_choices():
            await crud.delete(db, id=id)

    @classmethod
    async def get_site_message_list(
        cls,
        db: AsyncSession,
        request: Request,
        endpoint_creator: SenweaverEndpointCreator,
        offset: Optional[int],
        limit: Optional[int],
        page: Optional[int],
        items_per_page: Optional[int],
        filters: dict,
        ordering: Optional[list[str]],
        **kwargs,
    ) -> ResponseBase:
        self = endpoint_creator
        is_paginated = (page is not None) and (items_per_page is not None)
        has_offset_limit = (offset is not None) and (limit is not None)
        current_user = request.user
        _, role_ids = request.auth.get_role_scope()
        req_unread = filters.pop("unread", None)
        filters["__where"] = or_(
            Notice.notice_type == Notice.NoticeChoices.NOTICE,
            and_(
                Notice.notice_type == Notice.NoticeChoices.DEPT,
                (
                    NoticeDept.dept_id.is_(None)
                    if current_user.dept_id is None
                    else NoticeDept.dept_id == current_user.dept_id
                ),
            ),
            and_(
                Notice.notice_type == Notice.NoticeChoices.ROLE,
                NoticeRole.id.in_(role_ids),
            ),
            and_(
                Notice.notice_type.in_(Notice.get_user_choices()),
                (
                    NoticeUserRead.owner_id == current_user.id
                    if req_unread is None
                    else and_(
                        NoticeUserRead.owner_id == current_user.id,
                        NoticeUserRead.unread.is_not(req_unread),
                    )
                ),
            ),
        )
        if is_paginated and has_offset_limit:
            raise BadRequestException(
                detail="参数冲突：对分页结果使用“page”和“itemsPerPage”，对特定范围查询使用“offset”和“limit”。"
            )
        if is_paginated:
            offset = compute_offset(
                page=page, items_per_page=items_per_page
            )  # type: ignore
            limit = items_per_page
        if not has_offset_limit:
            offset = 0
            limit = 10
        kwargs = await self.crud._build_filters(filters)
        schema_to_select = self.select_schema
        sa_filters = self.crud._parse_filters(**kwargs)
        stmt = (
            select(Notice)
            .distinct()
            .outerjoin(NoticeDept, Notice.id == NoticeDept.dept_id)
            .outerjoin(NoticeRole, Notice.id == NoticeRole.notice_id)
            .outerjoin(NoticeUserRead, Notice.id == NoticeUserRead.notice_id)
            .filter(*sa_filters)
        )
        if ordering:
            stmt = self.crud._apply_sorting(stmt, ordering)

        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        records = result.scalars().all()
        list_data = []
        for item in records:
            data = await self.crud._row_to_data(
                db, "read_multi", item, schema=schema_to_select, return_as_model=True
            )
            notice_unread_stmt = select(func.count(NoticeUserRead.id)).where(
                NoticeUserRead.owner_id == current_user.id,
                NoticeUserRead.notice_id == item.id,
                NoticeUserRead.unread.is_(True),
            )
            notice_unread_count: Optional[int] = await db.scalar(notice_unread_stmt)
            setattr(data, "unread", notice_unread_count > 0)
            list_data.append(data)
        stmt_count = select(func.count()).select_from(
            select(Notice.id)
            .distinct()
            .outerjoin(NoticeDept, Notice.id == NoticeDept.dept_id)
            .outerjoin(NoticeRole, Notice.id == NoticeRole.notice_id)
            .outerjoin(NoticeUserRead, Notice.id == NoticeUserRead.notice_id)
            .filter(*sa_filters)
            .subquery()
        )
        total_count: Optional[int] = await db.scalar(stmt_count)

        unread_stmt_count = select(func.count()).select_from(
            select(Notice.id)
            .distinct()
            .outerjoin(NoticeDept, Notice.id == NoticeDept.dept_id)
            .outerjoin(NoticeRole, Notice.id == NoticeRole.notice_id)
            .outerjoin(NoticeUserRead, Notice.id == NoticeUserRead.notice_id)
            .filter(NoticeUserRead.unread == True, *sa_filters)
            .subquery()
        )
        unread_count: Optional[int] = await db.scalar(unread_stmt_count)

        if is_paginated:
            return PageResponse.create(
                results=list_data,
                total=total_count,
                page=page,
                page_size=items_per_page,
                unread_count=unread_count,
            )
        return success_response(
            {"results": list_data, "total": total_count, "unread_count": unread_count}
        )  # pragma: no cover

    @classmethod
    async def save(
        cls,
        db: AsyncSession,
        item: BaseModel,
        request: Request,
        action: str,
        endpoint_creator: SenweaverEndpointCreator,
        id: Optional[int] = None,
        **kwargs,
    ):
        data = item.model_dump(exclude_unset=True)
        files = data.pop("files", None)
        notice_user = data.pop("notice_user", None)
        notice_dept = data.pop("notice_dept", None)
        notice_role = data.pop("notice_role", None)
        users = []
        depts = []
        roles = []
        file = []
        user_data = {}
        updated_time = datetime.now(timezone.utc)
        if request and hasattr(request, "user"):
            user_data["modifier_id"] = request.user.id
            user_data["updated_time"] = updated_time
            if action == "create":
                creator_data = request.auth.get_creator_data(Notice)
                user_data.update(creator_data)
        data.update(user_data)
        if files:
            for index, file in enumerate(files):
                if file.startswith("http"):
                    base_url = str(request.base_url)
                    files[index] = file.replace(
                        urljoin(base_url, f"{settings.UPLOAD_URL}/"), ""
                    )
            file_result = await db.execute(
                select(Attachment).where(Attachment.filepath.in_(files))
            )
            file = file_result.scalars().all()
        if notice_user:
            exist_read_users = {}
            if action == "update":
                user_ids = [user["id"] for user in notice_user]
                read_user_result = await db.execute(
                    select(NoticeUserRead).where(NoticeUserRead.owner_id.in_(user_ids))
                )
                read_users = read_user_result.scalars().all()
                exist_read_users = {user.owner_id: user for user in read_users}
            for owner in notice_user:
                owner_id = owner["id"]
                if owner_id in exist_read_users:
                    users.append(exist_read_users[owner_id])
                else:
                    read_user_data = {"owner_id": owner_id, "unread": True}
                    read_user_data.update(user_data)
                    users.append(NoticeUserRead(**read_user_data))
        if notice_dept:
            dept_ids = []
            for dept in notice_dept:
                dept_ids.append(dept["id"])
            dept_result = await db.execute(select(Dept).where(Dept.id.in_(dept_ids)))
            depts = dept_result.scalars().all()
        if notice_role:
            role_ids = []
            for role in notice_role:
                role_ids.append(role["id"])
            role_result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
            roles = role_result.scalars().all()

        if action == "create":
            notice = Notice(**data)
        elif action == "update":
            stmt = (
                select(Notice)
                .options(
                    selectinload(Notice.notice_user),
                    selectinload(Notice.notice_dept),
                    selectinload(Notice.notice_role),
                    selectinload(Notice.file),
                )
                .where(Notice.id == id)
            )
            result = await db.execute(stmt)
            notice = result.scalars().first()
            if not notice:
                raise NotFoundException("消息通知不存在")
            for k, v in data.items():
                if hasattr(notice, k):
                    setattr(notice, k, v)
        for read_user in users:
            read_user.notice = notice
        notice.notice_user = users
        notice.notice_dept = depts
        notice.notice_role = roles
        notice.file = file
        if action == "create":
            db.add(notice)
        await db.commit()
        data["id"] = notice.id
        return data

    @classmethod
    def add_custom_router(cls, endpoint_creator: SenweaverEndpointCreator):
        module = endpoint_creator.module
        self = endpoint_creator
        resource_name = endpoint_creator.resource_name
        router = self.router
        # endpoint_creator.add_custom_route(_unread)

        @router.get(f"{self.path}/unread", summary="未读消息")
        @requires_permissions(f"{module.get_auth_str(resource_name, "unread")}")
        async def _unread(
            request: Request, db: AsyncSession = Depends(self.get_session)
        ) -> ResponseBase:
            # TODO 未读
            filters = {"unread": True}
            data = {
                "results": [
                    {"key": "1", "name": "layout.notice", "list": [], "total": 0},
                    {"key": "2", "name": "layout.announcement", "list": [], "total": 0},
                ],
                "total": 0,
            }
            return success_response(data)


notice_logic = NoticeLogic()
