# Functional Requirements Document (FRD)

**Project:** mangadex-dl-wui-vibed
**Version:** 1.0
**Date:** 2026-02-04

## 1. Introduction

### 1.1 Purpose

This document defines the functional requirements for **mangadex-dl-wui-vibed**, a web-based user interface for the `mangadex-dl` command-line tool. The application enables users to download manga from MangaDex through a simple browser interface and retrieve the results as CBZ files.

### 1.2 Scope

The application provides:
- A web UI for submitting MangaDex URLs
- Background download processing using the `mangadex-dl` CLI
- Real-time progress tracking via polling
- File delivery of completed CBZ downloads
- Persistent caching to avoid re-downloading chapters
- Automatic cleanup of expired tasks and cached files

### 1.3 Definitions

- **Task/Job**: A download job identified by a UUID, managed by RQ
- **CBZ**: Comic Book ZIP archive format
- **Cache**: Persistent storage for downloaded manga files
- **Task TTL**: Time-to-live for task metadata records
- **Cache TTL**: Time-to-live for cached CBZ files
- **RQ**: Redis Queue - Python job queue library
- **Worker**: RQ worker process that executes download jobs

## 2. System Overview

### 2.1 Architecture

```
User Browser <--> Flask Web Server <--> Redis Queue (RQ) <--> RQ Worker(s) <--> mangadex-dl CLI
                       |                      |                     |
                       |                      v                     v
                       |                   Job Status        Persistent Cache
                       v
                Static File Serving
```

**Components**:
- **Flask Web Server**: HTTP API and static file serving
- **Redis**: Job queue storage and status tracking
- **RQ Workers**: Background processes executing download jobs
- **Persistent Cache**: File system storage for CBZ files

### 2.2 Technology Stack

- **Backend**: Python 3.11+, Flask
- **Queue**: Redis + RQ (Redis Queue)
- **CLI Tool**: mangadex-dl
- **Storage**: File system (cache directory)
- **Concurrency**: RQ workers (configurable count)
- **Deployment**: Docker + Docker Compose

## 3. Functional Requirements

### FR-1: Web User Interface

**Description**: Provide a browser-based interface for manga downloads.

**Requirements**:
- FR-1.1: Display a form to input MangaDex URLs
- FR-1.2: Show visual feedback when download is initiated
- FR-1.3: Display real-time progress updates during download
- FR-1.4: Show download status (queued, running, completed, failed)
- FR-1.5: Provide download links for completed CBZ files
- FR-1.6: Display error messages for failed downloads
- FR-1.7: Support multiple simultaneous task displays

### FR-2: Download Initiation

**Description**: Accept and validate MangaDex URLs to start downloads.

**Requirements**:
- FR-2.1: Accept POST requests with MangaDex URL
- FR-2.2: Validate URL format (must be mangadex.org/title/*)
- FR-2.3: Generate unique task ID (UUID)
- FR-2.4: Return task ID immediately to user
- FR-2.5: Reject invalid URLs with error message
- FR-2.6: Enqueue download job to Redis Queue (RQ)
- FR-2.7: Enforce maximum concurrent downloads via RQ worker count

### FR-3: Background Download Processing

**Description**: Execute manga downloads in RQ worker processes.

**Requirements**:
- FR-3.1: Enqueue download job to RQ for worker processing
- FR-3.2: Invoke `mangadex-dl` via subprocess
- FR-3.3: Use persistent cache directory with per-manga subdirectory (`--path CACHE_DIR/{manga.title}`)
- FR-3.4: Download all chapters (`--input-pos "*"`)
- FR-3.5: Save as CBZ format (`--save-as cbz`)
- FR-3.6: Capture stdout/stderr from subprocess
- FR-3.7: Parse progress information from output
- FR-3.8: Update task status atomically
- FR-3.9: Handle subprocess errors gracefully
- FR-3.10: Record completed CBZ file paths
- FR-3.11: Name chapter files with volume and chapter numbers (`--filename-chapter "Vol. {chapter.volume} Ch. {chapter.chapter}{file_ext}"`)

### FR-4: Progress Tracking

**Description**: Provide real-time status updates for download tasks.

**Requirements**:
- FR-4.1: Expose GET endpoint `/api/status/<task_id>`
- FR-4.2: Return current task status (queued, running, completed, failed)
- FR-4.3: Return progress indication (status-only transitions; chapter-level progress deferred)
- FR-4.4: Return list of completed CBZ files
- FR-4.5: Return error message if task failed
- FR-4.6: Return 404 if task ID not found
- FR-4.7: Support polling from multiple clients simultaneously

### FR-5: File Delivery

**Description**: Serve downloaded CBZ files to users.

**Requirements**:
- FR-5.1: Expose GET endpoint `/api/file/<task_id>/<filename>`
- FR-5.2: Validate task ID exists and is completed
- FR-5.3: Validate filename belongs to the task
- FR-5.4: Serve file from persistent cache
- FR-5.5: Set appropriate content-type (application/x-cbz)
- FR-5.6: Set content-disposition with manga series name prefix (e.g., "Series Name - Chapter 1.cbz")
- FR-5.7: Return 404 if file not found
- FR-5.8: Return 403 if filename doesn't match task

### FR-6: Caching Strategy

**Description**: Implement persistent caching to avoid redundant downloads.

**Requirements**:
- FR-6.1: Maintain persistent cache directory
- FR-6.2: Organize cache by manga title subdirectories using `mangadex-dl`'s `{manga.title}` path placeholder, which resolves to the real manga title at download time
- FR-6.3: Use `mangadex-dl`'s native skip-downloaded logic
- FR-6.4: Reuse existing CBZ files for repeated URLs
- FR-6.5: Track cache file association with tasks
- FR-6.6: Implement cache TTL (default: 7 days; 0 = never expire)
- FR-6.7: Clean up expired cache files automatically
- FR-6.8: Keep cache separate from task temp directories

### FR-7: Task Management

**Description**: Manage lifecycle of download jobs via RQ.

**Requirements**:
- FR-7.1: Store job status and metadata in Redis via RQ
- FR-7.2: Track job status transitions (queued → started → finished/failed)
- FR-7.3: Store job metadata (URL, timestamps, status, result)
- FR-7.4: Associate CBZ files with job IDs
- FR-7.5: Implement job result TTL (default: 1 hour after completion)
- FR-7.6: Support concurrent job status queries
- FR-7.7: Leverage RQ's atomic job status updates
- FR-7.8: Persist job state across application restarts

### FR-8: Cleanup

**Description**: Automatically remove expired data.

**Requirements**:
- FR-8.1: Configure RQ job result TTL for automatic job cleanup
- FR-8.2: Run background cleanup process for cache files
- FR-8.3: Check for expired cache files periodically (every 5 minutes)
- FR-8.4: Remove cached files after cache TTL expires (skipped when TTL is 0)
- FR-8.5: Preserve cache files for active/recent jobs
- FR-8.6: Remove temp directories for completed jobs
- FR-8.7: Log cleanup actions
- FR-8.8: Handle cleanup errors without crashing

### FR-9: Configuration

**Description**: Support runtime configuration via environment variables.

**Requirements**:
- FR-9.1: Configure Redis connection URL
- FR-9.2: Configure cache directory path
- FR-9.3: Configure temp directory path
- FR-9.4: Configure job result TTL in seconds
- FR-9.5: Configure cache TTL in seconds (0 = disable expiration)
- FR-9.6: Configure RQ worker count (concurrent downloads)
- FR-9.7: Provide sensible defaults for all settings
- FR-9.8: Validate configuration values at startup

### FR-10: Error Handling

**Description**: Handle errors gracefully and provide user feedback.

**Requirements**:
- FR-10.1: Validate all API inputs
- FR-10.2: Return appropriate HTTP status codes
- FR-10.3: Provide descriptive error messages
- FR-10.4: Log errors to application logs
- FR-10.5: Handle subprocess failures
- FR-10.6: Handle filesystem errors
- FR-10.7: Handle Redis connection errors
- FR-10.8: Handle RQ job failures gracefully
- FR-10.9: Never expose stack traces to users

### FR-11: Cache Browsing UI

Users can browse previously downloaded manga from a dedicated cache page.

- FR-11.1: Provide a `/cache` page listing all cached manga series
- FR-11.2: Display series name, file count, download date, and per-file download links
- FR-11.3: Series name links back to original MangaDex URL when available
- FR-11.4: Serve cached CBZ files via `GET /api/cache/<series>/<filename>`
- FR-11.5: Reject path traversal attempts with 403
- FR-11.6: Store series metadata in Redis after each successful download
- FR-11.7: Remove Redis metadata when all files for a series expire from cache
- FR-11.8: Sticky navigation bar on all pages (Home and Cache)

## 4. Non-Functional Requirements

### NFR-1: Performance

- Support at least 3 concurrent downloads (configurable)
- Task status checks complete in < 100ms
- File downloads stream efficiently (no memory buffering)

### NFR-2: Reliability

- Graceful handling of `mangadex-dl` failures
- Automatic retry not implemented (user re-submits)
- No data loss on cache directory

### NFR-3: Maintainability

- Type hints throughout codebase
- Unit test coverage > 80%
- Integration tests for all endpoints
- Clear separation of concerns (routes, business logic, subprocess)

### NFR-4: Security

- Input validation on all endpoints
- Path traversal protection in file serving
- No shell injection vulnerabilities
- CORS not required (same-origin)

### NFR-5: Deployment

- Multi-container Docker deployment (Flask app + Redis + RQ workers)
- Managed via Docker Compose
- Persistent volumes for cache and Redis data
- Health check endpoint (/)
- Graceful scaling via worker count configuration

## 5. Out of Scope

The following are explicitly **not** included in this version:

- WebSocket-based real-time updates
- User authentication/authorization
- Dynamic queue prioritization
- Bandwidth throttling
- MangaDex API integration (uses CLI only)
- Manual cache deletion UI (browsing is supported; deletion is not)
- Download resume/pause functionality
- Multi-server deployment (horizontal scaling)
- Rate limiting per user

## 6. Dependencies

- **mangadex-dl**: Must be installed and available in PATH
- **Python 3.11+**: Required for type hints and modern syntax
- **Flask**: Web framework
- **Redis**: Queue storage and job status tracking
- **RQ (Redis Queue)**: Job queue library
- **Docker**: Containerization

## 7. Assumptions

- `mangadex-dl` CLI is stable and reliable
- MangaDex URLs follow consistent format
- Filesystem supports concurrent reads/writes
- Cache directory has sufficient disk space
- Users understand polling-based status updates
