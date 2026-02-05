"""Pytest configuration and fixtures."""

from pathlib import Path

import fakeredis
import pytest
from flask import Flask
from flask.testing import FlaskClient
from rq import Queue

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
