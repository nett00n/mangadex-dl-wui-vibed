#
# Copyright (c) - All Rights Reserved.
#
# This project is licenced under the GPLv3.
# See the LICENSE file for more information.
#

"""Flask routes for the web UI and API endpoints."""

from pathlib import Path

from flask import Blueprint, jsonify, render_template, request, send_file
from werkzeug.wrappers.response import Response

from app.config import Config
from app.downloader import get_display_filename
from app.tasks import enqueue_download, get_job_result, get_job_status
from app.validators import is_valid_mangadex_url

bp = Blueprint("main", __name__)


@bp.route("/")  # type: ignore[misc]
def index() -> str:
    """Render the main web UI page.

    Returns:
        str: Rendered HTML template
    """
    return render_template("index.html")


@bp.route("/api/download", methods=["POST"])  # type: ignore[misc]
def api_download() -> tuple[Response, int]:
    """Queue a manga download task.

    Returns:
        tuple: JSON response with task_id and HTTP status code
    """
    # Get JSON body
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    # Validate required field
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing required field: url"}), 400

    # Validate URL
    if not is_valid_mangadex_url(url):
        return jsonify({"error": "Invalid MangaDex URL"}), 400

    # Enqueue download
    task_id = enqueue_download(url)

    return jsonify({"task_id": task_id}), 200


@bp.route("/api/status/<task_id>")  # type: ignore[misc]
def api_status(task_id: str) -> tuple[Response, int]:
    """Get the status of a download task.

    Args:
        task_id: Unique identifier for the task

    Returns:
        tuple: JSON response with task status and HTTP status code
    """
    status = get_job_status(task_id)

    if status is None:
        return jsonify({"error": "Task not found"}), 404

    # Include file list for finished tasks
    if status.get("status") == "finished":
        result = get_job_result(task_id)
        if result:
            status["files"] = result

    return jsonify(status), 200


@bp.route("/api/file/<task_id>/<filename>")  # type: ignore[misc]
def api_file(task_id: str, filename: str) -> tuple[Response, int]:
    """Serve a downloaded CBZ file.

    Args:
        task_id: Unique identifier for the task
        filename: Name of the file to serve

    Returns:
        tuple: File download response or error message with HTTP status code
    """
    # Security: reject path traversal attempts
    if ".." in filename:
        return jsonify({"error": "Invalid filename"}), 403

    # Get job result (list of file paths)
    result = get_job_result(task_id)

    if not result:
        return jsonify({"error": "Task not found or not completed"}), 404

    # Find the file that matches the requested filename
    matching_file = None
    for file_path in result:
        path = Path(file_path)
        if path.name == filename:
            matching_file = path
            break

    if not matching_file or not matching_file.exists():
        return jsonify({"error": "File not found"}), 404

    # Serve the file with correct content-type
    return (
        send_file(
            matching_file,
            mimetype="application/x-cbz",
            as_attachment=True,
            download_name=get_display_filename(str(matching_file), Config.CACHE_DIR),
        ),
        200,
    )
