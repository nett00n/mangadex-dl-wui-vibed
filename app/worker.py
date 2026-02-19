#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""RQ worker job definitions."""

from pathlib import Path

from rq import get_current_job

from app.cache import store_manga_metadata
from app.config import Config
from app.downloader import download_manga


def perform_download_job(url: str) -> list[str]:
    """Execute a manga download job.

    This function is called by RQ workers to perform the actual download.

    Args:
        url: MangaDex URL to download

    Returns:
        list[str]: List of downloaded CBZ file paths
    """
    job = get_current_job()

    if job:
        job.meta["status"] = "downloading"
        job.save_meta()

    result = download_manga(url, Config.CACHE_DIR)

    if job:
        job.meta["status"] = "complete"
        job.meta["file_count"] = len(result)
        job.save_meta()

    # Store Redis metadata after successful download
    if result:
        _store_metadata_for_result(url, result)

    return result


def _store_metadata_for_result(url: str, file_paths: list[str]) -> None:
    """Store Redis metadata for downloaded files grouped by series directory.

    Args:
        url: Original MangaDex URL
        file_paths: List of absolute CBZ file paths returned by download_manga
    """
    # Group files by parent directory (series directory)
    series_map: dict[str, list[str]] = {}
    for fp in file_paths:
        path = Path(fp)
        series_dir = path.parent
        series_name = series_dir.name
        series_map.setdefault(series_name, []).append(path.name)

    # Lazy import to avoid circular dependency (tasks -> worker -> tasks)
    from app.tasks import _get_cache_redis_connection

    redis_conn = _get_cache_redis_connection()
    for series_name, basenames in series_map.items():
        # Determine cache_path: parent of CBZ files
        cache_path = str(Path(file_paths[0]).parent)
        # Use the actual series directory for the first file in this group
        for fp in file_paths:
            p = Path(fp)
            if p.name in basenames:
                cache_path = str(p.parent)
                break
        store_manga_metadata(
            redis_conn,
            url=url,
            series_name=series_name,
            cache_path=cache_path,
            files=basenames,
        )
