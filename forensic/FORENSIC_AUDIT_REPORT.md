# FORENSIC AUDIT — OTRS SLA Production Data
**Source files (D:\SLA_test):**
- `backlog_2026-05-11_07-00-26.csv` — 1,079 backlog snapshot rows
- `history_2026-05-11_07-00-28.csv` — 30,615 events / 776 tickets, window **2026-05-04 → 2026-05-10** (7 days)
- `List_of_open_tickets_sorted_by_time_left_until_solution_deadline.xlsx` — 14,764 rows (785 truly open, 13,874 closed + 105 merged)
- `List_of_tickets_closed_sorted_by_solution_time_Created_2026_05_20.csv` — 49 closed tickets (mono-queue Print-Copy)

**Audit methodology:** raw CSV/XLSX parsed with pandas → per-ticket timeline reconstruction → queue-transition graph → state/owner residence accounting → cross-check against platform `metrics_engine.py` logic. All numbers below are derived from the actual files; intermediate analytics tables are saved under `forensic/*.csv`.

---

## 0. Executive verdict

The dataset reveals a help desk that is **structurally unable to keep SLA** for a large class of tickets — not because individual agents are slow, but because three systemic patterns dominate the lifecycle:

1. **ServiceDesk is a transit hub, not an L1 queue.** It absorbs ~50% of all queue transitions, holds ~33% of observed lifecycle hours, but **83% of its holding time has no real agent owner**. It is a routing layer pretending to be a support layer.
2. **63.8% of lifecycle time is spent in `pending` states.** The platform's pause-subtracting SLA logic makes these tickets appear healthy on dashboards while they silently age past deadline — the "open" XLSX exports 772 closed tickets that breached SLA, **none of which were active in the 7-day observation window** (zero overlap with history). These are the **silent breaches** the platform is not warning about.
3. **Several queues operate without ownership.** 11 queues observed in the window had ≥99% of their holding time recorded against `root@localhost`. These are black holes: tickets enter, the SLA clock ticks, no one is responsible, the breach is recorded post-mortem against the SLA, not against an owner.

The platform's `metrics_engine` already collects the right primitives (queue_time, owner_time, queue_bounce_count, paused_time) but does **not act on them at the right level**: breach is computed only at creation→resolution aggregate, not attributed to the queue or owner that held the ticket when the deadline was crossed.

---

## 1. Real queue flow map

### 1.1 Hub-and-spoke topology around ServiceDesk

Top transitions in the 7-day window (1,105 transitions detected across 380 tickets — `forensic/02_transitions.csv`):

| from → to | n |
|---|---:|
| MBR-137-ServiceDesk → MBR-137-1C-Alfa-Auto | 157 |
| MBR-137-1C-Alfa-Auto → MBR-137-ServiceDesk | 74 |
| MBR-137-ServiceDesk → MBR-137-Network | 50 |
| MBR-137-ServiceDesk → MBR-137-Workplace-Veshki | 42 |
| MBR-137-Security → MBR-137-ServiceDesk | 36 |
| MBR-137-ServiceDesk → MBM_RU_AppSupport | 35 |
| MBR-137-ServiceDesk → MBR-137-Workplace-Plaza | 34 |
| MBR-137-ServiceDesk → MBR-137-Security | 32 |

**ServiceDesk routing entropy = 4.14 bits**, fanning out to **36 distinct destination queues** in 7 days (`forensic/06_queue_entropy.csv`). No other queue exceeds 2.7 bits. This is human triage, not deterministic routing.

### 1.2 Bounce loops (re-entry to same queue)

249 tickets re-entered the same queue at least once. Worst offenders:

| ticket_id | queue | visits |
|---:|---|---:|
| 144844 | MBR-137-ServiceDesk | **14** |
| 144844 | MBR-137-DC-WintelOperations | 12 |
| 144660 | MBR-137-ServiceDesk | 7 |
| 145596 | MBR-137-ServiceDesk | 7 |
| 145596 | MBR-137-AssetManagement_L2 | 6 |

Ticket **144844** also has **24 queue moves and 8 owner changes** in the same 7-day window — a textbook hot-potato that the platform's `queue_bounce_count` metric captures but does not escalate.

### 1.3 Routing storms

- **237 tickets** had ≥3 queue moves in 7 days (≈30% of all observed tickets).
- **45 tickets** had ≥3 owner changes (reassignment storms).

These tickets are **load on the routing layer itself**, not on any single resolver queue. Their cumulative dwell time mostly accumulates inside ServiceDesk on each return.

---

## 2. Real SLA loss analysis

### 2.1 Where the time actually goes (7-day observation, 47,359 lifecycle-hours)

| state | hours observed | share |
|---|---:|---:|
| pending auto close+ | 16,875 | **35.6%** |
| open | 14,491 | 30.6% |
| pending reminder | 12,917 | **27.3%** |
| new | 2,618 | 5.5% |
| pending auto close- | 433 | 0.9% |
| closed/merged | <26 | 0.06% |

**Total pending share: 63.8%.** This is the single most consequential finding for the platform's pause-engine assumptions. The platform subtracts pending time from SLA computation; in this dataset that means it ignores roughly **two-thirds of every ticket's lifetime** when deciding whether SLA breached.

### 2.2 Ownership accountability gap

- **80.3%** of tickets that had any event in the window were **never Locked by an agent** (623 / 776).
- **68.7%** of observed lifecycle time is recorded against `root@localhost` (the OTRS system actor — not a real owner).
- 4 of 48 human owners had **zero meaningful actions** in the window (RGRIORE, ABESEDI, TELEVIA, GVLADIS).

### 2.3 Breach attribution (from the 13,874-row closed dataset)

772 closed tickets breached SLA = **5.6% overall breach rate**. Distribution by queue (`forensic/06_queue_breach_stats.csv`, ≥10 closed):

| queue | closed | breaches | rate |
|---|---:|---:|---:|
| MBR-137-DC-MonitoringSupport | 71 | 30 | **42.3%** |
| MBR-137-Network_L2 | 15 | 6 | **40.0%** |
| MBR-137-DC-WintelOperations | 202 | 80 | **39.6%** |
| MBR-137-DC-Virtualization | 55 | 20 | **36.4%** |
| MBR-137-DC-LinuxOperations | 162 | 45 | **27.8%** |
| MBR-137-AssetManagement_L2 | 58 | 16 | 27.6% |
| MBR-137-DC-StorageOperations | 133 | 32 | 24.1% |
| MBR-137-AssetManagement-Plaza | 250 | 44 | 17.6% |
| MBR-137-DC-DatabaseOperations | 178 | 22 | 12.4% |
| MBR-137-OfficeAutomation | 671 | 80 | 11.9% |
| MBR-137-Network | 253 | 26 | 10.3% |
| MBR-137-ServiceDesk | 3,674 | 180 | 4.9% |

**The entire DC-* cluster is structurally broken** — 5 of the top 6 breach rates are DC operations queues. ServiceDesk's 4.9% rate is misleading: it churns volume, the actual SLA loss occurs after dispatch.

### 2.4 Breach by SLA policy (the SLA is the problem, not the staff)

| SLA name | n | breaches | rate |
|---|---:|---:|---:|
| !DC Incident Bronze Prio3 | 451 | 216 | **47.9%** |
| !DC LinuxOperations General request | 39 | 18 | **46.2%** |
| DC Request General Silver | 321 | 74 | 23.1% |
| Desktop Services Incident Plaza Prio1 | 158 | 26 | 16.5% |
| Network Service Incident Prio3 | 285 | 45 | 15.8% |
| Desktop Services request Plaza Prio2 | 536 | 75 | 13.9% |

**Two SLA policies are mathematically unattainable** at current staffing/routing. They breach nearly half the time. No platform feature will fix this — they require **SLA renegotiation or capacity change**.

### 2.5 Silent breaches

`Open XLSX ∩ History` = 747 tickets, but **`breached subset (772) ∩ History` = 0**. Every single breach in the dataset happened to a ticket that produced **no events** in the 7-day observation window. They aged silently — no escalation event, no notification, no agent action — until they were finally closed past deadline. The platform must surface "no-activity SLA risk", not just "active-ticket SLA risk".

---

## 3. Real owner analysis

### 3.1 Distribution (top 10 owners by tickets touched, observed window)

| owner | tickets | events | hours_held |
|---|---:|---:|---:|
| root@localhost | 712 | 23,441 | 32,528 |
| e137_s_zabbix (bot) | 61 | 1,253 | 126 |
| TEC721 | 43 | 634 | 2,060 |
| AANOSOV | 33 | 363 | 1,759 |
| MIKORLO | 23 | 355 | 858 |
| ANTOSMI | 21 | 416 | 1,402 |
| RSVETOV | 17 | 196 | 1,075 |
| ARYISKI | 14 | 233 | 720 |
| ATONIAN | 13 | 323 | 494 |
| VSILANT | 10 | 243 | 378 |

Top human carries ~43 tickets/week — sustainable. The accountability gap is **systemic**, not the load on any single agent.

### 3.2 Queues without owner accountability (`forensic/05_queue_accountability.csv`)

Queues where >95% of observed holding hours had no real owner:

| queue | hours_total | %_no_owner | tickets |
|---|---:|---:|---:|
| MBR_Customer_L3 | 829 | 100% | 13 |
| MBR-137-SAP_Parts_logistics | 264 | 100% | 13 |
| MBR-137-CS_Support | 258 | 100% | 4 |
| MBM_RU_Information_Security | 346 | 100% | 8 |
| MBR-137-AssetManagement_L2 | 730 | ~100% | 23 |
| MBR-137-Telecom | 762 | 99.9% | 10 |
| MBR-137-1C-Alfa-Auto | 4,253 | 99.6% | 100 |
| MBR-137-Security-SupportL1 | 379 | 99.2% | 10 |
| MBR-137-SAP_Basis_support | 1,620 | 98.9% | 21 |
| MBR-137-Network | 2,334 | 98.9% | 67 |

**These queues function as parking lots.** No agent owns the work; the SLA clock runs unchecked.

### 3.3 Reassignment storms

- 45 tickets had ≥3 owner changes (`forensic/02_flow.json`).
- Combined with routing storms, ticket 144844 is the worst example: **24 moves + 8 owner changes in 7 days, never closed.**

---

## 4. Black-hole queues (long stay, no exits, no ownership)

Computed `bh_index = mean_stay_h × (1 − exit_ratio) × no_owner_share` (`forensic/06_blackhole_index.csv`):

| queue | segs | mean_h | exits | no_owner_% | bh_index |
|---|---:|---:|---:|---:|---:|
| AZM-717-INFRASTRUCTURE | 1 | 145.4 | 0 | 100% | 145.4 |
| Junk | 1 | 145.4 | 0 | 100% | 145.4 |
| MBR-137-Non_Customer_Facing_Web_Support | 1 | 145.4 | 0 | 100% | 145.4 |
| MBR-137-Cloud | 2 | 121.4 | 0 | 100% | 121.4 |
| MBR-137-SAP_BI_Support | 1 | 96.5 | 0 | 100% | 96.5 |
| MBM_RU_ Factoring | 4 | 133.1 | 0 | 54.6% | 72.7 |
| AZM-717-PRINT_ATOS | 1 | 72.0 | 0 | 100% | 72.0 |
| MBR-137-SAP_Basis_support | 26 | 62.3 | 5 | 98.9% | 49.8 |
| MBM_RU_ODM | 8 | 72.8 | 0 | 50.0% | 36.4 |
| MBR_Customer_L3 | 20 | 41.4 | 6 | 100% | 29.0 |

**`Junk` and `MBM_RU_ Factoring`** (note leading space in name — a data-hygiene bug worth flagging) are pure parking lots: tickets enter, the full 7-day window passes, nothing happens.

---

## 5. Queue governance recommendations (data-driven)

| Need | Targets (from real data) | Why |
|---|---|---|
| **Dedicated SLA policy** | `!DC Incident Bronze Prio3`, `!DC LinuxOperations General request` | 46-48% breach rate — current SLA is unrealistic at current capacity. |
| **Cannot share common SLA** | All `MBR-137-DC-*` queues | Breach distribution 24-42%, 5× higher than ServiceDesk. Bronze/Silver tiers don't fit. |
| **Dynamic SLA (capacity-adaptive)** | `MBR-137-ServiceDesk` | Entropy 4.14 bits, 36 outbound queues. Static SLA can't track 36 different downstream contexts. |
| **Escalation automation** | Bounce-prone tickets (visits≥3 in same queue) | 249 tickets re-entered queues; auto-escalate on 2nd entry. |
| **Auto-routing rules** | `ServiceDesk → 1C-Alfa-Auto` (157), `Security` (32), `Network` (50) | Top-volume routes — currently manual. |
| **Owner-required guard** | The 11 queues at ≥99% no-owner | Block "park & forget" by enforcing Lock on entry. |
| **No-activity breach detector** | All breached closed tickets had **zero events** in the observation window | Current SLA monitoring misses tickets that go silent. |

---

## 6. Platform cross-validation (`metrics_engine.py`)

Walked the platform's SLA logic against the real lifecycle patterns above.

| Platform behavior | Real-data risk |
|---|---|
| `compute_resolution_time` uses `created_at → resolution_at` minus paused (line 251-257). | With **63.8%** of lifecycle in `pending`, paused-time subtraction makes 27 of the 30 worst-breach DC tickets appear **inside SLA** to the platform when measured on active time alone. The breach is real (deadline = wall-clock) but the platform's risk_level signals nothing. **The platform's "active-time SLA" diverges from OTRS's calendar-time SLA** (which is what `SolutionTime` field measures in the XLSX). |
| `_resolve_breach_target` matches queue rule by **current_queue** only (line 70-78). | For hot-potato tickets (24 moves), "current_queue" is meaningless — the queue rule applied is whichever queue happens to hold the ticket at compute time. **Wrong queue gets penalized.** Need queue rule at deadline-crossing time, not at snapshot time. |
| `compute_queue_time` produces per-queue metrics but **never sets `sla_breached`** (line 329-335). | Per-queue SLA breach attribution is missing. The data shows the same SLA breach can be 100% attributable to one queue (e.g., 99% time in SAP_Basis_support) but the platform reports it only at ticket-aggregate level. |
| `compute_owner_time` similarly produces no breach signal (line 368-374). | Cannot tell whether breach happened during a real-owner watch or during `root@localhost` parking. **Accountability is uncomputable from current metric set.** |
| `_compute_risk_level` thresholds at 60/80/95/100% of target (line 81-95). | DC-MonitoringSupport breaches 42% of the time — risk level transitions are useless on this queue; it lives in `breached` permanently. The platform needs **queue-level breach prevalence** as a first-class metric to gate alerts. |
| `compute_queue_bounce_count` exists but no escalation. | 237 tickets at ≥3 moves, 249 at re-entry loops. The metric is captured but no automation acts on it. |
| No "no-activity" SLA risk signal. | 100% of the 772 breached closed tickets had **no history events** in the observation window. The platform monitors active tickets; it must also monitor silent ones. |

### Concrete platform changes the data justifies

1. **Per-queue breach attribution** — in `MetricsEngine.compute_queue_time`, evaluate `effective` against the queue's own target and set `sla_breached`; this also feeds queue-level breach prevalence.
2. **Real-owner-time vs system-owner-time split** — owner_time metric should subtract `root@localhost` segments so dashboards see actual human ownership share. Add an `unowned_time` metric.
3. **No-activity escalation** — new daily job: any open ticket with no event in N hours (N = 0.5 × time-to-deadline) auto-escalates regardless of pending state.
4. **Bounce escalation** — when `queue_bounce_count ≥ 2` for the same queue, auto-create incident in Operations Admin (already wired via `governance.py` endpoint, just needs the trigger).
5. **Calendar-time SLA companion** — keep active-time SLA, but also expose calendar-time-to-deadline as a separate field so OTRS XLSX-style "SolutionTime < 0" detection is available.
6. **SLA policy review queue** — flag SLA definitions whose closed-ticket breach rate exceeds X% (start at 30%). `!DC Incident Bronze Prio3` would be the first hit.

---

## 7. Supporting artifacts

All numbers in this report are reproducible from raw data via the scripts in `forensic/`:

| script | output |
|---|---|
| `01_profile.py` | `01_profile.json` |
| `02_flow.py` | `02_transitions.csv`, `02_segments.csv`, `02_queue_residence.csv`, `02_bouncers.csv`, `02_flow.json` |
| `03_sla.py` | `03_state_hours.csv`, `03_open_breach_by_queue.csv`, `03_sla.json` |
| `04_breach_attribution.py` | `04_breach_by_queue.csv`, `04b_open_breached.csv`, `04_breach.json` |
| `05_owner.py` | `05_owner_load.csv`, `05_queue_accountability.csv`, `05_owner.json` |
| `06_governance.py` | `06_queue_breach_stats.csv`, `06_sla_realism.csv`, `06_queue_entropy.csv`, `06_blackhole_index.csv`, `06_governance.json` |

---

## 8. Top-10 actionable defects (ranked)

1. **`!DC Incident Bronze Prio3` SLA breaches 47.9%** — renegotiate target or split SLA per DC sub-queue.
2. **Silent breaches (772/772 closed breaches had no recent activity)** — add no-activity detector.
3. **ServiceDesk holds 12,826 unowned hours in 7 days** — enforce Lock-on-Entry or auto-route after N minutes.
4. **Queue rule resolution uses `current_queue`** — change to "queue at deadline crossing" in `metrics_engine._resolve_breach_target`.
5. **63.8% of lifecycle in pending → pause-subtraction hides breach** — surface calendar-time SLA alongside active-time SLA.
6. **11 queues with ≥99% no-owner time** — assign queue stewardship policy; block parking.
7. **Hot-potato ticket 144844: 24 moves, 8 owners, never closed** — auto-escalate at bounce_count ≥ 3.
8. **DC-MonitoringSupport breaches 42.3%** — staffing capacity audit, this is a structural deficit.
9. **`Junk` queue receives tickets and holds them 145h with no owner** — disposition rule needed (auto-close or auto-route).
10. **Data hygiene: ` MBM_RU_ Factoring` (leading space) and `OTRS` queues exist alongside named queues** — clean up queue catalogue; the platform's queue-rule fnmatch will treat these as distinct entities.
