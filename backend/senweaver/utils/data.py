from typing import Any


class DataSanitizer:
    SENSITIVE_KEYS = {
        "password",
        "pwd",
        "old_password",
        "sure_password",
        "credit_card",
        "phone",
        "token",
        "refresh",
        "refresh_token",
    }
    MASK = "******"

    @classmethod
    def sanitize(cls, data: Any) -> Any:
        """递归脱敏处理嵌套数据结构"""
        if isinstance(data, dict):
            return {
                key: cls.sanitize(cls._mask_value(key, value))
                for key, value in data.items()
            }
        elif isinstance(data, (list, tuple)):
            return [cls.sanitize(item) for item in data]
        return data

    @classmethod
    def _mask_value(cls, key: str, value: Any) -> Any:
        """对敏感字段进行掩码处理"""
        if key.lower() in cls.SENSITIVE_KEYS:
            return cls.MASK
        if isinstance(value, str) and any(
            sensitive_key in key.lower() for sensitive_key in cls.SENSITIVE_KEYS
        ):
            return cls.MASK
        return value
