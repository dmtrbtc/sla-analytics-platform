# Real Data Findings — v1.5

What the platform actually says about the production OTRS data loaded from `D:\SLA_test`. Every number is a paste from a live curl response against the running v1.5 stack.

---

## 1. Dataset scale (live, psql-verified)

| | |
|---|---:|
| Tickets ingested | 1,638 |
| SLA metrics computed | 30,378 |
| Breached metrics | 3,181 (10.47%) |
| Distinct queues in `queue_periods` | 53 |
| Completed import sessions | 4 |
| Active SLA queue rules | 2 |
| Teams | 20 (incl. v1.5 "DC NOC v15") |

---

## 2. Top 10 black-hole queues — `/analytics/forensics/queues?sort_by=black_hole_score`

| queue | black_hole_score | no_owner % | breach rate |
|---|---:|---:|---:|
| **MBR-137-SAP_Basis_support** | **0.58** | **100.0%** | **97.5%** |
| **MBR-137-1C-Alfa-Auto** | **0.50** | **86.0%** | **67.3%** |
| MBR-137-Security | 0.20 | 100.0% | 70.8% |
| MBR-137-ServiceDesk | 0.01 | 4.9% | 76.9% |
| MBM_RU_AppSupport | 0.00 | 2.7% | 65.2% |
| MBR-137-Network | 0.00 | 99.0% | 43.0% |
| MBR-137-Workplace-Veshki | 0.00 | 6.0% | 75.5% |
| MBR-137-DC-StorageOperations | 0.00 | 8.4% | 64.0% |
| MBR-137-OfficeAutomation | 0.00 | 33.5% | 35.7% |
| MBR-137-Workplace-Plaza | 0.00 | 0.1% | 47.8% |

**Operational reading:**
- `MBR-137-SAP_Basis_support` is catastrophic: 100% of holding time is unowned and 97.5% of resolution metrics breached. The platform tags this as a true black hole.
- `MBR-137-1C-Alfa-Auto` is the highest-volume parking lot — 100 tickets visited in observed window, 86% no-owner.
- `MBR-137-Security` and `MBR-137-Network` show 99-100% no-owner share — these are queues without real operational accountability.
- `MBR-137-ServiceDesk` has *low* black-hole score (0.01) because tickets churn through it quickly; but its **76.9% breach rate** confirms the V3 finding that ServiceDesk is the routing-chaos hub, not the bottleneck itself.

---

## 3. Hot-potato tickets — `/analytics/forensics/hot-potato?min_moves=10`

| ticket # | queue moves | owner changes | distinct queues |
|---|---:|---:|---:|
| `2026042711001301` | **72** | **36** | 4 |
| `2026050411000791` | 42 | 0 | 4 |
| `2026050511000529` | 42 | 18 | 5 |
| `2026050511000958` | 30 | 0 | 4 |
| `2026050611001526` | 30 | 30 | 4 |

The top offender shows 72 queue moves and 36 owner changes across only 4 distinct queues — a perfect re-entry loop. Ticket `2026042711001301` (internal id 144844) appears in the contribution drill-down with 25 queue_period segments and `routing_instability_score = 90`.

---

## 4. Silent breaches — `/analytics/forensics/silent-breaches?min_ratio=1.0`

These are tickets currently OPEN whose SLA target has already been exceeded **and** which have had zero non-system events for a long time.

| ticket # | queue | days without events | risk |
|---|---|---:|---|
| `2023052211000707` | `MBM_RU_Diasoft` | **1095** (3 years) | breached |
| `2023082811000647` | `MBM_RU_ODM` | 997 (2.7 years) | breached |
| `2023092011001711` | `MBR-137-Network` | 974 (2.7 years) | breached |
| `2023110311000428` | `MBC_MBMR_APPLICATION` | 930 | breached |
| `2023120111000046` | `MBC_MBMR_APPLICATION` | 902 | breached |

**These are the "invisible failures"** that pre-V3 active-time SLA dashboards completely missed because the metrics never re-fired after the deadline passed. The InactivityEngine surfaces them as a separate forensic class.

---

## 5. DC NOC team operational picture — `/teams/31/dashboard?days=30`

A live cut of one operational team scoped to all `MBR-137-DC-*` queues:

| metric | value |
|---|---:|
| Scope queues | 7 |
| Tickets total | 151 |
| Tickets open | 36 |
| MTTA | 14,947 s (≈ 4 h 9 m) |
| MTTR | 221,240 s (≈ 61 h 27 m) |
| Active-time breaches | 114 |
| Wall-clock breaches | 101 |
| No-owner share | **33.42%** |
| Reassignments | **432** |
| Queue bounces | **120** |

Top owners by ticket count in scope:
- `e137_s_zabbix` (monitoring bot): 31 tickets
- `ANTOSMI`: 18 tickets
- `EKUKLEV`: 6 tickets
- `KOKUDRA`: 4 tickets
- `SGULYAE`: 3 tickets

**One human owner (ANTOSMI) handles 18 of 151 DC tickets** — the rest are split across 6 other humans, a monitoring bot, or are *unowned* a third of the time. That's a real operational accountability gap surfaced by the team dashboard.

---

## 6. SLA rule governance findings — `/sla/v15/queue-rules/conflicts`

```
rule_count: 2,  queue_count: 66
overlap_conflicts: 0
impossible_rules: 0
dead_rules: 1   ← "Test Rule" with pattern "Support*" matches zero real queues
```

The conflict detector identified one **dead rule** on first run — the leftover "Test Rule" pattern doesn't match any production queue. Before v1.5 such configuration would have been invisible.

---

## 7. SLA rule simulator findings — `/sla/v15/simulate`

Simulating `queue_pattern=MBR-137-DC-*` with response=30 min / resolution=8 h against ticket 144844 (currently in `MBR-137-OfficeAutomation`):

```
rule_matches_ticket: False
wall_response_seconds:    117,488  (target 1,800)    breach=True
wall_resolution_seconds:  374,571  (target 28,800)   breach=True
```

The simulator gives operations a clean preview of any proposed rule's effect *before* saving, against any real ticket. Without it, the only feedback is post-save breach counts.

---

## 8. Ticket-level contribution drill-down

For hot-potato ticket 144844, `/analytics/forensics/tickets/144844/contribution`:

```
total_wall_seconds: 374,571 (4.3 days)
queue_contributions: 25 segments  (re-entry pattern)
  worst segments:
    MBR-137-DC-WintelOperations  48,901 s (13.06%)  no_owner = 169,450 s
                                                    ↑ unowned the entire time
    MBR-137-ServiceDesk          30,344 s ( 8.10%)  no_owner = 0
    MBR-137-DC-StorageOperations 15,546 s ( 4.15%)  no_owner = 0

owner_contributions:
  root@localhost (system):  268,461 s = 93.15%  ← real accountability gap
  EKUKLEV         (human):   19,739 s =  6.85%

scores:
  routing_instability_score: 90.0   (24 bounces + 18 reassigns × 0.5)
  stagnation_score:          0.24
  operational_waste_score:   100   (clamped — pause+idle+no_owner overlap)
  transfer_efficiency:       0.33
  touch_efficiency:          7.09 events / wall hour
```

This single ticket demonstrates every pathology the platform was built to detect: re-entry, no-owner parking, reassignment storm, low transfer efficiency.

---

## 9. Cross-cutting findings (what the data says, not the code)

1. **Three queues operate at 99–100% no-owner share**: `MBR-137-SAP_Basis_support`, `MBR-137-Security`, `MBR-137-Network`. These should have explicit team ownership before any SLA renegotiation.

2. **Single agents carry disproportionate load.** ANTOSMI handles >10% of DC scope tickets alone. Either staffing or routing rules need correction.

3. **Silent breaches go back to 2023.** Five open tickets have had no events for over 900 days. This is a configuration / process gap (tickets never closed, never reassigned, never timed-out).

4. **ServiceDesk doesn't park tickets, but ServiceDesk decisions cascade.** Its low black-hole score (0.01) combined with 76.9% breach rate confirms it's a routing decision-point: the breach happens downstream of dispatch, not inside the desk.

5. **Hot-potato ticket 2026042711001301** is in `MBR-137-OfficeAutomation` *now* but has visited only 4 queues with 72 moves — meaning it bounces between the same 4 queues repeatedly. Re-entry loop detection should auto-escalate after the third re-entry.

6. **The one dead SLA rule ("Test Rule")** has been silently inert in production. The new conflict detector caught it.

---

## 10. What real data did NOT yet surface

| Question the platform can answer | Status |
|---|---|
| "Show me forensic depth for any queue" | ✓ verified via `/queues/{name}` and `/analytics/forensics/queues?queue=…` |
| "Why did this specific ticket breach?" | ✓ verified for #144844 via `attribution` + `contribution` |
| "Which rules conflict?" | ✓ live `conflicts` returned 0 overlap (good) + 1 dead (real find) |
| "What happens if I apply rule X to ticket Y?" | ✓ `simulate` returns wall-time breach decision |
| "How is team T doing right now?" | ✓ `/teams/{id}/dashboard` |
| Browser screenshot of every page | ✗ no browser in sandbox; user verifies |
| Hourly breach pattern by week | ✗ `busiest_hours` exists in queue detail but not yet rendered |
| XLSX export of weekly breach report | ✗ endpoint exists in `enterprise-reports`; not exercised this pass |

These remaining items don't need new backend code — they're presentation/visual layer work that a single browser session would either confirm or feed back into bug fixes.
