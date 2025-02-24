import asyncio
import pathlib
import sys
from logging.config import fileConfig

from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql.schema import Index
from sqlmodel import SQLModel

from alembic import context
from app.system.model import *
from plugins.notifications.model import *
from plugins.settings.model import *

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

db_url = config.get_main_option("sqlalchemy.url")
# from config.settings import settings
# db_url = settings.DATABASE_URL

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

# 设置命名约定
naming_convention = {
    "ix": "ix_%(column_0_label)s",  # 索引
    "uq": "uq_%(table_name)s_%(column_0_name)s",  # 唯一约束
    "ck": "ck_%(table_name)s_%(constraint_name)s",  # 检查约束
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",  # 外键
    "pk": "pk_%(table_name)s",  # 主键
}

# 创建带有命名约定的元数据对象
target_metadata = SQLModel.metadata
target_metadata.naming_convention = naming_convention

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# 从 alembic.ini 中读取 'remove_foreign_keys' 配置（默认为 'true'）
remove_foreign_keys = (
    config.get_main_option("remove_foreign_keys", "false").lower() == "true"
)


def include_object(object, name, type_, reflected, compare_to):
    # 如果是索引类型，检查索引中的列是否含有外键
    if (
        remove_foreign_keys
        and isinstance(object, Index)
        and any(
            isinstance(col.foreign_keys, set) and col.foreign_keys
            for col in object.columns
        )
    ):
        return False  # 排除包含外键的索引
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = create_async_engine(db_url, echo=True, future=True)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
