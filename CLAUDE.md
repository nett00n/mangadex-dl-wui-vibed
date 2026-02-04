# CLAUDE.md

This file provides guidance to Claude Code when working with the mangadex-dl-wui project.

## Project Overview

**mangadex-dl-wui** is a web UI wrapper for the `mangadex-dl` CLI tool. It provides a simple Flask-based interface to download manga from MangaDex and retrieve the results as CBZ files.

### Architecture

```
Browser  -->  Flask (routes.py)  -->  Redis Queue (RQ)  -->  Worker Process  -->  subprocess: mangadex-dl
   ^                                       |                       |
   |--- polling /api/status/<id> ----------|                       |
   |                                                                |
   |--- GET /api/file/<id>/<name> ----> send_file(cbz) -----------|
```

**Key Design Decisions:**
- Shell out to `mangadex-dl` CLI via `subprocess.run()`
- **Redis + RQ** for job queue management and worker processes
- Concurrent download limit enforced by RQ worker count
- Polling for status updates (no WebSockets)
- Persistent download cache with `mangadex-dl`'s native skip-downloaded logic
- Auto-cleanup of expired task records (cached downloads persist longer)
- Job persistence across restarts

### Caching Strategy

- **Persistent cache**: `CACHE_DIR` (default: `/downloads/cache`) stores all manga downloads
- `mangadex-dl` invoked with `--path <CACHE_DIR>` to leverage native chapter skip logic
- Re-downloading the same manga reuses existing CBZ files (near-instant)
- Expired task records are cleaned up, but cached files have separate TTL
- `CACHE_TTL_SECONDS` (default: 7 days) controls cache eviction

## Project Structure

```
mangadex-dl-wui/
├── CLAUDE.md
├── docs/
│   ├── frd.md                    # Functional Requirements
│   ├── user-stories.md           # User stories with acceptance criteria
│   └── test-cases.md             # Test case tables
├── Dockerfile
├── docker-compose.yml            # No container_name
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .pre-commit-config.yaml
├── .gitignore
├── app/
│   ├── __init__.py               # Flask app factory
│   ├── config.py                 # Config (paths, timeouts, TTLs, cache dir, Redis)
│   ├── routes.py                 # 4 endpoints
│   ├── downloader.py             # subprocess wrapper + cache-aware download
│   ├── worker.py                 # RQ worker job definitions
│   ├── tasks.py                  # RQ job enqueue/status helpers
│   ├── cleanup.py                # Background cleanup (expired jobs, not cache)
│   ├── validators.py             # MangaDex URL validation
│   ├── templates/index.html
│   └── static/{style.css,app.js}
└── tests/
    ├── conftest.py
    ├── test_validators.py
    ├── test_downloader.py
    ├── test_tasks.py
    ├── test_cleanup.py
    ├── test_routes.py
    └── test_integration.py
```

## Development Workflow

### Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Running the App

```bash
# Development mode (requires 3 terminals)

# Terminal 1: Start Redis
redis-server

# Terminal 2: Start RQ worker(s)
rq worker --with-scheduler

# Terminal 3: Start Flask app
flask --app app run --debug

# Production mode (Docker - all services managed by compose)
docker compose up --build
```

### Testing

```bash
# Run all tests with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_routes.py -v

# Run with output
pytest -s

# Check pre-commit hooks
pre-commit run --all-files
```

### Code Quality

```bash
# Format code
black app/ tests/
isort app/ tests/

# Type checking
mypy app/

# Linting
ruff check app/ tests/
pylint app/

# All quality checks (done by pre-commit)
pre-commit run --all-files
```

## API Endpoints

1. **`POST /api/download`**
   - Body: `{"url": "https://mangadex.org/title/..."}`
   - Returns: `{"task_id": "uuid"}`

2. **`GET /api/status/<task_id>`**
   - Returns: `{"status": "queued|running|completed|failed", "progress": {...}, "files": [...]}`

3. **`GET /api/file/<task_id>/<filename>`**
   - Serves CBZ file from cache

4. **`GET /`**
   - Serves the web UI

## Configuration

Environment variables (see `app/config.py`):
- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379/0`)
- `CACHE_DIR`: Persistent download cache (default: `/downloads/cache`)
- `TEMP_DIR`: Temporary task directories (default: `/tmp/mangadex-wui`)
- `TASK_TTL_SECONDS`: Task record expiration (default: 3600)
- `CACHE_TTL_SECONDS`: Cached file expiration (default: 604800 / 7 days)
- `RQ_WORKER_COUNT`: Number of RQ workers (concurrent downloads, default: 3)

## Key CLI Flags for mangadex-dl

```bash
mangadex-dl \
  --save-as cbz \
  --path <CACHE_DIR> \
  --input-pos "*" \
  --progress-bar-layout none \
  <url>
```

## Important Notes

- **Redis is required** for queue management (RQ dependency)
- Always use `docker compose` (not `docker-compose`)
- Never set `container_name` in docker-compose.yml
- Run formatters and tests BEFORE and AFTER changes
- Use sudo for docker commands if needed
- RQ workers handle concurrent download limits automatically
- Task cleanup removes expired RQ jobs, NOT cached downloads
- Cache directory is persistent and shared across tasks

## References

- [mangadex-dl documentation](https://github.com/mansuf/mangadex-downloader)
- [Functional Requirements](docs/frd.md)
- [User Stories](docs/user-stories.md)
- [Test Cases](docs/test-cases.md)
