#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""Tests for cleanup tasks."""

import os
import time
from pathlib import Path
from unittest.mock import patch

import fakeredis
import pytest

from app.cache import get_cached_manga, store_manga_metadata
from app.cleanup import cleanup_cache, cleanup_temp_dirs, run_cleanup_loop


def test_cleanup_expired_file(tmp_path: Path) -> None:
    """Test cleanup removes expired files (UT-CLN-001)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Create an old file
    old_file = cache_dir / "old-manga.cbz"
    old_file.write_bytes(b"old content")

    # Set file modification time to 8 days ago (past default 7-day TTL)
    old_time = time.time() - (8 * 24 * 60 * 60)
    os.utime(old_file, (old_time, old_time))

    # Run cleanup with 7-day TTL
    cleanup_cache(str(cache_dir), ttl=7 * 24 * 60 * 60)

    # File should be removed
    assert not old_file.exists()


def test_cleanup_keeps_recent_file(tmp_path: Path) -> None:
    """Test cleanup keeps recent files (UT-CLN-002)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Create a recent file
    recent_file = cache_dir / "recent-manga.cbz"
    recent_file.write_bytes(b"recent content")

    # Run cleanup with 7-day TTL
    cleanup_cache(str(cache_dir), ttl=7 * 24 * 60 * 60)

    # File should still exist
    assert recent_file.exists()


def test_cleanup_keeps_active_job_files(tmp_path: Path) -> None:
    """Test cleanup keeps files referenced by active jobs (UT-CLN-003)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Create an old file
    old_file = cache_dir / "active-manga.cbz"
    old_file.write_bytes(b"active content")

    # Set file modification time to 8 days ago
    old_time = time.time() - (8 * 24 * 60 * 60)
    os.utime(old_file, (old_time, old_time))

    # Mock active jobs that reference this file
    with patch("app.cleanup.get_active_job_files") as mock_get_files:
        mock_get_files.return_value = [str(old_file)]

        # Run cleanup
        cleanup_cache(str(cache_dir), ttl=7 * 24 * 60 * 60)

        # File should still exist (referenced by active job)
        assert old_file.exists()


def test_cleanup_handles_permission_error(tmp_path: Path) -> None:
    """Test cleanup handles permission errors gracefully (UT-CLN-004)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Create a file
    test_file = cache_dir / "test-manga.cbz"
    test_file.write_bytes(b"test content")

    # Set old time
    old_time = time.time() - (8 * 24 * 60 * 60)
    os.utime(test_file, (old_time, old_time))

    # Mock os.remove to raise PermissionError
    with patch("os.remove") as mock_remove:
        mock_remove.side_effect = PermissionError("Access denied")

        # Should not crash
        try:
            cleanup_cache(str(cache_dir), ttl=7 * 24 * 60 * 60)
        except PermissionError:
            pytest.fail("cleanup_cache should handle PermissionError")


def test_run_cleanup_loop(tmp_path: Path) -> None:
    """Test cleanup loop runs one iteration (UT-CLN-005)."""
    with patch("time.sleep") as mock_sleep:
        # Make sleep raise StopIteration to exit loop after one iteration
        mock_sleep.side_effect = StopIteration

        with patch("app.cleanup.cleanup_cache") as mock_cleanup_cache:
            with patch("app.cleanup.cleanup_temp_dirs") as mock_cleanup_temp:
                try:
                    run_cleanup_loop()
                except StopIteration:
                    pass

                # Verify both cleanup functions were called
                assert mock_cleanup_cache.called
                assert mock_cleanup_temp.called


def test_cleanup_empty_directory(tmp_path: Path) -> None:
    """Test cleanup handles empty directory (UT-CLN-006)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Run cleanup on empty directory
    result = cleanup_cache(str(cache_dir), ttl=7 * 24 * 60 * 60)

    # Should return 0 and not crash
    assert result == 0 or result is None


def test_cleanup_only_unreferenced_expired_files(tmp_path: Path) -> None:
    """Test cleanup only removes unreferenced expired files (UT-CLN-007)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Create multiple files
    expired_file = cache_dir / "expired.cbz"
    expired_file.write_bytes(b"expired")

    referenced_file = cache_dir / "referenced.cbz"
    referenced_file.write_bytes(b"referenced")

    recent_file = cache_dir / "recent.cbz"
    recent_file.write_bytes(b"recent")

    # Make first two files old
    old_time = time.time() - (8 * 24 * 60 * 60)
    os.utime(expired_file, (old_time, old_time))
    os.utime(referenced_file, (old_time, old_time))

    # Mock active jobs that reference second file
    with patch("app.cleanup.get_active_job_files") as mock_get_files:
        mock_get_files.return_value = [str(referenced_file)]

        # Run cleanup
        cleanup_cache(str(cache_dir), ttl=7 * 24 * 60 * 60)

        # Only expired unreferenced file should be removed
        assert not expired_file.exists()
        assert referenced_file.exists()
        assert recent_file.exists()


def test_cleanup_temp_dirs(tmp_path: Path) -> None:
    """Test cleanup removes completed job temp directories (UT-CLN-008)."""
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()

    # Create temp directories for completed jobs
    completed_job_dir = temp_dir / "job-completed-123"
    completed_job_dir.mkdir()
    (completed_job_dir / "file.txt").write_text("test")

    with patch("app.cleanup.Config.TEMP_DIR", str(temp_dir)):
        with patch("app.cleanup.is_job_completed") as mock_is_completed:
            mock_is_completed.return_value = True

            # Run cleanup (reads TEMP_DIR from config)
            cleanup_temp_dirs()

            # Completed job directory should be removed
            assert not completed_job_dir.exists()


def test_cleanup_expired_files_in_subdirectories(tmp_path: Path) -> None:
    """Test cleanup removes expired files in manga subdirectories."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Create manga subdirectory with old files
    manga_dir = cache_dir / "Test Manga"
    manga_dir.mkdir()
    old_chapter = manga_dir / "chapter-1.cbz"
    old_chapter.write_bytes(b"old content")

    # Set file modification time to 8 days ago
    old_time = time.time() - (8 * 24 * 60 * 60)
    os.utime(old_chapter, (old_time, old_time))

    # Run cleanup with 7-day TTL
    cleanup_cache(str(cache_dir), ttl=7 * 24 * 60 * 60)

    # File should be removed
    assert not old_chapter.exists()


def test_cleanup_removes_empty_subdirectories(tmp_path: Path) -> None:
    """Test cleanup removes empty manga subdirectories after file deletion."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Create manga subdirectory with old file
    manga_dir = cache_dir / "Test Manga"
    manga_dir.mkdir()
    old_chapter = manga_dir / "chapter-1.cbz"
    old_chapter.write_bytes(b"old content")

    # Set file modification time to 8 days ago
    old_time = time.time() - (8 * 24 * 60 * 60)
    os.utime(old_chapter, (old_time, old_time))

    # Run cleanup
    cleanup_cache(str(cache_dir), ttl=7 * 24 * 60 * 60)

    # Both file and directory should be removed
    assert not old_chapter.exists()
    assert not manga_dir.exists()


def test_cleanup_keeps_subdirectory_with_active_files(tmp_path: Path) -> None:
    """Test cleanup keeps subdirectory if it contains recent files."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Create manga subdirectory with old and recent files
    manga_dir = cache_dir / "Test Manga"
    manga_dir.mkdir()

    old_chapter = manga_dir / "chapter-1.cbz"
    old_chapter.write_bytes(b"old content")
    old_time = time.time() - (8 * 24 * 60 * 60)
    os.utime(old_chapter, (old_time, old_time))

    recent_chapter = manga_dir / "chapter-2.cbz"
    recent_chapter.write_bytes(b"recent content")

    # Run cleanup
    cleanup_cache(str(cache_dir), ttl=7 * 24 * 60 * 60)

    # Old file should be removed, recent file and directory should remain
    assert not old_chapter.exists()
    assert recent_chapter.exists()
    assert manga_dir.exists()


def test_cleanup_ttl_zero_skips_all_files(tmp_path: Path) -> None:
    """Test cleanup with ttl=0 skips all files (UT-CLN-009)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Create an expired file
    expired_file = cache_dir / "expired.cbz"
    expired_file.write_bytes(b"expired content")

    # Set file modification time to 8 days ago
    old_time = time.time() - (8 * 24 * 60 * 60)
    os.utime(expired_file, (old_time, old_time))

    # Run cleanup with ttl=0 (never expire)
    result = cleanup_cache(str(cache_dir), ttl=0)

    # File should still exist and no files should be removed
    assert expired_file.exists()
    assert result == 0


def test_cleanup_cache_removes_stale_metadata(tmp_path: Path) -> None:
    """Expired files trigger deletion of Redis metadata (UT-CLN-010)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    series_dir = cache_dir / "Old Manga"
    series_dir.mkdir()
    old_chapter = series_dir / "ch1.cbz"
    old_chapter.write_bytes(b"old")
    old_time = time.time() - (8 * 24 * 60 * 60)
    os.utime(old_chapter, (old_time, old_time))

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    store_manga_metadata(
        fake_redis,
        url="https://mangadex.org/title/old",
        series_name="Old Manga",
        cache_path=str(series_dir),
        files=["ch1.cbz"],
    )

    with (
        patch("app.cleanup.get_active_job_files", return_value=[]),
        patch("app.cleanup._get_cache_redis_connection", return_value=fake_redis),
    ):
        cleanup_cache(str(cache_dir), ttl=7 * 24 * 60 * 60)

    assert get_cached_manga(fake_redis, "Old Manga") is None


def test_cleanup_cache_keeps_metadata_with_files(tmp_path: Path) -> None:
    """Series with remaining files keeps Redis metadata (UT-CLN-011)."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    series_dir = cache_dir / "Active Manga"
    series_dir.mkdir()
    recent_chapter = series_dir / "ch1.cbz"
    recent_chapter.write_bytes(b"recent")

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    store_manga_metadata(
        fake_redis,
        url="https://mangadex.org/title/active",
        series_name="Active Manga",
        cache_path=str(series_dir),
        files=["ch1.cbz"],
    )

    with (
        patch("app.cleanup.get_active_job_files", return_value=[]),
        patch("app.cleanup._get_cache_redis_connection", return_value=fake_redis),
    ):
        cleanup_cache(str(cache_dir), ttl=7 * 24 * 60 * 60)

    assert get_cached_manga(fake_redis, "Active Manga") is not None
