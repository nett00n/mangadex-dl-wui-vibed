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


def test_file_download_has_series_prefix_in_filename(
    client_with_dirs: FlaskClient,
    sample_cbz_in_series_dir: Path,
) -> None:
    """Test Content-Disposition filename includes series name prefix (IT-API-016)."""
    task_id = "test-task-series-123"
    filename = sample_cbz_in_series_dir.name
    cache_dir = str(sample_cbz_in_series_dir.parent.parent)

    with (
        patch("app.routes.get_job_result") as mock_get_result,
        patch("app.routes.Config") as mock_config,
    ):
        mock_get_result.return_value = [str(sample_cbz_in_series_dir)]
        mock_config.CACHE_DIR = cache_dir

        response = client_with_dirs.get(f"/api/file/{task_id}/{filename}")

        assert response.status_code == 200
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "Test Series" in content_disposition
        assert filename in content_disposition


# --- Cache page and cache file API tests ---


def test_cache_page_renders(client: FlaskClient) -> None:
    """GET /cache returns 200 (IT-CACHE-001)."""
    with patch("app.routes.list_cached_mangas") as mock_list:
        mock_list.return_value = []
        response = client.get("/cache")
        assert response.status_code == 200


def test_cache_page_shows_series(client: FlaskClient) -> None:
    """Cache page renders series cards with name and files (IT-CACHE-002)."""
    with patch("app.routes.list_cached_mangas") as mock_list:
        mock_list.return_value = [
            {
                "url": "https://mangadex.org/title/abc",
                "name": "Test Manga",
                "sanitized_name": "Test Manga",
                "cache_path": "/cache/Test Manga",
                "download_date": "2026-01-01T00:00:00+00:00",
                "files": ["ch1.cbz", "ch2.cbz"],
            },
        ]
        response = client.get("/cache")
        assert response.status_code == 200
        assert b"Test Manga" in response.data
        assert b"ch1.cbz" in response.data
        assert b"ch2.cbz" in response.data


def test_cache_file_download_success(
    client_with_dirs: FlaskClient,
    sample_cbz_in_series_dir: Path,
) -> None:
    """Serve cached file via /api/cache/<series>/<filename> (IT-CACHE-003)."""
    series = sample_cbz_in_series_dir.parent.name
    filename = sample_cbz_in_series_dir.name
    cache_dir = str(sample_cbz_in_series_dir.parent.parent)

    with patch("app.routes.Config") as mock_config:
        mock_config.CACHE_DIR = cache_dir

        response = client_with_dirs.get(f"/api/cache/{series}/{filename}")
        assert response.status_code == 200
        assert response.data == b"fake cbz content"


def test_cache_file_path_traversal_series(client: FlaskClient) -> None:
    """Reject '..' in series parameter (IT-CACHE-004)."""
    response = client.get("/api/cache/../etc/passwd/test.cbz")
    assert response.status_code in [403, 404]


def test_cache_file_path_traversal_filename(client: FlaskClient) -> None:
    """Reject '..' in filename parameter (IT-CACHE-005)."""
    response = client.get("/api/cache/some-series/../../etc/passwd")
    assert response.status_code in [403, 404]


def test_cache_file_not_found(client: FlaskClient, tmp_path: Path) -> None:
    """Missing file returns 404 (IT-CACHE-006)."""
    with patch("app.routes.Config") as mock_config:
        mock_config.CACHE_DIR = str(tmp_path)
        response = client.get("/api/cache/NoSeries/missing.cbz")
        assert response.status_code == 404


def test_delete_cache_series_success(client: FlaskClient) -> None:
    """DELETE /api/cache/<series> returns 200 and deletes series (IT-CACHE-007)."""
    with patch("app.routes.delete_cached_series") as mock_delete:
        mock_delete.return_value = True
        response = client.delete("/api/cache/My-Series")
        assert response.status_code == 200
        data = response.get_json()
        assert data == {"deleted": True}
        mock_delete.assert_called_once()


def test_delete_cache_series_not_found(client: FlaskClient) -> None:
    """DELETE /api/cache/<series> returns 404 when series absent (IT-CACHE-008)."""
    with patch("app.routes.delete_cached_series") as mock_delete:
        mock_delete.return_value = False
        response = client.delete("/api/cache/Unknown-Series")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data


def test_delete_cache_series_path_traversal(client: FlaskClient) -> None:
    """DELETE /api/cache/<series> rejects '..' with 403 (IT-CACHE-009)."""
    response = client.delete("/api/cache/evil..series")
    assert response.status_code == 403
    data = response.get_json()
    assert "error" in data


def test_cache_card_has_remove_button(client: FlaskClient) -> None:
    """Cache card has remove button with data-series attribute (IT-CACHE-010)."""
    with patch("app.routes.list_cached_mangas") as mock_list:
        mock_list.return_value = [
            {
                "url": "https://mangadex.org/title/abc",
                "name": "Test Manga",
                "sanitized_name": "Test Manga",
                "cache_path": "/cache/Test Manga",
                "download_date": "2026-01-01T00:00:00+00:00",
                "files": ["ch1.cbz"],
            },
        ]
        response = client.get("/cache")
        assert response.status_code == 200
        assert b"btn-remove-cache" in response.data
        assert b"Test Manga" in response.data


def test_cache_card_data_series_matches_file_path_component(
    client: FlaskClient,
) -> None:
    """manga.name rendered into data-series matches the directory in file paths (IT-CACHE-011).

    The JS on the cache page uses data-series to match against sessionStorage
    task file paths (e.g. /downloads/cache/<series>/ch.cbz). This test verifies
    the series name rendered into the DOM attribute is the same string that
    appears as a path component in file paths returned by the cache metadata.
    """
    series_name = "My Series"
    file_path = f"/downloads/cache/{series_name}/ch1.cbz"

    with patch("app.routes.list_cached_mangas") as mock_list:
        mock_list.return_value = [
            {
                "url": "https://mangadex.org/title/abc",
                "name": series_name,
                "sanitized_name": series_name,
                "cache_path": f"/downloads/cache/{series_name}",
                "download_date": "2026-01-01T00:00:00+00:00",
                "files": ["ch1.cbz"],
            },
        ]
        response = client.get("/cache")
        html = response.get_data(as_text=True)

    # The data-series value rendered in HTML must equal the directory component
    # in the file path so the JS sessionStorage cleanup can match them.
    path_component = file_path.split("/")[-2]
    assert series_name == path_component
    assert (
        f'data-series="{series_name}"' in html or f"data-series={series_name}" in html
    )


def test_index_contains_description(client: FlaskClient) -> None:
    """Description partial renders on index page."""
    response = client.get("/")
    # Minified HTML omits quotes on single-word attribute values
    assert b"class=description" in response.data


def test_index_contains_download_form(client: FlaskClient) -> None:
    """Download form partial renders on index page."""
    response = client.get("/")
    # Minified HTML omits quotes on single-word attribute values
    assert b"id=download-form" in response.data
    assert b"id=manga-url" in response.data
    assert b"id=submit-button" in response.data


def test_index_contains_footer(client: FlaskClient) -> None:
    """Footer partial renders on index page."""
    response = client.get("/")
    # Minified HTML omits quotes on single-word attribute values
    assert b"class=disclaimer" in response.data
    assert b"GPLv3" in response.data


def test_cache_card_structure(client: FlaskClient) -> None:
    """Cache page renders manga cards with expected structure."""
    with patch("app.routes.list_cached_mangas") as mock_list:
        mock_list.return_value = [
            {
                "url": "https://mangadex.org/title/abc",
                "name": "Test Manga",
                "sanitized_name": "Test Manga",
                "cache_path": "/cache/Test Manga",
                "download_date": "2026-01-01T00:00:00+00:00",
                "files": ["ch1.cbz"],
            },
        ]
        response = client.get("/cache")
        # Minified HTML omits quotes on single-word attribute values
        assert b"class=task-card" in response.data
        assert b"class=task-header" in response.data
        assert b"class=cache-series-name" in response.data
        # Multi-word class value keeps quotes in minified HTML
        assert b'class="status-badge' in response.data
        assert b"class=file-list" in response.data


def test_navbar_present_on_index(client: FlaskClient) -> None:
    """Navbar with Cache link appears on index page (IT-NAV-001)."""
    response = client.get("/")
    assert response.status_code == 200
    # Minified HTML omits quotes on single-word attribute values
    assert b"class=navbar" in response.data
    assert b"/cache" in response.data


def test_navbar_present_on_cache(client: FlaskClient) -> None:
    """Navbar with Home link appears on cache page (IT-NAV-002)."""
    with patch("app.routes.list_cached_mangas") as mock_list:
        mock_list.return_value = []
        response = client.get("/cache")
        assert response.status_code == 200
        # Minified HTML omits quotes on single-word attribute values
        assert b"class=navbar" in response.data
        assert b"Home" in response.data


# --- Inline assets and minification tests ---


def test_index_inlines_css(client: FlaskClient) -> None:
    """CSS is inlined in <style> tag, not linked externally."""
    response = client.get("/")
    assert b"<style>" in response.data
    assert b".navbar" in response.data  # CSS content present
    assert b'rel="stylesheet"' not in response.data  # no external link


def test_index_inlines_js(client: FlaskClient) -> None:
    """JS is inlined in <script> tag on index page."""
    response = client.get("/")
    # Check for a string literal from app.js that the JS minifier won't rename
    assert b"/api/download" in response.data  # app.js content present
    assert b"app.js" not in response.data  # no external script src


def test_cache_no_inline_js(client: FlaskClient) -> None:
    """Cache page does not include app.js (no scripts block)."""
    with patch("app.routes.list_cached_mangas") as mock_list:
        mock_list.return_value = []
        response = client.get("/cache")
        assert b"const UI" not in response.data


def test_favicon_served_as_static_file(client: FlaskClient) -> None:
    """Favicon references the assets static path."""
    response = client.get("/")
    assert b"/assets/logo/32x32.png" in response.data


def test_logo_served_as_static_file(client: FlaskClient) -> None:
    """Logo references the assets static path."""
    response = client.get("/")
    assert b"/assets/logo/128x128.png" in response.data


def test_html_is_minified(client: FlaskClient) -> None:
    """Rendered HTML is minified (no excessive whitespace)."""
    response = client.get("/")
    html = response.get_data(as_text=True)
    assert "\n    \n" not in html


def test_index_inlines_poll_config(client: FlaskClient) -> None:
    """Index page injects window.AppConfig with pollIntervalMs (IT-POLL-001)."""
    response = client.get("/")
    assert b"AppConfig" in response.data
    assert b"pollIntervalMs" in response.data


def test_index_poll_interval_default_is_2000ms(client: FlaskClient) -> None:
    """Index page injects default poll interval of 2000 ms (IT-POLL-002).

    The JS minifier converts 2000 to 2e3 in the output.
    """
    with patch("app.routes.Config") as mock_config:
        mock_config.POLL_INTERVAL_SECONDS = 2
        response = client.get("/")
    assert b"pollIntervalMs" in response.data
    # JS minifier rewrites 2000 as 2e3
    assert b"2e3" in response.data


def test_index_poll_interval_custom_value(client: FlaskClient) -> None:
    """Index page injects custom POLL_INTERVAL_SECONDS * 1000 ms (IT-POLL-003).

    The JS minifier converts 5000 to 5e3 in the output.
    """
    with patch("app.routes.Config") as mock_config:
        mock_config.POLL_INTERVAL_SECONDS = 5
        response = client.get("/")
    # JS minifier rewrites 5000 as 5e3
    assert b"5e3" in response.data
