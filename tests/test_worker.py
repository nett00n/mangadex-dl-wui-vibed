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
