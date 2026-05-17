# Release Notes — v0.4.0

## Production Scalability & Reliability Release

This release delivers deep production-grade hardening across database optimization, Celery reliability, API consistency, frontend performance, security, observability, and deployment readiness.

### 6A — Database Optimization
- **N+1 query fixes**: `report_service.py` (ticket lookup per SLA metric), `advanced_analytics.py` (per-ticket COUNT in first-touch resolution & reopen rate), `dashboard_service.py` (12 queries per team → 4 batched queries)
- **Batch INSERT**: `backlog_service.py` and `normalizer_service.py` now use executemany instead of row-by-row inserts
- **SELECT \* eliminated**: `reconstructor_service.py` and `normalizer_service.py` now use explicit column lists
- **4 COUNT queries combined**: `/sla/summary` endpoint now uses single query with CASE expressions
- **Unbounded `.all()` fixed**: `import_service.py` sessions list paginated; `lifecycle_service.py` archive uses `yield_per(5000)` for streaming
- **SQL injection fixed**: `materialized_view_service.py` validates view names against whitelist
- New migration `010_add_task_audit` for Celery task audit trail
- Doc: `docs/performance/QUERY_OPTIMIZATION_REPORT.md`

### 6B — Celery Reliability
- `MonitoredTask` base class with correlation IDs, execution timing, and DB audit logging
- `task_audit` table records every task execution (task_id, name, correlation_id, status, duration_ms, error)
- `get_task_audit()` helper for querying execution history

### 6C — API Hardening
- **Critical bug fix**: Global exception handler no longer catches `HTTPException` (was converting all 401/403/404 to 500)
- **Validation errors**: Now return structured `{detail, errors: [{field, message, type}]}` instead of raw Pydantic tracebacks
- **52 routes gained `response_model`**: Teams, SLA, tickets, reports, dashboard, audit routes now have proper response schemas
- **Status codes**: POST creates return 201 (instead of 200)
- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Strict-Transport-Security`, `Content-Security-Policy`, `Referrer-Policy`
- **Consistent pagination**: All list endpoints now paginated
- Doc: `docs/api/API_STANDARDS.md`

### 6D — Frontend Performance
- **Route-based code splitting**: All 11 page components use `React.lazy()` + `Suspense`
- **Vendor chunking**: `vendor-react` (160KB), `vendor-antd` (1MB), `vendor-echarts` (1MB), `vendor-query` (43KB)
- **15 unused files deleted**: Dead chart wrappers, unused hooks, unused API modules
- **Unused dependencies removed**: `ag-grid-react`, `ag-grid-community`
- **Duplicated logic centralized**: `formatDuration` consolidated, status colors shared
- Doc: `docs/performance/FRONTEND_PERFORMANCE_REPORT.md`

### 6E — Security Hardening
- **Exception leakage fixed**: Raw exception messages no longer exposed to clients in imports.py
- **Silent audit failure fixed**: `_sync_audit()` now logs errors instead of swallowing them
- **Path traversal protection**: Report downloads validate resolved path stays within EXPORT_DIR
- **CSV injection protection**: Formula characters (=, +, -, @) prefixed with `'` in CSV exports
- **Filename sanitization**: Uploaded filenames stripped of directory traversal characters
- **JWT secret length check**: Warning if SECRET_KEY < 32 characters
- Doc: `docs/security/SECURITY_AUDIT_v0.3.0.md`

### 6F — Operations & Observability
- **9 custom Prometheus metrics**: Celery task duration/counts, DB query latency, SLA metrics processed, import pipeline duration, error counters, queue backlog
- **Grafana dashboard template**: 8-panel dashboard JSON
- **Prometheus alert rules**: 5 alert rules (HighErrorRate, ImportStalled, QueueBacklog, SlowDBQueries, CeleryTaskFailures)

### 6G — Production Readiness
- `docker-compose.ha.yml`: Multi-replica backend/worker, postgres-replica, redis-sentinel, resource limits, healthchecks, logging config
- `docs/deployment/HIGH_AVAILABILITY.md`: Horizontal scaling, DB replication, Redis Sentinel, rolling updates
- `docs/deployment/ZERO_DOWNTIME_DEPLOYMENT.md`: Blue-green deployment, safe migrations, rollback procedures
- `docs/deployment/DISASTER_RECOVERY.md`: 7-phase DR checklist, PITR, RTO/RPO guidelines

### Infrastructure
- **Migration chain**: 001 → 002 → 003 → 004 → 005 → 006 → 007 → 008 → 009 → 010, all reversible
- **alembic mount added**: docker-compose mounts `./backend/alembic` to `/app/alembic` for live migration compatibility

### Chores
- Version bumped to `0.4.0`
- All 74 tests passing
- TypeScript strict check clean
- Vite build successful

### Notes
- Backward compatible — no breaking API changes
- Antd and ECharts chunks still ~1MB each due to library size — lazy-loaded on first use
- Custom Prometheus metrics auto-register with existing instrumentation
- Flower monitoring via `docker-compose.observability.yml` (port 5555)
