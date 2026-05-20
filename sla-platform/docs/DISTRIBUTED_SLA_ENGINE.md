# Distributed SLA Engine — Technical Deep Dive

## Architecture

The SLA engine operates in three modes:

1. **Per-ticket** (legacy): One ticket at a time, 10-20 queries each (N+1)
2. **Batch** (v0.8): Preloads all events for all tickets in 1 query, in-memory compute
3. **Distributed** (v1.0): Partitions tickets across Celery workers, parallel execution

## Distributed Mode

### Partitioning

```
Tickets (10000) → CHUNK_SIZE=500 → 20 partitions
                            ↓
                Celery Group (parallel)
              ┌──────┬──────┬──────┬──────┐
              │ P1   │ P2   │ ...  │ P20  │
              └──┬───┴──┬───┴──┬───┴──┬───┘
                 │      │      │      │
         ┌───────▼──────▼──────▼──────▼───────┐
         │   Batch Metrics Engine (each)       │
         │   1 query → all events → in memory  │
         │   CSV insert → 1 batch commit       │
         └─────────────────────────────────────┘
```

### Orchestrator

`compute_orchestrator.py` manages:
1. **Initialization** — Store total tickets, priority, SLA def count in Redis
2. **Deletion** — Clear existing SLA metrics for the import
3. **Partitioning** — Split tickets into even chunks (max 50 partitions)
4. **Launch** — Create Celery Group with priority 3 (critical) or 5 (normal)
5. **Progress** — Each partition updates shared Redis counter on completion

### Metrics Per Partition

- Partition worker preloads all events for its tickets in 1 query
- Batch computation uses `compute_metrics_batch` in memory
- Bulk CSV-style insert with 2000-row batching
- Progress updated atomically in Redis

### Queue Configuration

```
task_routes:
  app.services.sla.compute_orchestrator.* → sla_compute queue

Worker: celery -A app.core.celery_app worker -Q sla_compute -c 4
```

### Priority Processing

- Critical imports (high-priority SLA defs) get Celery priority 3
- Normal imports get priority 5
- SLA compute queue is processed before analytics/maintenance

## Performance Characteristics

| Mode | Tickets | Queries | Time (est) |
|------|---------|---------|------------|
| Per-ticket | 1000 | 10,000-20,000 | ~300s |
| Batch | 1000 | 5 | ~15s |
| Distributed (4 workers) | 10000 | 20 (5 each) | ~10s |

## Monitoring

`GET /api/v1/imports/{id}/orchestration` returns:
- Total tickets
- Partitions (total, completed, failed)
- Progress (completed/failed counts)
- Timestamps (started, updated)
