import json
from typing import Annotated

from fastapi import Path, Request
from fastcrud import FastCRUD
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from senweaver.auth.security import requires_permissions
from senweaver.core.senweaver_creator import SenweaverEndpointCreator
from senweaver.core.senweaver_crud import SenweaverCRUD
from senweaver.exception.http_exception import NotFoundException
from senweaver.utils.response import ResponseBase, success_response

from ..model.data_permission import DataPermission
from ..model.dept import Dept
from ..model.role import Role
from ..model.user import User
from ..schema.dept import IDeptEmpower


class DeptLogic:

    @classmethod
    async def get_user_count(cls, db: AsyncSession, obj: Dept, key: str, **kwargs):
        count = await SenweaverCRUD(User).count(db, dept_id=obj.id, is_deleted=False)
        return count

    @classmethod
    async def save_empower_data(
        cls, request: Request, dept_id: int, data: IDeptEmpower
    ):
        db: AsyncSession = request.auth.db.session
        stmt = (
            select(Dept)
            .options(selectinload(Dept.roles))
            .options(selectinload(Dept.rules))
            .where(Dept.id == dept_id)
        )
        db_row = await db.execute(stmt)
        dept = db_row.scalars().first()
        if not dept:
            raise NotFoundException(f"{Dept.__name__}{dept_id} not found")
        role_ids = [role.id for role in data.roles]
        rule_ids = [rule.id for rule in data.rules]
        role_result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
        rule_result = await db.execute(
            select(DataPermission).where(DataPermission.id.in_(rule_ids))
        )
        dept.roles = role_result.scalars().all()
        dept.rules = rule_result.scalars().all()
        dept.mode_type = data.mode_type
        await db.flush()
        await db.commit()

    @classmethod
    async def get_dept_tree_ids(
        cls,
        db: AsyncSession,
        dept_id: int,
        dept_all_list=None,
        dept_list=None,
        is_parent=False,
    ):
        parent = "parent_id"
        pk = "id"
        if is_parent:
            parent, pk = pk, parent

        if dept_all_list is None:
            dept_result = await FastCRUD(Dept).get_multi(
                db, limit=None, return_total_count=False, is_active=True
            )
            dept_all_list = dept_result["data"]
            dept_all_list = [
                {"id": d["id"], "parent_id": d["parent_id"]} for d in dept_all_list
            ]

        if dept_list is None:
            dept_list = [dept_id]

        for dept in dept_all_list:
            if dept.get(parent) == dept_id:
                if dept.get(pk):
                    dept_list.append(dept.get(pk))
                    await cls.get_dept_tree_ids(
                        db, dept.get(pk), dept_all_list, dept_list, is_parent
                    )
        return json.loads(json.dumps(list(set(dept_list))))

    @classmethod
    def add_custom_router(cls, endpoint_creator: SenweaverEndpointCreator):
        self = endpoint_creator
        router = self.router
        module = self.module

        @router.post(self.path + "/{id}/empower", summary="分配部门角色-数据权限")
        @requires_permissions(f"{module.get_auth_str(self.resource_name, "empower")}")
        async def empower(
            id: Annotated[int, Path(...)],
            data: IDeptEmpower,
            request: Request,
        ) -> ResponseBase:
            await DeptLogic.save_empower_data(request, id, data)
            return success_response()


dept_logic = DeptLogic()
