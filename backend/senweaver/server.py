import gc
from contextlib import asynccontextmanager
from typing import Any

import typer
import uvicorn
from config.settings import EnvironmentEnum, settings
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_limiter import FastAPILimiter
from fastapi_offline import FastAPIOffline
from senweaver.db.session import create_redis_pool
from senweaver.exception.exception_handler import register_exception
from senweaver.middleware.access import AccessMiddleware
from senweaver.middleware.db import SQLAlchemyMiddleware
from senweaver.module.manager import module_manager
from senweaver.utils.globals import GlobalsMiddleware, g
from senweaver.utils.request import get_request_identifier
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    redis_client = await create_redis_pool()
    app.state.redis = redis_client

    # cache
    FastAPICache.init(
        RedisBackend(redis_client),
        prefix=f"{settings.NAME.lower()}-cache",
        cache_status_header="X-SenWeaver-Cache",
    )
    await FastAPILimiter.init(
        redis_client,
        prefix=f"{settings.NAME.lower()}-limiter",
        identifier=get_request_identifier,
    )

    yield
    # shutdown
    await FastAPICache.clear()
    # close limiter
    await FastAPILimiter.close()
    # close redis
    await redis_client.close()
    g.cleanup()
    gc.collect()


def start_command(cli_app: typer.Typer):
    from app.app import command as app_command
    from plugins.plugins import command as plugin_command

    app_command(cli_app)
    plugin_command(cli_app)


def create_app(*args: Any, **kwargs: Any):
    # FastAPI
    app = FastAPIOffline(
        title=settings.TITLE,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
        docs_url=settings.DOCS_URL,
        redoc_url=settings.REDOCS_URL,
        openapi_url=settings.OPENAPI_URL,
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
    )
    module_manager.start(app)
    # swagger offline
    if settings.UPLOAD_PATH.exists():
        static_file_path = settings.UPLOAD_PATH.as_posix()
        app.mount(
            settings.UPLOAD_URL,
            StaticFiles(directory=static_file_path, html=True),
            name=f"senweaver_uploads",
        )

    # middleware
    register_middleware(app)

    # global exception handler
    register_exception(app)

    @app.get("/", include_in_schema=False)
    async def root():
        """
        An example "Hello SenWeaver" FastAPI route.
        """
        return {"msg": "Hello SenWeaver"}

    # routes
    from app.app import startup as app_startup
    from plugins.plugins import startup as plugin_startup
    from vendor.vendor import startup as vendor_startup

    app_startup(app)
    plugin_startup(app)
    vendor_startup(app)

    init_path()
    module_manager.run()
    return app


def init_path():
    pass
    # # 假设 settings.VENDOR_PATH 是你要使用的路径
    # vendor_path = Path(settings.VENDOR_PATH)

    # # 构建 pypi_path 并插入 sys.path
    # pypi_path = vendor_path / "pypi"
    # sys.path.insert(0, str(pypi_path))

    # # 遍历 VENDOR_PATH 中的所有包目录并插入 sys.path
    # for package in vendor_path.iterdir():
    #     if package.is_dir():
    #         sys.path.insert(0, str(package))


def register_middleware(app: FastAPI):
    # Gzip
    if settings.MIDDLEWARE_GZIP:
        from fastapi.middleware.gzip import GZipMiddleware

        app.add_middleware(GZipMiddleware)

    from senweaver.middleware.file import FileMiddleware

    app.add_middleware(FileMiddleware)

    # JWT auth,required
    module_manager.auth_module.start(app)

    app.add_middleware(
        SQLAlchemyMiddleware,
        db_url=str(settings.DATABASE_URL),
        engine_args={
            "echo": True,  # 打印SQL语句
            "future": True,
            "poolclass": (
                NullPool
                if settings.ENVIRONMENT == EnvironmentEnum.DEVELOPMENT
                else AsyncAdaptedQueuePool
            ),
            "pool_pre_ping": True,
            # "pool_size": settings.POOL_SIZE,
            # "max_overflow": 64,
        },
    )
    app.add_middleware(GlobalsMiddleware)
    app.add_middleware(AccessMiddleware)
    # CORS
    if settings.CORS_ENABLE:
        origins = []
        for origin in settings.CORS_ALLOW_ORIGINS.split(","):
            origins.append(origin.strip())
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        )


def run_app():
    uvicorn.run(
        app="senweaver.server:create_app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_RELOAD,
    )
