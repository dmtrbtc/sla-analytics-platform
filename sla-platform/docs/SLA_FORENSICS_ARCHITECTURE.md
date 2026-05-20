# SLA Forensics V3 — Architecture

V3 is an additive layer on top of the V2 SLA engine. It does not replace any
V2 module and shares the same source-of-truth tables.

```
                     ┌──────────────────────────────┐
                     │  raw_events / ticket_events  │
                     │  queue_periods               │
                     │  ownership_periods           │
                     │  ticket_snapshots            │
                     │  sla_metrics  (V2 + V3 rows) │
                     │  sla_definitions / queue_rules
                     └─────────────┬────────────────┘
                                   │
              ┌────────────────────┼────────────────────────┐
              ▼                                             ▼
   ┌───────────────────────┐                  ┌──────────────────────────┐
   │     V2 ENGINES        │                  │    V3 FORENSICS LAYER    │
   │ (services/sla/*)      │                  │  (services/forensics/*)  │
   │                       │                  │                          │
   │ • timeline_engine     │                  │ • attribution_engine     │
   │ • rule_engine         │                  │ • inactivity_engine      │
   │ • pause_engine        │                  │ • queue_forensics        │
   │ • metrics_engine      │                  │ • owner_forensics        │
   │ • risk_engine         │                  │                          │
   │ • business_hours      │                  │ All read-only consumers  │
   │                       │                  │ of the same tables.      │
   │ Writes: first_resp,   │                  │ Writes (additive only):  │
   │  resolution, queue,   │                  │  wall_response_time,     │
   │  owner, paused,       │                  │  wall_resolution_time,   │
   │  reopen, reassign,    │                  │  pause/idle/no_owner/    │
   │  bounce_count, etc.   │                  │  ownership_gap/transfer/ │
   │                       │                  │  stagnation_seconds      │
   └─────────┬─────────────┘                  └───────────┬──────────────┘
             │                                            │
             │  SLAEngine.compute_for_import(...)         │
             │  also invokes                              │
             │  ForensicAttributionEngine                 │
             │  .compute_wall_clock_metrics() ────────────┤
             ▼                                            ▼
   ┌──────────────────────────────────────────────────────────┐
   │  API SURFACE                                             │
   │   /sla/*                       (V2 unchanged)            │
   │   /analytics/*                 (V2 unchanged)            │
   │   /queue-intelligence/*        (V2 unchanged)            │
   │   /analytics/forensics/*       (V3, new — 10 endpoints)  │
   └──────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                      ┌──────────────────────┐
                      │  React frontend      │
                      │  /forensics page —   │
                      │  SLA Forensic        │
                      │  Command Center      │
                      └──────────────────────┘
```

## Module layout

```
backend/app/services/forensics/
  __init__.py
  attribution_engine.py      # Phase 1 & 2 — wall-clock + queue blame + root cause
  inactivity_engine.py       # Phase 3 — silent breach detection
  queue_forensics.py         # Phase 4 — entropy, black-hole, parking-lot, transitions, hot-potato
  owner_forensics.py         # Phase 5 — load, parked, gaps, overload, idle

backend/app/api/v1/
  forensics.py               # Phase 6 — REST endpoints

frontend/src/
  api/forensics.ts           # typed client
  pages/SLAForensicCommandCenter.tsx  # Phase 7 — Russian UI
```

## Computation principles

1. **All heavy aggregation is SQL.** Python in the engine is for orchestration
   and dataclass shaping only. No O(N²) loops; SQL window functions and CTEs
   carry the load.

2. **No new tables.** All forensic metrics use the existing `sla_metrics` table
   with new `metric_name` values. All other forensic views are computed on
   read from `queue_periods`, `ownership_periods`, `ticket_events`.

3. **Best-effort wiring.** `sla_engine.compute_for_import()` wraps the V3
   `compute_wall_clock_metrics()` call in a try/except so V3 failures cannot
   regress V2 metric writes.

4. **Stateless services.** Forensic services have no internal cache; they
   read fresh from DB on every API call. The TanStack Query layer in the
   frontend handles client-side caching (60s refetch).

5. **Idempotency via `import_id`.** V3 metrics are wiped together with V2
   metrics on re-import (existing `DELETE FROM sla_metrics WHERE import_id`).

6. **Backward compatibility guarantee.** No V2 metric_name is renamed or
   removed. Adding a new metric_name is non-breaking because all consumers
   filter on `metric_name = 'first_response_time'` etc.

## Attribution algorithm (Phase 2 detail)

```
For each breached ticket:
  target_seconds        = resolve target (queue rule | SLA def)
  deadline              = ticket.created_at + target_seconds   ← wall-clock
  blame_chain           = compute_queue_blame(ticket_id, target_seconds)
                          [SQL CTE: qp ⨝ no_own ⨝ bounces ⨝ touches]
  breach_queue          = blame_chain.first(qp.entered_at ≤ deadline ≤ qp.exited_at)
                          ?? blame_chain.top_by_score
  breach_owner          = ownership_periods at deadline timestamp
  breach_transition     = closest Move event to deadline
  reason                = decision tree over blame_chain.top:
                            no_owner_ratio > 0.80          → "no_owner"
                            bounce_count ≥ 3               → "bounce_loop"
                            stagnation_score ≥ 0.8 + age   → "stagnation"
                            reassignments ≥ 3              → "reassignment_storm"
                            pause / target > 0.70          → "waiting_state_abuse"
                            moves ≥ 5, distinct_queues ≥ 4 → "routing_chaos"
                            moves ≥ 1                      → "transfer_delay"
                            touches == 0                   → "no_activity"
                            else                           → "stagnation"
```

The `queue_blame_score` is a 0-100 weighted sum:
```
0.30 × wall_share         (how much of total stay was here)
0.20 × idle_ratio         (was unworked here?)
0.20 × no_owner_ratio     (was unowned here?)
0.15 × stagnation_norm    (no events here?)
0.10 × bounce_norm        (re-entered here often?)
0.05 × overdue_ratio      (did wall exceed SLA here alone?)
```

## Silent breach detector (Phase 3 detail)

SQL one-shot:
1. For each open ticket, find `MAX(event_time)` filtered to non-system events.
2. `last_activity_age_seconds = NOW() - that_max`.
3. Compare to ticket's SLA `resolution_target_seconds`.
4. If `age/target ≥ min_inactivity_ratio` (default 0.5) → emit silent breach.
5. Force `risk_level` to `breached / critical / high / medium` based on ratio.

Per-queue silence score uses `PERCENTILE_CONT(0.5)` (median) of the same
inactivity series.

## Frontend dashboard composition

The `/forensics` page makes a single `GET /analytics/forensics/summary` call
that returns the entire bundle (10+ sections) in one trip. Tabs render
sub-tables; charts use ECharts (Sankey for transitions, bar for black-hole
ranking, pie for "where time was lost").
