# Release v0.8.0 — Enterprise SLA Accuracy + Large Dataset Stability

**Date:** 2026-05-19

## Summary
Enterprise-grade import stability, performance hardening, SLA explainability, and operations center upgrades.

## New Features

### Import Pipeline Observability
- Real-time progress bar with animated percentage on ImportDetail page
- Rows/sec throughput, ETA, elapsed time, and memory usage displayed live
- `GET /sessions/{id}/progress` endpoint for polling detailed pipeline status
- WebSocket events now include rows/sec, ETA, and elapsed time

### Performance + SQL Hardening
- 13 new composite indexes via migration 017 targeting real analytics query patterns:
  - `ticket_events(owner_name, event_time)` — owner analytics
  - `ticket_events(queue_name, event_time)` — queue analytics
  - `raw_events(duplicate_key)` — deduplication
  - `sla_metrics(computed_at, sla_breached)` — dashboard trends
  - `ticket_snapshots(is_closed, created_at)` — aging analysis
  - `ownership_periods(owner, start_time)` — workload queries
  - `queue_periods(team_prefix, entered_at)` — team analytics
  - +6 more composite indexes (see migration 017)
- Redis caching decorator (`@cached`) with `skip_args` support for DB session params
- Sync caching decorator (`@cached_sync`) for non-async services
- Applied caching to 5 expensive dashboard/analytics methods (120-300s TTL)
- Cache auto-invalidation on import completion and SLA computation
- Slow query logging middleware with configurable threshold (`SLOW_QUERY_SECONDS`)
- `query_timer` context manager for manual instrumentation

### Migration 016 Fix
- `CREATE INDEX IF NOT EXISTS` syntax to prevent duplicate index failures

### Import Pipeline Memory Optimization
- Batch normalization flush every 2000 rows with per-ticket commits
- Streaming CSV via `csv.DictReader` chunks instead of full DataFrame materialization
- Streaming file upload via `upload.iter_chunks()` — no in-memory buffering
- Eliminated triple I/O (write + SHA256 + row counting) → single streaming pass
- Periodic commits every 50 tickets in reconstructor service

## Infrastructure
- All 5 containers healthy (postgres, redis, backend, worker, frontend)
- Alembic at head: `017_performance_indexes`
- pytest: 267 passed, tsc: 0 errors, vite build: 3818 modules

## Files Changed
- **17 files modified**, **1 new migration**, +456/-307 lines
