"""RQ worker job definitions."""


def perform_download_job(url: str) -> list[str]:
    """Execute a manga download job.

    This function is called by RQ workers to perform the actual download.

    Args:
        url: MangaDex URL to download

    Returns:
        list[str]: List of downloaded CBZ file paths
    """
    # TODO: Implement download job execution
    pass
