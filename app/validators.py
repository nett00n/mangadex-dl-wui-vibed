"""URL validation utilities."""

from urllib.parse import urlparse


def is_valid_mangadex_url(url: str | None) -> bool:
    """Validate if a URL is a valid MangaDex title URL.

    Args:
        url: URL string to validate

    Returns:
        bool: True if valid MangaDex URL, False otherwise
    """
    # Guard: None or empty string
    if not url:
        return False

    # Parse the URL
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    # Scheme must be https
    if parsed.scheme != "https":
        return False

    # Domain must be exactly mangadex.org
    if parsed.netloc.lower() != "mangadex.org":
        return False

    # Path must start with /title/ and have a title ID
    path = parsed.path
    if not path.startswith("/title/"):
        return False

    # Title ID must not be empty
    title_id = path[7:]  # len("/title/") == 7
    if not title_id:
        return False

    # Security: Reject path traversal attempts
    return ".." not in path
