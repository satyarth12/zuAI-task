import logging
import pathlib
from datetime import UTC, timezone
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(verbose=True, override=True)

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def get_logger(name, log_file, level=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    file_handler = logging.FileHandler(log_file)
    formatter = logging.Formatter(
        "%(levelname) -10s %(funcName) -25s %(lineno) -1d: %(message)s"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


class _ServerSettings(BaseSettings):
    # server settings
    APP_NAME: Optional[str] = "sample-paper-server"
    DEBUG_MODE: Optional[bool] = True
    HOST: Optional[str] = "0.0.0.0"
    PORT: Optional[int] = 8000
    TIMEZONE: Optional[timezone] = UTC

    # gemini settings
    GEMINI_API_KEY: str

    # db connection settings
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str
    REDIS_MAX_CONNECTIONS: int = 10
    MONGODB_CONNECTION_STRING: str
    MONGODB_MIN_POOL_SIZE: int = 1
    MONGODB_MAX_POOL_SIZE: int = 10

    # db and collection names
    MONGODB_DATABASE: str
    MONGODB_SAMPLE_PAPERS_COLLECTION: str

    class Config:
        case_sensitive = False
        env_file = f"{ROOT}/.env"
        extra = "ignore"


@lru_cache
def get_settings() -> _ServerSettings:
    return _ServerSettings()


server_settings = get_settings()
