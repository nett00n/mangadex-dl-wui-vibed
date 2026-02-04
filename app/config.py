"""Application configuration."""

import os


class Config:
    """Application configuration class."""

    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CACHE_DIR = os.environ.get("CACHE_DIR", "/downloads/cache")
    TEMP_DIR = os.environ.get("TEMP_DIR", "/tmp/mangadex-wui")
    TASK_TTL_SECONDS = int(os.environ.get("TASK_TTL_SECONDS", "3600"))
    CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "604800"))
    RQ_WORKER_COUNT = int(os.environ.get("RQ_WORKER_COUNT", "3"))
