#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""Application configuration."""

import os


def _get_positive_int_from_env(env_var: str, default: int, min_value: int = 1) -> int:
    """Get a positive integer from environment variable.

    Args:
        env_var: Environment variable name
        default: Default value if not set
        min_value: Minimum allowed value (default: 1)

    Returns:
        int: Validated integer value

    Raises:
        ValueError: If value is not a valid positive integer >= min_value
    """
    raw_value = os.environ.get(env_var, str(default))
    value = int(raw_value)  # Raises ValueError for non-integer
    if value < min_value:
        raise ValueError(f"{env_var} must be >= {min_value}, got {value}")
    return value


class Config:
    """Application configuration class."""

    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CACHE_DIR = os.environ.get("CACHE_DIR", "/downloads/cache")
    TEMP_DIR = os.environ.get("TEMP_DIR", "/tmp/mangadex-wui")
    TASK_TTL_SECONDS = _get_positive_int_from_env("TASK_TTL_SECONDS", 3600)
    CACHE_TTL_SECONDS = _get_positive_int_from_env("CACHE_TTL_SECONDS", 604800)
    RQ_WORKER_COUNT = _get_positive_int_from_env("RQ_WORKER_COUNT", 3)
