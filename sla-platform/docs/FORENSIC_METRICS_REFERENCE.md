# Forensic Metrics Reference (V3)

All metric definitions, units, formulas, and thresholds used by the V3
forensic engine. Designed to be the single source of truth for both backend
and frontend.

---

## A. Ticket-level metrics (written to `sla_metrics`)

| metric_name | unit | formula | breach signal |
|---|---|---|---|
| `wall_response_time` | seconds | `first_response_at − created_at` | `value > response_target_seconds` |
| `wall_resolution_time` | seconds | `resolution_at − created_at` (or `NOW()` if open) | `value > resolution_target_seconds` |
| `pause_seconds` | seconds | sum of pause intervals from pause_engine | informational |
| `idle_seconds` | seconds | `wall − active − no_owner` | informational |
| `no_owner_seconds` | seconds | Σ ownership_periods where owner ∈ {`root@localhost`, ∅} | informational |
| `ownership_gap_seconds` | seconds | Σ gaps between consecutive ownership_periods | informational |
| `transfer_wait_seconds` | seconds | Σ (next_event_time − Move_event_time) for system-only follow-ups | informational |
| `stagnation_seconds` | seconds | longest gap between two non-system ticket_events | informational |

All metrics carry the same FK/snapshot columns as V2 metrics
(`sla_definition_id`, `import_id`, `queue_name`, `owner`, `computed_at`).

---

## B. Per-queue forensic scores

Returned by `GET /analytics/forensics/queues`.

| field | unit | formula | high-watermark |
|---|---|---|---|
| `total_tickets` | count | `COUNT(DISTINCT ticket_id)` in queue_periods | — |
| `total_wall_hours` | hours | `Σ duration_seconds / 3600` | — |
| `mean_stay_hours` | hours | `AVG(duration_seconds) / 3600` | — |
| `p90_stay_hours` | hours | `PERCENTILE_CONT(0.9)` | — |
| `no_owner_ratio` | 0..1 | `no_owner_seconds / owned_total` | red ≥ 0.95 |
| `touch_rate_per_hour` | 1/h | `non_sys_events / wall_hours` | red ≤ 0.2 |
| `entropy_bits` | bits | Shannon entropy of outbound fanout | absolute, "more = chaotic" |
| `unique_targets` | count | distinct downstream queues | — |
| `routing_chaos_score` | 0..1 | `entropy / log2(unique_targets)` | red ≥ 0.9 |
| `parking_lot_score` | 0..1 | `min(1, no_owner) · (1 − min(1, touch_rate)) · min(1, mean_h/24)` | red ≥ 0.7 |
| `black_hole_score` | 0..1 | `parking_lot · (0.5 + 0.5·breach_rate) · (1 − 0.5·exit_rate)` | red ≥ 0.5 |
| `stagnation_score` | 0..1 | `max(0, 1 − touch_rate/2)` | red ≥ 0.8 |
| `transfer_loop_score` | 0..1 | `re_entries / total_entries` | red ≥ 0.3 |
| `pressure_score` | 0..1 | `breach_count / total_tickets` | red ≥ 0.3 |
| `breach_count` | count | SLA-breached resolution metrics in queue | — |
| `breach_rate` | 0..1 | `breach_count / total_evaluated` | red ≥ 0.3 |

Defaults the V3 engine uses for "system owner": LOWER(owner) IN
(`root@localhost`, `otrs admin (root@localhost)`, `''`).

---

## C. Per-owner forensic scores

Returned by `GET /analytics/forensics/owners`.

| field | unit | formula | red |
|---|---|---|---|
| `load_tickets` | count | distinct tickets owned (system owners excluded) | — |
| `load_hours` | hours | `Σ ownership_period.duration / 3600` | — |
| `parked_tickets` | count | tickets owned but with 0 non-system events while owned | ≥ 1 |
| `non_sys_events` | count | non-system ticket_events by this owner | — |
| `touch_frequency` | 1/h | `non_sys_events / load_hours` | ≤ 0.5 |
| `reassignment_pressure` | ratio | `handoffs_received / load_tickets` | ≥ 1.0 |
| `overload_score` | composite | `load_hours/40 + load_tickets/40` | ≥ 1.5 |
| `idle_flag` | bool | `non_sys_events = 0 AND load_tickets > 0` | true |
| `ownership_gap_seconds` | seconds | sum of gaps between consecutive periods this owner held | — |

---

## D. Silent breach metrics

Returned by `GET /analytics/forensics/silent-breaches`.

| field | unit | formula |
|---|---|---|
| `last_activity_age_seconds` | seconds | `NOW() − MAX(event_time WHERE NOT is_system_action)` |
| `sla_target_seconds` | seconds | ticket's matched SLA resolution target |
| `inactivity_ratio` | 0..∞ | `age / target` |
| `silent_breach_probability` | 0..1 | `min(1, ratio/1.5)` |
| `risk_level` | enum | `breached` ≥ 1.0, `critical` ≥ 0.95, `high` ≥ 0.80, `medium` ≥ 0.50 |

Per-queue `silence_score` = `min(1, median_age_seconds / 28800)` (target = 8h reference).

---

## E. Breach root cause

Returned by `GET /analytics/forensics/breaches` and
`GET /analytics/forensics/tickets/{id}/attribution`.

| field | type | meaning |
|---|---|---|
| `breach_queue` | string | queue holding ticket **at wall-clock deadline crossing** |
| `breach_owner` | string \| null | owner at deadline crossing |
| `breach_transition` | string \| null | Move event nearest to deadline (`A → B`) |
| `breach_reason` | enum | see taxonomy below |
| `breach_at` | datetime | `created_at + target_seconds` |
| `queue_blame_score` | 0..100 | top contributing queue's score |
| `owner_blame_score` | 0..100 | hold duration of breach owner / SLA target × 100 |
| `contributing_queues[]` | list | full blame chain sorted desc |
| `contributing_owners[]` | list | top 5 owners by holding time |

### Reason taxonomy

| reason | trigger |
|---|---|
| `queue_overload` | top queue's `overdue_ratio > 2.0` |
| `no_owner` | top queue's `no_owner_seconds / wall > 0.80` |
| `transfer_delay` | ≥ 1 Move and top queue holds > 30% of SLA target |
| `bounce_loop` | top queue's `bounce_count ≥ 3` |
| `reassignment_storm` | ≥ 3 owner changes |
| `waiting_state_abuse` | `pause_seconds / target > 0.70` |
| `unresolved_pause` | last pause never resumed (open ticket still paused) |
| `routing_chaos` | ≥ 5 moves and ≥ 4 distinct queues |
| `stagnation` | top queue `stagnation_score ≥ 0.8` AND wall > 50% target |
| `no_activity` | zero non-system events ever |

---

## F. Hot-potato ticket fields

Returned by `GET /analytics/forensics/hot-potato`.

| field | unit |
|---|---|
| `ticket_id` | int |
| `ticket_number` | string |
| `current_queue` | string |
| `current_state` | string |
| `moves` | queue-transition count |
| `owner_changes` | owner-change count |
| `distinct_queues` | unique queues visited |

Defaults: `min_moves = 3`. Real-data baseline: 237 tickets ≥ 3 moves, top
offender is ticket 144844 with 24 moves and 18 owner changes.

---

## G. Aggregated KPIs (Forensic Command Center bundle)

Returned by `GET /analytics/forensics/summary` under `kpis`:

| field | seconds aggregate |
|---|---|
| `pause_total` | Σ `pause_seconds` |
| `idle_total` | Σ `idle_seconds` |
| `no_owner_total` | Σ `no_owner_seconds` |
| `gap_total` | Σ `ownership_gap_seconds` |
| `xfer_total` | Σ `transfer_wait_seconds` |
| `stag_total` | Σ `stagnation_seconds` |
| `wall_total` | Σ `wall_resolution_time` |
| `wall_breached` | count(`sla_breached=true` on `wall_resolution_time`) |
| `active_breached` | count(`sla_breached=true` on `resolution_time`) |

`wall_breached − active_breached` is the **hidden-breach delta** —
tickets the V2 engine reports as inside SLA that the V3 wall-clock
detector flags as breached.

---

## H. Thresholds calibrated against real OTRS data

These thresholds were calibrated on `D:\SLA_test` to align V3 with the
forensic audit baseline (see `forensic/FORENSIC_AUDIT_REPORT.md`):

| Score | "red" cutoff | rationale |
|---|---|---|
| `black_hole_score` | ≥ 0.5 | MBR-137-1C-Alfa-Auto and MBR-137-SAP_Basis_support cross this |
| `parking_lot_score` | ≥ 0.7 | identifies the 11 known no-owner queues |
| `no_owner_ratio` | ≥ 0.95 | matches "99% no-owner" queues from audit |
| `routing_chaos_score` | ≥ 0.9 | normalized — favors fully-dispersed small queues |
| `entropy_bits` | ≥ 3.5 | absolute — ServiceDesk leads at 4.14 |
| `pressure_score` | ≥ 0.3 | DC-* queues with 30-42% breach rates |
| `stagnation_score` | ≥ 0.8 | < 0.4 touches/h |
| `inactivity_ratio` (silent) | ≥ 0.5 | min default; engine accepts 0.1..5.0 |
