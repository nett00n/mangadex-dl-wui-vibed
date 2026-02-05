"""Tests for URL validation."""

import pytest

from app.validators import is_valid_mangadex_url


@pytest.mark.parametrize(
    "url",
    [
        pytest.param(
            "https://mangadex.org/title/abc-123",
            id="UT-VAL-001",
        ),
        pytest.param(
            "https://mangadex.org/title/12345678-1234-1234-1234-123456789abc",
            id="UT-VAL-002",
        ),
        pytest.param(
            "https://mangadex.org/title/abc-123?tab=chapters",
            id="UT-VAL-009",
        ),
    ],
)
def test_valid_mangadex_urls(url: str) -> None:
    """Test that valid MangaDex URLs are accepted.

    Args:
        url: URL to validate
    """
    assert is_valid_mangadex_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        pytest.param(
            "https://example.com/title/abc-123",
            id="UT-VAL-003",
        ),
        pytest.param(
            "https://mangadex.org/chapter/abc-123",
            id="UT-VAL-004",
        ),
        pytest.param(
            "mangadex.org/title/abc-123",
            id="UT-VAL-005",
        ),
        pytest.param(
            "http://mangadex.org/title/abc-123",
            id="UT-VAL-006",
        ),
        pytest.param(
            "",
            id="UT-VAL-007",
        ),
    ],
)
def test_invalid_mangadex_urls(url: str) -> None:
    """Test that invalid MangaDex URLs are rejected.

    Args:
        url: URL to validate
    """
    assert is_valid_mangadex_url(url) is False


def test_none_input() -> None:
    """Test that None input is rejected (UT-VAL-008)."""
    assert is_valid_mangadex_url(None) is False  # type: ignore[arg-type]


def test_path_traversal() -> None:
    """Test that path traversal attempts are rejected (UT-VAL-010)."""
    url = "https://mangadex.org/title/../../../etc/passwd"
    assert is_valid_mangadex_url(url) is False
