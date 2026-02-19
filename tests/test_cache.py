#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""Tests for Redis-backed cache metadata operations."""

from pathlib import Path

import fakeredis
import pytest

from app.cache import (
    cleanup_stale_metadata,
    delete_manga_metadata,
    get_cached_manga,
    list_cached_mangas,
    store_manga_metadata,
)


@pytest.fixture
def redis_conn() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis(decode_responses=True)


def test_store_manga_metadata(redis_conn: fakeredis.FakeRedis) -> None:
    """Store metadata and retrieve it via hgetall."""
    store_manga_metadata(
        redis_conn,
        url="https://mangadex.org/title/abc",
        series_name="Test Manga",
        cache_path="/downloads/cache/Test Manga",
        files=["ch1.cbz", "ch2.cbz"],
    )

    result = get_cached_manga(redis_conn, "Test Manga")
    assert result is not None
    assert result["url"] == "https://mangadex.org/title/abc"
    assert result["name"] == "Test Manga"
    assert result["cache_path"] == "/downloads/cache/Test Manga"
    assert set(result["files"]) == {"ch1.cbz", "ch2.cbz"}  # type: ignore[arg-type]
    assert result["download_date"] != ""


def test_store_manga_metadata_updates_existing(redis_conn: fakeredis.FakeRedis) -> None:
    """Second store merges files with existing ones (no duplicates)."""
    store_manga_metadata(
        redis_conn,
        url="https://mangadex.org/title/abc",
        series_name="Test Manga",
        cache_path="/downloads/cache/Test Manga",
        files=["ch1.cbz", "ch2.cbz"],
    )
    store_manga_metadata(
        redis_conn,
        url="https://mangadex.org/title/abc",
        series_name="Test Manga",
        cache_path="/downloads/cache/Test Manga",
        files=["ch2.cbz", "ch3.cbz"],
    )

    result = get_cached_manga(redis_conn, "Test Manga")
    assert result is not None
    assert set(result["files"]) == {"ch1.cbz", "ch2.cbz", "ch3.cbz"}  # type: ignore[arg-type]


def test_list_cached_mangas(redis_conn: fakeredis.FakeRedis) -> None:
    """list_cached_mangas returns all stored series."""
    store_manga_metadata(
        redis_conn,
        url="https://mangadex.org/title/a",
        series_name="Series A",
        cache_path="/cache/Series A",
        files=["ch1.cbz"],
    )
    store_manga_metadata(
        redis_conn,
        url="https://mangadex.org/title/b",
        series_name="Series B",
        cache_path="/cache/Series B",
        files=["ch2.cbz"],
    )

    results = list_cached_mangas(redis_conn)
    names = [r["name"] for r in results]
    assert "Series A" in names
    assert "Series B" in names


def test_list_cached_mangas_empty(redis_conn: fakeredis.FakeRedis) -> None:
    """list_cached_mangas returns empty list when Redis has no entries."""
    assert list_cached_mangas(redis_conn) == []


def test_get_cached_manga(redis_conn: fakeredis.FakeRedis) -> None:
    """get_cached_manga returns correct metadata for known series."""
    store_manga_metadata(
        redis_conn,
        url="https://mangadex.org/title/xyz",
        series_name="My Manga",
        cache_path="/cache/My Manga",
        files=["ch1.cbz"],
    )

    result = get_cached_manga(redis_conn, "My Manga")
    assert result is not None
    assert result["name"] == "My Manga"
    assert result["url"] == "https://mangadex.org/title/xyz"


def test_get_cached_manga_not_found(redis_conn: fakeredis.FakeRedis) -> None:
    """get_cached_manga returns None for unknown series."""
    assert get_cached_manga(redis_conn, "Nonexistent Manga") is None


def test_delete_manga_metadata(redis_conn: fakeredis.FakeRedis) -> None:
    """delete_manga_metadata removes the Redis key."""
    store_manga_metadata(
        redis_conn,
        url="https://mangadex.org/title/abc",
        series_name="Delete Me",
        cache_path="/cache/Delete Me",
        files=["ch1.cbz"],
    )
    delete_manga_metadata(redis_conn, "Delete Me")
    assert get_cached_manga(redis_conn, "Delete Me") is None


def test_cleanup_stale_metadata(
    redis_conn: fakeredis.FakeRedis,
    tmp_path: Path,
) -> None:
    """cleanup_stale_metadata removes entries whose files no longer exist."""
    cache_dir = tmp_path / "cache" / "Stale Manga"
    cache_dir.mkdir(parents=True)

    # Store metadata pointing to a non-existent file
    store_manga_metadata(
        redis_conn,
        url="https://mangadex.org/title/stale",
        series_name="Stale Manga",
        cache_path=str(cache_dir),
        files=["missing.cbz"],
    )

    deleted = cleanup_stale_metadata(redis_conn)
    assert deleted == 1
    assert get_cached_manga(redis_conn, "Stale Manga") is None


def test_cleanup_stale_metadata_keeps_existing_files(
    redis_conn: fakeredis.FakeRedis,
    tmp_path: Path,
) -> None:
    """cleanup_stale_metadata keeps entries that still have files on disk."""
    cache_dir = tmp_path / "cache" / "Active Manga"
    cache_dir.mkdir(parents=True)
    (cache_dir / "ch1.cbz").write_bytes(b"data")

    store_manga_metadata(
        redis_conn,
        url="https://mangadex.org/title/active",
        series_name="Active Manga",
        cache_path=str(cache_dir),
        files=["ch1.cbz"],
    )

    deleted = cleanup_stale_metadata(redis_conn)
    assert deleted == 0
    assert get_cached_manga(redis_conn, "Active Manga") is not None
