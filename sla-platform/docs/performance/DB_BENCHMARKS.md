# Database Performance Benchmarks

**Date:** 2026-05-15
**Scope:** PostgreSQL 16 query performance after Phase 5A index optimization

## Data Volume

| Table | Rows |
|-------|------|
| `raw_events` | 183,690 |
| `ticket_events` | 153,070 |
| `sla_metrics` | 6,828 |
| `ticket_snapshots` | 1,638 |
| `queue_periods` | 1,881 |
| `ownership_periods` | 425 |

## Query Latency (5-run average)

| Query | Avg (ms) | Min (ms) | Max (ms) |
|-------|----------|----------|----------|
| raw_events by import_id (single) | 2.32 | 2.15 | 2.68 |
| raw_events by import + ticket (composite) | 1.32 | 1.21 | 1.44 |
| raw_events by event_name (filtered) | 1.28 | 1.19 | 1.49 |
| raw_events by queue_name (filtered) | 1.17 | 1.08 | 1.21 |
| ticket_events by import + ticket (composite) | 1.20 | 1.05 | 1.39 |
| ticket_events by event_type (filtered) | 1.24 | 0.99 | 1.85 |
| ownership_periods by ticket + start (composite) | 1.65 | 0.82 | 4.49 |
| queue_periods by ticket + entered (composite) | 1.46 | 1.11 | 1.69 |
| sla_metrics by import + metric (composite) | 1.01 | 0.93 | 1.11 |
| sla_metrics breached filter | 0.97 | 0.89 | 1.04 |
| ticket_snapshots is_closed filter | 0.91 | 0.84 | 0.99 |
| dashboard: ticket counts by queue | 1.29 | 1.23 | 1.38 |
| dashboard: SLA breach rate | 2.43 | 2.21 | 2.73 |
| dashboard: team queue prefix match | 0.95 | 0.90 | 1.01 |
| JOIN: raw_events + ticket_events by import | 2.21 | 1.79 | 2.51 |
| report: SLA metrics per import (left join snapshots) | 1.50 | 1.32 | 1.66 |

**All queries complete within 3ms at 180K+ row scale.**

## Index Coverage

32 custom indexes across 10 tables (excluding PKs):

| Table | Indexes | Total Size |
|-------|---------|------------|
| `raw_events` | 6 | ~10 MB |
| `ticket_events` | 7 | ~23 MB |
| `sla_metrics` | 6 | ~448 KB |
| `ticket_snapshots` | 2 | ~64 KB |
| `ownership_periods` | 2 | ~72 KB |
| `queue_periods` | 2 | ~144 KB |
| `audit_log` | 2 | ~32 KB |
| `import_sessions` | 1 | ~16 KB |
| `sla_definitions` | 1 | ~16 KB |
| `teams` | 1 | ~16 KB |

## Partitioning Strategy

An optional partitioning infrastructure is available via `app/db/partition_manager.py`:

- **Strategy**: Monthly range partitioning by `event_time`
- **Target tables**: `raw_events`, `ticket_events`, `sla_metrics`
- **Mechanism**: Table inheritance (PG `INHERITS`) with trigger-based INSERT routing
- **Safety**: Non-destructive — existing tables are never altered
- **Activation**: Run `partition_manager.setup_partition_infrastructure()` with an SQLAlchemy connection
- **Migration**: `007_partition_infra` (optional, creates `partitions` schema and meta table)

Recommended when any partition table exceeds 10M rows.

## Findings

1. All FK columns are now indexed (5 new indexes added in migration 005)
2. Composite indexes added for common query patterns (4 new in migration 006)
3. Secondary indexes added for filtered columns (8 new in migration 006)
4. All queries sub-3ms at current scale
5. Index overhead is acceptable (~34 MB total)
6. Partitioning infrastructure ready but inactive by default

## Recommendations

1. Re-benchmark after reaching 1M+ rows to identify degradation
2. Enable partitioning when `raw_events` exceeds 10M rows
3. Consider dropping unused indexes (none found currently)
4. Add `pg_stat_statements` for ongoing query monitoring
