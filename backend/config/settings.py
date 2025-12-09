import secrets
from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class IdTypeEnum(Enum):
    AUTO = "auto"
    UUID = "uuid"
    SNOWFLAKE = "snowflake"
    CUSTOM = "custom"


class EnvironmentEnum(str, Enum):
    DEVELOPMENT = "dev"
    TEST = "test"
    PRODUCTION = "prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        env_file_encoding="utf-8",
        extra="ignore",
    )
    # Path
    ROOT_PATH: Path = Path(__file__).resolve().parent.parent
    APP_PATH: Path = ROOT_PATH.joinpath("app")
    DATA_PATH: Path = ROOT_PATH.joinpath("data")
    PUBLIC_URL: str = "/static"
    PUBLIC_PATH: Path = ROOT_PATH.joinpath("public")
    PLUGIN_PATH: Path = ROOT_PATH.joinpath("plugins")
    VENDOR_PATH: Path = ROOT_PATH.joinpath("vendor")
    LOG_PATH: Path = DATA_PATH.joinpath("logs")
    UPLOAD_PATH: Path = DATA_PATH.joinpath("uploads")
    UPLOAD_URL: str = "/uploads"
    UPLOAD_PUBLIC_URL: str = f"{UPLOAD_URL}/public"

    # FastApi Project
    NAME: str = "SenWeaver"
    VERSION: str = "0.1.0"
    TITLE: str = "SenWeaver"
    DESCRIPTION: str = "Description"
    DOCS_URL: str | None = "/docs"
    REDOCS_URL: str | None = "/redocs"
    OPENAPI_URL: str | None = "/openapi.json"

    # Uvicorn
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_RELOAD: bool = False

    # Env Config
    ENVIRONMENT: EnvironmentEnum = EnvironmentEnum.DEVELOPMENT
    DEMO_MODE: bool = False
    DEMO_MODE_WHITE_ROUTES: set[tuple[str, str]] = {
        ("POST", "/system/login/basic"),
        ("POST", "/system/logout"),
        ("GET", "/auth/captcha"),
    }
    # Database
    DATABASE_ID_TYPE: IdTypeEnum = IdTypeEnum.SNOWFLAKE
    DATABASE_URL: str
    POOL_SIZE: int = 5
    # Redis
    REDIS_ENABLE: bool = False
    REDIS_URL: str  # redis://:pass@localhost:port/dbname

    # CAPTCHA
    CAPTCHA_ENABLE: bool = False
    CAPTCHA_EXPIRE_SECONDS: int = 60

    # Middleware
    MIDDLEWARE_GZIP: bool = False
    MIDDLEWARE_ACCESS: bool = True
    MIDDLEWARE_OPERATION: bool = False

    # Request ID
    TRACE_ID_REQUEST_HEADER_KEY: str = "X-Request-ID"
    # Token
    ALGORITHM: str = "HS256"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    TOKEN_REFRESH_EXPIRE_MINUTES: int = 60 * 24 * 15  # 刷新过期时间，单位：秒
    AUTH_ENGINE: str = "app.system.core.auth.SystemAuthManager"  # 授权验证
    # CORS
    CORS_ENABLE: bool = True  # 是否启用跨域
    CORS_ALLOW_ORIGINS: str  # 只允许访问的域名
    CORS_ALLOW_CREDENTIALS: bool = True  # 是否支持携带 cookie
    CORS_ALLOW_METHODS: list[str] = ["*"]  # 设置允许跨域的http方法，比如 get、post等。
    CORS_ALLOW_HEADERS: list[str] = ["*"]  # 允许携带的headers，可以用来鉴别来源等作用。


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = Settings()
