#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""RQ worker job definitions."""

from rq import get_current_job

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

    return result
