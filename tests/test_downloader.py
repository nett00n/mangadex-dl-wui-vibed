#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""Tests for manga downloader."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.downloader import (
    build_cli_args,
    download_manga,
    get_display_filename,
    parse_progress,
    sanitize_filename,
    scan_for_cbz,
)


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
        f"{cache_dir}/{{manga.title}}",
        "--input-pos",
        "*",
        "--progress-bar-layout",
        "none",
        "--filename-chapter",
        "Vol. {chapter.volume} Ch. {chapter.chapter}{file_ext}",
        url,
    ]
    assert args == expected


def test_cli_args_contain_manga_title_path_placeholder() -> None:
    """Test that --path arg contains literal {manga.title} placeholder (UT-DL-018)."""
    url = "https://mangadex.org/title/test-123"
    cache_dir = "/test/cache"

    args = build_cli_args(url, cache_dir)

    path_idx = args.index("--path")
    path_value = args[path_idx + 1]
    assert "{manga.title}" in path_value
    assert path_value == "/test/cache/{manga.title}"


def test_cli_args_contain_filename_chapter_format() -> None:
    """Test --filename-chapter arg with volume placeholder is present (UT-DL-019)."""
    url = "https://mangadex.org/title/test-123"
    cache_dir = "/test/cache"

    args = build_cli_args(url, cache_dir)

    assert "--filename-chapter" in args
    fmt_idx = args.index("--filename-chapter")
    fmt_value = args[fmt_idx + 1]
    assert "{chapter.volume}" in fmt_value
    assert "{chapter.chapter}" in fmt_value
    assert "{file_ext}" in fmt_value


def test_download_manga_success(tmp_path: Path) -> None:
    """Test successful manga download (UT-DL-001)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    url = "https://mangadex.org/title/test-123"

    # Mock subprocess to create files in a subdirectory (mimics mangadex-dl behavior)
    def create_files(*args, **kwargs):
        manga_dir = cache_dir / "Test Manga"
        manga_dir.mkdir(exist_ok=True)
        (manga_dir / "chapter-1.cbz").write_bytes(b"fake content")
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("app.downloader.which", return_value="/usr/local/bin/mangadex-dl"):
        with patch("subprocess.run", side_effect=create_files) as mock_run:
            files = download_manga(url, str(cache_dir))

            assert mock_run.called
            assert len(files) == 1
            assert files[0].endswith(".cbz")


def test_download_manga_subprocess_failure(tmp_path: Path) -> None:
    """Test subprocess failure handling (UT-DL-002)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    url = "https://mangadex.org/title/test-123"

    with patch("app.downloader.which", return_value="/usr/local/bin/mangadex-dl"):
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

    with patch("app.downloader.which", return_value="/usr/local/bin/mangadex-dl"):
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


def test_scan_for_cbz_with_subdirectories(tmp_path: Path) -> None:
    """Test CBZ file scanning finds files in subdirectories."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Create subdirectories with CBZ files (mimics mangadex-dl structure)
    manga1_dir = cache_dir / "Test Manga 1"
    manga1_dir.mkdir()
    (manga1_dir / "chapter-1.cbz").write_bytes(b"content1")
    (manga1_dir / "chapter-2.cbz").write_bytes(b"content2")

    manga2_dir = cache_dir / "Test Manga 2"
    manga2_dir.mkdir()
    (manga2_dir / "chapter-1.cbz").write_bytes(b"content3")

    # Also create a top-level CBZ (for backwards compatibility)
    (cache_dir / "top-level.cbz").write_bytes(b"content4")

    files = scan_for_cbz(str(cache_dir))

    assert len(files) == 4
    assert all(f.endswith(".cbz") for f in files)
    # Should be sorted
    assert files == sorted(files)


def test_download_manga_returns_only_new_files(tmp_path: Path) -> None:
    """Test download_manga returns only newly created files via snapshot diff."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Create pre-existing manga directory with cached chapters
    existing_manga_dir = cache_dir / "Existing Manga"
    existing_manga_dir.mkdir()
    (existing_manga_dir / "chapter-1.cbz").write_bytes(b"old content")

    url = "https://mangadex.org/title/test-123"

    # Mock subprocess to create NEW files in a different subdirectory
    def create_new_files(*args, **kwargs):
        new_manga_dir = cache_dir / "New Manga"
        new_manga_dir.mkdir(exist_ok=True)
        (new_manga_dir / "chapter-1.cbz").write_bytes(b"new content")
        (new_manga_dir / "chapter-2.cbz").write_bytes(b"new content 2")
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("app.downloader.which", return_value="/usr/local/bin/mangadex-dl"):
        with patch("subprocess.run", side_effect=create_new_files) as mock_run:
            files = download_manga(url, str(cache_dir))

            assert mock_run.called
            # Should only return the 2 new files, not the pre-existing one
            assert len(files) == 2
            assert all("New Manga" in f for f in files)
            assert not any("Existing Manga" in f for f in files)


def test_sanitize_filename_removes_unsafe_chars() -> None:
    """Test sanitize_filename replaces filesystem-unsafe characters (UT-DL-011)."""
    assert sanitize_filename("My:Manga/Title") == "My_Manga_Title"


def test_sanitize_filename_empty_string() -> None:
    """Test sanitize_filename returns fallback for empty/blank input (UT-DL-012)."""
    assert sanitize_filename("") == "download"
    assert sanitize_filename("...") == "download"


def test_sanitize_filename_normal_name() -> None:
    """Test sanitize_filename leaves safe names unchanged (UT-DL-013)."""
    assert sanitize_filename("Chapter 1.cbz") == "Chapter 1.cbz"


def test_get_display_filename_with_series_subdir(tmp_path: Path) -> None:
    """Test display filename uses series subdirectory as prefix (UT-DL-014)."""
    cache = tmp_path / "cache"
    series_dir = cache / "Series Name"
    series_dir.mkdir(parents=True)
    cbz = series_dir / "Chapter 1.cbz"
    cbz.write_bytes(b"")

    result = get_display_filename(str(cbz), str(cache))

    assert result == "Series Name - Chapter 1.cbz"


def test_get_display_filename_root_level(tmp_path: Path) -> None:
    """Test display filename for root-level cache file has no prefix (UT-DL-015)."""
    cache = tmp_path / "cache"
    cache.mkdir()
    cbz = cache / "file.cbz"
    cbz.write_bytes(b"")

    result = get_display_filename(str(cbz), str(cache))

    assert result == "file.cbz"


def test_get_display_filename_nested_subdir(tmp_path: Path) -> None:
    """Test display filename uses immediate parent directory as prefix (UT-DL-016)."""
    cache = tmp_path / "cache"
    series_dir = cache / "Top" / "Series Name"
    series_dir.mkdir(parents=True)
    cbz = series_dir / "Chapter 1.cbz"
    cbz.write_bytes(b"")

    result = get_display_filename(str(cbz), str(cache))

    assert result == "Series Name - Chapter 1.cbz"


def test_get_display_filename_special_chars(tmp_path: Path) -> None:
    """Test display filename sanitizes special chars in names (UT-DL-017)."""
    cache = tmp_path / "cache"
    series_dir = cache / "My: Manga"
    series_dir.mkdir(parents=True)
    cbz = series_dir / "Chapter 1.cbz"
    cbz.write_bytes(b"")

    result = get_display_filename(str(cbz), str(cache))

    assert result == "My_ Manga - Chapter 1.cbz"
