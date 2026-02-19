#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""Redis-backed metadata for cached manga series."""

import json
from datetime import UTC, datetime
from pathlib import Path

import redis


def _redis_key(series_name: str) -> str:
    return f"cache:manga:{series_name}"


def store_manga_metadata(
    redis_conn: redis.Redis,  # type: ignore[type-arg]
    url: str,
    series_name: str,
    cache_path: str,
    files: list[str],
) -> None:
    """Create or update Redis hash metadata for a cached manga series.

    If the key already exists, new files are merged with existing ones.

    Args:
        redis_conn: Redis connection instance
        url: Original MangaDex URL
        series_name: Series name (directory name)
        cache_path: Full path to series directory
        files: List of CBZ file basenames
    """
    key = _redis_key(series_name)

    existing_raw = redis_conn.hget(key, "files")
    if existing_raw:
        try:
            existing_files: list[str] = json.loads(existing_raw)
        except (json.JSONDecodeError, TypeError):
            existing_files = []
        merged = list(dict.fromkeys(existing_files + files))
    else:
        merged = files

    redis_conn.hset(
        key,
        mapping={
            "url": url,
            "name": series_name,
            "sanitized_name": series_name.replace("_", " "),
            "cache_path": cache_path,
            "download_date": datetime.now(UTC).isoformat(),
            "files": json.dumps(merged),
        },
    )


def list_cached_mangas(
    redis_conn: redis.Redis,  # type: ignore[type-arg]
) -> list[dict[str, str | list[str]]]:
    """Return metadata for all cached manga series from Redis.

    Args:
        redis_conn: Redis connection instance

    Returns:
        list[dict]: List of series metadata dicts, sorted by series name
    """
    results: list[dict[str, str | list[str]]] = []
    cursor = 0
    while True:
        cursor, keys = redis_conn.scan(cursor, match="cache:manga:*", count=100)
        for key in keys:
            entry = redis_conn.hgetall(key)
            if not entry:
                continue
            files_raw = entry.get("files", "[]")
            try:
                files: list[str] = json.loads(files_raw)
            except (json.JSONDecodeError, TypeError):
                files = []
            results.append(
                {
                    "url": entry.get("url", ""),
                    "name": entry.get("name", ""),
                    "sanitized_name": entry.get("sanitized_name", ""),
                    "cache_path": entry.get("cache_path", ""),
                    "download_date": entry.get("download_date", ""),
                    "files": files,
                },
            )
        if cursor == 0:
            break
    results.sort(key=lambda x: str(x.get("name", "")).lower())
    return results


def get_cached_manga(
    redis_conn: redis.Redis,  # type: ignore[type-arg]
    series_name: str,
) -> dict[str, str | list[str]] | None:
    """Return metadata for a single cached manga series.

    Args:
        redis_conn: Redis connection instance
        series_name: Series name to look up

    Returns:
        dict | None: Series metadata or None if not found
    """
    key = _redis_key(series_name)
    entry = redis_conn.hgetall(key)
    if not entry:
        return None
    files_raw = entry.get("files", "[]")
    try:
        files: list[str] = json.loads(files_raw)
    except (json.JSONDecodeError, TypeError):
        files = []
    return {
        "url": entry.get("url", ""),
        "name": entry.get("name", ""),
        "sanitized_name": entry.get("sanitized_name", ""),
        "cache_path": entry.get("cache_path", ""),
        "download_date": entry.get("download_date", ""),
        "files": files,
    }


def delete_manga_metadata(
    redis_conn: redis.Redis,  # type: ignore[type-arg]
    series_name: str,
) -> None:
    """Delete Redis hash metadata for a series.

    Args:
        redis_conn: Redis connection instance
        series_name: Series name to remove
    """
    redis_conn.delete(_redis_key(series_name))


def cleanup_stale_metadata(
    redis_conn: redis.Redis,  # type: ignore[type-arg]
) -> int:
    """Remove metadata entries whose files no longer exist on disk.

    Args:
        redis_conn: Redis connection instance

    Returns:
        int: Number of entries deleted
    """
    deleted = 0
    cursor = 0
    while True:
        cursor, keys = redis_conn.scan(cursor, match="cache:manga:*", count=100)
        for key in keys:
            entry = redis_conn.hgetall(key)
            if not entry:
                redis_conn.delete(key)
                deleted += 1
                continue
            cache_path = entry.get("cache_path", "")
            files_raw = entry.get("files", "[]")
            try:
                files: list[str] = json.loads(files_raw)
            except (json.JSONDecodeError, TypeError):
                files = []
            # Check if any CBZ file still exists on disk
            any_file_exists = any(Path(cache_path, f).exists() for f in files if f)
            if not any_file_exists:
                redis_conn.delete(key)
                deleted += 1
        if cursor == 0:
            break
    return deleted
