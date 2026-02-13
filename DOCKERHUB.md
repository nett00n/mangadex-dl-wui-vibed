# mangadex-dl-wui-vibed

A browser-based web UI for [mangadex-downloader](https://github.com/mansuf/mangadex-downloader). Paste a MangaDex URL, hit Download, and get a CBZ file — no command line required.

[![Docker Hub](https://img.shields.io/docker/pulls/5mdt/mangadex-dl-wui-vibed)](https://hub.docker.com/r/5mdt/mangadex-dl-wui-vibed)
[![GitHub](https://img.shields.io/badge/source-GitHub-181717?logo=github)](https://github.com/nett00n/mangadex-dl-wui-vibed)
[![License](https://img.shields.io/badge/license-GPLv3-blue.svg)](https://github.com/nett00n/mangadex-dl-wui-vibed/blob/main/LICENSE.md)

---

## Tags

| Tag | Description |
|-----|-------------|
| `release` | Latest build from `main` branch |
| `v1.2.3` | Specific release tag |
| `sha-<commit>` | Pinned to an exact commit |

**Platforms:** `linux/amd64`, `linux/arm64`

---

## Quick Start

```yaml
services:
  app:
    image: 5mdt/mangadex-dl-wui-vibed:release
    restart: unless-stopped
    environment:
      REDIS_URL: redis://redis:6379/0
      CACHE_DIR: /downloads/cache
      TEMP_DIR: /tmp/mangadex-wui-vibed
      TASK_TTL_SECONDS: "3600"
      CACHE_TTL_SECONDS: "604800"
      RQ_WORKER_COUNT: "3"
    volumes:
      - downloads:/downloads/cache
    ports:
      - "5000:5000"
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

volumes:
  downloads:
  redis_data:
```

Visit `http://localhost:5000`

---

## With Traefik and Watchtower

```yaml
services:
  app:
    image: 5mdt/mangadex-dl-wui-vibed:release
    restart: unless-stopped
    environment:
      REDIS_URL: redis://redis:6379/0
      CACHE_DIR: /downloads/cache
      TEMP_DIR: /tmp/mangadex-wui-vibed
      TASK_TTL_SECONDS: "3600"
      CACHE_TTL_SECONDS: "604800"
      RQ_WORKER_COUNT: "3"
    volumes:
      - downloads:/downloads/cache
    depends_on:
      - redis
    networks:
      - traefik_default
      - default
    labels:
      com.centurylinklabs.watchtower.enable: "true"
      traefik.docker.network: traefik_default
      traefik.enable: true
      traefik.http.routers.mangadex-dl-wui-vibed.entrypoints: websecure
      traefik.http.routers.mangadex-dl-wui-vibed.rule: Host(`${SERVICE_NAME_OVERRIDE:-mangadex-dl-wui-vibed}.${DOMAIN_NAME:-local}`)
      traefik.http.routers.mangadex-dl-wui-vibed.service: mangadex-dl-wui-vibed
      traefik.http.routers.mangadex-dl-wui-vibed.tls: true
      traefik.http.routers.mangadex-dl-wui-vibed.tls.certresolver: letsencrypt-cloudflare-dns-challenge
      traefik.http.services.mangadex-dl-wui-vibed.loadbalancer.server.port: 5000
      local.yacht.port.5000: WebUI

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

volumes:
  downloads:
  redis_data:

networks:
  traefik_default:
    external: true
```

Set `DOMAIN_NAME` (and optionally `SERVICE_NAME_OVERRIDE`) in your `.env` file or shell environment.

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `CACHE_DIR` | `/downloads/cache` | Persistent manga cache |
| `TEMP_DIR` | `/tmp/mangadex-wui-vibed` | Temporary task directories |
| `TASK_TTL_SECONDS` | `3600` | Task record expiration (seconds) |
| `CACHE_TTL_SECONDS` | `604800` | Cached file expiration (`0` = never expire) |
| `RQ_WORKER_COUNT` | `3` | Concurrent download workers |

---

## Architecture

```
Browser --> Flask --> Redis Queue (RQ) --> Worker --> subprocess: mangadex-dl
```

All downloads run as background jobs. The web UI polls for status and serves completed CBZ files directly.

---

## Disclaimer

This project is for **educational purposes only** and is not affiliated with [MangaDex.org](https://mangadex.org) or [mangadex-downloader](https://github.com/mansuf/mangadex-downloader). Users are responsible for complying with MangaDex's Terms of Service and applicable copyright law. Please support manga creators through official channels.

---

[Source code & full documentation](https://github.com/nett00n/mangadex-dl-wui-vibed)
