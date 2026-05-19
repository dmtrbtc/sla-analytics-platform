# Release Notes — v0.5.0

## Real-Time Operations & Executive Intelligence

### New Features

#### Real-Time Dashboard Updates
- **WebSocket live integration** in DashboardOps — auto-invalidates React Query caches on incoming events (sla_breach, ticket_created, ticket_updated, queue_overloaded, risk_changed)
- **Live connection indicator** — green/red Badge showing WebSocket status ("В реальном времени" / "Нет соединения")
- Dashboard auto-refreshes in real-time without polling

#### Time Percentiles (P50/P90/P95/P99)
- **Backend**: `DashboardService.get_overview` now computes `percentile_cont` for both response_time and resolution_time using PostgreSQL window functions
- **API**: `response_percentiles` and `resolution_percentiles` objects added to `/api/v1/dashboards/overview` response (backward compatible — `avg_response_time_seconds` / `avg_resolution_time_seconds` preserved)
- **Frontend**: percentile table card on DashboardOps showing P50/P90/P95/P99 + average for response and resolution times

#### Executive Reporting Suite
- **Branded multi-sheet XLSX** with executive theme colors (navy brand header, styled KPI cards)
- **Sheet 1 — Executive Summary**: KPI dashboard with 6 metrics, pie chart (breaches by queue), bar chart (daily breach trend)
- **Sheet 2 — SLA Performance**: detailed metric rows with red/green conditional formatting on breach status
- **Sheet 3 — Queue Analysis**: per-queue breach % with red/yellow/green conditional formatting
- **Sheet 4 — Trends**: raw daily breach count data
- New report type: `executive` in reports API and UI
- i18n: `reports.types.executive` in ru/en

### Performance Improvements (N+1 Query Audit)

Applied 3 critical N+1 fixes:

1. **`metrics_engine.py`** — Cached `SLAQueueRule` at module level with 60s TTL (was re-querying all active rules 2x per ticket, per import). Eliminates 2N redundant queries.

2. **`report_service.py`** — Replaced nested loop N+1 in `sla_breaches_report` (was querying `OwnershipPeriod` individually for each QueuePeriod row). Now batch-loads all OwnershipPeriods with a single `IN` clause.

3. **`advanced_analytics.py`** — Merged 5 separate COUNT queries in `aging_tickets` into a single query with PostgreSQL `FILTER` expressions.

### Live Integration Tests
- New `test_live_integration.py` (integration test suite):
  - Dashboard overview with percentile validation
  - Incident CRUD lifecycle (detect → create → get → acknowledge → comment → resolve)
  - AI prediction, staffing, hints endpoints
  - WebSocket connect/subscribe with JWT auth
  - WebSocket auth rejection test
  - Executive report generation trigger

### QA Results
- `pytest tests/unit/`: 221 passed, 1 warning (pre-existing Pydantic deprecation) — no regressions
- `tsc --noEmit`: clean (0 errors)
- Backend Python syntax: all modified files pass `ast.parse`

### Files Changed (17 files, +714 / -101 lines)
- `backend/app/services/dashboard_service.py` — percentile aggregation
- `backend/app/services/report_service.py` — executive report + N+1 fix
- `backend/app/services/sla/metrics_engine.py` — queue rule caching
- `backend/app/services/analytics/advanced_analytics.py` — N+1 fix
- `backend/app/utils/excel_writer.py` — branded XLSX writer + conditional formatting
- `backend/app/tasks/report_tasks.py` — executive report task
- `frontend/src/pages/DashboardOps.tsx` — WebSocket + percentiles
- `frontend/src/pages/Reports.tsx` — executive report type
- `frontend/src/i18n/locales/ru/common.json` — new keys
- `frontend/src/i18n/locales/en/common.json` — new keys
- `backend/tests/integration/test_live_integration.py` — new E2E tests

### Upgrade Notes
- Docker rebuild required: `docker compose up -d --build`
- Hard refresh browser cache after deployment
- No DB migrations required (0.5.0 uses existing schema)
- Version: 0.5.0
