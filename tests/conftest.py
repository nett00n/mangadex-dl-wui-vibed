#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""Pytest configuration and fixtures."""

import threading
from collections.abc import Generator
from pathlib import Path

import fakeredis
import pytest
from flask import Flask
from flask.testing import FlaskClient
from rq import Queue
from werkzeug.serving import make_server

from app import create_app


@pytest.fixture
def app() -> Flask:
    """Create Flask application for testing.

    Returns:
        Flask: Test application instance
    """
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create Flask test client.

    Args:
        app: Flask application instance

    Returns:
        FlaskClient: Test client
    """
    return app.test_client()


@pytest.fixture
def fake_redis_conn() -> fakeredis.FakeRedis:
    """Create a fake Redis connection for testing.

    Returns:
        fakeredis.FakeRedis: Fake Redis instance
    """
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def rq_queue(fake_redis_conn: fakeredis.FakeRedis) -> Queue:
    """Create an RQ queue backed by fake Redis.

    Args:
        fake_redis_conn: Fake Redis connection

    Returns:
        Queue: RQ queue instance
    """
    return Queue(connection=fake_redis_conn, is_async=False)


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Create a temporary cache directory.

    Args:
        tmp_path: Pytest temporary path fixture

    Returns:
        Path: Cache directory path
    """
    cache = tmp_path / "cache"
    cache.mkdir()
    return cache


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create a temporary temp directory.

    Args:
        tmp_path: Pytest temporary path fixture

    Returns:
        Path: Temp directory path
    """
    temp = tmp_path / "temp"
    temp.mkdir()
    return temp


@pytest.fixture
def sample_cbz_file(cache_dir: Path) -> Path:
    """Create a dummy CBZ file for testing.

    Args:
        cache_dir: Cache directory path

    Returns:
        Path: Path to created CBZ file
    """
    cbz_file = cache_dir / "test-manga.cbz"
    cbz_file.write_bytes(b"fake cbz content")
    return cbz_file


@pytest.fixture
def sample_cbz_in_series_dir(cache_dir: Path) -> Path:
    """Create a dummy CBZ file inside a series subdirectory for testing.

    Args:
        cache_dir: Cache directory path

    Returns:
        Path: Path to created CBZ file (under cache_dir/Test Series/)
    """
    series_dir = cache_dir / "Test Series"
    series_dir.mkdir()
    cbz_file = series_dir / "test-chapter.cbz"
    cbz_file.write_bytes(b"fake cbz content")
    return cbz_file


@pytest.fixture
def app_with_dirs(cache_dir: Path, temp_dir: Path) -> Flask:
    """Create Flask app with custom cache and temp directories.

    Args:
        cache_dir: Cache directory path
        temp_dir: Temp directory path

    Returns:
        Flask: Test application instance
    """
    app = create_app()
    app.config["TESTING"] = True
    app.config["CACHE_DIR"] = str(cache_dir)
    app.config["TEMP_DIR"] = str(temp_dir)
    return app


@pytest.fixture
def client_with_dirs(app_with_dirs: Flask) -> FlaskClient:
    """Create Flask test client with custom directories.

    Args:
        app_with_dirs: Flask app with custom directories

    Returns:
        FlaskClient: Test client
    """
    return app_with_dirs.test_client()


class LiveServer:
    """Live server for UI testing."""

    def __init__(self, app: Flask, port: int = 5000):
        self.app = app
        self.port = port
        self.server = make_server("127.0.0.1", port, app, threaded=True)
        self.thread = threading.Thread(target=self.server.serve_forever)

    def start(self):
        """Start the server in a background thread."""
        self.thread.start()

    def stop(self):
        """Stop the server."""
        self.server.shutdown()
        self.thread.join()

    @property
    def url(self) -> str:
        """Get the server URL."""
        return f"http://127.0.0.1:{self.port}"


@pytest.fixture
def live_server(app: Flask) -> Generator[LiveServer, None, None]:
    """Create a live Flask server for UI testing.

    Args:
        app: Flask application instance

    Yields:
        LiveServer: Running server instance
    """
    server = LiveServer(app, port=5555)
    server.start()
    yield server
    server.stop()


@pytest.fixture
def mock_task_status() -> dict[str, dict[str, str | dict[str, int] | list[str]]]:
    """Fixture to mock task status responses for UI tests.

    Returns:
        dict: Mapping of URL patterns to status responses
    """
    return {
        "test-running": {
            "status": "started",
        },
        "test-completed": {
            "status": "finished",
            "files": ["/cache/chapter-1.cbz", "/cache/chapter-2.cbz"],
        },
        "test-failed": {
            "status": "failed",
            "error": "Download failed: Connection timeout",
        },
    }


@pytest.fixture
def live_server_with_mocks(
    app: Flask,
    mock_task_status: dict[str, dict[str, str | dict[str, int] | list[str]]],
) -> Generator[LiveServer, None, None]:
    """Create a live Flask server with mocked responses for UI testing.

    Args:
        app: Flask application instance
        mock_task_status: Status mocks

    Yields:
        LiveServer: Running server instance with mocks
    """
    from unittest.mock import patch

    # Track task IDs to status mapping
    task_url_map = {}

    def mock_enqueue(url: str) -> str:
        import uuid

        task_id = str(uuid.uuid4())
        # Determine status based on URL pattern
        if "test-running" in url:
            task_url_map[task_id] = "test-running"
        elif "test-completed" in url:
            task_url_map[task_id] = "test-completed"
        elif "test-failed" in url:
            task_url_map[task_id] = "test-failed"
        else:
            task_url_map[task_id] = "default"
        return task_id

    def mock_get_status(task_id: str) -> dict[str, str | dict[str, int] | list[str]]:
        # Get status based on task ID mapping
        pattern = task_url_map.get(task_id, "default")
        if pattern in mock_task_status:
            return mock_task_status[pattern]
        # Default to queued
        return {"status": "queued"}

    with patch("app.routes.enqueue_download", side_effect=mock_enqueue):
        with patch("app.routes.get_job_status", side_effect=mock_get_status):
            server = LiveServer(app, port=5556)
            server.start()
            yield server
            server.stop()
