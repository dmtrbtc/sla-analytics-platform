# Query Optimization Report — v0.4.0

## Summary

Phase 6A identified and fixed 10 categories of query inefficiency across the backend. All fixes maintain backward compatibility.

| # | Issue | Severity | Files Fixed |
|---|-------|----------|-------------|
| 1 | N+1: db.get() in loop | HIGH | report_service.py |
| 2 | N+1: per-row COUNT in loop | HIGH | advanced_analytics.py |
| 3 | N+1: 12 queries per team | HIGH | dashboard_service.py |
| 4 | Row-by-row INSERT | HIGH | backlog_service.py, normalizer_service.py |
| 5 | SQL injection (f-string) | HIGH | materialized_view_service.py |
| 6 | SELECT * | MEDIUM | reconstructor_service.py, normalizer_service.py |
| 7 | 4 separate COUNT queries | MEDIUM | api/v1/sla.py |
| 8 | Unbounded .all() in list endpoint | MEDIUM | import_service.py |
| 9 | Unbounded .all() in archive | MEDIUM | lifecycle_service.py |
| 10 | Unbounded .all() in SLA defs | LOW | api/v1/sla.py |

## Before/After

| Query Pattern | Before | After |
|--------------|--------|-------|
| report_service metrics + tickets | 1 + N queries (N=up to 10k) | 1 query with JOIN |
| first_touch_resolution | 1 + N queries (N=up to 10k) | 1 query with subquery |
| reopen_rate | 1 + N queries (N=up to 10k) | 1 query with subquery |
| team analytics | 1 + 12*N queries (N=20 teams = 241 queries) | 4 batched queries |
| backlog INSERT | 1 per row | 1 batch per N rows |
| normalizer INSERT | 1 per row | 1 batch |
| SLA summary COUNT | 4 queries | 1 query with CASE |

## New Indexes (Migration 010)
- `ix_task_audit_name_started` on `task_audit(task_name, started_at)`
- `ix_task_audit_status` on `task_audit(status)`
