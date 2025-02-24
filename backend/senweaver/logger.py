import time

from loguru import logger

from config.settings import settings

# 移除控制台输出
# logger.remove(handler_id=None)
log_path = settings.LOG_PATH
log_path.mkdir(parents=True, exist_ok=True)


# 日志文件
log_stdout_file = log_path / f'info_{time.strftime("%Y-%m-%d")}.log'
log_stderr_file = log_path / f'error_{time.strftime("%Y-%m-%d")}.log'

# loguru 日志: https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger.add
log_config = dict(
    rotation="10 MB", retention="15 days", compression="tar.gz", enqueue=True
)
# stdout
logger.add(
    log_stdout_file,
    level="INFO",
    filter=lambda record: record["level"].name == "INFO" or record["level"].no <= 25,
    **log_config,
    backtrace=False,
    diagnose=False,
)
# stderr
logger.add(
    log_stderr_file,
    level="ERROR",
    filter=lambda record: record["level"].name == "ERROR" or record["level"].no >= 30,
    **log_config,
    backtrace=True,
    diagnose=True,
)
