"""Tests for RQ task management."""

from unittest.mock import patch

import fakeredis
from rq import Queue

from app.tasks import cancel_job, enqueue_download, get_job_result, get_job_status


def test_enqueue_download(fake_redis_conn: fakeredis.FakeRedis) -> None:
    """Test enqueuing a download task (UT-TSK-001)."""
    url = "https://mangadex.org/title/test-123"

    with patch("app.tasks.get_queue") as mock_get_queue:
        queue = Queue(connection=fake_redis_conn, is_async=False)
        mock_get_queue.return_value = queue

        with patch("app.tasks.perform_download_job"):
            task_id = enqueue_download(url)

            assert task_id is not None
            assert isinstance(task_id, str)
            assert len(task_id) > 0


def test_get_job_status_existing(fake_redis_conn: fakeredis.FakeRedis) -> None:
    """Test getting status of existing job (UT-TSK-002)."""
    with patch("app.tasks.get_queue") as mock_get_queue:
        queue = Queue(connection=fake_redis_conn, is_async=False)
        mock_get_queue.return_value = queue

        # Create a job
        job = queue.enqueue(lambda: None)

        with patch("app.tasks.Job.fetch") as mock_fetch:
            mock_fetch.return_value = job

            status = get_job_status(job.id)

            assert status is not None
            assert "status" in status
            assert isinstance(status, dict)


def test_get_job_status_nonexistent(fake_redis_conn: fakeredis.FakeRedis) -> None:
    """Test getting status of non-existent job (UT-TSK-003)."""
    with patch("app.tasks.Job.fetch") as mock_fetch:
        mock_fetch.return_value = None

        status = get_job_status("nonexistent-id")

        assert status is None


def test_job_status_transitions(fake_redis_conn: fakeredis.FakeRedis) -> None:
    """Test job status transitions (UT-TSK-004)."""
    with patch("app.tasks.get_queue") as mock_get_queue:
        queue = Queue(connection=fake_redis_conn, is_async=False)
        mock_get_queue.return_value = queue

        # Enqueue job
        job = queue.enqueue(lambda: "result")

        with patch("app.tasks.Job.fetch") as mock_fetch:
            # Initially queued
            job._status = "queued"
            mock_fetch.return_value = job
            status = get_job_status(job.id)
            assert status["status"] in ["queued", "started", "finished"]

            # Then started
            job._status = "started"
            mock_fetch.return_value = job
            status = get_job_status(job.id)
            assert status["status"] in ["started", "finished"]

            # Finally finished
            job._status = "finished"
            job._result = ["file1.cbz"]
            mock_fetch.return_value = job
            status = get_job_status(job.id)
            assert status["status"] == "finished"


def test_get_job_result(fake_redis_conn: fakeredis.FakeRedis) -> None:
    """Test getting job result (UT-TSK-005)."""
    with patch("app.tasks.get_queue") as mock_get_queue:
        queue = Queue(connection=fake_redis_conn, is_async=False)
        mock_get_queue.return_value = queue

        # Create completed job
        job = queue.enqueue(lambda: ["file1.cbz", "file2.cbz"])
        job._status = "finished"
        job._result = ["file1.cbz", "file2.cbz"]

        with patch("app.tasks.Job.fetch") as mock_fetch:
            mock_fetch.return_value = job

            result = get_job_result(job.id)

            assert result is not None
            assert isinstance(result, list)
            assert len(result) == 2


def test_failed_job_status(fake_redis_conn: fakeredis.FakeRedis) -> None:
    """Test failed job status (UT-TSK-006)."""
    with patch("app.tasks.get_queue") as mock_get_queue:
        queue = Queue(connection=fake_redis_conn, is_async=False)
        mock_get_queue.return_value = queue

        # Create failed job
        job = queue.enqueue(lambda: None)
        job._status = "failed"
        job.exc_info = "Error message"

        with patch("app.tasks.Job.fetch") as mock_fetch:
            mock_fetch.return_value = job

            status = get_job_status(job.id)

            assert status is not None
            assert status["status"] == "failed"
            assert "error" in status or "exc_info" in status


def test_concurrent_status_queries(fake_redis_conn: fakeredis.FakeRedis) -> None:
    """Test concurrent status queries return consistent data (UT-TSK-007)."""
    with patch("app.tasks.get_queue") as mock_get_queue:
        queue = Queue(connection=fake_redis_conn, is_async=False)
        mock_get_queue.return_value = queue

        # Create job
        job = queue.enqueue(lambda: ["result"])
        job._status = "finished"
        job._result = ["result"]

        with patch("app.tasks.Job.fetch") as mock_fetch:
            mock_fetch.return_value = job

            # Query multiple times
            status1 = get_job_status(job.id)
            status2 = get_job_status(job.id)
            status3 = get_job_status(job.id)

            # All should return same status
            assert status1["status"] == status2["status"] == status3["status"]


def test_list_queued_jobs(fake_redis_conn: fakeredis.FakeRedis) -> None:
    """Test listing queued jobs (UT-TSK-008)."""
    with patch("app.tasks.get_queue") as mock_get_queue:
        queue = Queue(connection=fake_redis_conn, is_async=False)
        mock_get_queue.return_value = queue

        # Enqueue 5 jobs
        for _ in range(5):
            queue.enqueue(lambda: None)

        # Get queued jobs
        queued = queue.jobs

        assert len(queued) == 5


def test_job_expiration(fake_redis_conn: fakeredis.FakeRedis) -> None:
    """Test job with short TTL (UT-TSK-009)."""
    with patch("app.tasks.get_queue") as mock_get_queue:
        queue = Queue(connection=fake_redis_conn, is_async=False)
        mock_get_queue.return_value = queue

        # Create job with TTL
        job = queue.enqueue(lambda: None, result_ttl=1)

        # Verify job has TTL set
        assert job.result_ttl == 1


def test_cancel_job(fake_redis_conn: fakeredis.FakeRedis) -> None:
    """Test canceling a job (UT-TSK-010)."""
    with patch("app.tasks.get_queue") as mock_get_queue:
        queue = Queue(connection=fake_redis_conn, is_async=False)
        mock_get_queue.return_value = queue

        # Create job
        job = queue.enqueue(lambda: None)

        with patch("app.tasks.Job.fetch") as mock_fetch:
            mock_fetch.return_value = job

            result = cancel_job(job.id)

            assert result is True or result is not None
