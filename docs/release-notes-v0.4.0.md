# Release Notes — v0.4.0

## Enterprise Hardening Pass — SLA Governance & Operational Intelligence

### Runtime Validation
- Docker: all 5 containers healthy (backend, frontend, worker, postgres, redis)
- API: all 80+ endpoints return 200/201/4xx correctly
- Frontend: all pages render (Dashboard, DashboardOps, SLAConfig, Imports, Reports, Tickets, Teams)
- Charts render correctly (ECharts heatmap, breach trends, queue distribution)
- CSV export downloads with Russian filename
- Auth flow: login → JWT → refresh → logout works end-to-end
- Auto-refresh: React Query polling active on all analytics pages (30-60s intervals)

### Full Russian Enterprise UX
- `index.html`: `lang="en"` → `lang="ru"`, added Russian meta description
- **Login.tsx**: placeholder `"admin"` → translated i18n key
- **TicketDetail.tsx**: `"Ticket #"` → translated label
- **ImportDetail.tsx**: raw `.toUpperCase()` status → `t()` i18n
- **Header.tsx**: fallback `"User"` → `t("auth.user")`
- **AdminUsers.tsx**: raw role strings → `t("adminUsers.roles.*")`
- **DashboardOps.tsx**: export filename `analytics_` → `analitika_`
- **SLAConfig.tsx**: all placeholders in Russian (email, webhook patterns)
- **NotificationCenter.tsx**: level display → i18n keys, date format → Russian locale (`dayjs/locale/ru`)
- **Imports.tsx**: column "History" → "История"
- **i18n**: added `common.all`, `notifications.level_*`, `slaConfig.patternPlaceholder` to both ru/en
- Ant Design locale: `ru_RU` already configured in main.tsx

### SLA Governance Polish
- **Queue Rules**: clone button (CopyOutlined icon), enable/disable toggle (Switch), search/filter input, active/inactive filter dropdown, priority color tags (5/10/20 thresholds)
- **Calendars**: delete button with Popconfirm confirmation
- **Escalations**: delete button with confirmation, severity color tags (warning/gold, high/orange, critical/red)
- **Simulator**: live risk calculation with risk level indicators, severity colors

### Operational Intelligence V2
- **DashboardOps NOC-style dashboard**:
  - 4 dashboard KPI cards (open tickets, SLA breach %, avg response, avg resolution)
  - 6 analytics KPI cards (tickets at risk, overloaded queues, avg wait, avg reassignments, problematic queue, unowned)
  - Agent workload table (top 10 agents by open tickets)
  - Problematic queue of the day widget
  - Worst agent / best agent spotlight cards
- ECharts heatmap with Russian weekday labels
- 30-60s auto-refresh on all queries

### Performance Hardening
- **Migration 015**: `015_add_enterprise_indexes` — 7 new composite indexes:
  - `ix_ticket_snapshots_current_state` — state-based filtering
  - `ix_ticket_snapshots_current_owner` — owner-based analytics
  - `ix_ticket_events_type_time` — event-based filters
  - `ix_ticket_events_ticket_time` — timeline queries
  - `ix_ownership_periods_team_start` — team analytics
  - `ix_sla_metrics_queue_metric_time` — queue-level SLA
  - `ix_queue_periods_queue_entered` — queue analytics
- **Connection pool**: `pool_size` 5→20, `max_overflow` 10→30, added `pool_pre_ping=True`, `pool_recycle=3600`
- **Health check**: returns HTTP 503 when degraded (DB/Redis down)
- **SECRET_KEY**: 23 chars → 48 chars (meets HS256 minimum)

### Security + Ops
- **SECRET_KEY** strengthened to 48 characters (configurable via env)
- **Health check** returns 503 on dependency failure
- **CSP** relaxed to allow inline scripts, eval, API connections
- **Observability**: Prometheus metrics endpoint active (celery, DB, SLA, import metrics)
- **Rate limiting**: in-memory token bucket (60 RPM per path)
- **Security headers**: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, CSP

### QA Results
- `pytest tests/unit/`: 220 passed, 1 pre-existing Hypothesis slow test failure
- `flake8`: pre-existing warnings only (unused imports, line length, comparison style)
- `tsc --noEmit`: clean (0 errors)
- `vite build`: success (3796 modules, ~13.5s)
- `docker compose config`: valid
- Alembic head: `015_enterprise_idx`

### Upgrade Notes
- Run `alembic upgrade head` to apply migration 015 (7 new indexes)
- Docker rebuild required: `docker compose up -d --build`
- Hard refresh browser cache after deployment
- Version: 0.4.0
