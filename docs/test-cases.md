# Test Cases

**Project:** mangadex-dl-wui-vibed
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
| UT-WKR-007 | Metadata stored on success | Mock download returns files | `perform_download_job(url)` | Redis `cache:manga:<series>` key created | US-8.1 |

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
| UT-DL-008 | Generate CLI args with per-manga path and filename format | Valid inputs | `build_cli_args(url, cache_dir)` | Correct flags including `--path CACHE/{manga.title}` and `--filename-chapter` | US-1.1 |
| UT-DL-018 | CLI args path contains `{manga.title}` placeholder | Valid inputs | `build_cli_args(url, cache_dir)` | `--path` value ends with `/{manga.title}` | US-1.1 |
| UT-DL-019 | CLI args include `--filename-chapter` with volume format | Valid inputs | `build_cli_args(url, cache_dir)` | `--filename-chapter` present; format contains `{chapter.volume}`, `{chapter.chapter}`, `{file_ext}` | US-1.1 |
| UT-DL-009 | Scan output directory | Dir with CBZ files | `scan_for_cbz(cache_dir)` | Returns all CBZ file paths | US-1.4 |
| UT-DL-010 | Empty output directory | Empty dir | `scan_for_cbz(cache_dir)` | Returns empty list | US-1.5 |
| UT-DL-011 | Sanitize filename removes unsafe chars | Input `'My:Manga/Title'` | `sanitize_filename(name)` | Returns `'My_Manga_Title'` | US-1.4 |
| UT-DL-012 | Sanitize filename handles empty string | Input `''` | `sanitize_filename(name)` | Returns `'download'` | US-1.4 |
| UT-DL-013 | Sanitize filename preserves normal names | Input `'Chapter 1.cbz'` | `sanitize_filename(name)` | Returns `'Chapter 1.cbz'` unchanged | US-1.4 |
| UT-DL-014 | Display filename with series subdirectory | File at `cache/Series Name/Chapter 1.cbz` | `get_display_filename(path, cache)` | Returns `'Series Name - Chapter 1.cbz'` | US-1.4 |
| UT-DL-015 | Display filename for root-level file | File at `cache/file.cbz` | `get_display_filename(path, cache)` | Returns `'file.cbz'` (no prefix) | US-1.4 |
| UT-DL-016 | Display filename for nested subdirectory | File at `cache/Top/Series/ch.cbz` | `get_display_filename(path, cache)` | Uses immediate parent `'Series'` as prefix | US-1.4 |
| UT-DL-017 | Display filename sanitizes special characters | Series name `'My: Manga'` | `get_display_filename(path, cache)` | Returns `'My_ Manga - Chapter 1.cbz'` | US-1.4 |

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
| UT-CLN-009 | TTL zero skips cleanup | TTL=0, expired files | `cleanup_cache(cache_dir, ttl=0)` | No files deleted | US-3.3 |
| UT-CLN-010 | Remove stale Redis metadata | Expired files, metadata in Redis | `cleanup_cache(cache_dir, ttl)` | Redis metadata deleted | US-8.1 |
| UT-CLN-011 | Keep metadata with active files | Recent files, metadata in Redis | `cleanup_cache(cache_dir, ttl)` | Redis metadata preserved | US-8.1 |

---

### Module: `app/cache.py`

| Test ID | Test Case | Setup | Action | Expected Result | Related US |
|---------|-----------|-------|--------|-----------------|------------|
| UT-CAC-001 | Store manga metadata | Empty Redis | `store_manga_metadata(...)` | Hash written to Redis | US-8.1 |
| UT-CAC-002 | Update merges files | Existing metadata | `store_manga_metadata(...)` again | Files merged, no duplicates | US-8.1 |
| UT-CAC-003 | List all cached mangas | Multiple entries | `list_cached_mangas()` | All series returned, sorted | US-8.1 |
| UT-CAC-004 | List empty Redis | No entries | `list_cached_mangas()` | Returns `[]` | US-8.1 |
| UT-CAC-005 | Get single series | Series in Redis | `get_cached_manga(name)` | Returns metadata dict | US-8.1 |
| UT-CAC-006 | Get missing series | Empty Redis | `get_cached_manga(name)` | Returns `None` | US-8.1 |
| UT-CAC-007 | Delete metadata | Series in Redis | `delete_manga_metadata(name)` | Redis key removed | US-8.1 |
| UT-CAC-008 | Cleanup stale entries | Metadata, no files on disk | `cleanup_stale_metadata()` | Entry deleted, count=1 | US-8.1 |
| UT-CAC-009 | Delete series with files | Series in Redis, CBZ files on disk | `delete_cached_series(name)` | Files deleted, dir removed if empty, metadata removed, returns `True` | US-8.3 |
| UT-CAC-010 | Delete series not found | Empty Redis | `delete_cached_series(name)` | Returns `False` | US-8.3 |
| UT-CAC-011 | Delete series missing files | Series in Redis, files already gone | `delete_cached_series(name)` | Handles gracefully, metadata removed, returns `True` | US-8.3 |

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
| UT-CFG-013 | Zero cache TTL | `CACHE_TTL_SECONDS=0` | `0` (never expire) | US-3.3 |

---

## UI Test Cases (Browser/Playwright)

### Module: `tests/test_ui.py`

| Test ID | Test Case | User Action | Expected UI Behavior | Status | Related US |
|---------|-----------|-------------|---------------------|--------|------------|
| JS-UI-001 | Form renders with input and button | Page load | Form visible with URL input and submit button | ✅ Passing | US-1.1 |
| JS-UI-002 | Submit valid URL returns task card | Enter valid URL, click submit | Task card appears with task ID | ✅ Passing | US-1.1 |
| JS-UI-003 | Empty URL shows client error | Submit empty form | HTML5 validation or JS error message | ✅ Passing | US-1.2 |
| JS-UI-004 | Invalid URL shows server error | Submit invalid URL | Error alert with "Invalid" message | ✅ Passing | US-1.2 |
| JS-UI-005 | Display queued status | Submit URL | Task card shows "queued" badge | ✅ Passing | US-1.3 |
| JS-UI-006 | Display running status with indeterminate progress | Task transitions to started | Indeterminate progress bar with "Downloading..." text visible | ✅ Passing | US-1.3 |
| JS-UI-007 | Display completed status with files | Task completes | File list with download links visible | ✅ Passing | US-1.4 |
| JS-UI-008 | Display failed status with error | Task fails | "failed" badge + error message visible | ✅ Passing | US-1.5 |
| JS-UI-009 | Auto-polling starts after submit | Submit URL | Status updates automatically (polling) | ✅ Passing | US-1.3 |
| JS-UI-010 | Polling stops on completion | Task finishes | Status remains "finished", no more polls | ✅ Passing | US-1.3 |
| JS-UI-011 | Polling stops on failure | Task fails | Status remains "failed", no more polls | ✅ Passing | US-1.5 |
| JS-UI-012 | Download file link works | Click file download link | Link has correct href and download attr | ✅ Passing | US-1.4 |
| JS-UI-013 | Multiple tasks displayed | Submit 2+ URLs | Multiple task cards shown independently | ✅ Passing | US-2.1, US-2.2 |
| JS-UI-014 | Button disabled during submit | Click submit | Button disabled briefly during request | ✅ Passing | US-1.1 |
| JS-UI-015 | Retry option on failure | Task fails | Retry button appears and is clickable | ✅ Passing | US-1.5 |
| JS-UI-016 | Task dismiss/removal | Click dismiss button | Task card removed from DOM | ✅ Passing | US-4.1 |
| JS-EDGE-001 | Network error on submit | Server unreachable | Error message shown | ⏭️ Skipped | US-4.2 |
| JS-EDGE-004 | Multiple rapid submits (debounce) | Click submit 5x rapidly | Only 1-2 tasks created (debounced) | ✅ Passing | US-1.1 |
| JS-EDGE-006 | XSS prevention | Submit malicious input | Content escaped, no script execution | ✅ Passing | US-5.2 |
| JS-A11Y-001 | Form has proper labels | Page load | Label associated with input (for/id) | ✅ Passing | NFR-3 |
| JS-A11Y-002 | Error messages have role="alert" | Error occurs | Error container has role="alert" | ✅ Passing | NFR-3 |
| JS-A11Y-003 | Loading state announced | Page load | Tasks container has aria-live="polite" | ✅ Passing | NFR-3 |

**Test Summary**: 21 passing, 1 skipped (network interception requires route mocking)

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
| IT-API-016 | Series prefix in Content-Disposition | `GET /api/file/<id>/<file.cbz>` (file in series subdir) | `Content-Disposition` contains `"Series Name - file.cbz"` | 200 | US-1.4 |
| IT-CACHE-001 | Cache page renders | `GET /cache` | HTML page with cache listing | 200 | US-8.1 |
| IT-CACHE-002 | Cache page shows series | `GET /cache` (Redis has data) | Series name and files visible | 200 | US-8.1 |
| IT-CACHE-003 | Cache file download | `GET /api/cache/<series>/<file.cbz>` | Binary CBZ data | 200 | US-8.1 |
| IT-CACHE-004 | Cache path traversal in series | `GET /api/cache/../etc/test.cbz` | Rejected | 403/404 | US-5.1 |
| IT-CACHE-005 | Cache path traversal in filename | `GET /api/cache/series/../../etc/passwd` | Rejected | 403/404 | US-5.1 |
| IT-CACHE-006 | Cache file not found | `GET /api/cache/NoSeries/missing.cbz` | `{"error": "File not found"}` | 404 | US-8.1 |
| IT-CACHE-007 | Delete cached series success | `DELETE /api/cache/<series>` (series exists) | Files deleted, metadata removed, `{"deleted": true}` | 200 | US-8.3 |
| IT-CACHE-008 | Delete cached series not found | `DELETE /api/cache/<series>` (series absent) | `{"error": "Not found"}` | 404 | US-8.3 |
| IT-CACHE-009 | Delete path traversal rejected | `DELETE /api/cache/..%2Fetc` | `{"error": "Invalid series name"}` | 403 | US-5.1 |
| IT-CACHE-010 | Cache card renders remove button | `GET /cache` (Redis has data) | Card contains remove button with `data-series` attribute | 200 | US-8.3 |
| IT-CACHE-011 | Cache deletion clears sessionStorage tasks | Delete series; sessionStorage has finished task with files in that series dir | Matching task entries removed from `sessionStorage['mangadex-tasks']` | — | US-8.3 |
| IT-NAV-001 | Navbar on index page | `GET /` | Navbar with Cache link rendered | 200 | US-8.2 |
| IT-NAV-002 | Navbar on cache page | `GET /cache` | Navbar with Home link rendered | 200 | US-8.2 |

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
| IT-E2E-011 | Cache no expiration | TTL=0, old files | Cache files preserved | US-3.3 |

---

## Test Coverage Requirements

### Unit Tests

| Module | Target Coverage | Focus Areas | Status |
|--------|----------------|-------------|--------|
| `validators.py` | 100% | All URL patterns, edge cases | ✅ 10/10 passing |
| `tasks.py` | 90% | RQ integration, job status queries | ✅ 10/10 passing |
| `worker.py` | 90% | Job execution, progress updates | ✅ 6/6 passing |
| `downloader.py` | 90% | Subprocess handling, parsing | ✅ 19/19 passing |
| `cleanup.py` | 85% | Cache expiration, file cleanup | ✅ 8/8 passing |
| `config.py` | 100% | All env vars, validation | ✅ 13/13 passing |
| `routes.py` | 85% | All endpoints, error responses | ✅ 16/16 passing |

**Unit Test Summary**: 91/91 passing (Phases 1-4 complete + Phase 6 display filename + Phase 7 path placeholders)

### UI Tests (Playwright)

| Category | Implemented Tests | Focus Areas | Status |
|----------|------------------|-------------|--------|
| Form & Submission | 4 | Submit, validation, errors | ✅ 4/4 passing |
| Status Display | 4 | Queued, running, finished, failed | ✅ 4/4 passing |
| Polling | 3 | Auto-start, auto-stop | ✅ 3/3 passing |
| File Downloads | 2 | Links, downloads | ✅ 2/2 passing |
| Multiple Tasks | 4 | Concurrent tasks, dismiss, retry | ✅ 4/4 passing |
| Edge Cases | 2 | Debounce, XSS | ✅ 2/2 passing, 1 skipped |
| Accessibility | 3 | ARIA, labels, alerts | ✅ 3/3 passing |

**UI Test Summary**: 21/22 passing, 1 skipped (Phase 5 complete)

### Integration Tests

| Category | Minimum Tests | Focus Areas | Status |
|----------|---------------|-------------|--------|
| API Endpoints | 16 | All routes, error cases | ✅ 16/16 passing |
| E2E Workflows | 10 | Complete user journeys | ✅ 10/10 passing |
| Concurrency | 5 | RQ workers, Redis concurrency | ✅ Covered |
| Security | 5 | Path traversal, input validation | ✅ Covered |
| Queue Management | 5 | Job enqueue, status, cancellation | ✅ Covered |

**Overall Test Summary**: **111 tests passing, 1 skipped** ✅

---

## Test Execution Plan

### Pre-commit Checks

```shell
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

---

## Implementation Status

### Phase 1-4: Backend (Complete) ✅
- **82/82 unit tests passing**
- All modules implemented: config, validators, downloader, worker, tasks, cleanup, routes
- Test coverage: >80% for all modules
- All code quality checks passing (black, isort, ruff, mypy)

### Phase 5: Web UI JavaScript (Complete) ✅
- **21/22 UI tests passing, 1 skipped**
- `app/static/app.js`: 323 lines vanilla JavaScript (no framework)
- Architecture: ApiClient, TaskManager, UI modules
- Features: Form submission, auto-polling, status display, file downloads, multiple tasks
- Security: XSS prevention, input validation
- Accessibility: ARIA attributes, semantic HTML
- Testing: Playwright + pytest for real browser testing

### Overall Project Status
- **Total: 111 tests passing, 1 skipped** ✅
- **All user stories implemented** (US-1.1 through US-7.2)
- **Production-ready**

### Test Execution
```shell
# Run all tests
pytest -v  # 111 passed, 1 skipped

# Run UI tests only
pytest tests/test_ui.py -v  # 21 passed, 1 skipped

# Run backend tests only
pytest tests/ --ignore=tests/test_ui.py  # 90 passed
```
