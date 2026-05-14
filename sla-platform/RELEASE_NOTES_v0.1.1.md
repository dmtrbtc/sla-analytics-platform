# Release v0.1.1 — Caddy Production Deployment

## Summary

Migrated production reverse proxy from nginx to Caddy for simplified TLS management,
built-in WebSocket support, and automatic HTTPS via Let's Encrypt.

## Changes

### Infrastructure
- **Caddy reverse proxy**: Replaced nginx in `docker-compose.prod.yml` with Caddy v2
- **Caddyfile**: Created `docker/caddy/Caddyfile` with SPA routing, API proxy, WebSocket support
- **nginx archived**: Original nginx config moved to `docker/nginx-legacy/` for reference

### Features
- ✅ Automatic HTTPS via Let's Encrypt (Caddy ACME)
- ✅ WebSocket support for real-time API communication
- ✅ gzip + zstd compression
- ✅ Security headers (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy)
- ✅ 100MB upload limit for API endpoints
- ✅ SPA routing preserved via reverse proxy to frontend

### Version
- Backend API version bumped to `0.1.1`

## Files Changed

| File | Action |
|------|--------|
| `docker/caddy/Caddyfile` | **NEW** — Caddy configuration |
| `docker-compose.prod.yml` | **MODIFIED** — nginx → Caddy |
| `docker/nginx/` → `docker/nginx-legacy/` | **MOVED** — archived |
| `backend/app/core/version.py` | **MODIFIED** — 0.1.0 → 0.1.1 |
| `README.md` | **MODIFIED** — updated deployment section |

## Deployment

```bash
# Production
docker compose -f docker-compose.prod.yml up -d

# Verify
curl -s http://localhost/health
curl -s http://localhost/api/docs
```

## Rollback

```bash
docker compose -f docker-compose.prod.yml down
git checkout v0.1.0 -- docker-compose.prod.yml
mv docker/nginx-legacy docker/nginx
docker compose -f docker-compose.prod.yml up -d
```
