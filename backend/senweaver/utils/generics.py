from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.types import TIMESTAMP, BigInteger, String, TypeDecorator

from senweaver.utils.snowflake import snowflake_id


class SnowflakeID(TypeDecorator):
    impl = BigInteger

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is None:
            value = snowflake_id()
        return value

    def process_result_value(self, value, dialect):
        return value


class DateTimeType(TypeDecorator):  # pragma: no cover
    """
    MySQL and SQLite will always return naive-Python datetimes.

    We store everything as UTC, but we want to have
    only offset-aware Python datetimes, even with MySQL and SQLite.
    """

    impl = TIMESTAMP
    cache_ok = True

    def process_result_value(self, value: Optional[datetime], dialect):
        if value is not None:
            if dialect.name != "postgresql":
                # 确保datetime对象具有UTC时区信息
                value = value.replace(tzinfo=timezone.utc)
            # 将datetime对象转换为ISO 8601格式字符串
            return value.isoformat()
        return value
