"""Tests for manga downloader."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.downloader import build_cli_args, download_manga, parse_progress, scan_for_cbz


def test_build_cli_args() -> None:
    """Test CLI argument builder (UT-DL-008)."""
    url = "https://mangadex.org/title/test-123"
    cache_dir = "/test/cache"

    args = build_cli_args(url, cache_dir)

    expected = [
        "mangadex-dl",
        "--save-as",
        "cbz",
        "--path",
        cache_dir,
        "--input-pos",
        "*",
        "--progress-bar-layout",
        "none",
        url,
    ]
    assert args == expected


def test_download_manga_success(tmp_path: Path) -> None:
    """Test successful manga download (UT-DL-001)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Create a fake CBZ file that the subprocess would create
    fake_cbz = cache_dir / "test-manga.cbz"
    fake_cbz.write_bytes(b"fake content")

    url = "https://mangadex.org/title/test-123"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        files = download_manga(url, str(cache_dir))

        assert mock_run.called
        assert len(files) == 1
        assert files[0].endswith(".cbz")


def test_download_manga_subprocess_failure(tmp_path: Path) -> None:
    """Test subprocess failure handling (UT-DL-002)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    url = "https://mangadex.org/title/test-123"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Download failed: network error",
        )

        with pytest.raises(Exception, match="Download failed: network error"):
            download_manga(url, str(cache_dir))


def test_download_manga_invalid_url(tmp_path: Path) -> None:
    """Test invalid URL handling (UT-DL-003)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    url = "https://example.com/invalid"

    with pytest.raises(Exception, match="Invalid MangaDex URL"):
        download_manga(url, str(cache_dir))


def test_parse_progress_chapter_counts() -> None:
    """Test progress parsing extracts chapter counts (UT-DL-004)."""
    stdout = "Downloading chapter 5 of 10\nProgress: 50%"

    progress = parse_progress(stdout)

    assert progress["current"] == 5
    assert progress["total"] == 10


def test_parse_progress_cached_chapters() -> None:
    """Test progress parsing detects cached chapters (UT-DL-005)."""
    stdout = "Chapter 1: Skipped (already downloaded)\nChapter 2: Downloading..."

    progress = parse_progress(stdout)

    assert "cached" in progress
    cached_value = progress.get("cached", 0)
    assert isinstance(cached_value, int)
    assert cached_value > 0


def test_download_manga_timeout(tmp_path: Path) -> None:
    """Test timeout handling (UT-DL-006)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    url = "https://mangadex.org/title/test-123"

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("mangadex-dl", 300)

        with pytest.raises(subprocess.TimeoutExpired):
            download_manga(url, str(cache_dir))


def test_download_manga_filesystem_error(tmp_path: Path) -> None:
    """Test filesystem error handling (UT-DL-007)."""
    # Use non-existent path
    cache_dir = tmp_path / "nonexistent" / "cache"

    url = "https://mangadex.org/title/test-123"

    with pytest.raises(Exception, match="Directory does not exist"):
        download_manga(url, str(cache_dir))


def test_scan_for_cbz_with_files(tmp_path: Path) -> None:
    """Test CBZ file scanning with files present (UT-DL-009)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Create test files
    (cache_dir / "manga1.cbz").write_bytes(b"content1")
    (cache_dir / "manga2.cbz").write_bytes(b"content2")
    (cache_dir / "readme.txt").write_text("not a cbz")

    files = scan_for_cbz(str(cache_dir))

    assert len(files) == 2
    assert all(f.endswith(".cbz") for f in files)


def test_scan_for_cbz_empty_dir(tmp_path: Path) -> None:
    """Test CBZ file scanning with empty directory (UT-DL-010)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    files = scan_for_cbz(str(cache_dir))

    assert files == []
