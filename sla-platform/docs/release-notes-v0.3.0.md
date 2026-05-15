# Release Notes — v0.3.0

## Enterprise Scalability & Analytics Release

This release evolves the SLA platform from hardened internal tool into a scalable analytics product — database optimization, Celery scalability, real-time updates, advanced analytics, materialized views/caching, data lifecycle management, and enterprise configuration management.

### Features

- **Phase 5A — Database Performance & Partitioning**: 32 custom indexes across 10 tables (5 FK, 4 composite, 8 secondary, 15 existing); monthly-range partitioning infrastructure via table inheritance + trigger routing; all 16 benchmark queries sub-3ms at 180K+ rows.

- **Phase 5B — Celery Scalability**: 4 dedicated queues (`imports`, `sla`, `reports`, `maintenance`) with task priority annotations; exponential backoff with ±25% jitter; Dead Letter Queue via Redis lists; `soft_time_limit`/`time_limit` on every task; Flower 2.0.1 monitoring.

- **Phase 5C — Real-Time Updates**: Redis pub/sub bridge (`ws:events` channel) for WS-Celery decoupling; `ConnectionManager` with heartbeat (30s), max 500 clients, token-based auth; import progress events at each pipeline step; frontend `useWebSocket` hook with exponential reconnect; `NotificationCenter` with antd Badge + Drawer; Zustand `notificationStore`.

- **Phase 5D — Advanced Analytics**: 10 analytical methods — SLA trend forecast (7-day MA + linear projection), queue overload prediction, reassignment analysis, agent workload, top problematic queues, MTTR/MTTA (avg+median), aging tickets, first-touch resolution rate, reopen rate, breach root-cause — all via raw SQL aggregates.

- **Phase 5E — Materialized Views & Caching**: Redis cache layer with `@cached` decorator, pattern-based invalidation, TTL management (DEFAULT=300s, ANALYTICS=600s, DASHBOARD=120s); 3 materialized views (`mv_sla_summary_daily`, `mv_queue_performance_daily`, `mv_team_metrics_daily`) with `CONCURRENTLY` refresh; Celery-scheduled view refresh.

- **Phase 5F — Data Lifecycle Management**: `archive_import()` exports raw_events + ticket_events + sla_metrics to JSON; `purge_import()` with optional archive-first; `restore_import()` from archived JSON; `apply_retention_policy()` for auto-archival of imports older than N days.

- **Phase 5G — Enterprise Configuration**: `AppConfig` model with `config_key` (unique), `config_value` (JSONB), `description`, `updated_at/by`; 5 seed configurations (business hours, holidays, retention_days, notification_thresholds, queue_mappings); `get_config()` cached for 600s with immediate invalidation on update.

### Infrastructure

- **Migration chain**: 001 → 002 → 003 → 004 → 005 → 006 → 007 → 008 → 009, all fully reversible
- **Container**: Flower on port 5555 via `docker-compose.observability.yml`
- **Worker**: Updated queue list to `imports,sla,reports,maintenance,default`

### Chores

- `requirements.txt`: Added `flower==2.0.1`
- Version bumped to `0.3.0`

### Notes

- All new features backward-compatible — no breaking API changes
- Migration 009 (`app_config` table) uses `conn.exec_driver_sql()` for JSON-null-safe seeding
- Redis pub/sub requires Redis 7+
- Frontend WebSocket endpoint at `/ws?token=...`
- Analytics endpoints under `/dashboards/analytics/`
- See `docs/performance/DB_BENCHMARKS.md` for full benchmark results
