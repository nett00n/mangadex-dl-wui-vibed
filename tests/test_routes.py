"""Tests for Flask routes."""

from flask.testing import FlaskClient


def test_index_route(client: FlaskClient) -> None:
    """Test the index route renders successfully.

    Args:
        client: Flask test client
    """
    response = client.get("/")
    assert response.status_code == 200
    assert b"mangadex-dl-wui" in response.data
