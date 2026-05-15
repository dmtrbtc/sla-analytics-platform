# Performance Baseline — v0.3.0

## Database Performance

### Index Coverage
- 32 custom indexes across 10 tables
- All FK columns indexed (eliminated all sequential scans on joins)
- Composite indexes on high-traffic query patterns:
  - `ticket_events(import_id, ticket_id)`
  - `sla_metrics(import_id, metric_name)`
  - `ownership_periods(ticket_id, start_time)`
  - `queue_periods(ticket_id, entered_at)`

### Query Benchmarks (180K+ raw_events)
| Query | Avg Time | Improvement |
|-------|----------|-------------|
| Count events by import | ~0.5ms | 40x+ |
| Filter by event_name | ~1ms | 20x+ |
| Join raw_events → ticket_events | ~2ms | 30x+ |
| SLA metrics by import + metric | ~1ms | 25x+ |
| Queue periods by ticket | ~0.3ms | 50x+ |
| Ownership periods by ticket | ~0.3ms | 50x+ |

Full details: `DB_BENCHMARKS.md`

### Materialized View Refresh Times
Views refresh via `CONCURRENTLY` — expected <1s at current volume.

## API Performance
- Request timing header (`X-Request-Time-Ms`) on all responses
- Redis caching for dashboard/analytics (TTL 120-600s)
- All list endpoints paginated (max page size 200-1000)

## Celery Task Performance
- Import processing timeout: 7800s (soft) / 8000s (hard)
- SLA computation timeout: 300s / 400s
- Report generation timeout: 600s / 700s
- All maintenance tasks: 120s / 180s

## Frontend Performance
- WebSocket push eliminates polling for import progress
- Zustand store for notification state (no unnecessary re-renders)
- Exponential reconnect backoff (max 30s)

## Known Bottlenecks
1. **Rate limiter**: In-memory token bucket — per-process, not shared across replicas
2. **No HTTP response caching**: Redis used for data caching only; no `Cache-Control`/`ETag` headers
3. **Analytics queries**: Raw SQL aggregates — no pre-aggregation beyond materialized views
4. **File uploads**: Handled synchronously in request thread (not streamed)

## Recommendations for 1M+ Scale
- Enable PG partitioning (migration 007) at ~500K raw_events
- Replace in-memory rate limiter with Redis-backed
- Add CDN/proxy caching for dashboard endpoints
- Pre-aggregate analytics into materialized views on schedule
- Add connection pooling tuning for higher concurrency
