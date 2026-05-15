# Release Notes — v0.2.0

## Production Hardening Release

This release focuses on production hardening across testing, security, observability, performance, backup procedures, CI/CD, and operations documentation.

### Features

- **Phase 4A — Testing Foundation**: 74 passing tests across 11 test files covering auth, imports, parser, SLA metrics, dashboard, tickets, teams, audit, and reports. Shared test helpers, sync DB setup via psycopg2, real HTTP client testing pattern.

- **Phase 4C — Security Middleware**: Rate limiter (excludes `/health`, `/api/docs`, `/api/openapi.json`), CORS hardening, global exception handler, `RequestValidationError` handler.

- **Phase 4D — Observability**: Structured JSON logging via `structlog`, Prometheus metrics at `/metrics` (`prometheus-fastapi-instrumentator`), `X-Request-Time-Ms` timing header, comprehensive `/health` endpoint (app + DB + Redis checks).

- **Phase 4E — Performance Audit**: Audit report documenting N+1 queries (report_service, normalizer, reconstructor, dashboard_service), missing FK indexes (12 columns), cache bypass in metrics_engine, with recommended quick wins.

- **Phase 4F — Backup Scripts**: PostgreSQL custom-format dump + plain SQL (`backup.sh`), restore with connection termination + confirmation (`restore.sh`), Docker volume backup via alpine tar (`backup-volumes.sh`), 30-day retention rotation.

- **Phase 4G — CI/CD Hardening**: Coverage XML upload to Codecov, Docker layer caching via buildx + actions/cache, Trivy security scan on backend image with SARIF upload to GitHub.

- **Phase 4H — Operations Docs**: Comprehensive operations documentation — incident recovery, scaling, DB maintenance, troubleshooting, upgrade/rollback procedures.

### Fixes

- **business_hours.py**: `_resolve_config(None)` now returns `WEEKDAY_SCHEDULE` instead of `None` (was treating default config as 24/7)
- **pause_engine.py**: `calculate_business_seconds` import moved to module level, duplicate local import removed
- **test fixtures**: Duplicate function bodies removed, cleanup ordering fixed, FK violations corrected, missing imports added

### Chores

- `requirements.txt`: Added `prometheus-fastapi-instrumentator==7.0.0`
- Version bumped to `0.2.0`

### Notes

- Backend now serves Prometheus metrics at `/metrics`
- Rate limiter excludes monitoring and docs endpoints
- Default admin: `admin@sla-platform.dev` / `admin123`
- All changes Docker-compatible; no breaking changes to existing API
