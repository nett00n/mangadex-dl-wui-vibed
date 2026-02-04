# Test Cases

**Project:** mangadex-dl-wui
**Version:** 1.0
**Date:** 2026-02-04

---

## Unit Test Cases

### Module: `app/validators.py`

| Test ID | Test Case | Input | Expected Output | Related US |
|---------|-----------|-------|-----------------|------------|
| UT-VAL-001 | Valid MangaDex title URL | `https://mangadex.org/title/abc-123` | `True` | US-1.1 |
| UT-VAL-002 | Valid MangaDex title URL with UUID | `https://mangadex.org/title/12345678-1234-1234-1234-123456789abc` | `True` | US-1.1 |
| UT-VAL-003 | Invalid domain | `https://example.com/title/abc` | `False` | US-1.2 |
| UT-VAL-004 | Invalid path (not /title/) | `https://mangadex.org/chapter/abc-123` | `False` | US-1.2 |
| UT-VAL-005 | Missing protocol | `mangadex.org/title/abc-123` | `False` | US-1.2 |
| UT-VAL-006 | HTTP instead of HTTPS | `http://mangadex.org/title/abc-123` | `False` | US-1.2 |
| UT-VAL-007 | Empty string | `""` | `False` | US-1.2 |
| UT-VAL-008 | None input | `None` | `False` | US-1.2 |
| UT-VAL-009 | URL with query params | `https://mangadex.org/title/abc?tab=art` | `True` | US-1.1 |
| UT-VAL-010 | Path traversal attempt | `https://mangadex.org/title/../etc/passwd` | `False` | US-5.1 |

---

### Module: `app/tasks.py` (RQ Job Helpers)

| Test ID | Test Case | Setup | Action | Expected Result | Related US |
|---------|-----------|-------|--------|-----------------|------------|
| UT-TSK-001 | Enqueue download job | Mock RQ queue | `enqueue_download(url)` | Returns job ID, job queued in Redis | US-1.1 |
| UT-TSK-002 | Get existing job status | Job exists in Redis | `get_job_status(job_id)` | Returns job status object | US-1.3 |
| UT-TSK-003 | Get non-existent job | Empty Redis | `get_job_status(invalid_id)` | Returns `None` or raises NotFound | US-1.2 |
| UT-TSK-004 | Job status transitions | Job in queue | Worker picks up job | Status: queued → started → finished | US-1.3 |
| UT-TSK-005 | Get job result | Completed job | `get_job_result(job_id)` | Returns CBZ file list | US-1.4 |
| UT-TSK-006 | Job failure handling | Failed job | `get_job_status(job_id)` | Status=failed, exception info stored | US-1.5 |
| UT-TSK-007 | Concurrent job queries | Multiple clients | Each queries `get_job_status()` | Redis handles concurrency atomically | US-4.3 |
| UT-TSK-008 | List queued jobs | 5 jobs in queue | `list_queued_jobs()` | Returns all 5 job IDs | US-2.2 |
| UT-TSK-009 | Job TTL expiration | Job older than TTL | RQ cleanup | Expired job removed from Redis | US-4.1 |
| UT-TSK-010 | Job cancellation | Running job | `cancel_job(job_id)` | Job marked as canceled | US-4.2 |

---

### Module: `app/worker.py` (RQ Worker Jobs)

| Test ID | Test Case | Setup | Action | Expected Result | Related US |
|---------|-----------|-------|--------|-----------------|------------|
| UT-WKR-001 | Execute download job | Mock downloader | `perform_download_job(url)` | Downloads manga, returns file list | US-1.4 |
| UT-WKR-002 | Job progress updates | Running job | Job updates progress | RQ job meta contains progress data | US-1.3 |
| UT-WKR-003 | Job failure handling | Mock downloader error | `perform_download_job(url)` | Exception raised, job status=failed | US-1.5 |
| UT-WKR-004 | Job result storage | Successful job | Job completes | Result stored in Redis | US-1.4 |
| UT-WKR-005 | Job timeout handling | Long-running job | Timeout exceeded | Job canceled, timeout error recorded | US-4.2 |
| UT-WKR-006 | Worker concurrency | Multiple jobs | Workers process in parallel | Each worker handles one job | US-2.1 |

---

### Module: `app/downloader.py`

| Test ID | Test Case | Mocking | Action | Expected Result | Related US |
|---------|-----------|---------|--------|-----------------|------------|
| UT-DL-001 | Successful download | Mock subprocess success | `download_manga(url, cache_dir)` | Returns list of CBZ files | US-1.4 |
| UT-DL-002 | Subprocess failure | Mock subprocess error | `download_manga(url, cache_dir)` | Raises exception with stderr | US-1.5 |
| UT-DL-003 | Invalid URL to CLI | Mock subprocess | `download_manga(bad_url, cache_dir)` | Exception raised | US-1.2 |
| UT-DL-004 | Parse progress output | Mock stdout with progress | `parse_progress(stdout)` | Extracts chapter counts correctly | US-1.3 |
| UT-DL-005 | Detect cached chapters | Mock stdout with "skipped" | `parse_progress(stdout)` | Recognizes cached chapters | US-3.1 |
| UT-DL-006 | CLI timeout | Mock long-running process | `download_manga(url, cache_dir)` | Timeout handled gracefully | US-4.2 |
| UT-DL-007 | Filesystem error | Mock fs write failure | `download_manga(url, cache_dir)` | Exception with helpful message | US-4.2 |
| UT-DL-008 | Generate CLI args | Valid inputs | `build_cli_args(url, cache_dir)` | Correct flags in list | US-1.1 |
| UT-DL-009 | Scan output directory | Dir with CBZ files | `scan_for_cbz(cache_dir)` | Returns all CBZ file paths | US-1.4 |
| UT-DL-010 | Empty output directory | Empty dir | `scan_for_cbz(cache_dir)` | Returns empty list | US-1.5 |

---

### Module: `app/cleanup.py`

| Test ID | Test Case | Setup | Action | Expected Result | Related US |
|---------|-----------|-------|--------|-----------------|------------|
| UT-CLN-001 | Remove expired cache file | Cache file older than cache TTL | `cleanup_cache(cache_dir, ttl)` | Cache file deleted | US-3.3 |
| UT-CLN-002 | Keep recent cache file | Cache file newer than cache TTL | `cleanup_cache(cache_dir, ttl)` | Cache file remains | US-3.2 |
| UT-CLN-003 | Keep active job files | Expired cache, active RQ job | `cleanup_cache(cache_dir, ttl)` | Active job files preserved | US-3.3 |
| UT-CLN-004 | Handle cleanup errors | Mock fs permission error | `cleanup_cache(ttl)` | Logs error, doesn't crash | US-4.2 |
| UT-CLN-005 | Cleanup loop iteration | Mock Redis connection | `run_cleanup_loop()` | Sleeps, then cleans periodically | US-4.1 |
| UT-CLN-006 | Empty cache directory | No files | `cleanup_cache(cache_dir, ttl)` | No errors, no changes | US-4.1 |
| UT-CLN-007 | Scan for job references | Files in cache | Check Redis for active jobs | Only unreferenced files cleaned | US-3.3 |
| UT-CLN-008 | Remove temp directories | Completed jobs | `cleanup_temp_dirs()` | Temp dirs for done jobs removed | US-4.1 |

---

### Module: `app/config.py`

| Test ID | Test Case | Environment Vars | Expected Config | Related US |
|---------|-----------|------------------|-----------------|------------|
| UT-CFG-001 | Default Redis URL | None set | `redis://localhost:6379/0` | US-6.1 |
| UT-CFG-002 | Custom Redis URL | `REDIS_URL=redis://redis:6379/1` | `redis://redis:6379/1` | US-6.1 |
| UT-CFG-003 | Default cache dir | None set | `/downloads/cache` | US-6.1 |
| UT-CFG-004 | Custom cache dir | `CACHE_DIR=/data/manga` | `/data/manga` | US-6.1 |
| UT-CFG-005 | Default job result TTL | None set | `3600` seconds | US-6.1 |
| UT-CFG-006 | Custom job result TTL | `TASK_TTL_SECONDS=7200` | `7200` seconds | US-6.1 |
| UT-CFG-007 | Default cache TTL | None set | `604800` (7 days) | US-6.1 |
| UT-CFG-008 | Custom cache TTL | `CACHE_TTL_SECONDS=1209600` | `1209600` (14 days) | US-6.1 |
| UT-CFG-009 | Default worker count | None set | `3` | US-6.1 |
| UT-CFG-010 | Custom worker count | `RQ_WORKER_COUNT=5` | `5` | US-6.1 |
| UT-CFG-011 | Invalid TTL value | `TASK_TTL_SECONDS=abc` | Validation error or default | US-6.1 |
| UT-CFG-012 | Negative TTL value | `TASK_TTL_SECONDS=-100` | Validation error or default | US-6.1 |

---

## Integration Test Cases

### Module: `tests/test_routes.py`

| Test ID | Test Case | Request | Expected Response | Status Code | Related US |
|---------|-----------|---------|-------------------|-------------|------------|
| IT-API-001 | Download valid URL | `POST /api/download {"url": "https://mangadex.org/title/test"}` | `{"task_id": "<uuid>"}` | 200 | US-1.1 |
| IT-API-002 | Download invalid URL | `POST /api/download {"url": "https://evil.com"}` | `{"error": "Invalid URL"}` | 400 | US-1.2 |
| IT-API-003 | Download missing URL | `POST /api/download {}` | `{"error": "Missing URL"}` | 400 | US-1.2 |
| IT-API-004 | Status for queued task | `GET /api/status/<valid_id>` | `{"status": "queued", ...}` | 200 | US-1.3 |
| IT-API-005 | Status for running task | `GET /api/status/<running_id>` | `{"status": "running", "progress": {...}}` | 200 | US-1.3 |
| IT-API-006 | Status for completed task | `GET /api/status/<done_id>` | `{"status": "completed", "files": [...]}` | 200 | US-1.4 |
| IT-API-007 | Status for failed task | `GET /api/status/<failed_id>` | `{"status": "failed", "error": "..."}` | 200 | US-1.5 |
| IT-API-008 | Status for invalid task ID | `GET /api/status/invalid-uuid` | `{"error": "Task not found"}` | 404 | US-1.2 |
| IT-API-009 | Download file success | `GET /api/file/<id>/<file.cbz>` | Binary CBZ data | 200 | US-1.4 |
| IT-API-010 | Download non-existent file | `GET /api/file/<id>/missing.cbz` | `{"error": "File not found"}` | 404 | US-5.1 |
| IT-API-011 | Download with path traversal | `GET /api/file/<id>/../etc/passwd` | `{"error": "Invalid filename"}` | 403 | US-5.1 |
| IT-API-012 | Download file from wrong task | `GET /api/file/<id1>/<id2_file.cbz>` | `{"error": "File not found"}` | 403/404 | US-5.1 |
| IT-API-013 | Home page load | `GET /` | HTML page with form | 200 | US-6.3 |
| IT-API-014 | CORS not set | `GET /` | No CORS headers | 200 | NFR-4 |
| IT-API-015 | Content-Type for CBZ | `GET /api/file/<id>/<file.cbz>` | `Content-Type: application/x-cbz` | 200 | US-1.4 |

---

### Module: `tests/test_integration.py`

| Test ID | Test Case | Scenario | Expected Outcome | Related US |
|---------|-----------|----------|------------------|------------|
| IT-E2E-001 | Full download workflow | Submit URL → Poll status → Download file | All steps succeed, CBZ received | US-1.1, US-1.3, US-1.4 |
| IT-E2E-002 | Concurrent downloads | Submit 3 URLs simultaneously | All complete independently | US-2.1 |
| IT-E2E-003 | Cached download reuse | Download same URL twice | Second download faster, same files | US-3.1 |
| IT-E2E-004 | Task expiration | Wait > TASK_TTL | Task removed, cache persists | US-4.1, US-3.2 |
| IT-E2E-005 | Cache expiration | Wait > CACHE_TTL | Cache files deleted | US-3.3 |
| IT-E2E-006 | Error handling | Submit URL, mock CLI failure | Task marked failed, error message shown | US-1.5, US-4.2 |
| IT-E2E-007 | Max concurrent limit | Submit 5 URLs (max=3) | 3 running, 2 queued | US-2.1 |
| IT-E2E-008 | Restart persistence | Download → Restart app → Re-download | Cache reused after restart | US-3.2 |
| IT-E2E-009 | Multiple clients | 2 clients poll same task | Both get consistent status | US-2.2 |
| IT-E2E-010 | Large file download | Download multi-chapter manga | No memory issues, streaming works | US-7.2 |

---

## Test Coverage Requirements

### Unit Tests

| Module | Target Coverage | Focus Areas |
|--------|----------------|-------------|
| `validators.py` | 100% | All URL patterns, edge cases |
| `tasks.py` | 90% | RQ integration, job status queries |
| `worker.py` | 90% | Job execution, progress updates |
| `downloader.py` | 90% | Subprocess handling, parsing |
| `cleanup.py` | 85% | Cache expiration, file cleanup |
| `config.py` | 100% | All env vars, validation |
| `routes.py` | 85% | All endpoints, error responses |

### Integration Tests

| Category | Minimum Tests | Focus Areas |
|----------|---------------|-------------|
| API Endpoints | 15 | All routes, error cases |
| E2E Workflows | 10 | Complete user journeys |
| Concurrency | 5 | RQ workers, Redis concurrency |
| Security | 5 | Path traversal, input validation |
| Queue Management | 5 | Job enqueue, status, cancellation |

---

## Test Execution Plan

### Pre-commit Checks

```bash
# Run before every commit
pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=80
black --check app/ tests/
isort --check app/ tests/
mypy app/
ruff check app/ tests/
```

### Continuous Integration

```yaml
# Run on every push
- Unit tests with coverage
- Integration tests
- Code quality checks (black, isort, mypy, ruff)
- Security scan (bandit)
```

### Manual Testing

| Scenario | Frequency | Tester |
|----------|-----------|--------|
| Full E2E workflow | Before release | Developer |
| Browser compatibility | Before release | Developer |
| Docker deployment | Before release | DevOps |
| Load testing (10+ concurrent) | Before major release | QA |

---

## Test Data

### Valid MangaDex URLs (for testing)

```
https://mangadex.org/title/a1b2c3d4-e5f6-7890-abcd-ef1234567890
https://mangadex.org/title/test-manga-slug
https://mangadex.org/title/another-test?tab=chapters
```

### Invalid URLs (for testing)

```
https://example.com/title/test
https://mangadex.org/chapter/abc123
http://mangadex.org/title/test
mangadex.org/title/test
https://mangadex.org/title/../etc/passwd
```

### Mock CLI Outputs

**Success:**
```
Downloading: Test Manga
Chapter 1/10 - Downloaded
Chapter 2/10 - Downloaded
...
Chapter 10/10 - Downloaded
All chapters downloaded successfully
```

**Cached:**
```
Downloading: Test Manga
Chapter 1/10 - Already downloaded (skipped)
Chapter 2/10 - Already downloaded (skipped)
...
```

**Failure:**
```
Error: Failed to fetch manga metadata
HTTPError: 404 Not Found
```

---

## Notes

- All tests should use fixtures for setup/teardown (see `conftest.py`)
- Mock `subprocess.run()` in unit tests to avoid actual downloads
- Use temporary directories for integration tests
- Clean up all test artifacts in teardown
- Use `pytest-timeout` to prevent hanging tests
- Run tests in parallel where possible (`pytest -n auto`)
