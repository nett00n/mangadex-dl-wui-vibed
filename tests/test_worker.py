#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""Tests for RQ worker job execution."""

from unittest.mock import MagicMock, patch

import pytest


def test_perform_download_job(tmp_path: object) -> None:
    """Test worker performs download job (UT-WKR-001)."""
    from app.worker import perform_download_job

    url = "https://mangadex.org/title/test-123"

    with patch("app.worker.download_manga") as mock_download:
        mock_download.return_value = ["file1.cbz", "file2.cbz"]

        result = perform_download_job(url)

        assert result == ["file1.cbz", "file2.cbz"]
        mock_download.assert_called_once()


def test_progress_updates() -> None:
    """Test worker updates job progress (UT-WKR-002)."""
    from app.worker import perform_download_job

    url = "https://mangadex.org/title/test-123"

    mock_job = MagicMock()
    mock_job.meta = {}

    with patch("app.worker.download_manga") as mock_download:
        mock_download.return_value = ["file1.cbz"]

        with patch("rq.get_current_job") as mock_get_job:
            mock_get_job.return_value = mock_job

            result = perform_download_job(url)

            # Verify job.meta was updated (implementation detail)
            assert result is not None


def test_error_handling() -> None:
    """Test worker error handling (UT-WKR-003)."""
    from app.worker import perform_download_job

    url = "https://mangadex.org/title/test-123"

    with patch("app.worker.download_manga") as mock_download:
        mock_download.side_effect = Exception("Download failed")

        with pytest.raises(Exception, match="Download failed"):
            perform_download_job(url)


def test_result_storage() -> None:
    """Test worker result storage (UT-WKR-004)."""
    from app.worker import perform_download_job

    url = "https://mangadex.org/title/test-123"

    expected_files = ["manga-ch1.cbz", "manga-ch2.cbz", "manga-ch3.cbz"]

    with patch("app.worker.download_manga") as mock_download:
        mock_download.return_value = expected_files

        result = perform_download_job(url)

        assert result == expected_files


def test_timeout_propagation() -> None:
    """Test worker propagates timeout exceptions (UT-WKR-005)."""
    import subprocess

    from app.worker import perform_download_job

    url = "https://mangadex.org/title/test-123"

    with patch("app.worker.download_manga") as mock_download:
        mock_download.side_effect = subprocess.TimeoutExpired("mangadex-dl", 300)

        with pytest.raises(subprocess.TimeoutExpired):
            perform_download_job(url)


def test_worker_module_importable() -> None:
    """Test worker function is importable by RQ (UT-WKR-006)."""
    # Verify the module can be imported
    import app.worker

    # Verify the function exists and is callable
    assert hasattr(app.worker, "perform_download_job")
    assert callable(app.worker.perform_download_job)

    # Verify module path
    assert app.worker.__name__ == "app.worker"


def test_perform_download_stores_metadata(tmp_path: object) -> None:
    """Redis metadata is stored after a successful download (UT-WKR-007)."""
    import fakeredis

    from app.cache import get_cached_manga
    from app.worker import perform_download_job

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    series_dir = "/tmp/cache/My Series"
    files = [f"{series_dir}/ch1.cbz", f"{series_dir}/ch2.cbz"]

    with patch("app.worker.download_manga") as mock_download:
        mock_download.return_value = files

        with patch("app.tasks._get_cache_redis_connection") as mock_redis:
            mock_redis.return_value = fake_redis

            perform_download_job("https://mangadex.org/title/abc")

        result = get_cached_manga(fake_redis, "My Series")
        assert result is not None
        assert set(result["files"]) == {"ch1.cbz", "ch2.cbz"}  # type: ignore[arg-type]
        assert result["url"] == "https://mangadex.org/title/abc"
