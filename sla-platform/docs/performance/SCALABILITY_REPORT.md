# Scalability Report — v0.3.0

## Database Layer

### Indexes
| Table | Indexes | Type |
|-------|---------|------|
| raw_events | 7 (3 FK, 4 secondary) | B-tree |
| ticket_events | 5 (2 FK, 3 composite) | B-tree |
| sla_metrics | 4 (1 FK, 3 composite) | B-tree |
| import_sessions | 3 (1 FK, 2 status) | B-tree |
| ticket_snapshots | 3 (1 FK, 2 secondary) | B-tree |
| queue_periods | 4 (2 FK, 2 composite) | B-tree |
| ownership_periods | 4 (2 FK, 2 composite) | B-tree |
| team_members | 1 (FK) | B-tree |
| refresh_tokens | 1 (expires_at) | B-tree |

### Benchmark Results (180K+ raw_events)
All 16 queries sub-3ms average. Full results: `DB_BENCHMARKS.md`

### Partitioning
Monthly-range partitioning infrastructure available via `partition_manager.py` using table inheritance + trigger routing. Not enabled by default — activate via migration 007 when data volume warrants.

### Materialized Views
- `mv_sla_summary_daily`: Daily SLA compliance by metric type
- `mv_queue_performance_daily`: Daily queue throughput/capacity metrics
- `mv_team_metrics_daily`: Daily team workload aggregates
- All refreshable via `CONCURRENTLY` (zero-downtime), scheduled through Celery

## Celery Layer

### Queues
| Queue | Priority | Key Tasks | Timeout (soft/hard) |
|-------|----------|-----------|---------------------|
| imports | 3 | process_import, parse_csv | 7800s/8000s |
| sla | 2 | compute_sla_metrics | 300s/400s |
| reports | 4 | generate_report | 600s/700s |
| maintenance | 8 | purge_expired_tokens, cleanup_stale, refresh_views, dlq_replay | 120s/180s |

### Reliability
- Exponential backoff: `min(30 × 2^retry, 3600)` with ±25% jitter
- Dead Letter Queue per queue type (Redis lists: `dead_letter:*`)
- `MaxRetriesExceededError` routes to DLQ on final exhaustion
- Flower monitoring on port 5555

## Real-Time Layer
- WebSocket: `/ws` with JWT token auth, max 500 concurrent clients
- Heartbeat: 30s interval, stale connections pruned
- Redis pub/sub bridge: Celery → Redis → FastAPI → Browser
- Frontend: exponential reconnect (max 10 attempts, 30s ceiling), ping/pong

## Caching Layer
- Redis-backed with `@cached` decorator
- TTLs: DEFAULT 300s, ANALYTICS 600s, DASHBOARD 120s, CONFIG 600s
- Pattern-based invalidation for dashboard/analytics/matviews
- Decorator handles sync/async functions transparently

## Limits & Recommendations
- Current DB volume: ~180K raw_events — indexes sufficient; re-benchmark at 1M+
- Rate limiter is in-memory (token bucket) — replace with Redis for multi-replica
- Grafana/Loki dashboards not yet deployed (Phase 5I pending)
- Backup/restore scripts written but not CI-tested
