import time

from config.settings import EnvironmentEnum, settings
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from pydantic import ValidationError
from senweaver.utils.request import get_request_trace_id
from starlette import status

pydantic_translation_map = {
    # 通用错误
    "no_such_attribute": "对象没有属性 '{attribute}'",
    "json_invalid": "无效的 JSON: {error}",
    "json_type": "JSON 输入应为字符串、字节或字节数组",
    "recursion_loop": "递归错误 - 检测到循环引用",
    "model_type": "输入应为有效的字典或 {class_name} 的实例",
    "model_attributes_type": "输入应为有效的字典或对象以提取字段",
    "dataclass_exact_type": "输入应为 {class_name} 的实例",
    "dataclass_type": "输入应为字典或 {class_name} 的实例",
    "missing": "字段必填",
    "frozen_field": "字段已冻结",
    "frozen_instance": "实例已冻结",
    "extra_forbidden": "不允许额外的输入",
    "invalid_key": "键应为字符串",
    "get_attribute_error": "提取属性时出错: {error}",
    "none_required": "输入应为 None",
    "enum": "输入应为 {expected}",
    "greater_than": "输入应大于 {gt}",
    "greater_than_equal": "输入应大于或等于 {ge}",
    "less_than": "输入应小于 {lt}",
    "less_than_equal": "输入应小于或等于 {le}",
    "finite_number": "输入应为有限数字",
    "too_short": "长度至少有 {min_length} ，实际为 {actual_length}",
    "too_long": "长度最多有 {max_length} ，实际为 {actual_length}",
    # 字符串错误
    "string_type": "输入应为有效的字符串",
    "string_sub_type": "输入应为字符串，而不是 str 的子类实例",
    "string_unicode": "输入应为有效的字符串，无法将原始数据解析为 Unicode 字符串",
    "string_pattern_mismatch": "字符串应匹配模式 '{pattern}'",
    "string_too_short": "字符串应至少有 {min_length} 个字符",
    "string_too_long": "字符串应最多有 {max_length} 个字符",
    # 字典和映射错误
    "dict_type": "输入应为有效的字典",
    "mapping_type": "输入应为有效的映射，错误: {error}",
    "iterable_type": "输入应为可迭代对象",
    "iteration_error": "遍历对象时出错，错误: {error}",
    "list_type": "输入应为有效的列表",
    "tuple_type": "输入应为有效的元组",
    "set_type": "输入应为有效的集合",
    # 布尔值错误
    "bool_type": "输入应为有效的布尔值",
    "bool_parsing": "输入应为有效的布尔值，无法解析输入",
    # 整数错误
    "int_type": "输入应为有效的整数",
    "int_parsing": "输入应为有效的整数，无法将字符串解析为整数",
    "int_parsing_size": "无法将输入字符串解析为整数，超出最大大小",
    "int_from_float": "输入应为有效的整数，但输入包含小数部分",
    "multiple_of": "输入应为 {multiple_of} 的倍数",
    # 浮点数错误
    "float_type": "输入应为有效的数字",
    "float_parsing": "输入应为有效的数字，无法将字符串解析为数字",
    # 字节错误
    "bytes_type": "输入应为有效的字节",
    "bytes_too_short": "数据应至少有 {min_length} 字节",
    "bytes_too_long": "数据应最多有 {max_length} 字节",
    # 值错误
    "value_error": "值错误: {error}",
    "assertion_error": "断言失败: {error}",
    "literal_error": "输入应为 {expected}",
    # 日期和时间错误
    "date_type": "输入应为有效的日期",
    "date_parsing": "输入应为有效的日期，格式为 YYYY-MM-DD，错误: {error}",
    "date_from_datetime_parsing": "输入应为有效的日期或时间，错误: {error}",
    "date_from_datetime_inexact": "提供的日期时间应为精确日期（时间部分应为零）",
    "date_past": "日期应为过去的时间",
    "date_future": "日期应为未来的时间",
    "time_type": "输入应为有效的时间",
    "time_parsing": "输入应为有效的时间格式，错误: {error}",
    "datetime_type": "输入应为有效的日期时间",
    "datetime_parsing": "输入应为有效的日期时间，错误: {error}",
    "datetime_object_invalid": "无效的日期时间对象，错误: {error}",
    "datetime_past": "输入应为过去的时间",
    "datetime_future": "输入应为未来的时间",
    "timezone_naive": "输入不应包含时区信息",
    "timezone_aware": "输入应包含时区信息",
    "timezone_offset": "时区偏移量应为 {tz_expected}，实际为 {tz_actual}",
    "time_delta_type": "输入应为有效的时间差",
    "time_delta_parsing": "输入应为有效的时间差，错误: {error}",
    # 集合错误
    "frozen_set_type": "输入应为有效的冻结集合",
    # 类型检查错误
    "is_instance_of": "输入应为 {class} 的实例",
    "is_subclass_of": "输入应为 {class} 的子类",
    "callable_type": "输入应为可调用对象",
    # 联合类型错误
    "union_tag_invalid": "输入标签 '{tag}' 使用 {discriminator} 未匹配任何预期标签: {expected_tags}",
    "union_tag_not_found": "无法使用鉴别器 {discriminator} 提取标签",
    # 参数错误
    "arguments_type": "参数应为元组、列表或字典",
    "missing_argument": "缺少必需的参数",
    "unexpected_keyword_argument": "意外的关键字参数",
    "missing_keyword_only_argument": "缺少必需的关键字参数",
    "unexpected_positional_argument": "意外的位置参数",
    "missing_positional_only_argument": "缺少必需的位置参数",
    "multiple_argument_values": "为参数提供了多个值",
    # URL 错误
    "url_type": "URL 输入应为字符串或 URL",
    "url_parsing": "输入应为有效的 URL，错误: {error}",
    "url_syntax_violation": "输入违反了严格的 URL 语法规则，错误: {error}",
    "url_too_long": "URL 应最多有 {max_length} 个字符",
    "url_scheme": "URL 协议应为 {expected_schemes}",
    # UUID 错误
    "uuid_type": "UUID 输入应为字符串、字节或 UUID 对象",
    "uuid_parsing": "输入应为有效的 UUID，错误: {error}",
    "uuid_version": "UUID 版本应为 {expected_version}",
    # 小数错误
    "decimal_type": "小数输入应为整数、浮点数、字符串或 Decimal 对象",
    "decimal_parsing": "输入应为有效的小数",
    "decimal_max_digits": "小数输入的总位数应不超过 {max_digits}",
    "decimal_max_places": "小数输入的小数位数应不超过 {decimal_places}",
    "decimal_whole_digits": "小数输入的小数点前的位数应不超过 {whole_digits}",
}


def get_error_response(**kwargs):
    kwargs["requestId"] = get_request_trace_id()
    kwargs["time"] = int(time.time())
    return kwargs


async def _validation_exception_handler(
    request: Request, e: RequestValidationError | ValidationError
) -> ORJSONResponse:
    """
    数据验证异常处理

    :param request: 请求对象
    :param e: 验证错误异常
    :return: ORJSONResponse
    """
    errors = []
    for error in e.errors():
        error_type = error["type"]
        ctx = error.get("ctx", {})
        default_msg = error["msg"]

        # 获取翻译后的消息
        translated_msg = pydantic_translation_map.get(error_type, default_msg)
        if ctx:
            try:
                translated_msg = translated_msg.format(**ctx)
            except KeyError:
                pass

        # 更新错误消息
        error["msg"] = translated_msg
        errors.append(error)

    # 提取第一个错误作为主要错误信息
    error = errors[0]
    if error.get("type") == "json_invalid":
        message = "JSON 解析失败"
    else:
        field = ".".join(str(loc) for loc in error.get("loc", []))
        error_msg = error.get("msg", "未知错误")
        error_input = error.get("input", "无输入")
        message = (
            f"{field} {error_msg}，输入：{error_input}"
            if settings.ENVIRONMENT == EnvironmentEnum.DEVELOPMENT
            else error_msg
        )

    # 构造响应内容
    content = get_error_response(
        code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"请求参数非法: {message}",
        data=(
            {"errors": errors}
            if settings.ENVIRONMENT == EnvironmentEnum.DEVELOPMENT
            else None
        ),
    )
    return ORJSONResponse(
        content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )
