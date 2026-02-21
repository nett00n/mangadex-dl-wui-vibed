#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""Manga download functionality using mangadex-dl CLI."""

import re
import subprocess
from pathlib import Path
from shutil import which

from app.validators import is_valid_mangadex_url


def run_mangadex_dl(
    url: str,
    cache_dir: str,
    timeout: int = 3600,
) -> tuple[int, str, str]:
    """Safely execute mangadex-dl CLI with validated arguments.

    SECURITY: This function uses a safe subprocess invocation pattern:
    - Validates the binary exists before execution
    - Uses argument list (no shell=True) to prevent command injection
    - Assumes URL has been validated by validators.py before calling
    - Returns stdout/stderr for logging and progress parsing

    Args:
        url: MangaDex URL to download (must be pre-validated)
        cache_dir: Directory to cache downloaded files
        timeout: Maximum execution time in seconds (default: 3600)

    Returns:
        tuple[int, str, str]: (return_code, stdout, stderr)

    Raises:
        RuntimeError: If mangadex-dl binary is not found in PATH
        subprocess.TimeoutExpired: If execution exceeds timeout
    """
    exe = which("mangadex-dl")
    if not exe:
        raise RuntimeError("mangadex-dl not found in PATH")

    args = [
        exe,
        "--save-as",
        "cbz",
        "--path",
        f"{cache_dir}/{{manga.title}}",
        "--input-pos",
        "*",
        "--progress-bar-layout",
        "none",
        "--filename-chapter",
        "Vol. {chapter.volume} Ch. {chapter.chapter}{file_ext}",
        "--delay-requests",  # https://mangadex-dl.mansuf.link/en/stable/cli_usage/advanced/throttle_requests.html
        "1",
        url,
    ]

    # Use check=False to handle errors explicitly
    # Capture output for logging and progress tracking
    proc = subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def download_manga(url: str, cache_dir: str) -> list[str]:
    """Download manga from MangaDex using the CLI tool.

    Uses before/after snapshot to isolate newly created files for this job,
    preventing cross-contamination from concurrent downloads.

    Args:
        url: MangaDex URL to download
        cache_dir: Directory to cache downloaded files

    Returns:
        list[str]: List of newly created CBZ file paths for this download

    Raises:
        Exception: If URL is invalid or directory doesn't exist
        RuntimeError: If mangadex-dl execution fails
    """
    # Validate URL before processing
    if not is_valid_mangadex_url(url):
        raise Exception("Invalid MangaDex URL")

    # Check directory exists
    if not Path(cache_dir).exists():
        raise Exception("Directory does not exist")

    # Snapshot files before download
    existing_files = set(scan_for_cbz(cache_dir))

    returncode, stdout, stderr = run_mangadex_dl(url, cache_dir)

    if returncode != 0:
        raise RuntimeError(f"mangadex-dl failed with code {returncode}: {stderr}")

    # Snapshot files after download and return only new files
    all_files = set(scan_for_cbz(cache_dir))
    new_files = all_files - existing_files
    return sorted(new_files)


def parse_progress(stdout: str) -> dict[str, str | int]:
    """Parse progress information from mangadex-dl stdout.

    Args:
        stdout: Standard output from mangadex-dl command

    Returns:
        dict: Parsed progress information with keys:
            - current: Current chapter number being downloaded
            - total: Total number of chapters
            - cached: Number of skipped (cached) chapters
    """
    progress: dict[str, str | int] = {}

    # Parse "Downloading chapter X of Y"
    chapter_match = re.search(r"Downloading chapter (\d+) of (\d+)", stdout)
    if chapter_match:
        progress["current"] = int(chapter_match.group(1))
        progress["total"] = int(chapter_match.group(2))

    # Count "Skipped" occurrences for cached chapters
    cached_count = stdout.count("Skipped")
    if cached_count > 0:
        progress["cached"] = cached_count

    return progress


def build_cli_args(url: str, cache_dir: str) -> list[str]:
    """Build command-line arguments for mangadex-dl.

    Args:
        url: MangaDex URL to download
        cache_dir: Directory to cache downloaded files

    Returns:
        list[str]: Command arguments list
    """
    return [
        "mangadex-dl",
        "--save-as",
        "cbz",
        "--path",
        f"{cache_dir}/{{manga.title}}",
        "--input-pos",
        "*",
        "--progress-bar-layout",
        "none",
        "--filename-chapter",
        "Vol. {chapter.volume} Ch. {chapter.chapter}{file_ext}",
        url,
    ]


def scan_for_cbz(directory: str) -> list[str]:
    """Scan directory recursively for CBZ files.

    Args:
        directory: Directory path to scan

    Returns:
        list[str]: Sorted list of CBZ file paths found (including subdirectories)
    """
    dir_path = Path(directory)
    return sorted(str(f.resolve()) for f in dir_path.rglob("*.cbz"))


def sanitize_filename(name: str) -> str:
    """Remove or replace characters unsafe for filenames.

    Args:
        name: Raw filename string

    Returns:
        str: Sanitized filename safe for all major operating systems
    """
    sanitized = re.sub(r'[/<>:"\\|?*]', "_", name)
    sanitized = re.sub(r"_+", "_", sanitized)
    sanitized = sanitized.strip(" _.")
    return sanitized or "download"


def get_display_filename(file_path: str, cache_dir: str) -> str:
    """Build a display filename prefixed with the manga series name.

    The file is NOT renamed on disk; this name is used only for Content-Disposition
    headers and UI display so that mangadex-dl's cache skip logic is preserved.

    Args:
        file_path: Absolute path to the CBZ file
        cache_dir: Absolute path to the cache root directory

    Returns:
        str: Display filename, e.g. "Series Name - Chapter 1.cbz"
    """
    path = Path(file_path).resolve()
    cache = Path(cache_dir).resolve()
    if path.parent == cache:
        return sanitize_filename(path.name)
    series_name = sanitize_filename(path.parent.name)
    chapter_name = sanitize_filename(path.name)
    return f"{series_name} - {chapter_name}"
