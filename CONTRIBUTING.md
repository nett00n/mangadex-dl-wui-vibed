# Contributing to mangadex-dl-wui

This guide covers setup, development workflows, architecture, and testing for contributors.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Setup](#development-setup)
- [Running the Application](#running-the-application)
- [Project Architecture](#project-architecture)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [API Reference](#api-reference)
- [Configuration](#configuration)

## Prerequisites

**Required:**
- Python 3.10+ (3.12 recommended)
- Redis 6.0+
- Docker Engine with Compose v2+ (provides `docker compose` subcommand, not legacy `docker-compose`)
- `mangadex-dl` CLI tool installed and available in PATH

**Development Tools:**
- pre-commit
- pytest, black, isort, mypy, ruff, pylint (installed via requirements-dev.txt)

## Development Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Copy environment template
cp .env.example .env
# Edit .env with your local configuration
```

**Note:** This project uses `.venv` as the virtual environment directory. All documentation and tooling assumes this convention.

## Running the Application

### Development Mode

Requires 3 terminal sessions:

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start RQ worker(s)
source .venv/bin/activate
rq worker --with-scheduler

# Terminal 3: Start Flask app
source .venv/bin/activate
export FLASK_APP=app
flask --app app --debug run
```

Visit http://localhost:5000 in your browser.

### Production Mode (Docker)

```bash
# Build and start all services
docker compose up --build

# Run in detached mode
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

**Docker Compose Version:** This project requires Docker Engine with Compose v2+ which provides the `docker compose` subcommand (not the legacy standalone `docker-compose`). Minimum versions:
- Docker Engine 20.10.0+ (includes Compose v2)
- Docker Compose plugin 2.0.0+

Check your version: `docker compose version`

## Project Architecture

### Request Flow

```
Browser  -->  Flask (routes.py)  -->  Redis Queue (RQ)  -->  Worker Process  -->  subprocess: mangadex-dl
   ^                                       |                       |
   |--- polling /api/status/<id> ----------|                       |
   |                                                                |
   |--- GET /api/file/<id>/<name> ----> send_file(cbz) -----------|
```

### Key Design Decisions

- **Subprocess execution**: Shells out to `mangadex-dl` CLI via safe `subprocess.run()` (see `app/downloader.py:run_mangadex_dl()`)
- **Job queue**: Redis + RQ for job management and worker processes
- **Concurrency**: Limited by RQ worker count (configured via `RQ_WORKER_COUNT`)
- **Status updates**: Client polling (no WebSockets)
- **Caching**: Persistent download cache with native `mangadex-dl` skip logic
- **Cleanup**: Expired task records auto-cleaned; cached files have separate TTL
- **Persistence**: Jobs survive restarts via Redis

### Caching Strategy

- **Persistent cache**: `CACHE_DIR` (default: `/downloads/cache`) stores all manga downloads
- `mangadex-dl` invoked with `--path <CACHE_DIR>` to leverage native chapter skip logic
- **Directory structure**: `mangadex-dl` creates per-manga subdirectories (`CACHE_DIR/<Manga Title>/`)
- `scan_for_cbz` uses recursive glob (`rglob`) to find CBZ files in all subdirectories
- `download_manga` snapshots files before/after download to return only newly created files per job
- Re-downloading the same manga reuses existing CBZ files (near-instant)
- Task records expire after `TASK_TTL_SECONDS` (default: 1 hour)
- Cached files expire after `CACHE_TTL_SECONDS` (default: 7 days)
- Cleanup handles files in subdirectories and removes empty directories

### Project Structure

```
mangadex-dl-wui/
├── CLAUDE.md                     # AI assistant instructions
├── CONTRIBUTING.md               # This file - developer guide
├── docs/
│   ├── frd.md                    # Functional Requirements
│   ├── user-stories.md           # User stories with acceptance criteria
│   └── test-cases.md             # Test case tables
├── Dockerfile
├── docker-compose.yml
├── .env.example                  # Environment variable template
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .pre-commit-config.yaml
├── .gitignore
├── app/
│   ├── __init__.py               # Flask app factory
│   ├── config.py                 # Config (paths, timeouts, TTLs, Redis)
│   ├── routes.py                 # 4 HTTP endpoints
│   ├── downloader.py             # Safe subprocess wrapper for mangadex-dl
│   ├── worker.py                 # RQ worker job definitions
│   ├── tasks.py                  # RQ job enqueue/status helpers
│   ├── cleanup.py                # Background cleanup (expired jobs)
│   ├── validators.py             # MangaDex URL validation
│   ├── templates/index.html      # Web UI template
│   └── static/
│       ├── style.css
│       └── app.js
└── tests/
    ├── conftest.py
    ├── test_validators.py
    ├── test_downloader.py
    ├── test_tasks.py
    ├── test_cleanup.py
    ├── test_routes.py
    └── test_integration.py
```

### Subprocess Safety

The `app/downloader.py` module implements safe subprocess execution:

```python
def run_mangadex_dl(url: str, cache_dir: str, timeout: int = 3600) -> tuple[int, str, str]:
    """Safely execute mangadex-dl CLI with validated arguments.

    SECURITY:
    - Validates binary exists before execution
    - Uses argument list (no shell=True) to prevent command injection
    - Requires URL pre-validation by validators.py
    - Returns stdout/stderr for logging and progress parsing
    """
    exe = which("mangadex-dl")
    if not exe:
        raise RuntimeError("mangadex-dl not found in PATH")

    args = [exe, "--save-as", "cbz", "--path", str(cache_dir),
            "--input-pos", "*", "--progress-bar-layout", "none", url]

    proc = subprocess.run(args, check=False, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr
```

**Critical:** Always validate URLs using `validators.py` before calling `run_mangadex_dl()`.

## Testing

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_routes.py -v

# Run with captured output
pytest -s

# Run tests matching pattern
pytest -k "test_download"
```

### Test Organization

- `test_validators.py`: URL validation logic
- `test_downloader.py`: Subprocess wrapper and CLI interaction
- `test_tasks.py`: RQ job enqueue/status operations
- `test_cleanup.py`: Task record expiration
- `test_routes.py`: HTTP endpoint behavior
- `test_integration.py`: End-to-end workflows

## Code Quality

### Pre-commit Hooks

All quality checks run automatically on commit:

```bash
# Manually run all hooks
pre-commit run --all-files

# Run specific hook
pre-commit run black
```

### Manual Quality Checks

```bash
# Code formatting
black app/ tests/
isort app/ tests/

# Type checking
mypy app/

# Linting
ruff check app/ tests/
pylint app/
```

### Development Workflow

1. **Before making changes**: Run formatters and tests
2. **Make your changes**: Keep them small, focused, and reviewable
3. **After changes**: Run formatters and tests again
4. **Commit**: Pre-commit hooks will enforce quality standards

## API Reference

### POST /api/download

Submit a manga download request.

**Request:**
```json
{
  "url": "https://mangadex.org/title/..."
}
```

**Response (202 Accepted):**
```json
{
  "task_id": "uuid-string"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid URL format
- `500 Internal Server Error`: Queue submission failed

### GET /api/status/{task_id}

Poll download status.

**Response (200 OK):**
```json
{
  "status": "queued|running|completed|failed",
  "progress": {
    "current": 5,
    "total": 10,
    "percent": 50
  },
  "files": ["chapter-1.cbz", "chapter-2.cbz"],
  "error": "Error message if failed"
}
```

**Error Responses:**
- `404 Not Found`: Task ID does not exist or expired

### GET /api/file/{task_id}/{filename}

Download a completed CBZ file.

**Response (200 OK):**
- Content-Type: `application/x-cbz`
- Content-Disposition: `attachment; filename="{filename}"`
- Body: CBZ file binary data

**Error Responses:**
- `404 Not Found`: Task or file does not exist
- `410 Gone`: Task expired, file no longer available

### GET /

Serve the web UI.

**Response (200 OK):**
- Content-Type: `text/html`
- Body: HTML page

## Configuration

All configuration is via environment variables. See `.env.example` for a complete template with explanations.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL. For auth: `redis://:password@host:port/db` |
| `CACHE_DIR` | `/downloads/cache` | Persistent cache directory for downloaded manga |
| `TEMP_DIR` | `/tmp/mangadex-wui` | Temporary task working directories |
| `TASK_TTL_SECONDS` | `3600` (1 hour) | Task record expiration time |
| `CACHE_TTL_SECONDS` | `604800` (7 days) | Cached file expiration time |
| `RQ_WORKER_COUNT` | `3` | Number of concurrent download workers |
| `PYTHON_VERSION` | `3.12` | Python version (Docker build only) |

### Development vs Production

**Development** (.env):
```bash
REDIS_URL=redis://localhost:6379/0
CACHE_DIR=./downloads/cache
TEMP_DIR=/tmp/mangadex-wui
```

**Production** (docker-compose.yml environment):
```yaml
REDIS_URL=redis://redis:6379/0
CACHE_DIR=/downloads/cache
```

### Security Considerations

- **Never commit `.env`** - it's gitignored for a reason
- **Redis authentication**: Use `redis://:password@host:port/db` format in production
- **URL validation**: Always validate user input before processing
- **Rate limiting**: Consider adding rate limits for the API in production

## Key CLI Flags for mangadex-dl

The application invokes `mangadex-dl` with these flags:

```bash
mangadex-dl \
  --save-as cbz \                # Output format
  --path <CACHE_DIR> \           # Cache directory for persistence
  --input-pos "*" \              # Download all chapters (wildcard)
  --progress-bar-layout none \   # Disable progress bar for cleaner output
  <url>
```

**Note:** `--input-pos "*"` is required to download all chapters without interactive prompts.

## Troubleshooting

### Worker Not Processing Jobs

1. Check Redis is running: `redis-cli ping`
2. Check worker is running: `rq info`
3. Check worker logs for errors
4. Verify `REDIS_URL` matches between app and worker

### mangadex-dl Not Found

1. Install via pip: `pip install mangadex-downloader`
2. Verify in PATH: `which mangadex-dl`
3. In Docker: ensure Dockerfile includes installation

### Tests Failing

1. Check all dependencies installed: `pip install -r requirements-dev.txt`
2. Verify `.venv` is activated
3. Check Redis is running (some tests may need it)
4. Run with verbose output: `pytest -vv`

## References

- [mangadex-dl documentation](https://github.com/mansuf/mangadex-downloader)
- [Flask documentation](https://flask.palletsprojects.com/)
- [RQ (Redis Queue) documentation](https://python-rq.org/)
- [Functional Requirements](docs/frd.md)
- [User Stories](docs/user-stories.md)
- [Test Cases](docs/test-cases.md)

## License

See LICENSE file for details.
