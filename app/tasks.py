"""RQ job management utilities."""

import redis
from rq import Queue
from rq.job import Job

from app import worker
from app.config import Config
from app.worker import perform_download_job  # noqa: F401 - imported for test patching

_redis_conn = None
_queue = None


def _get_redis_connection() -> redis.Redis:  # type: ignore[type-arg]
    """Get or create Redis connection."""
    global _redis_conn
    if _redis_conn is None:
        _redis_conn = redis.from_url(Config.REDIS_URL)
    return _redis_conn


def get_queue() -> Queue:
    """Get or create RQ queue."""
    global _queue
    if _queue is None:
        _queue = Queue(connection=_get_redis_connection())
    return _queue


def enqueue_download(url: str) -> str:
    """Enqueue a download job in the Redis queue.

    Args:
        url: MangaDex URL to download

    Returns:
        str: Job ID (UUID)
    """
    queue = get_queue()
    job = queue.enqueue(
        worker.perform_download_job,
        url,
        result_ttl=Config.TASK_TTL_SECONDS,
    )
    return job.id


def get_job_status(job_id: str) -> dict[str, str] | None:
    """Get the status of a job.

    Args:
        job_id: Job identifier

    Returns:
        dict | None: Job status information or None if not found
    """
    queue = get_queue()
    try:
        job = Job.fetch(job_id, connection=queue.connection)
    except Exception:
        return None

    if job is None:
        return None

    # Get status - prefer _status if available (for testing), otherwise use get_status()
    status_obj = getattr(job, "_status", None)
    if status_obj is None:
        status_obj = job.get_status()

    # Convert JobStatus enum to string if needed
    status = status_obj.value if hasattr(status_obj, "value") else str(status_obj)
    result_dict = {"status": status}

    if status == "failed":
        # Get error info if available
        error = getattr(job, "exc_info", None)
        if error:
            result_dict["error"] = error

    return result_dict


def get_job_result(job_id: str) -> list[str] | None:
    """Get the result of a completed job.

    Args:
        job_id: Job identifier

    Returns:
        list[str] | None: List of file paths or None if not completed
    """
    queue = get_queue()
    try:
        job = Job.fetch(job_id, connection=queue.connection)
    except Exception:
        return None

    if job is None:
        return None

    # Check if job is finished
    status = getattr(job, "_status", None) or job.get_status()
    if status == "finished":
        # Try to get result
        result = getattr(job, "_result", None)
        if result is not None:
            return result
        try:
            return job.result
        except Exception:
            return None

    return None


def list_queued_jobs() -> list[str]:
    """List all queued job IDs.

    Returns:
        list[str]: List of job IDs
    """
    queue = get_queue()
    return [job.id for job in queue.jobs]


def cancel_job(job_id: str) -> bool:
    """Cancel a queued or running job.

    Args:
        job_id: Job identifier

    Returns:
        bool: True if cancelled, False otherwise
    """
    queue = get_queue()
    try:
        job = Job.fetch(job_id, connection=queue.connection)
    except Exception:
        return False

    if job is None:
        return False

    job.cancel()
    return True
