# Contributing to mangadex-dl-wui-vibed

This guide covers setup, development workflows, architecture, and testing for contributors.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Setup](#development-setup)
- [Running the Application](#running-the-application)
- [Project Architecture](#project-architecture)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [API Reference](#api-reference)
- [Frontend Architecture](#frontend-architecture)
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

```shell
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

```shell
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

```shell
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
   |
   |--- GET /cache ------------> list_cached_mangas (Redis) -----> cache.html
   |--- GET /api/cache/<s>/<f> -> send_file(cbz from CACHE_DIR)
```

### Key Design Decisions

- **Subprocess execution**: Shells out to `mangadex-dl` CLI via safe `subprocess.run()` (see `app/downloader.py:run_mangadex_dl()`)
- **Job queue**: Redis + RQ for job management and worker processes
- **Concurrency**: Limited by RQ worker count (configured via `RQ_WORKER_COUNT`)
- **Status updates**: Client polling (no WebSockets)
- **Caching**: Persistent download cache with native `mangadex-dl` skip logic
- **Cleanup**: Expired task records auto-cleaned; cached files have separate TTL
- **Persistence**: Jobs survive restarts via Redis
- **Cache metadata**: Redis hashes (`cache:manga:<series>`) record URL, path, files, and download date per series; cleaned up when all files expire

### Caching Strategy

- **Persistent cache**: `CACHE_DIR` (default: `/downloads/cache`) stores all manga downloads
- `mangadex-dl` invoked with `--path CACHE_DIR/{manga.title}` — the `{manga.title}` placeholder is resolved by `mangadex-dl` at download time to the real manga title, creating a per-manga subdirectory automatically
- **Directory structure**: `CACHE_DIR/<Manga Title>/Vol. 1 Ch. 1.cbz` (volume and chapter in filename via `--filename-chapter`)
- `scan_for_cbz` uses recursive glob (`rglob`) to find CBZ files in all subdirectories
- `download_manga` snapshots files before/after download to return only newly created files per job
- Re-downloading the same manga reuses existing CBZ files (near-instant) because the same URL produces the same `{manga.title}` path
- **Display filenames**: `get_display_filename()` derives a prefixed display name (e.g., `"Series Name - Vol. 1 Ch. 1.cbz"`) from the file's path structure without renaming on disk, preserving cache skip logic; used for `Content-Disposition` headers and UI link text
- Task records expire after `TASK_TTL_SECONDS` (default: 1 hour)
- Cached files expire after `CACHE_TTL_SECONDS` (default: 7 days; 0 = never expire)
- Cleanup handles files in subdirectories and removes empty directories

### Project Structure

```
mangadex-dl-wui-vibed/
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
│   ├── routes.py                 # 6 HTTP endpoints
│   ├── downloader.py             # Safe subprocess wrapper for mangadex-dl
│   ├── worker.py                 # RQ worker job definitions
│   ├── tasks.py                  # RQ job enqueue/status helpers
│   ├── cleanup.py                # Background cleanup (expired jobs + metadata)
│   ├── cache.py                  # Redis-backed cache metadata CRUD
│   ├── validators.py             # MangaDex URL validation
│   ├── templates/
│   │   ├── base.html             # Shared layout with sticky navbar
│   │   ├── index.html            # Download UI (extends base.html)
│   │   ├── cache.html            # Cache browser (extends base.html)
│   │   └── partials/             # Reusable Jinja2 partials ({% include %})
│   │       ├── _navbar.html      # Sticky nav with brand + Home/Cache links
│   │       ├── _footer.html      # Disclaimer footer
│   │       ├── _description.html # App description box (index page)
│   │       ├── _download_form.html # URL input form + submit button
│   │       ├── _manga_card.html  # Manga card (mirrors JS UI.renderTask())
│   │       ├── _style.css        # Symlink → ../../static/style.css (inline at render)
│   │       └── _app.js           # Symlink → ../../static/app.js (inline at render)
│   └── static/
│       ├── style.css             # Edit here; inlined via _style.css symlink
│       └── app.js                # Edit here; inlined via _app.js symlink
└── tests/
    ├── conftest.py
    ├── test_cache.py
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

    args = [exe, "--save-as", "cbz", "--path", f"{cache_dir}/{{manga.title}}",
            "--input-pos", "*", "--progress-bar-layout", "none",
            "--filename-chapter", "Vol. {chapter.volume} Ch. {chapter.chapter}{file_ext}", url]

    proc = subprocess.run(args, check=False, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr
```

**Critical:** Always validate URLs using `validators.py` before calling `run_mangadex_dl()`.

## Testing

```shell
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

### Makefile

All targets run in Docker — no local Python environment needed.

```shell
make ci        # all checks: fmt-check → lint → mypy → test + coverage
make ci-fix    # auto-format, then all checks
make test      # pytest + coverage only
make lint      # ruff + mypy only
make fmt       # black + isort (modifies files in place)
make clean     # remove reports/, caches
```

### CI Script (`scripts/ci.sh`)

Runs checks inside a throwaway Docker container. Supports individual steps so the Makefile (and any other caller) can run only the checks it needs.

```shell
./scripts/ci.sh                   # all checks (default)
./scripts/ci.sh --fix             # auto-format, then all checks
./scripts/ci.sh --step=fmt        # format check only
./scripts/ci.sh --step=fmt --fix  # auto-format only
./scripts/ci.sh --step=lint       # ruff + mypy only
./scripts/ci.sh --step=test       # pytest + coverage only
```

The script:
1. Creates (if absent) a named Docker volume `mangadex-dl-wui-pip-cache` for pip downloads — subsequent runs are significantly faster
2. Spins up a `python:3.12-slim` container with the project mounted at `/app`
3. Installs dev dependencies with version constraints matching `pyproject.toml` (skips `mangadex-downloader`)
4. Runs the requested step(s): `black`/`isort`, `ruff`, `mypy`, `pytest --cov`
5. Re-owns all generated files in `reports/` to the calling user (avoids root-owned files from the Docker container)

### Reports

Generated into `reports/` (git-ignored):

| File                         | Contents                              |
| ---------------------------- | ------------------------------------- |
| `reports/coverage.xml`       | Cobertura XML coverage (for CI tools) |
| `reports/htmlcov/index.html` | Interactive HTML coverage report      |
| `reports/mypy/index.txt`     | mypy type-check output                |

Use this when your local `.venv` is unavailable or you want a clean-room verification before pushing.

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

```shell
# Manually run all hooks
pre-commit run --all-files

# Run specific hook
pre-commit run black
```

### Manual Quality Checks

```shell
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
- Content-Disposition: `attachment; filename="{series_name} - {filename}"`
- Body: CBZ file binary data

**Error Responses:**
- `404 Not Found`: Task or file does not exist
- `410 Gone`: Task expired, file no longer available

### GET /api/cache/{series}/{filename}

Download a cached CBZ file directly from `CACHE_DIR` by series name and filename.

**Response (200 OK):**
- Content-Type: `application/x-cbz`
- Content-Disposition: `attachment; filename="{series_name} - {filename}"`
- Body: CBZ file binary data

**Error Responses:**
- `403 Forbidden`: Path traversal attempt (`..`) or non-CBZ file requested
- `404 Not Found`: File does not exist in cache

### GET /cache

Browse previously downloaded manga in the cache.

**Response (200 OK):**
- Content-Type: `text/html`
- Body: Cache listing page with series cards and download links

### GET /

Serve the web UI.

**Response (200 OK):**
- Content-Type: `text/html`
- Body: HTML page

### Redis Metadata Keys

Cache metadata is stored in Redis hashes with the key pattern `cache:manga:<series_name>`:

| Field            | Description                           |
| ---------------- | ------------------------------------- |
| `url`            | Original MangaDex URL                 |
| `name`           | Series directory name                 |
| `sanitized_name` | Human-readable display name           |
| `cache_path`     | Full path to series directory on disk |
| `download_date`  | ISO 8601 timestamp of last download   |
| `files`          | JSON array of CBZ file basenames      |

Metadata is written by `app/worker.py` after each successful download and removed by `app/cleanup.py` when all CBZ files for a series have expired.

## Frontend Architecture

The web UI is implemented using vanilla JavaScript with no framework dependencies. It provides a reactive task management interface with automatic status polling and persistent state.

### Key Components

**`app/static/app.js`** - JavaScript modules:

1. **`ApiClient`** - HTTP client for backend communication
   - `postDownload(url)` - Submit download request
   - `getStatus(taskId)` - Poll task status
   - `getFileUrl(taskId, filename)` - Build download URL

2. **`TaskManager`** - Task state management and polling
   - `tasks` - Map of task IDs to task objects
   - `addTask(taskId, url)` - Register new task
   - `updateTask(taskId, status)` - Update task state
   - `removeTask(taskId)` - Remove task
   - `startPolling(taskId)` - Begin status polling (2s interval)
   - `stopPolling(taskId)` - Stop polling
   - `saveTasks()` - Persist tasks to sessionStorage
   - `loadTasks()` - Restore tasks from sessionStorage

3. **`UI`** - DOM rendering and user interaction
   - `renderTask(taskId, status)` - Render/update task card
   - `renderError(message)` - Display error message
   - `extractMangaName(url)` - Extract manga name from URL slug
   - `retryTask(taskId)` - Retry failed download
   - `escapeHtml(text)` - XSS prevention

**`app/static/style.css`** - Responsive CSS with mobile support. Inlined at render time via `{% include "partials/_style.css" %}` — edit this file directly; the symlink makes it available to Jinja2.

**`app/static/app.js`** - Client-side task management and polling. Inlined at render time via `{% include "partials/_app.js" %}` — edit this file directly; the symlink makes it available to Jinja2.

**`app/templates/index.html`** - HTML structure with accessibility features

### Template Partials

Logical sections are extracted into reusable Jinja2 partials under `app/templates/partials/`:

| Partial               | Used in      | Content                                                           |
| --------------------- | ------------ | ----------------------------------------------------------------- |
| `_navbar.html`        | `base.html`  | Sticky nav with brand + Home/Cache links                          |
| `_footer.html`        | `base.html`  | Disclaimer footer with license/links                              |
| `_description.html`   | `index.html` | Blue-bordered app description box                                 |
| `_download_form.html` | `index.html` | URL input form + submit button                                    |
| `_manga_card.html`    | `cache.html` | Manga card with header, status badge, file list                   |
| `_style.css`          | `base.html`  | Symlink → `../../static/style.css` (for `{% include %}` inlining) |
| `_app.js`             | `index.html` | Symlink → `../../static/app.js` (for `{% include %}` inlining)    |

**JS/Jinja2 sync constraint:** `_manga_card.html` and `UI.renderTask()` in `app/static/app.js` render structurally equivalent cards (server-side for the cache page, client-side for active downloads). When modifying the card layout, **both must be updated together** to keep the visual structure consistent.

### Inline Asset Strategy

Each page load returns a **single self-contained HTTP response** with no external asset requests:

- **CSS**: Inlined in a `<style>` tag via `{% include "partials/_style.css" %}` in `base.html`
- **JS**: Inlined in a `<script>` tag via `{% include "partials/_app.js" %}` in `index.html`
- **Images**: Favicon (`assets/logo/32x32.png`) and logo (`assets/logo/128x128.png`) are read at startup, base64-encoded, and injected as data URIs via a Flask context processor (`favicon_b64`, `logo_b64` template variables) registered in `app/__init__.py`
- **Minification**: All `text/html` responses are minified (including inline CSS/JS) via a `@app.after_request` hook using `minify-html` with `minify_js=True, minify_css=True`. Minification is always on with no configuration flag.

The CSS/JS source files remain editable in `app/static/` with full IDE support. Symlinks in `app/templates/partials/` make them includable by Jinja2's template loader.

### SessionStorage Persistence

Tasks persist across page refreshes within the same browser tab/session using `sessionStorage`:

- **Key**: `mangadex-tasks`
- **Value**: JSON object mapping task IDs to task objects
- **Task object structure**:
  ```json
  {
    "status": "queued|started|finished|failed",
    "url": "https://mangadex.org/title/...",
    "error": "error message (if failed)",
    "files": ["file1.cbz", "file2.cbz"] // (if finished)
  }
  ```

Tasks are automatically saved on:
- Task creation (`addTask`)
- Status updates (`updateTask`)
- Task removal (`removeTask`)

Tasks are loaded on page load (`DOMContentLoaded`). Non-terminal tasks (not finished/failed) automatically resume polling. Finished tasks missing file data are automatically refreshed via a one-time API call on page load.

### Manga Name Display

The UI extracts manga names from MangaDex URL slugs:

- URL: `https://mangadex.org/title/{uuid}/{slug}` → Manga name: `{slug with dashes replaced by spaces}`
- URL: `https://mangadex.org/title/{uuid}` → Manga name: `{uuid}`

Examples:
- `https://mangadex.org/title/123/one-piece-digital` → "one piece digital"
- `https://mangadex.org/title/123` → "123"

The manga name is displayed as a clickable link in the task card, opening the MangaDex page in a new tab.

### Task Lifecycle

1. **Submit** - User submits URL → `POST /api/download` → Task ID returned
2. **Poll** - JavaScript polls `GET /api/status/{task_id}` every 2 seconds
3. **Update** - Task card updates with status (queued → started → finished/failed)
4. **Persist** - Task state saved to sessionStorage after each update
5. **Complete** - Polling stops when status is finished/failed
6. **Dismiss** - User can remove task card (clears from sessionStorage)

### Retry Functionality

When a task fails, a "Retry" button appears. Clicking it:
1. Retrieves the URL from the stored task data
2. Removes the failed task from state and sessionStorage
3. Pre-fills the URL input field
4. User can submit to create a new download attempt

### Security

- **XSS Prevention**: All user data is escaped via `escapeHtml()` before rendering
- **CSRF**: Not needed (no authentication, stateless API)
- **URL Validation**: Both client-side (HTML5 `required` attribute) and server-side validation

### Browser Compatibility

- Modern browsers with ES6+ support (2020+)
- SessionStorage support required
- Tested with Chrome, Firefox, Safari

## Configuration

All configuration is via environment variables. See `.env.example` for a complete template with explanations.

### Environment Variables

| Variable            | Default                    | Description                                                      |
| ------------------- | -------------------------- | ---------------------------------------------------------------- |
| `REDIS_URL`         | `redis://localhost:6379/0` | Redis connection URL. For auth: `redis://:password@host:port/db` |
| `CACHE_DIR`         | `/downloads/cache`         | Persistent cache directory for downloaded manga                  |
| `TEMP_DIR`          | `/tmp/mangadex-wui-vibed`  | Temporary task working directories                               |
| `TASK_TTL_SECONDS`  | `3600` (1 hour)            | Task record expiration time                                      |
| `CACHE_TTL_SECONDS` | `604800` (7 days)          | Cached file expiration time (0 = never expire)                   |
| `RQ_WORKER_COUNT`   | `3`                        | Number of concurrent download workers                            |
| `PYTHON_VERSION`    | `3.12`                     | Python version (Docker build only)                               |

### Development vs Production

**Development** (.env):
```shell
REDIS_URL=redis://localhost:6379/0
CACHE_DIR=./downloads/cache
TEMP_DIR=/tmp/mangadex-wui-vibed
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

```shell
mangadex-dl \
  --save-as cbz \                                          # Output format
  --path "CACHE_DIR/{manga.title}" \                       # Per-manga subdirectory
  --input-pos "*" \                                        # Download all chapters (wildcard)
  --progress-bar-layout none \                             # Disable progress bar for cleaner output
  --filename-chapter "Vol. {chapter.volume} Ch. {chapter.chapter}{file_ext}" \  # Volume+chapter in filename
  <url>
```

**Notes:**
- `--input-pos "*"` is required to download all chapters without interactive prompts.
- `{manga.title}` in `--path` is a `mangadex-dl` path placeholder resolved to the real manga title at runtime (not a Python f-string). In Python code, the double braces `{{manga.title}}` produce the literal `{manga.title}` string.
- `{chapter.volume}`, `{chapter.chapter}`, `{file_ext}` in `--filename-chapter` are also `mangadex-dl` placeholders. If a chapter has no volume data, `{chapter.volume}` may render as empty or `None`.
- The resulting cache structure is: `CACHE_DIR/<Manga Title>/Vol. 1 Ch. 1.cbz`

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
