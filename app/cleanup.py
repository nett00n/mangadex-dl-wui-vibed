#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""Background cleanup tasks for cache and temporary files."""

import contextlib
import os
import shutil
import time
from pathlib import Path

from rq.job import Job

from app.cache import cleanup_stale_metadata
from app.config import Config
from app.tasks import _get_cache_redis_connection, get_queue


def get_active_job_files() -> list[str]:
    """Get list of files referenced by active jobs.

    Returns:
        list[str]: List of file paths currently referenced by active jobs
    """
    queue = get_queue()
    active_files = []

    # Get all jobs (queued, started, deferred)
    for job in queue.jobs:
        try:
            # Get job status
            status = getattr(job, "_status", None) or job.get_status()
            status_str = status.value if hasattr(status, "value") else str(status)

            # Only consider active jobs (queued, started, deferred)
            if status_str in ["queued", "started", "deferred"]:
                # Try to get result from meta or result attribute
                result = getattr(job, "result", None)
                if result and isinstance(result, list):
                    active_files.extend(result)
        except Exception:  # noqa: S112
            # Skip jobs we can't process
            continue

    return active_files


def is_job_completed(job_id: str) -> bool:
    """Check if a job is completed.

    Args:
        job_id: Job identifier

    Returns:
        bool: True if job is finished or failed, False otherwise
    """
    queue = get_queue()
    try:
        job = Job.fetch(job_id, connection=queue.connection)
        if job is None:
            return True  # Treat missing jobs as completed

        status = getattr(job, "_status", None) or job.get_status()
        status_str = status.value if hasattr(status, "value") else str(status)

        return status_str in ["finished", "failed"]
    except Exception:
        return True  # Treat errors as completed (safe to cleanup)


def cleanup_cache(cache_dir: str, ttl: int) -> int:
    """Remove cached files older than TTL, including files in subdirectories.

    Also removes empty subdirectories after file cleanup.

    Args:
        cache_dir: Directory containing cached files
        ttl: Time-to-live in seconds (0 = never expire)

    Returns:
        int: Number of files removed
    """
    cache_path = Path(cache_dir)
    if not cache_path.exists():
        return 0

    if ttl == 0:
        return 0  # TTL=0 means no expiration

    # Get files referenced by active jobs (convert to set for O(1) lookup)
    active_files = set(get_active_job_files())

    removed_count = 0
    current_time = time.time()

    # First pass: remove expired CBZ files (recursively in subdirectories)
    for file_path in cache_path.rglob("*.cbz"):
        # Skip files referenced by active jobs
        if str(file_path) in active_files or str(file_path.resolve()) in active_files:
            continue

        try:
            # Check file age
            file_mtime = file_path.stat().st_mtime
            file_age = current_time - file_mtime

            if file_age > ttl:
                os.remove(file_path)
                removed_count += 1
        except PermissionError:
            # Skip files we can't delete
            continue
        except Exception:  # noqa: S112
            # Skip other errors
            continue

    # Second pass: remove empty subdirectories
    # Iterate from deepest to shallowest to handle nested empty dirs
    for dir_path in sorted(
        cache_path.rglob("*"),
        key=lambda p: len(p.parts),
        reverse=True,
    ):
        if dir_path.is_dir() and dir_path != cache_path:
            try:
                # rmdir only removes empty directories (safe operation)
                dir_path.rmdir()
            except OSError:
                # Directory not empty or other error - skip
                continue

    # Third pass: remove Redis metadata for series with no remaining files
    with contextlib.suppress(Exception):
        cleanup_stale_metadata(_get_cache_redis_connection())

    return removed_count


def cleanup_temp_dirs() -> int:
    """Remove old temporary directories.

    Returns:
        int: Number of directories removed
    """
    temp_dir = Path(Config.TEMP_DIR)
    if not temp_dir.exists():
        return 0

    removed_count = 0

    # Iterate through directories in temp dir
    for dir_path in temp_dir.iterdir():
        if not dir_path.is_dir():
            continue

        # Extract job ID from directory name pattern "job-*-{id}"
        dir_name = dir_path.name
        if not dir_name.startswith("job-"):
            continue

        # Try to extract job ID (last part after last hyphen)
        parts = dir_name.split("-")
        if len(parts) < 3:
            continue

        job_id = parts[-1]

        # Check if job is completed
        if is_job_completed(job_id):
            try:
                shutil.rmtree(dir_path)
                removed_count += 1
            except Exception:  # noqa: S112
                # Skip directories we can't delete
                continue

    return removed_count


def run_cleanup_loop() -> None:
    """Run periodic cleanup tasks in a loop.

    This function should be called by a background worker.
    """
    while True:
        cleanup_cache(Config.CACHE_DIR, Config.CACHE_TTL_SECONDS)
        cleanup_temp_dirs()
        time.sleep(60)  # Sleep for 60 seconds between cleanup runs
