from typing import Any, Optional, Union

from pydantic import model_validator
from sqlalchemy import JSON, TEXT, Boolean, String
from sqlmodel import Relationship

from app.system.model import Attachment, Dept, Role, User
from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db import models
from senweaver.db.models import ChoiceType, Field
from senweaver.utils.partial import optional
from senweaver.utils.translation import _

from .notice_dept import NoticeDept
from .notice_file import NoticeFile
from .notice_role import NoticeRole
from .notice_user_read import NoticeUserRead


class NoticeBase(BaseMixin):
    class NoticeChoices(models.IntegerChoices):
        SYSTEM = 0, "系统通知"
        NOTICE = 1, "系统公告"
        USER = 2, "用户通知"
        DEPT = 3, "部门通知"
        ROLE = 4, "角色通知"

    class LevelChoices(models.TextChoices):
        DEFAULT = "info", "普遍通知"
        PRIMARY = "primary", "一般通知"
        SUCCESS = "success", "成功通知"
        DANGER = "danger", "重要通知"

    level: LevelChoices = Field(
        default=LevelChoices.DEFAULT,
        max_length=20,
        index=True,
        nullable=False,
        sa_type=ChoiceType(LevelChoices),
        title="通知级别",
    )
    notice_type: NoticeChoices = Field(
        default=NoticeChoices.USER,
        index=True,
        nullable=False,
        sa_type=ChoiceType(NoticeChoices),
        title="通知类型",
    )

    title: Optional[str] = Field(
        default=None, title="通知标题", nullable=False, sa_type=String(255)
    )

    message: Optional[str] = Field(default=None, sa_type=TEXT, title="通知内容")
    extra_json: Any = Field(
        default=None, sa_type=JSON, title="额外的Json数据", nullable=True
    )
    publish: Optional[bool] = Field(default=True, sa_type=Boolean, title="发布")

    @classmethod
    def get_user_choices(cls):
        return [cls.NoticeChoices.USER, cls.NoticeChoices.SYSTEM]

    @classmethod
    def get_notice_choices(cls):
        return [
            cls.NoticeChoices.NOTICE,
            cls.NoticeChoices.DEPT,
            cls.NoticeChoices.ROLE,
        ]


class Notice(AuditMixin, NoticeBase, PKMixin, table=True):
    __tablename__ = "notifications_notice"
    __table_args__ = ({"comment": "消息内容"},)
    file: list["Attachment"] = Relationship(
        link_model=NoticeFile,
        sa_relationship_kwargs=dict(
            primaryjoin="NoticeFile.notice_id==Notice.id",
            secondaryjoin="NoticeFile.attachment_id==Attachment.id",
            foreign_keys="[NoticeFile.notice_id,NoticeFile.attachment_id]",
        ),
    )
    notice_user: list["NoticeUserRead"] = Relationship(
        sa_relationship_kwargs=dict(
            back_populates="notice",
            primaryjoin="NoticeUserRead.notice_id==Notice.id",
            foreign_keys="[NoticeUserRead.notice_id]",
        )
    )
    notice_dept: list["Dept"] = Relationship(
        link_model=NoticeDept,
        sa_relationship_kwargs=dict(
            primaryjoin="NoticeDept.notice_id==Notice.id",
            secondaryjoin="NoticeDept.dept_id==Dept.id",
            foreign_keys="[NoticeDept.notice_id,NoticeDept.dept_id]",
        ),
    )
    notice_role: list["Role"] = Relationship(
        link_model=NoticeRole,
        sa_relationship_kwargs=dict(
            primaryjoin="NoticeRole.notice_id==Notice.id",
            secondaryjoin="NoticeRole.role_id==Role.id",
            foreign_keys="[NoticeRole.notice_id,NoticeRole.role_id]",
        ),
    )


@optional()
class NoticeRead(AuditMixin, NoticeBase, PKMixin):
    pass


class NoticeCreate(NoticeBase):
    pass


class NoticeCreateInternal(NoticeBase):
    pass


@optional()
class NoticeUpdate(NoticeBase):
    pass


class NoticeUpdateInternal(NoticeUpdate):
    pass
