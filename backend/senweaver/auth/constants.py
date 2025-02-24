from enum import Enum

from senweaver.db.models import IntegerChoices


class Logical(str, Enum):
    AND = "and"
    OR = "or"


class LoginTypeChoices(IntegerChoices):
    USERNAME = 0, "用户名和密码"
    SMS = 1, "短信验证"
    EMAIL = 2, "邮箱验证"
    WECHAT = 4, "微信扫码"
    UNKNOWN = 9, "未知"


SENWEAVER_GUEST = "__senweaver_guest__"
SENWEAVER_ROLES = "__senweaver_roles__"
SENWEAVER_ROLE_IDS = "__senweaver_role_ids__"
SENWEAVER_PERMS = "__senweaver_perms__"
SENWEAVER_MENUS = "__senweaver_menus__"
SENWEAVER_REQ_MENU = "__senweaver_req_menu__"
SENWEAVER_SUPERUSER = "__senweaver_superuser__"
SENWEAVER_FILTERS = "__senweaver_filters__"
SENWEAVER_FIELDS = "__senweaver_fields__"
SENWEAVER_SCOPE_TYPE = "__senweaver_scope_type__"
SENWEAVER_SCOPES = "__senweaver_scopes__"
SENWEAVER_CHECK_DATA_SCOPE = "__senweaver_check_data_scope__"
SENWEAVER_CHECK_FIELD_SCOPE = "__senweaver_check_field_scope__"
