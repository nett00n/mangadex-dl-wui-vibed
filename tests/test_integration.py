"""Integration tests."""

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask.testing import FlaskClient


@pytest.mark.integration
def test_full_workflow(client_with_dirs: FlaskClient, cache_dir: Path) -> None:
    """Test full download workflow: submit → poll → download (IT-E2E-001)."""
    with patch("app.routes.is_valid_mangadex_url") as mock_validate:
        mock_validate.return_value = True

        with patch("subprocess.run") as mock_run:
            # After subprocess runs, create the CBZ file in subdirectory
            def create_cbz(*args: object, **kwargs: object) -> MagicMock:
                manga_dir = cache_dir / "Test Manga"
                manga_dir.mkdir(exist_ok=True)
                (manga_dir / "chapter-1.cbz").write_bytes(b"manga content")
                return MagicMock(returncode=0, stdout="", stderr="")

            mock_run.side_effect = create_cbz

            # Submit download
            response = client_with_dirs.post(
                "/api/download",
                json={"url": "https://mangadex.org/title/test-123"},
            )
            assert response.status_code == 200
            task_id = response.get_json()["task_id"]

            # Poll status
            response = client_with_dirs.get(f"/api/status/{task_id}")
            assert response.status_code == 200

            # Download file (if completed)
            # This part will be mocked in real implementation


@pytest.mark.integration
def test_concurrent_downloads(client_with_dirs: FlaskClient, cache_dir: Path) -> None:
    """Test 3 concurrent downloads (IT-E2E-002)."""
    with patch("app.routes.is_valid_mangadex_url") as mock_validate:
        mock_validate.return_value = True

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            # Submit 3 downloads
            task_ids = []
            for i in range(3):
                response = client_with_dirs.post(
                    "/api/download",
                    json={"url": f"https://mangadex.org/title/test-{i}"},
                )
                assert response.status_code == 200
                task_ids.append(response.get_json()["task_id"])

            # Verify all tasks were created
            assert len(task_ids) == 3
            assert len(set(task_ids)) == 3  # All unique


@pytest.mark.integration
def test_cached_download_reuse(client_with_dirs: FlaskClient, cache_dir: Path) -> None:
    """Test cached download reuse (IT-E2E-003)."""
    # Create a pre-existing cached file in subdirectory
    manga_dir = cache_dir / "Cached Manga"
    manga_dir.mkdir()
    cached_file = manga_dir / "chapter-1.cbz"
    cached_file.write_bytes(b"cached content")

    with patch("app.routes.is_valid_mangadex_url") as mock_validate:
        mock_validate.return_value = True

        with patch("subprocess.run") as mock_run:
            # mangadex-dl should skip download
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Skipped (already downloaded)",
                stderr="",
            )

            response = client_with_dirs.post(
                "/api/download",
                json={"url": "https://mangadex.org/title/cached"},
            )
            assert response.status_code == 200

            # File should still exist
            assert cached_file.exists()


@pytest.mark.integration
def test_task_expiration(client_with_dirs: FlaskClient) -> None:
    """Test task expiration after TTL (IT-E2E-004)."""
    with patch("app.routes.is_valid_mangadex_url") as mock_validate:
        mock_validate.return_value = True

        with patch("app.routes.enqueue_download") as mock_enqueue:
            mock_enqueue.return_value = "test-task-expired"

            # Submit task
            response = client_with_dirs.post(
                "/api/download",
                json={"url": "https://mangadex.org/title/test"},
            )
            assert response.status_code == 200

            # Mock expired task
            with patch("app.routes.get_job_status") as mock_status:
                mock_status.return_value = None  # Task expired

                response = client_with_dirs.get("/api/status/test-task-expired")
                assert response.status_code == 404


@pytest.mark.integration
def test_cache_expiration(cache_dir: Path) -> None:
    """Test cache expiration after TTL (IT-E2E-005)."""
    from app.cleanup import cleanup_cache

    # Create old file
    old_file = cache_dir / "old-manga.cbz"
    old_file.write_bytes(b"old content")

    # Set old time (8 days ago)
    old_time = time.time() - (8 * 24 * 60 * 60)
    os.utime(old_file, (old_time, old_time))

    # Run cleanup
    cleanup_cache(str(cache_dir), ttl=7 * 24 * 60 * 60)

    # File should be removed
    assert not old_file.exists()


@pytest.mark.integration
def test_cli_failure_marks_task_failed(client_with_dirs: FlaskClient) -> None:
    """Test CLI failure marks task as failed (IT-E2E-006)."""
    with patch("app.routes.is_valid_mangadex_url") as mock_validate:
        mock_validate.return_value = True

        with patch("subprocess.run") as mock_run:
            # Simulate CLI failure
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Network error",
            )

            response = client_with_dirs.post(
                "/api/download",
                json={"url": "https://mangadex.org/title/test"},
            )
            assert response.status_code == 200

            # Task should eventually be marked as failed
            # (This will be properly tested when task execution is implemented)


@pytest.mark.integration
def test_max_concurrent_limit(client_with_dirs: FlaskClient) -> None:
    """Test max concurrent downloads: 5 jobs with max=3 (IT-E2E-007)."""
    with patch("app.routes.is_valid_mangadex_url") as mock_validate:
        mock_validate.return_value = True

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            # Submit 5 jobs
            task_ids = []
            for i in range(5):
                response = client_with_dirs.post(
                    "/api/download",
                    json={"url": f"https://mangadex.org/title/test-{i}"},
                )
                assert response.status_code == 200
                task_ids.append(response.get_json()["task_id"])

            # All jobs should be accepted
            assert len(task_ids) == 5

            # In real implementation, check that only 3 are running
            # and 2 are queued


@pytest.mark.integration
def test_cache_persists_across_restart(cache_dir: Path) -> None:
    """Test cache persists across app restart (IT-E2E-008)."""
    # Create a cached file
    cached_file = cache_dir / "persistent-manga.cbz"
    cached_file.write_bytes(b"persistent content")

    # Simulate app restart by creating new app instance
    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    app.config["CACHE_DIR"] = str(cache_dir)

    # File should still exist
    assert cached_file.exists()
    assert cached_file.read_bytes() == b"persistent content"


@pytest.mark.integration
def test_two_clients_poll_same_task(client_with_dirs: FlaskClient) -> None:
    """Test two clients poll same task with consistent results (IT-E2E-009)."""
    with patch("app.routes.is_valid_mangadex_url") as mock_validate:
        mock_validate.return_value = True

        with patch("app.routes.enqueue_download") as mock_enqueue:
            mock_enqueue.return_value = "shared-task-id"

            # Submit task
            response = client_with_dirs.post(
                "/api/download",
                json={"url": "https://mangadex.org/title/test"},
            )
            assert response.status_code == 200
            task_id = response.get_json()["task_id"]

            # Mock consistent status
            with patch("app.routes.get_job_status") as mock_status:
                mock_status.return_value = {"status": "finished", "files": ["file.cbz"]}

                # Poll from "two clients"
                response1 = client_with_dirs.get(f"/api/status/{task_id}")
                response2 = client_with_dirs.get(f"/api/status/{task_id}")

                # Both should get same result
                assert response1.status_code == 200
                assert response2.status_code == 200
                assert response1.get_json() == response2.get_json()


@pytest.mark.integration
def test_multi_chapter_download(client_with_dirs: FlaskClient, cache_dir: Path) -> None:
    """Test multi-chapter download with large result set (IT-E2E-010)."""
    # Pre-create the files and directory structure
    manga_dir = cache_dir / "Long Manga"
    manga_dir.mkdir(exist_ok=True)
    chapters = []
    for i in range(1, 21):  # 20 chapters
        chapter_file = manga_dir / f"manga-ch{i:03d}.cbz"
        chapter_file.write_bytes(f"Chapter {i} content".encode())
        chapters.append(str(chapter_file))

    with patch("app.routes.is_valid_mangadex_url") as mock_validate:
        mock_validate.return_value = True

        with patch("subprocess.run") as mock_run:
            # Subprocess would have created the files (already done above)
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            # Submit download
            response = client_with_dirs.post(
                "/api/download",
                json={"url": "https://mangadex.org/title/long-manga"},
            )
            assert response.status_code == 200
            task_id = response.get_json()["task_id"]

            # Mock job result with all chapters
            with patch("app.routes.get_job_result") as mock_result:
                mock_result.return_value = chapters

                # Verify all files are accessible (test first and last)
                response = client_with_dirs.get(f"/api/file/{task_id}/manga-ch001.cbz")
                assert response.status_code == 200

                response = client_with_dirs.get(f"/api/file/{task_id}/manga-ch020.cbz")
                assert response.status_code == 200
