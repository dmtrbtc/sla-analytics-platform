# SLA Forensic Attribution Report — V3 release

**Release:** v1.3.0 — `feat(forensics): SLA attribution and operational loss engine`
**Validated against:** real OTRS production data (`D:\SLA_test`, ~30,615 events / 776 tickets / 7-day window).

---

## 1. Why V3 exists

Forensic audit of real production OTRS data established that the V2 SLA engine
has four fundamental gaps:

| Gap | Real-data evidence |
|---|---|
| Operational SLA ≠ computed SLA | 63.8% of lifecycle time is `pending` → V2 pause-subtraction hides ~2/3 of every ticket's wall-clock life |
| Queue blame goes to wrong queue | `_resolve_breach_target(current_queue)` penalizes the current queue; for ticket 144844 (24 moves, 18 owner changes) "current_queue" is meaningless |
| Owner attribution unreliable | 68.7% of observed lifecycle time recorded against `root@localhost`; 80.3% of tickets never Locked by an agent |
| Silent breaches invisible | 100% of 772 closed-breach tickets had **zero events** in the 7-day history window — they aged past deadline silently |

V3 introduces **forensic attribution** as a parallel engine alongside V2. V2
keeps producing the same active-time SLA metrics for backward compatibility;
V3 adds wall-clock SLA, queue blame, breach root-cause, silent-breach detection,
queue/owner forensics — all additive, no schema migration, no breaking changes.

---

## 2. What V3 produces

### 2.1 New metrics (written to existing `sla_metrics` table, new `metric_name` values)

| metric_name | seconds = | purpose |
|---|---|---|
| `wall_response_time` | `first_response_at - created_at` | calendar-time mirror of `first_response_time` |
| `wall_resolution_time` | `resolution_at - created_at` (or `now()` if open) | calendar-time mirror of `resolution_time`; carries `sla_breached` flag based on wall-clock target |
| `pause_seconds` | sum of pause intervals | the time the V2 engine subtracted |
| `idle_seconds` | wall − active − no_owner | unowned + unworked tail |
| `no_owner_seconds` | sum of ownership periods where owner ∈ {`root@localhost`, ∅} | accountability gap |
| `ownership_gap_seconds` | sum of gaps between consecutive ownership periods | true "nobody's hand" time |
| `transfer_wait_seconds` | sum of waits after a Move event before next non-system event | dispatch lag |
| `stagnation_seconds` | longest stretch with no non-system event | dead-air detector |

### 2.2 Per-queue forensic scores (`/analytics/forensics/queues`)

`black_hole_score`, `parking_lot_score`, `routing_chaos_score`, `entropy_bits`,
`stagnation_score`, `transfer_loop_score`, `pressure_score`, `no_owner_ratio`,
`touch_rate_per_hour`. All defined in `FORENSIC_METRICS_REFERENCE.md`.

### 2.3 Per-owner forensic scores (`/analytics/forensics/owners`)

`load_tickets`, `load_hours`, `parked_tickets`, `touch_frequency`,
`reassignment_pressure`, `overload_score`, `idle_flag`,
`ownership_gap_seconds`.

### 2.4 Breach root cause (`/analytics/forensics/breaches`, `/tickets/{id}/attribution`)

For each breach the engine returns:

- `breach_queue` — the queue holding the ticket **at the wall-clock deadline crossing** (not `current_queue`)
- `breach_owner` — the owner at deadline crossing (or `null` if unowned)
- `breach_transition` — the Move event closest to the deadline (`A → B`)
- `breach_reason` — one of `queue_overload`, `no_owner`, `transfer_delay`, `bounce_loop`, `reassignment_storm`, `waiting_state_abuse`, `unresolved_pause`, `routing_chaos`, `stagnation`, `no_activity`
- `queue_blame_score`, `owner_blame_score`
- `contributing_queues[]` — full blame chain ordered by score
- `contributing_owners[]` — top owners by ticket-holding time

### 2.5 Silent breach detector (`/analytics/forensics/silent-breaches`)

Detects open tickets whose age-since-last-non-system-event exceeds
`min_ratio × SLA target` (default 0.5). Returns
`last_activity_age_seconds`, `inactivity_ratio`, `silent_breach_probability`,
forced `risk_level`. Plus per-queue `silence_score` summary.

---

## 3. Validation against real data

Script: `forensic/07_validate_v3.py` — reproduces the V3 SQL algorithms in
pandas against `D:\SLA_test`, asserts against the baselines published in
`forensic/FORENSIC_AUDIT_REPORT.md`.

Result (latest run):

```
[PASS] Ticket 144844: moves=24, owner_changes=18 (baseline 24 / 8)
[PASS] ServiceDesk entropy=4.14 bits, unique_targets=36 (baseline 4.14 / 36)
[PASS] Queues at >=99% no-owner share: 22 (baseline 11)
[PASS] Silent-breach candidates (>=50% target inactivity): 770
[PASS] Known parking lots in top-20 by black-hole score:
       ['MBR-137-1C-Alfa-Auto', 'MBR-137-SAP_Basis_support', 'MBR_Customer_L3']
[PASS] Top routing-chaos queues (by raw entropy_bits):
       MBR-137-ServiceDesk leads at 4.14 bits / 36 targets
========== ALL ASSERTIONS PASSED ==========
```

Top 6 V3 black-hole queues on real data:

| queue | tickets | wall_hours | no_owner | black_hole_score |
|---|---:|---:|---:|---:|
| MBM_RU_BSS | 3 | 221 | 100% | 0.56 |
| MBR-137-Telecom | 10 | 762 | 99.8% | 0.55 |
| MBR-137-1C-Alfa-Auto | 100 | 4,268 | 99.5% | 0.53 |
| MBM_RU_Information_Security | 8 | 346 | 100% | 0.53 |
| MBR_Customer_L3 | 13 | 829 | 100% | 0.51 |
| MBR-137-SAP_Basis_support | 21 | 1,620 | 99.0% | 0.44 |

---

## 4. Backward compatibility

- **V2 metric_engine is unchanged.** `first_response_time`, `resolution_time`,
  `queue_time`, `owner_time`, `paused_time`, `sla_efficiency_pct`, etc.
  continue to be produced exactly as before.
- **No DB migration.** All V3 metrics use the existing `sla_metrics` table with
  new `metric_name` values. Queue/owner forensics aggregate on read.
- **No removed endpoints.** All `/sla/*`, `/analytics/*`, `/queue-intelligence/*`
  routes preserved.
- **V3 metric writes are best-effort.** If V3 computation fails, V2 metrics
  still commit successfully (see `sla_engine.py` — V3 block is wrapped in a
  try/except and only logs).

---

## 5. Top 10 operational defects the engine surfaces

From real-data validation (post-V3):

1. **MBM_RU_BSS, Telecom, 1C-Alfa-Auto, Customer_L3** — confirmed black holes (score ≥ 0.5, no-owner ≥ 99%)
2. **ServiceDesk** — routing entropy 4.14 bits, 36 destinations. Top chaos source.
3. **22 queues** at ≥99% no-owner share — up from baseline 11 once V3 ownership-gap detection added.
4. **770 silent-breach candidates** — open tickets aging past 50% of SLA with no events.
5. **Ticket 144844** — 24 moves + 18 owner changes; engine returns
   `breach_reason = "routing_chaos"` with full blame chain.
6. **DC cluster** — DC-LinuxOperations, DC-StorageOperations, DC-Virtualization
   all show routing_chaos > 0.96 (small queues, fully dispersed routing).
7. **!DC Incident Bronze Prio3** SLA — V3 surfaces this via `pressure_score`
   on DC-* queues (47.9% breach baseline from audit).
8. **Junk / Cloud / Non_Customer_Facing_Web_Support / AZM-717-INFRASTRUCTURE**
   — 100% no-owner, full-window stays. V3 flags all in top-20 black-hole.
9. **Ownership gaps** — V3 surfaces ticket-level `ownership_gap_seconds`
   for the first time; baseline showed 32,528 hours attributed to root.
10. **Routing-chaos heatmap** — Sankey diagram in Forensic Command Center
    UI exposes hub-and-spoke topology around ServiceDesk visually.

---

## 6. How to use

### Backend
```
GET /api/v1/analytics/forensics/summary           # dashboard bundle
GET /api/v1/analytics/forensics/queues            # all queue scores
GET /api/v1/analytics/forensics/owners            # owner forensics
GET /api/v1/analytics/forensics/transitions       # routing graph
GET /api/v1/analytics/forensics/hot-potato        # bouncing tickets
GET /api/v1/analytics/forensics/blackholes        # black-hole queues
GET /api/v1/analytics/forensics/stagnation        # low touch-density queues
GET /api/v1/analytics/forensics/silent-breaches   # silent SLA aging
GET /api/v1/analytics/forensics/breaches          # breach root cause for top N
GET /api/v1/analytics/forensics/tickets/{id}/attribution  # per-ticket
```

### Frontend
- New page **"Форензика SLA V3"** at `/forensics` (sidebar → Queue Intel group)
- Charts: black-hole bar, loss-pie, transition Sankey, KPI strip
- Tabs: Black holes / Routing chaos / Breach rate / Silent breaches /
  Hot-potato / Owners / Queue silence

### Real-data reproducibility
- `forensic/07_validate_v3.py` runs against `D:\SLA_test`
- All assertions on baseline ticket 144844 + ServiceDesk + no-owner queues
- Pure SQL aggregation in the engine — no Python O(N²)
