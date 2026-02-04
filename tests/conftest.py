"""Pytest configuration and fixtures."""

import pytest
from flask import Flask
from flask.testing import FlaskClient

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
