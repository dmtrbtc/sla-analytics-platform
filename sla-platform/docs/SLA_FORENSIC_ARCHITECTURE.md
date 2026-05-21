# SLA Forensic Architecture — v1.5

How the platform actually computes "WHO is to blame, WHERE, and WHY" for every breach. Each section maps to live SQL/code paths.

---

## 1. Source-of-truth tables

```
raw_events            — every OTRS event row, untyped
ticket_events         — typed events with src/dest queue, owner change, system flag
ticket_snapshots      — current state per ticket
queue_periods         — entered_at / exited_at / duration per (ticket, queue)
ownership_periods     — owner / queue_name / start_time / end_time per ownership stint
sla_metrics           — V2 + V3 outputs (metric_name discriminator)
sla_definitions       — SLA targets (legacy)
sla_queue_rules       — pattern-based SLA targets (current)
sla_escalation_rules  — pluggable escalation chain
favorite_queues       — per-user starred queues (v1.4)
queue_groups          — named queue collections (v1.4)
dashboard_presets     — operational workspaces (v1.4)
teams                 — team meta + queue_prefix + queues JSONB + escalation_chain JSONB
```

Every forensic answer is a read against these tables. No new tables in v1.5.

---

## 2. Dual SLA model

```
ACTIVE SLA      — first_response_time, resolution_time
                  measured creation→event minus pauses;  emitted by MetricsEngine
WALL-CLOCK SLA  — wall_response_time, wall_resolution_time
                  raw seconds, no pause subtraction;     emitted by
                  ForensicAttributionEngine.compute_wall_clock_metrics

Loss buckets (creation→resolution scope):
  pause_seconds            — Σ pause intervals
  idle_seconds             — wall − active − no_owner
  no_owner_seconds         — Σ ownership where owner ∈ {root, ∅}
  ownership_gap_seconds    — Σ inter-owner-period gaps
  transfer_wait_seconds    — Σ system-only waits after a Move
  stagnation_seconds       — longest gap between non-system events
```

Wall vs active divergence shows up in `forensic_summary.kpis`:
`hidden_breach_delta = wall_breached − active_breached`.

---

## 3. Breach attribution algorithm (v1.3 → v1.5)

For each ticket, compute `deadline = created_at + target_seconds`. Then:

1. **Queue at deadline** — the queue_period whose `entered_at ≤ deadline ≤ exited_at` is the official `breach_queue`. NOT `current_queue`. This is the core fix from v1.3.
2. **Owner at deadline** — the ownership_period covering that timestamp.
3. **Transition near deadline** — Move event closest to `deadline` in `|Δt|`.
4. **Queue blame chain** — every queue the ticket ever sat in, scored 0–100 with the weighted formula in `attribution_engine.compute_queue_blame`.
5. **Reason** — decision tree over the top-blame queue's signals + reassignment count + pause ratio + touches. Output one of the 10-value taxonomy in `attribution_engine.BREACH_REASONS`.

The full algorithm including weights is in `services/forensics/attribution_engine.py`. Verified live for ticket 144844.

---

## 4. Per-ticket queue contribution (v1.5 new)

`ContributionEngine.for_ticket(db, ticket_id)` returns:

```
QueueContributionRow per (ticket, queue_period_segment):
  wall_seconds, active_seconds, idle_seconds, no_owner_seconds
  queue_loss_percent = wall_in_queue / total_wall × 100
  owners[]            = per-owner sub-breakdown in this segment

OwnerContributionRow per (ticket, owner):
  owned_seconds, owner_loss_percent, is_system

Scores:
  routing_instability_score = bounces × 1.0 + reassigns × 0.5
  stagnation_score          = longest_event_gap / total_wall  (0..1)
  operational_waste_score   = (no_owner + idle + pause) / wall × 100 (clamped 100)
  transfer_efficiency       = moves_with_human_follow_within_1h / total_moves
  touch_efficiency          = non_sys_events / wall_hours
```

Exposed at `GET /analytics/forensics/tickets/{ticket_id}/contribution`.

For ticket 144844 live:
- 25 queue segments
- `root@localhost` holds 93.15% of owned time → confirms operational accountability gap
- `routing_instability_score = 90.0` from 24 bounces + 18 reassigns × 0.5

---

## 5. Per-queue forensic fingerprints

`QueueForensicsService.compute_all(queues=None)` returns one row per queue with:

```
total_tickets, total_wall_hours, mean_stay_hours, p90_stay_hours
no_owner_ratio          = no_owner_seconds / owned_total
touch_rate_per_hour     = non_sys_events / wall_hours
entropy_bits            = Shannon entropy of outbound fanout
unique_targets          = distinct destination queues
routing_chaos_score     = entropy / log2(unique_targets)
parking_lot_score       = min(1,no_owner) · (1-touch_rate) · min(1,mean_h/24)
black_hole_score        = parking_lot · (0.5 + 0.5·breach_rate) · (1 - 0.5·exit_rate)
stagnation_score        = max(0, 1 - touch_rate/2)
transfer_loop_score     = reentries / total_entries
pressure_score          = breach_count / tickets
breach_count, breach_rate
```

v1.5 added `queues: list[str] | None` parameter — when supplied, the SQL CTE result is post-filtered to that set. Same pattern applied to `OwnerForensicsService` (with SQL-side `AND op.queue_name = ANY(:queue_list)` to keep the aggregation honest), `InactivityEngine.detect_silent_breaches`, `transitions()`, `hot_potato_tickets()`.

---

## 6. SLA governance (v1.5 new)

| Endpoint | Purpose |
|---|---|
| `GET /sla/v15/queue-rules/{id}/matched-tickets` | Translate `queue_pattern` (glob) to SQL LIKE and return real tickets the rule would apply to. Aggregates per-queue counts of total + open. |
| `GET /sla/v15/queue-rules/conflicts` | Detect (a) overlap_conflicts: any concrete real queue matched by ≥2 active rules with different targets; (b) impossible_rules: invalid target relationships; (c) dead_rules: patterns matching zero real queues. |
| `POST /sla/v15/simulate` | Apply a proposed rule to a real ticket; return whether wall_response and wall_resolution would have breached, plus the ticket's existing metrics for comparison. No DB mutation. |

The conflict detector found a **real dead rule** in the production dataset on first run — the legacy "Test Rule" with `Support*` pattern matches no real OTRS queue.

---

## 7. Team operations (v1.5 new)

`GET /teams/{id}/dashboard?days=N` returns:

```
team:          { id, name, queue_prefix, queues_extra, color, response/resolution_target }
scope_queues:  team.queues UNION (queues LIKE queue_prefix%)
ticket_counts: { total, open }
metrics:       mtta_seconds, mttr_seconds, response_count,
               active_breaches, wall_breaches,
               no_owner_seconds, no_owner_pct,
               reassignments, queue_bounces
top_owners:    aggregated from ownership_periods inside scope_queues
```

The team's scope is the union of its declared `queues` JSONB list and any queues matching `queue_prefix`. For "DC NOC v15" team with prefix `MBR-137-DC-`, scope auto-expands to 7 real DC queues in the live dataset.

---

## 8. Favorite-queue propagation

Every analytics endpoint that returns per-queue or per-owner aggregations now accepts `queue: list[str]` repeated query parameter:

```
/dashboards/overview?queue=A&queue=B
/analytics/forensics/queues?queue=A
/analytics/forensics/blackholes?queue=A
/analytics/forensics/stagnation?queue=A
/analytics/forensics/owners?queue=A
/analytics/forensics/transitions?queue=A
/analytics/forensics/hot-potato?queue=A
/analytics/forensics/silent-breaches?queue=A
/analytics/forensics/summary?queue=A   (← v1.5: scopes every component at once)
```

The frontend `FavoritesContext` keeps an `activeFilter: string[]` in localStorage. Pages opt-in by reading `useFavorites().activeFilter` and passing it as `queue` param. `axios.client` has a `paramsSerializer` that emits `?queue=A&queue=B` (FastAPI's required format).

---

## 9. Caveats / known divergences

| Behavior | Why |
|---|---|
| `operational_waste_score` clamped to 100 | pause_seconds is measured on creation→resolution while idle/no_owner come from queue_periods — they can overlap when a paused ticket sits in an unowned queue. Raw seconds remain in the payload; the clamp keeps the *score* readable. |
| Active-time SLA may show breach=false while wall-clock shows breach=true | By design. Wall reflects calendar reality (what OTRS' own export reports); active reflects work-time minus pauses. The difference is the *hidden breach delta* the UI surfaces. |
| `routing_chaos_score` of small queues can saturate near 1.0 | Normalized by `log2(unique_targets)` — a queue with 3 fully-dispersed outbound targets hits ~1.0 even though it's not actually chaotic. `entropy_bits` (raw) is the more useful metric for cross-queue comparison. The summary endpoint uses `entropy_bits` for its top-chaos sorting. |
