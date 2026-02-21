# User Stories

**Project:** mangadex-dl-wui-vibed
**Version:** 1.0
**Date:** 2026-02-04

---

## Epic 1: Download Management

### US-1.1: Submit Download Request ✅

**As a** user
**I want to** submit a MangaDex URL through a web form
**So that** I can download manga without using the command line

**Acceptance Criteria**:
- Given I am on the home page
- When I enter a valid MangaDex URL (https://mangadex.org/title/*)
- And I click "Download"
- Then I receive a unique task ID
- And the download starts in the background
- And I see a confirmation message

**Related FRs**: FR-1.1, FR-1.2, FR-2.1, FR-2.3, FR-2.4
**Status**: ✅ **Implemented** - Phase 5 (JS-UI-001, JS-UI-002, tests/test_ui.py)

---

### US-1.2: Invalid URL Handling ✅

**As a** user
**I want to** receive clear error messages for invalid URLs
**So that** I know what went wrong and can correct it

**Acceptance Criteria**:
- Given I am on the home page
- When I enter an invalid URL (not mangadex.org/title/*)
- And I click "Download"
- Then I see an error message explaining the issue
- And no download task is created

**Related FRs**: FR-2.2, FR-2.5, FR-10.1, FR-10.3
**Status**: ✅ **Implemented** - Phase 5 (JS-UI-003, JS-UI-004, tests/test_ui.py)

---

### US-1.3: Track Download Progress ✅

**As a** user
**I want to** see real-time progress of my download
**So that** I know how long to wait

**Acceptance Criteria**:
- Given I have submitted a download request
- When the download is processing
- Then I see the current status (queued, downloading, completed, failed)
- And I see an indeterminate progress indicator while downloading
- And the information updates automatically via polling
- Note: Chapter-level progress tracking (current/total) is deferred; status-only transitions are tracked

**Related FRs**: FR-1.3, FR-1.4, FR-4.1, FR-4.2, FR-4.3
**Status**: ✅ **Implemented** - Phase 5 (JS-UI-005, JS-UI-006, JS-UI-009, JS-UI-010, tests/test_ui.py)

---

### US-1.4: Download Completed Files ✅

**As a** user
**I want to** download the CBZ files when the task completes
**So that** I can read the manga offline

**Acceptance Criteria**:
- Given my download task has completed successfully
- When I view the task status
- Then I see a list of all downloaded CBZ files
- And each file has a download link
- And each file's download name includes the manga series name as a prefix
- When I click a download link
- Then the CBZ file downloads to my browser with the prefixed filename

**Related FRs**: FR-1.5, FR-4.4, FR-5.1, FR-5.2, FR-5.4, FR-5.5, FR-5.6
**Status**: ✅ **Implemented** - Phase 5 (JS-UI-007, JS-UI-012, tests/test_ui.py)

---

### US-1.5: Handle Failed Downloads ✅

**As a** user
**I want to** see clear error messages when downloads fail
**So that** I understand what went wrong

**Acceptance Criteria**:
- Given my download task has failed
- When I view the task status
- Then I see status "failed"
- And I see a descriptive error message
- And I have the option to retry with a new task

**Related FRs**: FR-1.6, FR-4.5, FR-10.3, FR-10.4
**Status**: ✅ **Implemented** - Phase 5 (JS-UI-008, JS-UI-011, JS-UI-015, tests/test_ui.py)

---

## Epic 2: Concurrent Operations

### US-2.1: Multiple Simultaneous Downloads ✅

**As a** user
**I want to** submit multiple download requests
**So that** I can download multiple manga at once

**Acceptance Criteria**:
- Given I have submitted one download request
- When I submit another download request
- Then both downloads proceed independently
- And I can track each download separately
- And the system respects the max concurrent limit

**Related FRs**: FR-1.7, FR-2.7, FR-3.1, FR-7.6, FR-9.5
**Status**: ✅ **Implemented** - Phase 5 (JS-UI-013, tests/test_ui.py)

---

### US-2.2: View Multiple Task Statuses ✅

**As a** user
**I want to** track multiple downloads simultaneously
**So that** I can monitor all my active downloads

**Acceptance Criteria**:
- Given I have multiple active downloads
- When I poll for status updates
- Then each task maintains independent status
- And I can query any task by its ID
- And concurrent status checks don't interfere

**Related FRs**: FR-4.7, FR-7.6
**Status**: ✅ **Implemented** - Phase 5 (JS-UI-013, tests/test_ui.py)

---

## Epic 3: Caching and Efficiency

### US-3.1: Avoid Re-downloading Chapters ✅

**As a** user
**I want** already-downloaded chapters to be reused
**So that** I don't waste time and bandwidth

**Acceptance Criteria**:
- Given I previously downloaded a manga
- When I submit the same URL again
- Then the system reuses existing CBZ files from cache
- And the download completes much faster
- And I get the same files as before

**Related FRs**: FR-6.1, FR-6.2, FR-6.3, FR-6.4, FR-6.5
**Status**: ✅ **Implemented** - Phase 2 (app/downloader.py, mangadex-dl native caching)

---

### US-3.2: Persistent Cache Across Restarts ✅

**As a** user
**I want** my downloads to persist across app restarts
**So that** I don't lose downloaded manga

**Acceptance Criteria**:
- Given I have downloaded manga to the cache
- When the application restarts
- Then the cached files remain available
- And re-requesting the same URL still reuses cache
- But old task IDs are no longer valid

**Related FRs**: FR-6.1, FR-6.8
**Status**: ✅ **Implemented** - Phase 1 (app/config.py, CACHE_DIR configuration)

---

### US-3.3: Automatic Cache Cleanup ✅

**As a** system administrator
**I want** old cached files to be automatically deleted
**So that** disk space doesn't fill up indefinitely

**Acceptance Criteria**:
- Given cached files older than CACHE_TTL
- When the cleanup job runs
- Then expired cache files are deleted
- And recent cache files are preserved
- And active task files are never deleted
- Given CACHE_TTL_SECONDS is set to 0
- When the cleanup job runs
- Then no cache files are deleted regardless of age

**Related FRs**: FR-6.6, FR-6.7, FR-8.5, FR-8.6
**Status**: ✅ **Implemented** - Phase 4 (app/cleanup.py, UT-CLN-001-008)

---

## Epic 4: System Reliability

### US-4.1: Task Record Cleanup ✅

**As a** system administrator
**I want** expired task records to be automatically cleaned up
**So that** memory usage remains bounded

**Acceptance Criteria**:
- Given completed tasks older than TASK_TTL
- When the cleanup job runs
- Then expired task records are removed from memory
- And their temp directories are deleted
- But cached CBZ files are preserved

**Related FRs**: FR-7.5, FR-8.1, FR-8.2, FR-8.3, FR-8.4
**Status**: ✅ **Implemented** - Phase 4 (app/cleanup.py) + Phase 5 (JS-UI-016 dismiss button)

---

### US-4.2: Graceful Error Recovery ✅

**As a** user
**I want** the system to handle errors gracefully
**So that** one failure doesn't break the entire application

**Acceptance Criteria**:
- Given a download encounters an error
- When the error occurs
- Then the task status changes to "failed"
- And other tasks continue unaffected
- And I see a helpful error message
- And no stack traces are exposed

**Related FRs**: FR-3.9, FR-10.5, FR-10.6, FR-10.7, FR-10.8
**Status**: ✅ **Implemented** - Phase 3 (app/worker.py) + Phase 4 (app/routes.py)

---

### US-4.3: Concurrent Job Safety ✅

**As a** developer
**I want** job operations to be safe from race conditions
**So that** concurrent access doesn't corrupt data

**Acceptance Criteria**:
- Given multiple workers processing jobs
- When they access Redis simultaneously
- Then RQ ensures atomic job status updates
- And no race conditions occur
- And data consistency is maintained via Redis transactions

**Related FRs**: FR-7.1, FR-7.6, FR-7.7, FR-7.8
**Status**: ✅ **Implemented** - Phase 3 (app/tasks.py, RQ/Redis atomic operations)

---

## Epic 5: File Security

### US-5.1: Path Traversal Protection ✅

**As a** system administrator
**I want** file access to be validated
**So that** users can't access files outside their tasks

**Acceptance Criteria**:
- Given a file download request
- When the filename contains path traversal attempts (../)
- Then the request is rejected with 403
- And no files outside the cache are accessible
- And only files belonging to the task ID are served

**Related FRs**: FR-5.3, FR-5.7, FR-5.8, NFR-4
**Status**: ✅ **Implemented** - Phase 1 (app/validators.py) + Phase 4 (app/routes.py)

---

### US-5.2: Input Validation ✅

**As a** system administrator
**I want** all API inputs to be validated
**So that** the system is protected from injection attacks

**Acceptance Criteria**:
- Given any API endpoint
- When I submit malicious input
- Then the input is sanitized/rejected
- And no shell commands are injected
- And no arbitrary file paths are accessed

**Related FRs**: FR-10.1, NFR-4
**Status**: ✅ **Implemented** - Phase 1 (app/validators.py) + Phase 2 (app/downloader.py subprocess safety) + Phase 5 (JS XSS prevention)

---

## Epic 6: Configuration and Deployment

### US-6.1: Environment-based Configuration ✅

**As a** system administrator
**I want to** configure the app via environment variables
**So that** I can customize behavior without code changes

**Acceptance Criteria**:
- Given I set environment variables
- When the application starts
- Then it uses my configured values
- And falls back to sensible defaults if not set
- And invalid values are rejected with clear errors

**Related FRs**: FR-9.1, FR-9.2, FR-9.3, FR-9.4, FR-9.5, FR-9.6, FR-9.7, FR-9.8
**Status**: ✅ **Implemented** - Phase 1 (app/config.py, UT-CFG-001-012)

---

### US-6.2: Docker Deployment ✅

**As a** system administrator
**I want to** deploy the app using Docker Compose
**So that** deployment is simple and reproducible

**Acceptance Criteria**:
- Given I run `docker compose up`
- When all containers start (Flask app, Redis, RQ workers)
- Then the Flask app is accessible
- And Redis is running and connectable
- And RQ workers are processing the queue
- And the cache directory is mounted as a volume
- And mangadex-dl is available in the worker container
- And the app is ready to accept requests

**Related FRs**: NFR-5
**Status**: ✅ **Implemented** - docker-compose.yml, Dockerfile

---

### US-6.3: Health Checks ✅

**As a** system administrator
**I want** a health check endpoint
**So that** I can monitor if the app is running

**Acceptance Criteria**:
- Given the app is running
- When I request GET /
- Then I receive a 200 response
- And the HTML page loads successfully

**Related FRs**: FR-1.1, NFR-5
**Status**: ✅ **Implemented** - Phase 4 (app/routes.py, IT-API-013)

---

## Epic 8: Cache Browsing

### US-8.1: Browse Cached Manga ✅

**As a** user
**I want to** see a list of previously downloaded manga
**So that** I can re-download files without resubmitting URLs

**Acceptance Criteria**:
- Given I have previously downloaded manga
- When I navigate to /cache
- Then I see a list of cached series with file names and download links
- And each series shows the source MangaDex URL (linked)
- And I can download any CBZ file directly from the cache page

**Related FRs**: FR-11.1, FR-11.2, FR-11.3, FR-11.4
**Status**: ✅ **Implemented** - (app/cache.py, app/routes.py, app/templates/cache.html)

---

### US-8.2: Sticky Navigation Bar ✅

**As a** user
**I want** a persistent navigation bar at the top of every page
**So that** I can switch between Home and Cache without scrolling

**Acceptance Criteria**:
- Given I am on any page
- When I scroll down
- Then the navigation bar remains visible at the top
- And links to both Home and Cache pages are present
- And the active page link is visually highlighted

**Related FRs**: FR-11.8
**Status**: ✅ **Implemented** - (app/templates/base.html, app/static/style.css)

---

## Epic 7: Performance

### US-7.1: Fast Status Checks ✅

**As a** user
**I want** status checks to be fast
**So that** the UI feels responsive

**Acceptance Criteria**:
- Given I poll the status endpoint
- When the server processes my request
- Then the response arrives in < 100ms
- And the endpoint supports high polling frequency

**Related FRs**: NFR-1
**Status**: ✅ **Implemented** - Phase 3 (app/tasks.py, Redis-backed status queries)

---

### US-7.2: Efficient File Streaming ✅

**As a** user
**I want** large CBZ files to download efficiently
**So that** I don't encounter memory issues

**Acceptance Criteria**:
- Given I download a large CBZ file
- When the server sends the file
- Then it streams efficiently without buffering to memory
- And large files don't cause OOM errors

**Related FRs**: NFR-1
**Status**: ✅ **Implemented** - Phase 4 (app/routes.py, Flask send_file streaming)

---

## Traceability Matrix

| User Story | Functional Requirements                                |
| ---------- | ------------------------------------------------------ |
| US-1.1     | FR-1.1, FR-1.2, FR-2.1, FR-2.3, FR-2.4                 |
| US-1.2     | FR-2.2, FR-2.5, FR-10.1, FR-10.3                       |
| US-1.3     | FR-1.3, FR-1.4, FR-4.1, FR-4.2, FR-4.3                 |
| US-1.4     | FR-1.5, FR-4.4, FR-5.1, FR-5.2, FR-5.4, FR-5.5, FR-5.6 |
| US-1.5     | FR-1.6, FR-4.5, FR-10.3, FR-10.4                       |
| US-2.1     | FR-1.7, FR-2.7, FR-3.1, FR-7.6, FR-9.6                 |
| US-2.2     | FR-4.7, FR-7.6                                         |
| US-3.1     | FR-6.1, FR-6.2, FR-6.3, FR-6.4, FR-6.5                 |
| US-3.2     | FR-6.1, FR-6.8                                         |
| US-3.3     | FR-6.6, FR-6.7, FR-8.4, FR-8.5                         |
| US-4.1     | FR-7.5, FR-8.1, FR-8.2, FR-8.3, FR-8.6                 |
| US-4.2     | FR-3.9, FR-10.5, FR-10.6, FR-10.7, FR-10.8, FR-10.9    |
| US-4.3     | FR-7.1, FR-7.6, FR-7.7, FR-7.8                         |
| US-5.1     | FR-5.3, FR-5.7, FR-5.8, NFR-4                          |
| US-5.2     | FR-10.1, NFR-4                                         |
| US-6.1     | FR-9.1-9.8                                             |
| US-6.2     | NFR-5                                                  |
| US-6.3     | FR-1.1, NFR-5                                          |
| US-7.1     | NFR-1                                                  |
| US-7.2     | NFR-1                                                  |
| US-8.1     | FR-11.1, FR-11.2, FR-11.3, FR-11.4, FR-11.6, FR-11.7   |
| US-8.2     | FR-11.8                                                |
