from datetime import datetime, timezone
from typing import Generic, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import ConfigDict
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import InstrumentedAttribute, declared_attr, relationship
from sqlmodel import BigInteger, Boolean, DateTime, ForeignKey, Relationship, String
from typing_extensions import Self

from config.settings import IdTypeEnum, settings
from senweaver.db import models
from senweaver.db.models import ChoiceType, Field, IntegerChoices, SQLModel
from senweaver.utils.snowflake import snowflake_id


class PKAutoMixin(SQLModel):
    id: Optional[int] = Field(
        default=None,
        title="ID",
        primary_key=True,
        nullable=False,
        sa_type=BigInteger,
        sa_column_kwargs={"autoincrement": True},
    )


class PKUuidMixin(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True, title="ID")


class PKSnowflakeMixin(SQLModel):
    id: int = Field(
        default_factory=snowflake_id,
        primary_key=True,
        title="ID",
        nullable=False,
        sa_type=BigInteger,
        sa_column_kwargs={"autoincrement": False},
    )


class PKCustomMixin(SQLModel):
    id: str = Field(
        primary_key=True,
        title="ID",
        nullable=False,
        sa_type=String(128),
        max_length=128,
        sa_column_kwargs={"comment": "ID", "autoincrement": False, "name": "id"},
    )


if settings.DATABASE_ID_TYPE == IdTypeEnum.AUTO:
    PKModel = PKAutoMixin
elif settings.DATABASE_ID_TYPE == IdTypeEnum.UUID:
    PKModel = PKUuidMixin
elif settings.DATABASE_ID_TYPE == IdTypeEnum.SNOWFLAKE:
    PKModel = PKSnowflakeMixin
else:
    raise NotImplementedError("Invalid DATABASE_ID_TYPE")


class PKMixin(PKModel):
    # model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    pass


class BaseMixin(SQLModel):
    created_time: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc), title="创建时间"
    )
    updated_time: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        title="更新时间",
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )
    description: Optional[str] = Field(
        default=None, title="描述", max_length=256, nullable=True
    )


class AuditMixin(SQLModel):
    creator_id: Optional[int] = Field(
        title="创建人ID", default=None, nullable=True, index=True, sa_type=BigInteger
    )
    modifier_id: Optional[int] = Field(
        title="修改人ID", default=None, nullable=True, index=True, sa_type=BigInteger
    )
    dept_belong_id: Optional[int] = Field(
        title="数据归属部门",
        default=None,
        nullable=True,
        index=True,
        sa_type=BigInteger,
    )

    model_config = ConfigDict(ignored_types=(declared_attr,))

    @declared_attr
    def creator(cls):
        return relationship(
            "User",
            primaryjoin=f"foreign({cls.__name__}.creator_id) == User.id",
            foreign_keys=cls.creator_id,
            lazy="noload",
            uselist=False,
        )

    @declared_attr
    def modifier(cls):
        return relationship(
            "User",
            primaryjoin=f"foreign({cls.__name__}.modifier_id) == User.id",
            foreign_keys=cls.modifier_id,
            lazy="noload",
            uselist=False,
        )

    @declared_attr
    def dept_belong(cls):
        return relationship(
            "Dept",
            primaryjoin=f"foreign({cls.__name__}.dept_belong_id) == Dept.id",
            foreign_keys=cls.dept_belong_id,
            lazy="noload",
            uselist=False,
        )


class SoftDeleteMixin(SQLModel):
    is_deleted: bool | None = Field(default=False, sa_type=Boolean, title="删除标志")
    deleted_time: Optional[datetime] = Field(default=None, title="删除时间")


class ModeTypeMixin(SQLModel):
    class ModeChoices(models.IntegerChoices):
        OR = 0, "或 (or) 模式"
        AND = 1, "且 (and) 模式"

    mode_type: Optional[Union[ModeChoices, int]] = Field(
        default=ModeChoices.OR,
        nullable=False,
        sa_type=ChoiceType(ModeChoices),
        title="权限模式",
        description="权限模式, 且模式表示数据需要同时满足规则列表中的每条规则，或模式即满足任意一条规则即可",
    )  #

    @property
    def get_mode_type_display(self):
        if self.mode_type is None:
            return ""
        if isinstance(self.mode_type, int):
            return ModeTypeMixin.ModeChoices(self.mode_type).label
        return self.mode_type.label


class UserRegMixin(SQLModel):
    username: str = Field(
        ...,
        min_length=2,
        max_length=32,
        sa_type=String(32),
        title="用户名",
        unique=True,
        index=True,
        regex="^[a-z0-9\u4e00-\u9fa5]+$",
        schema_extra={"example": "senweaver"},
    )
    nickname: Optional[str] = Field(
        default=None, max_length=150, sa_type=String(150), title="用户昵称"
    )
    phone: Optional[str] = Field(
        default=None,
        unique=True,
        max_length=16,
        sa_type=String(16),
        title="中国手机不带国家代码，国际手机号格式为：国家代码-手机号",
    )
    email: Optional[str] = Field(
        default=None,
        title="Email",
        sa_type=String(128),
        index=True,
        unique=True,
        nullable=True,
        schema_extra={"example": "senweaver@example.com"},
    )
    password: Optional[str] = Field(
        nullable=False, max_length=128, sa_type=String(128), title="密码"
    )


class UserMixin(ModeTypeMixin):
    class GenderChoices(IntegerChoices):
        UNKNOWN = 0, "未知"
        MALE = 1, "男"
        FEMALE = 2, "女"

    username: str = Field(
        ...,
        min_length=2,
        max_length=32,
        sa_type=String(32),
        title="用户名",
        description="必填；长度为150个字符或以下；只能包含字母、数字、特殊字符“@”、“.”、“-”和“_”。",
        unique=True,
        index=True,
        regex="^[a-z0-9\u4e00-\u9fa5]+$",
        schema_extra={"example": "senweaver"},
    )
    name: Optional[str] = Field(
        default=None, max_length=50, sa_type=String(50), title="姓名"
    )
    nickname: Optional[str] = Field(
        default=None, max_length=150, sa_type=String(150), title="用户昵称"
    )
    phone: Optional[str] = Field(
        default=None,
        unique=True,
        max_length=16,
        sa_type=String(16),
        title="手机",
        description="中国手机不带国家代码，国际手机号格式为：国家代码-手机号",
    )
    email: Optional[str] = Field(
        default=None,
        title="邮箱",
        sa_type=String(128),
        index=True,
        unique=True,
        nullable=True,
        regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        schema_extra={"example": "senweaver@example.com"},
    )
    password: Optional[str] = Field(
        nullable=False,
        max_length=128,
        sa_type=String(128),
        title="密码",
        sw_input_type="password",
    )
    password_time: Optional[datetime] = Field(default=None, title="密码修改时间")
    last_login: Optional[datetime] = Field(
        default=None, title="最后登录时间", sa_type=DateTime(timezone=True)
    )
    is_active: bool = Field(
        default=True,
        title="激活状态",
        description="指明用户是否被认为是活跃的。以反选代替删除帐号。",
    )
    avatar: Optional[str] = Field(
        default=None,
        max_length=255,
        sa_type=String(255),
        title="头像",
        sw_input_type="image upload",
    )
    gender: Union[GenderChoices, int] = Field(
        default=GenderChoices.UNKNOWN,
        sa_type=ChoiceType(GenderChoices),
        nullable=True,
        title="性别",
    )
    dept_id: int = Field(
        default=None, sa_type=BigInteger, nullable=True, index=True, title="部门id"
    )
    group_id: int = Field(default=None, nullable=True, title="分组id")

    @property
    def is_authenticated(self) -> bool:
        return not self.delete_time and self.is_active

    @property
    def display_name(self) -> str:
        return self.nickname or self.username

    @property
    def identity(self) -> str:
        return self.username
