from typing import Optional
from urllib.parse import urljoin

from sqlalchemy import Boolean, Integer, String

from config.settings import settings
from senweaver.core.models import AuditMixin, BaseMixin, PKMixin
from senweaver.db.models import Field
from senweaver.utils.globals import g
from senweaver.utils.partial import optional


class AttachmentBase(BaseMixin):
    storage: Optional[str] = Field(
        default=None,
        sa_type=String(100),
        title="存储引擎",
        index=True,
        sa_column_kwargs={"server_default": "local"},
    )

    bucket: Optional[str] = Field(default=None, sa_type=String(100), title="存储桶")
    category: Optional[str] = Field(default=None, sa_type=String(50), title="分类")
    filename: str = Field(default=None, sa_type=String(200), title="文件名称")
    suffix: str = Field(default=None, sa_type=String(20), title="文件后缀")
    filesize: int = Field(default=None, sa_type=Integer, title="文件大小")
    filepath: Optional[str] = Field(
        default=None, sa_type=String(255), index=True, title="文件路径"
    )
    file_url: Optional[str] = Field(
        default=None,
        sa_type=String(255),
        title="网络地址",
        description="一般为外部互联网可以访问的地址",
    )
    mime_type: str = Field(default=None, sa_type=String(100), title="文件类型")
    hash: str = Field(default=None, sa_type=String(255), title="文件哈希")
    is_tmp: bool = Field(
        default=False,
        title="临时文件",
        sa_type=Boolean,
        description="临时文件会被定时任务自动清理",
    )
    is_upload: bool = Field(default=False, title="上传文件", sa_type=Boolean)

    @property
    def access_url(self) -> str:
        """访问地址"""
        if self.file_url:
            return self.file_url
        if g.request:
            return urljoin(
                str(g.request.base_url), f"{settings.UPLOAD_URL}/{self.filepath}"
            )
        return self.filename


class Attachment(AuditMixin, AttachmentBase, PKMixin, table=True):
    __tablename__ = "system_attachment"
    __table_args__ = {"comment": "文件信息"}


@optional()
class AttachmentRead(AuditMixin, AttachmentBase, PKMixin):
    pass


class AttachmentCreate(AttachmentBase):
    pass


class AttachmentCreateInternal(AttachmentBase):
    pass


@optional()
class AttachmentUpdate(AttachmentBase):
    pass


class AttachmentUpdateInternal(AttachmentUpdate):
    pass
