# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-05-14

### Added
- Phase 1: Complete import pipeline (CSV → raw_events → ticket_events → ticket_snapshots)
  - Backlog & history CSV parsing via Polars
  - Event normalization with 20+ event types
  - Ticket lifecycle reconstruction (ownership_periods, queue_periods, snapshots)
  - Idempotent import processing with cleanup on reprocess

- Phase 2: SLA Engine
  - 4 metric types: response_time, resolution_time, queue_time, owner_time
  - Business hours engine (24/7, weekday, custom JSON schedule)
  - Pause engine (pending-state time exclusion)
  - Rule engine (queue_pattern fnmatch + priority scoring)
  - SLADefinition CRUD API and seeding
  - SLA metric computation with aggregate SQL summary endpoints

- Phase 3: Analytics & Dashboards
  - Dashboard overview API with 14 aggregated KPIs
  - Team analytics with SLA comparison
  - Ticket flow Sankey-compatible transitions
  - Time-series analytics (daily/weekly/monthly)
  - 4 report types with XLSX/CSV async export via Celery
  - Audit logging for SLA changes, reprocess, reports
  - Full frontend: Dashboard, Team Dashboard, Tickets, Ticket Detail, Reports, Import Detail

### Fixed
- Orphaned ownership/queue periods on reprocess (cleanup via subquery)
- Rule engine skipping priority SLA definitions (wildcard fallback)
- FK check performance (added indexes for raw_event_id, import_id)
- Executemany bulk insert (30k rows in ~13s vs row-by-row)
- Session lifecycle in get_sync_db (proper generator/cleanup)

### Performance
- Indexes: ix_sla_metrics_import_id, ix_ticket_events_raw_event_id
- All dashboard queries use aggregate SQL
- Pagination on all large lists
