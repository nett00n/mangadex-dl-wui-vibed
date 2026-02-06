# CLAUDE.md

Mandatory rules for all code generation and modification in mangadex-dl-wui-vibed.

**IMPORTANT:** Always read and reference [CONTRIBUTING.md](CONTRIBUTING.md) for complete project architecture, development workflows, API specifications, and implementation details.

## Environment

- Use the Python virtual environment **`.venv`** (NOT `venv`)
- Activate with: `source .venv/bin/activate`
- Do not use alternative environment managers (poetry, conda, etc.)
- See `.env.example` for required environment variables

## Principles

- **KISS** (Keep It Simple, Stupid) and **YAGNI** (You Aren't Gonna Need It)
- Apply DRY only when it improves clarity
- Fail fast with explicit error messages
- Prefer immutability where practical
- Ensure operations are idempotent
- Make changes small, reversible, and reviewable
- Reduce nesting and cyclomatic complexity

## Standards

- Follow **PEP 8** and the **Zen of Python**
- Prefer explicit over implicit
- **TDD**: Tests required for all new behavior and bug fixes
- Run formatters and tests **BEFORE and AFTER** changes

## Documentation

- Update docs for any change affecting behavior, configuration, interface, or workflow
- Include documentation for:
  - New features
  - Changed behavior
  - Removed/deprecated functionality
  - Environment changes
- If no doc update is required, state this explicitly in the change
- **Changes without corresponding documentation are incomplete**

## Project Context

**mangadex-dl-wui-vibed** is a Flask-based web UI wrapper for the `mangadex-dl` CLI tool. It uses Redis + RQ for job queuing and subprocess execution for downloading manga from MangaDex.

### Architecture Quick Reference

```
Browser --> Flask --> RQ (Redis) --> Worker --> subprocess: mangadex-dl
```

**Key Files:**
- `app/downloader.py`: Safe subprocess wrapper (see `run_mangadex_dl()`)
- `app/validators.py`: URL validation (ALWAYS validate before download)
- `app/routes.py`: 4 HTTP endpoints
- `app/config.py`: Environment variable configuration

**For complete architecture details, see [CONTRIBUTING.md](CONTRIBUTING.md#project-architecture)**

## Critical Security Rules

### Subprocess Safety

**MANDATORY:** Use the safe wrapper in `app/downloader.py`:

```python
from app.downloader import run_mangadex_dl

# URL must be validated first!
returncode, stdout, stderr = run_mangadex_dl(url, cache_dir)
```

**NEVER:**
- Use `shell=True` with subprocess
- Pass unvalidated URLs to `run_mangadex_dl()`
- Build command strings (use argument lists)

**ALWAYS:**
- Validate URLs with `validators.py` first
- Use the `which()` check before execution
- Handle subprocess errors explicitly

### URL Validation

```python
from app.validators import validate_mangadex_url

# ALWAYS validate before processing
if not validate_mangadex_url(url):
    return {"error": "Invalid MangaDex URL"}, 400
```

## Docker and Compose

- Use **`docker compose`** (NOT `docker-compose`)
- Requires Docker Engine 20.10.0+ with Compose v2+
- **NEVER** set `container_name` in docker-compose.yml
- Use `sudo` for docker commands if needed

## Configuration

All configuration via environment variables (see `.env.example`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection (auth: `redis://:password@host:port/db`) |
| `CACHE_DIR` | `/downloads/cache` | Persistent manga cache |
| `TEMP_DIR` | `/tmp/mangadex-wui-vibed` | Temporary task directories |
| `TASK_TTL_SECONDS` | `3600` | Task record expiration (1 hour) |
| `CACHE_TTL_SECONDS` | `604800` | Cached file expiration (7 days) |
| `RQ_WORKER_COUNT` | `3` | Concurrent download workers |

## Development Workflow

### Before Making Changes

```shell
source .venv/bin/activate
pre-commit run --all-files
pytest --cov=app
```

### After Making Changes

```shell
black app/ tests/
isort app/ tests/
pytest --cov=app --cov-report=term-missing
pre-commit run --all-files
```

### Code Quality Tools

- **Formatting**: black, isort
- **Type checking**: mypy
- **Linting**: ruff, pylint
- **Testing**: pytest with coverage

**All enforced by pre-commit hooks**

## API Endpoints Quick Reference

1. `POST /api/download` - Submit download (body: `{"url": "..."}`)
2. `GET /api/status/<task_id>` - Poll status
3. `GET /api/file/<task_id>/<filename>` - Download CBZ
4. `GET /` - Web UI

**For complete API specs, see [CONTRIBUTING.md](CONTRIBUTING.md#api-reference)**

## Testing Requirements

- All new features require tests
- All bug fixes require regression tests
- Minimum coverage: maintain or improve current levels
- Test files mirror source structure: `app/foo.py` → `tests/test_foo.py`

## Important Notes

- Redis is required (RQ dependency)
- RQ workers handle concurrency automatically
- Task cleanup removes job records, NOT cached downloads
- Cache uses `mangadex-dl`'s native skip logic for fast re-downloads
- `--input-pos "*"` downloads all chapters without prompts

## References

- [CONTRIBUTING.md](CONTRIBUTING.md) - **READ THIS for complete project details**
- [mangadex-dl documentation](https://github.com/mansuf/mangadex-downloader)
- [Functional Requirements](docs/frd.md)
- [User Stories](docs/user-stories.md)
- [Test Cases](docs/test-cases.md)
