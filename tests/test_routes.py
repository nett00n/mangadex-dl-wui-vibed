#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""Tests for Flask routes."""

from pathlib import Path
from unittest.mock import patch

from flask.testing import FlaskClient


def test_index_route(client: FlaskClient) -> None:
    """Test the index route renders successfully (IT-API-013).

    Args:
        client: Flask test client
    """
    response = client.get("/")
    assert response.status_code == 200
    assert b"mangadex-dl-wui-vibed" in response.data


def test_download_valid_url(client: FlaskClient) -> None:
    """Test POST /api/download with valid URL (IT-API-001)."""
    with patch("app.routes.is_valid_mangadex_url") as mock_validate:
        mock_validate.return_value = True

        with patch("app.routes.enqueue_download") as mock_enqueue:
            mock_enqueue.return_value = "test-task-id-123"

            response = client.post(
                "/api/download",
                json={"url": "https://mangadex.org/title/test-123"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert "task_id" in data
            assert data["task_id"] == "test-task-id-123"


def test_download_invalid_url(client: FlaskClient) -> None:
    """Test POST /api/download with invalid URL (IT-API-002)."""
    with patch("app.routes.is_valid_mangadex_url") as mock_validate:
        mock_validate.return_value = False

        response = client.post(
            "/api/download",
            json={"url": "https://example.com/invalid"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


def test_download_missing_url(client: FlaskClient) -> None:
    """Test POST /api/download with missing URL (IT-API-003)."""
    response = client.post("/api/download", json={})

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_status_queued(client: FlaskClient) -> None:
    """Test GET /api/status/<id> for queued job (IT-API-004)."""
    with patch("app.routes.get_job_status") as mock_get_status:
        mock_get_status.return_value = {"status": "queued", "progress": {}}

        response = client.get("/api/status/test-id")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "queued"


def test_status_running(client: FlaskClient) -> None:
    """Test GET /api/status/<id> for running job (IT-API-005)."""
    with patch("app.routes.get_job_status") as mock_get_status:
        mock_get_status.return_value = {
            "status": "started",
            "progress": {"current": 5, "total": 10},
        }

        response = client.get("/api/status/test-id")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "started"
        assert "progress" in data


def test_status_completed(client: FlaskClient) -> None:
    """Test GET /api/status/<id> for completed job (IT-API-006)."""
    with patch("app.routes.get_job_status") as mock_get_status:
        mock_get_status.return_value = {
            "status": "finished",
            "files": ["manga-ch1.cbz", "manga-ch2.cbz"],
        }

        response = client.get("/api/status/test-id")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "finished"
        assert "files" in data


def test_status_completed_enriches_with_files(client: FlaskClient) -> None:
    """Test GET /api/status/<id> enriches finished jobs with files."""
    with (
        patch("app.routes.get_job_status") as mock_get_status,
        patch("app.routes.get_job_result") as mock_get_result,
    ):
        # get_job_status returns finished without files
        mock_get_status.return_value = {"status": "finished"}

        # get_job_result provides the files
        mock_get_result.return_value = ["manga-ch1.cbz", "manga-ch2.cbz"]

        response = client.get("/api/status/test-id")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "finished"
        assert "files" in data
        assert data["files"] == ["manga-ch1.cbz", "manga-ch2.cbz"]

        # Verify get_job_result was called
        mock_get_result.assert_called_once_with("test-id")


def test_status_failed(client: FlaskClient) -> None:
    """Test GET /api/status/<id> for failed job (IT-API-007)."""
    with patch("app.routes.get_job_status") as mock_get_status:
        mock_get_status.return_value = {"status": "failed", "error": "Download error"}

        response = client.get("/api/status/test-id")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "failed"
        assert "error" in data


def test_status_invalid_id(client: FlaskClient) -> None:
    """Test GET /api/status/<id> for invalid ID (IT-API-008)."""
    with patch("app.routes.get_job_status") as mock_get_status:
        mock_get_status.return_value = None

        response = client.get("/api/status/invalid-id")

        assert response.status_code == 404


def test_file_download_success(
    client_with_dirs: FlaskClient,
    sample_cbz_file: Path,
) -> None:
    """Test GET /api/file/<id>/<name> success (IT-API-009)."""
    task_id = "test-task-123"
    filename = sample_cbz_file.name

    with patch("app.routes.get_job_result") as mock_get_result:
        mock_get_result.return_value = [str(sample_cbz_file)]

        response = client_with_dirs.get(f"/api/file/{task_id}/{filename}")

        assert response.status_code == 200
        assert response.data == b"fake cbz content"


def test_file_not_found(client: FlaskClient) -> None:
    """Test GET /api/file/<id>/<name> file not found (IT-API-010)."""
    with patch("app.routes.get_job_result") as mock_get_result:
        mock_get_result.return_value = []

        response = client.get("/api/file/test-id/nonexistent.cbz")

        assert response.status_code == 404


def test_file_path_traversal(client: FlaskClient) -> None:
    """Test GET /api/file/<id>/<name> path traversal attempt (IT-API-011)."""
    response = client.get("/api/file/test-id/../../../etc/passwd")

    # Should reject path traversal
    assert response.status_code in [403, 404]


def test_file_wrong_task(client_with_dirs: FlaskClient, sample_cbz_file: Path) -> None:
    """Test GET /api/file/<id>/<name> wrong task file (IT-API-012)."""
    with patch("app.routes.get_job_result") as mock_get_result:
        # Job result doesn't include requested file
        mock_get_result.return_value = ["/other/path/other-file.cbz"]

        response = client_with_dirs.get(f"/api/file/test-id/{sample_cbz_file.name}")

        assert response.status_code in [403, 404]


def test_no_cors_headers(client: FlaskClient) -> None:
    """Test responses don't include CORS headers (IT-API-014)."""
    response = client.get("/")

    # Should not have CORS headers
    assert "Access-Control-Allow-Origin" not in response.headers


def test_cbz_content_type(client_with_dirs: FlaskClient, sample_cbz_file: Path) -> None:
    """Test CBZ file has correct content-type (IT-API-015)."""
    task_id = "test-task-123"
    filename = sample_cbz_file.name

    with patch("app.routes.get_job_result") as mock_get_result:
        mock_get_result.return_value = [str(sample_cbz_file)]

        response = client_with_dirs.get(f"/api/file/{task_id}/{filename}")

        assert response.status_code == 200
        # Accept either CBZ-specific or generic binary content-type
        assert response.content_type in [
            "application/x-cbz",
            "application/octet-stream",
            "application/zip",
        ]
