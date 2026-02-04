"""Flask routes for the web UI and API endpoints."""

from flask import Blueprint, jsonify, render_template
from werkzeug.wrappers.response import Response

bp = Blueprint("main", __name__)


@bp.route("/")
def index() -> str:
    """Render the main web UI page.

    Returns:
        str: Rendered HTML template
    """
    return render_template("index.html")


@bp.route("/api/download", methods=["POST"])
def api_download() -> tuple[Response, int]:
    """Queue a manga download task.

    Returns:
        tuple: JSON response with task_id and HTTP status code
    """
    return jsonify({"status": "not implemented"}), 501


@bp.route("/api/status/<task_id>")
def api_status(task_id: str) -> tuple[Response, int]:
    """Get the status of a download task.

    Args:
        task_id: Unique identifier for the task

    Returns:
        tuple: JSON response with task status and HTTP status code
    """
    return jsonify({"status": "not implemented"}), 501


@bp.route("/api/file/<task_id>/<filename>")
def api_file(task_id: str, filename: str) -> tuple[Response, int]:
    """Serve a downloaded CBZ file.

    Args:
        task_id: Unique identifier for the task
        filename: Name of the file to serve

    Returns:
        tuple: File download response or error message with HTTP status code
    """
    return jsonify({"status": "not implemented"}), 501
