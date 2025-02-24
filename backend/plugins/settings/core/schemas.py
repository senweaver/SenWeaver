# -*- coding: utf-8 -*-
from typing import Any, List, Optional, Union

from pydantic import BaseModel, EmailStr, Field, HttpUrl, SecretStr, field_validator

from senweaver.db import models


class ISettingData(BaseModel):
    name: str
    value: Any


class IBasicSet(BaseModel):
    SITE_URL: Optional[HttpUrl] = Field(
        default="http://127.0.0.1",
        title="当前站点 URL",
        description="站点 URL 是当前产品服务的外部可访问地址，通常在系统邮件中的链接中使用",
    )
    FRONT_END_WEB_WATERMARK_ENABLED: Optional[bool] = Field(
        default=False,
        title="前端页面水印",
        description="开启前端页面水印",
    )

    PERMISSION_FIELD_ENABLED: Optional[bool] = Field(
        default=True,
        title="字段权限",
        description="字段权限用于授权访问数据字段展示",
    )

    PERMISSION_DATA_ENABLED: Optional[bool] = Field(
        default=True,
        title="数据权限",
        description="数据权限用于授权访问数据",
    )

    EXPORT_MAX_LIMIT: Optional[int] = Field(
        default=20000,
        title="数据导出限制",
        description="导出数据最大行数限制",
    )

    @field_validator("SITE_URL", mode="before")
    def check_SITE_URL(cls, v):
        if not v:
            return "http://127.0.0.1"
        return v.strip("/")


class IRegisterAuthSet(BaseModel):
    SECURITY_REGISTER_ACCESS_ENABLED: bool = Field(
        default=True, title="允许注册", description="允许用户进行注册"
    )

    SECURITY_REGISTER_CAPTCHA_ENABLED: bool = Field(
        default=True,
        title="注册图片验证码",
        description="开启图片验证码，防止机器人注册",
    )

    SECURITY_REGISTER_ENCRYPTED_ENABLED: bool = Field(
        default=True, title="注册信息加密", description="开启敏感信息加密，防止数据泄露"
    )

    SECURITY_REGISTER_TEMP_TOKEN_ENABLED: bool = Field(
        default=True, title="注册临时令牌", description="开启临时令牌，防止被攻击"
    )

    SECURITY_REGISTER_BY_EMAIL_ENABLED: bool = Field(
        default=True, title="通过邮件注册", description="允许用户通过发送邮件验证码"
    )

    SECURITY_REGISTER_BY_SMS_ENABLED: bool = Field(
        default=True, title="通过手机注册", description="允许用户通过发送短信验证码"
    )

    SECURITY_REGISTER_BY_BASIC_ENABLED: bool = Field(
        default=True,
        title="通过用户名密码注册",
        description="E允许用户通过用户名密码注册",
    )


class IResetAuthSet(BaseModel):
    SECURITY_RESET_PASSWORD_ACCESS_ENABLED: Optional[bool] = Field(
        default=True, title="允许重置密码", description="允许用户重置密码"
    )

    SECURITY_RESET_PASSWORD_CAPTCHA_ENABLED: Optional[bool] = Field(
        default=True,
        title="重置密码图片验证码",
        description="开启图片验证码，防止机器人重置密码",
    )

    SECURITY_RESET_PASSWORD_ENCRYPTED_ENABLED: Optional[bool] = Field(
        default=True,
        title="重置密码信息加密",
        description="开启敏感信息加密，防止数据泄露",
    )

    SECURITY_RESET_PASSWORD_TEMP_TOKEN_ENABLED: Optional[bool] = Field(
        default=True, title="重置密码临时令牌", description="开启临时令牌，防止被攻击"
    )

    SECURITY_RESET_PASSWORD_BY_EMAIL_ENABLED: Optional[bool] = Field(
        default=True, title="通过邮件重置密码", description="允许用户通过发送邮件验证码"
    )

    SECURITY_RESET_PASSWORD_BY_SMS_ENABLED: Optional[bool] = Field(
        default=True, title="通过短信重置密码", description="允许用户通过发送短信验证码"
    )


class ISmsSet(BaseModel):
    SMS_ENABLED: bool
    SMS_BACKEND: str


class ISMSConfig(BaseModel):
    code: str = Field(..., description="国家代码")
    phone: str = Field(default="", description="手机号")


class ISmsConfigModel(BaseModel):
    SMS_TEST_PHONE: ISMSConfig = Field(..., description="短信测试配置")
    ALIBABA_ACCESS_KEY_ID: str = Field(..., description="阿里巴巴访问密钥ID")
    ALIBABA_VERIFY_SIGN_NAME: str = Field(..., description="阿里巴巴验证签名名称")
    ALIBABA_VERIFY_TEMPLATE_CODE: str = Field(..., description="阿里巴巴验证模板代码")


class IVerifySet(BaseModel):
    VERIFY_CODE_TTL: int = Field(
        default=300,
        ge=5,
        le=60 * 60 * 10,
        title="验证码有效时间 (秒)",
        description="验证码过期时间",
    )

    VERIFY_CODE_LIMIT: int = Field(
        default=60,
        ge=5,
        le=60 * 60 * 10,
        title="验证码速率限制 (秒)",
        description="验证码发送速率限制",
    )

    VERIFY_CODE_LENGTH: Optional[int] = Field(
        default=6, ge=4, le=16, title="验证码长度", description="发送验证码的长度"
    )

    VERIFY_CODE_UPPER_CASE: Optional[bool] = Field(default=False, title="大写字母")

    VERIFY_CODE_LOWER_CASE: Optional[bool] = Field(default=False, title="小写字母")

    VERIFY_CODE_DIGIT_CASE: Optional[bool] = Field(default=True, title="数字")


class IEmailSet(BaseModel):
    EMAIL_ENABLED: Optional[bool] = Field(
        default=False, title="邮件", description="启用邮件服务 (Email)"
    )

    EMAIL_HOST: str = Field(default="", title="主机", examples=[""], max_length=1024)

    EMAIL_PORT: str = Field(default="465", title="端口", examples=["465"], max_length=5)

    EMAIL_HOST_USER: Optional[EmailStr] = Field(
        default=None,
        title="账号",
        description="登录到邮件服务器的用户名。这通常是你的邮件地址",
        max_length=128,
    )

    EMAIL_HOST_PASSWORD: Optional[SecretStr] = Field(
        default=None,
        title="密码",
        description="登录到邮件服务器的密码",
        write_only=True,
    )

    EMAIL_FROM: Optional[str] = Field(
        default=None,
        title="发件人",
        description="发件人电子邮件地址（默认使用“SenWeaver”）",
        max_length=128,
    )

    EMAIL_SUBJECT_PREFIX: Optional[str] = Field(
        default="SenWeaver",
        title="主题前缀",
        examples=["SenWeaver"],
        description="发送邮件的主题行前缀",
        max_length=128,
    )

    EMAIL_USE_SSL: Optional[bool] = Field(
        default=False,
        title="使用SSL",
        description="与 SMTP 服务器通信时是否使用隐式 TLS（安全）连接。在大多数电子邮件文档中，这种类型的 TLS 连接称为 SSL。它通常在端口 465 上使用",
    )

    EMAIL_USE_TLS: Optional[bool] = Field(
        default=False,
        title="使用 TLS",
        description="与 SMTP 服务器通信时是否使用 TLS（安全）连接。这用于显式 TLS 连接，通常在端口 587 上",
    )

    EMAIL_RECIPIENT: Optional[EmailStr] = Field(
        default=None, title="收件人", description="收件人用于测试电子邮件服务器的连通性"
    )


class ICaptchaSet(BaseModel):
    class ChallengeChoices(models.TextChoices):
        RANDOM_CHAR = "captcha.helpers.random_char_challenge", "随机字符串"
        MATH_CHALLENGE = "captcha.helpers.math_challenge", "数学运算"

    class NoiseFunctionsChoices(models.TextChoices):
        FUNCTION_NULL = "captcha.helpers.noise_null", "无噪声函数"
        FUNCTION_ARCS = "captcha.helpers.noise_arcs", "弧噪声函数"
        FUNCTION_DOTS = "captcha.helpers.noise_dots", "点噪声函数"

    CAPTCHA_CHALLENGE_FUNCT: Optional[str] = Field(
        default=ChallengeChoices.MATH_CHALLENGE,
        title="图片算法模式",
        description="图片验证码生成的算法模式",
        json_schema_extra={
            "input_type": "choice",
            "choices": [
                {"value": choice.value, "label": choice.label}
                for choice in ChallengeChoices
            ],
        },
    )

    CAPTCHA_LENGTH: Optional[int] = Field(
        default=4, ge=2, le=16, title="验证码长度", description="图片验证码长度"
    )

    CAPTCHA_FONT_SIZE: Optional[int] = Field(
        default=26,
        ge=10,
        le=50,
        title="验证码字体大小",
        description="图片验证码字体大小",
    )

    CAPTCHA_TIMEOUT: int = Field(
        default=5,
        ge=1,
        le=60 * 24 * 7,
        title="验证码过期时间 (分)",
        description="图片验证码过期时间",
    )

    CAPTCHA_BACKGROUND_COLOR: str = Field(
        default="#ffffff",
        title="验证码背景色",
        max_length=256,
        json_schema_extra={"input_type": "color"},
    )

    CAPTCHA_FOREGROUND_COLOR: str = Field(
        default="#001100",
        title="验证码字体色",
        max_length=256,
        json_schema_extra={"input_type": "color"},
    )

    CAPTCHA_NOISE_FUNCTIONS: Any = Field(
        default=[
            NoiseFunctionsChoices.FUNCTION_ARCS,
            NoiseFunctionsChoices.FUNCTION_DOTS,
        ],
        title="噪声函数",
        json_schema_extra={
            "input_type": "multiple choice",
            "choices": [
                {"value": choice.value, "label": choice.label}
                for choice in NoiseFunctionsChoices
            ],
        },
    )


class IBindPhoneSet(BaseModel):
    ECURITY_BIND_PHONE_ACCESS_ENABLED: Optional[bool] = Field(
        default=True, title="绑定手机", description="允许用户绑定手机"
    )

    SECURITY_BIND_PHONE_CAPTCHA_ENABLED: Optional[bool] = Field(
        default=True,
        title="绑定手机图片验证码",
        description="开启图片验证码，防止机器人重置密码",
    )

    SECURITY_BIND_PHONE_ENCRYPTED_ENABLED: Optional[bool] = Field(
        default=True,
        title="绑定手机信息加密",
        description="开启敏感信息加密，防止数据泄露",
    )

    SECURITY_BIND_PHONE_TEMP_TOKEN_ENABLED: Optional[bool] = Field(
        default=True, title="绑定手机临时令牌", description="开启临时令牌，防止被攻击"
    )


class IBindEmailSet(BaseModel):
    SECURITY_BIND_EMAIL_ACCESS_ENABLED: Optional[bool] = Field(
        default=True, title="绑定邮件", description="允许用户进行绑定邮件"
    )

    SECURITY_BIND_EMAIL_CAPTCHA_ENABLED: Optional[bool] = Field(
        default=True,
        title="绑定邮件图片验证码",
        description="开启图片验证码，防止机器人重置密码",
    )

    SECURITY_BIND_EMAIL_TEMP_TOKEN_ENABLED: Optional[bool] = Field(
        default=True, title="绑定邮件临时令牌", description="开启临时令牌，防止被攻击"
    )

    SECURITY_BIND_EMAIL_ENCRYPTED_ENABLED: Optional[bool] = Field(
        default=True,
        title="绑定邮件信息加密",
        description="开启敏感信息加密，防止数据泄露",
    )


class IPasswordSet(BaseModel):
    SECURITY_PASSWORD_MIN_LENGTH: int = Field(
        default=6, ge=6, le=30, title="密码最小长度"
    )
    SECURITY_ADMIN_USER_PASSWORD_MIN_LENGTH: int = Field(
        default=6, ge=6, le=30, title="管理员密码最小长度"
    )
    SECURITY_PASSWORD_UPPER_CASE: Optional[bool] = Field(
        default=False, title="大写字母"
    )
    SECURITY_PASSWORD_LOWER_CASE: Optional[bool] = Field(
        default=False, title="小写字母"
    )
    SECURITY_PASSWORD_NUMBER: Optional[bool] = Field(default=False, title="数字")
    SECURITY_PASSWORD_SPECIAL_CHAR: Optional[bool] = Field(
        default=False, title="必须包含特殊字符"
    )


class ILoginLimitSet(BaseModel):

    SECURITY_CHECK_DIFFERENT_CITY_LOGIN: Optional[bool] = Field(
        default=True,
        title="异地登录通知",
        description="根据登录 IP 是否所属常用登录城市进行判断，若账号在非常用城市登录，会发送异地登录提醒",
    )
    SECURITY_LOGIN_LIMIT_COUNT: int = Field(
        default=7, ge=3, le=99999, title="限制用户登录失败次数"
    )
    SECURITY_LOGIN_LIMIT_TIME: int = Field(
        default=30,
        ge=5,
        le=99999,
        title="禁止用户登录间隔 (分)",
        description="当用户登录失败次数达到限制后，那么在此间隔内禁止登录",
    )
    SECURITY_LOGIN_IP_LIMIT_COUNT: int = Field(
        default=50, ge=3, le=99999, title="限制 IP 登录失败次数"
    )
    SECURITY_LOGIN_IP_LIMIT_TIME: int = Field(
        default=30,
        ge=5,
        le=99999,
        title="禁止 IP 登录间隔 (分)",
        description="当用户登录失败次数达到限制后，那么在此间隔内禁止登录",
    )
    SECURITY_LOGIN_IP_WHITE_LIST: Optional[List[str]] = Field(
        default=[],
        title="IP 登录白名单",
        description="* 表示匹配所有。例如: 192.168.10.1, 192.168.1.0/24, 10.1.1.1-10.1.1.20, 2001:db8:2de::e13, 2001:db8:1a:1110::/64  (支持网域)",
    )
    SECURITY_LOGIN_IP_BLACK_LIST: Optional[List[str]] = Field(
        default=[],
        title="IP 登录黑名单",
        description="* 表示匹配所有。例如: 192.168.10.1, 192.168.1.0/24, 10.1.1.1-10.1.1.20, 2001:db8:2de::e13, 2001:db8:1a:1110::/64  (支持网域)",
    )


class ILoginAuthSet(BaseModel):
    SECURITY_LOGIN_ACCESS_ENABLED: Optional[bool] = Field(
        default=True, title="允许登录", description="允许用户进行登录"
    )

    SECURITY_LOGIN_CAPTCHA_ENABLED: Optional[bool] = Field(
        default=True,
        title="登录图片验证码",
        description="开启图片验证码，防止机器人登录",
    )

    SECURITY_LOGIN_ENCRYPTED_ENABLED: Optional[bool] = Field(
        default=True, title="登录信息加密", description="开启敏感信息加密，防止数据泄露"
    )

    SECURITY_LOGIN_TEMP_TOKEN_ENABLED: Optional[bool] = Field(
        default=True, title="登录临时令牌", description="开启临时令牌，防止被攻击"
    )

    SECURITY_LOGIN_BY_EMAIL_ENABLED: Optional[bool] = Field(
        default=True, title="通过邮件登录", description="允许用户通过发送邮件验证码"
    )

    SECURITY_LOGIN_BY_SMS_ENABLED: Optional[bool] = Field(
        default=False, title="通过手机登录", description="允许用户通过发送短信验证码"
    )

    SECURITY_LOGIN_BY_BASIC_ENABLED: Optional[bool] = Field(
        default=True,
        title="通过用户名密码登录",
        description="允许用户通过用户名密码登录",
    )
