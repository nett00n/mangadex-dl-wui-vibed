"""Manga download functionality using mangadex-dl CLI."""


def download_manga(url: str, cache_dir: str) -> list[str]:
    """Download manga from MangaDex using the CLI tool.

    Args:
        url: MangaDex URL to download
        cache_dir: Directory to cache downloaded files

    Returns:
        list[str]: List of downloaded CBZ file paths
    """
    # TODO: Implement subprocess wrapper for mangadex-dl
    pass


def parse_progress(stdout: str) -> dict[str, str | int]:
    """Parse progress information from mangadex-dl stdout.

    Args:
        stdout: Standard output from mangadex-dl command

    Returns:
        dict: Parsed progress information
    """
    # TODO: Implement stdout parsing
    pass


def build_cli_args(url: str, cache_dir: str) -> list[str]:
    """Build command-line arguments for mangadex-dl.

    Args:
        url: MangaDex URL to download
        cache_dir: Directory to cache downloaded files

    Returns:
        list[str]: Command arguments list
    """
    # TODO: Implement CLI argument builder
    pass


def scan_for_cbz(directory: str) -> list[str]:
    """Scan directory for CBZ files.

    Args:
        directory: Directory path to scan

    Returns:
        list[str]: List of CBZ file paths found
    """
    # TODO: Implement directory scanning
    pass
