# Performance Audit Report

**Date:** 2026-05-15
**Scope:** Backend (FastAPI/SQLAlchemy) — N+1 queries, missing indexes, SELECT *, service efficiency

## Critical Issues

| Issue | File | Description |
|-------|------|-------------|
| N+1 in SLA report | `app/services/report_service.py:50-51` | `db.get(TicketSnapshot)` per metric row — up to 10k queries |
| N+1 per-ticket SELECT * | `app/services/normalizer_service.py:42-50` | `SELECT * FROM raw_events` per ticket in loop |
| N+1 per-ticket SELECT * | `app/services/reconstructor_service.py:30-38` | `SELECT * FROM ticket_events` per ticket in loop |
| N+1 team analytics | `app/services/dashboard_service.py:235-383` | 11 aggregate queries per team (275 for 25 teams) |

## High Issues

| Issue | File | Description |
|-------|------|-------------|
| Cache bypass in metrics | `app/services/sla/metrics_engine.py:144,152,191,199` | `compute_pause_segments` re-queried per period — `pause_cache` computed but ignored |
| Missing FK indexes | `app/domain/models.py` (12 FK columns) | No `index=True` on `import_id`, `ticket_id`, `user_id`, etc. |
| Full table ticket load | `app/services/sla_engine.py:37-41` | Loads all matching tickets as full ORM objects |

## Medium Issues

| Issue | File | Description |
|-------|------|-------------|
| Row-by-row upsert | `app/services/backlog_service.py:46-96` | Per-row `db.execute()` with ON CONFLICT |
| Raw SELECT * | `app/services/normalizer_service.py:45`, `reconstructor_service.py:33` | Fetches all columns when subset suffices |
| No load_only/defer | Every ORM query in codebase | All columns loaded even when few needed |
| Per-step stats flush | `app/tasks/import_tasks.py:195-201` | Separate DB commit per pipeline step |

## Low Issues

| Issue | File | Description |
|-------|------|-------------|
| Missing secondary indexes | `app/domain/models.py` (17 columns) | No indexes on `event_type`, `metric_name`, `is_closed`, etc. |

## Recommended Quick Wins

1. Add `index=True` to all FK columns in `models.py` (~12 columns)
2. Pass `pause_segments` into `calculate_active_time()` to avoid re-query
3. Replace `db.get` loop in `report_service.py` with single JOIN
4. Replace `SELECT *` with explicit columns in normalizer/reconstructor
