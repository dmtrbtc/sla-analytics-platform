# Queue Operations Model — v1.5

How the platform thinks about queues, ownership, teams, favourites and SLA rules as one coherent operational model. Each section corresponds to a live entity in the running v1.5 database.

---

## 1. Concept layers

```
┌────────────────────────────────────────────────────────────────┐
│  CONFIG LAYER  (admin defines)                                 │
│    sla_definitions, sla_queue_rules, sla_escalation_rules      │
│    business_calendars                                          │
│    teams (+ queue_prefix, queues, escalation_chain)            │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  PERSONALISATION LAYER  (per user)                             │
│    favorite_queues       (per-user star)                       │
│    queue_groups          (private or shared collections)       │
│    dashboard_presets     (operational workspaces)              │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  TICKET STATE LAYER   (ingested)                               │
│    ticket_snapshots, raw_events, ticket_events                 │
│    queue_periods, ownership_periods                            │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  COMPUTED METRIC LAYER                                         │
│    sla_metrics (V2 active + V3 wall-clock + loss buckets)      │
│    Aggregations: QueueForensicsService, OwnerForensicsService, │
│                  InactivityEngine, ContributionEngine          │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER  (UI + API)                                │
│    /dashboards/*, /analytics/forensics/*, /sla/v15/*,          │
│    /teams/{id}/dashboard, /queues/{queue_name}                 │
└────────────────────────────────────────────────────────────────┘
```

Each upper layer is a derived view of the layer below. Migrations are additive — pre-v1.4 tickets remain valid in every aggregation.

---

## 2. Resolution semantics

When the system needs to answer "what SLA applies to ticket T?" it walks downward:

```
1. Is T in any team's `queues` JSONB list?  → use team.response/resolution
2. Does T.current_queue match team.queue_prefix LIKE? → same
3. Is there an sla_queue_rule whose pattern fnmatches T.current_queue?
   → pick the highest-priority rule (ties → earliest created_at)
4. Fall back to active sla_definitions
5. Fall back to engine default (8h response / 40h resolution)
```

For breach attribution, however, the queue is fixed at the *deadline-crossing moment*, not at compute time. This decouples blame from the ticket's current location.

---

## 3. Queue identity

A queue is a free-text string. Real names in the loaded dataset:
- `MBR-137-ServiceDesk` (the central hub, 255 tickets)
- `MBR-137-1C-Alfa-Auto` (top hidden parking lot, 100 tickets in observed history)
- `MBR-137-DC-WintelOperations`, `MBR-137-DC-LinuxOperations`, `MBR-137-DC-StorageOperations`, etc.
- `MBM_RU_AppSupport`, `AZM-717-AssetManagement_Esipovo_L2`, `MBM_RU_ODM`

Patterns: `MBR-137-*` for the main installation, `MBM_RU_*` for MBM, `AZM-717-*` for AZM. The platform's queue rule `queue_pattern` accepts fnmatch globs (`*`, `?`) and the conflict detector translates them to SQL LIKE on read.

Total observed queues in the live DB: **53** (psql verified).

---

## 4. Team scope

A team's responsibility surface is:

```
scope_queues(team) = team.queues ∪ {q ∈ ticket_snapshots.current_queue
                                      | q LIKE (team.queue_prefix || '%')}
```

For "DC NOC v15" (`queue_prefix=MBR-137-DC-`):
- prefix expansion → MBR-137-DC-DatabaseOperations, DC-LinuxOperations, DC-MonitoringSupport, DC-ServersPatching, DC-StorageOperations, DC-Virtualization, DC-WintelOperations
- explicit `queues` JSONB → already a subset of the above
- final scope = 7 distinct queues, 151 tickets, 432 reassignments, 33.42% no-owner share

This expansion is computed live each time `/teams/{id}/dashboard` is called — no materialisation is required, queues_seen is small (53).

---

## 5. Operational workspaces

A dashboard preset is a saved combination of `(queue_group_id, workspace_kind, layout)`. Six workspace_kinds ship:

| kind | typical group |
|---|---|
| `noc` | NOC View — DC + Network queues |
| `servicedesk` | ServiceDesk hot queues |
| `infra` | All MBR-137-* infra-cluster queues |
| `sap` | SAP_* queues |
| `executive` | top 10 SLA-critical queues |
| `custom` | analyst-defined |

Applying a preset (UI button "Применить") sets `FavoritesContext.activeFilter` to the preset's group's queues. Every dashboard that consumes `activeFilter` then rescopes automatically. Preset selection is persisted in localStorage and only sent to the server when modified.

---

## 6. Forensic visibility tiers

For an operations analyst, the platform exposes three forensic depths:

| Depth | Endpoint | Power |
|---|---|---|
| Macro | `GET /analytics/forensics/summary?queue=…` | KPIs, top blackholes, transitions Sankey, hot-potato list |
| Per-queue | `GET /queues/{queue_name}` | snapshot, MTTA/MTTR, entropy, top breached owners, busiest hours, health_score |
| Per-ticket | `GET /analytics/forensics/tickets/{id}/contribution` | full queue chain + owner breakdown + 5 operational scores |
| Per-ticket-attribution | `GET /analytics/forensics/tickets/{id}/attribution` | the breach_queue / breach_owner / breach_reason taxonomy |

Each tier respects the queue filter when applicable.

---

## 7. SLA governance tiers

| Surface | Purpose |
|---|---|
| `sla_definitions` | global default SLA tiers (legacy) |
| `sla_queue_rules` | pattern-based overrides (current) |
| `sla_escalation_rules` | per-rule escalation chain |
| `teams.escalation_chain` (JSONB) | per-team escalation overlay (v1.4) |

Conflict detection looks ONLY at active `sla_queue_rules` and flags:
- **overlap** when two rules cover the same real queue with different targets
- **impossible** when targets are invalid (resolution ≤ 0 or response > resolution)
- **dead** when a pattern matches zero real queues

Simulator runs against any real ticket and shows what would have happened — useful before saving a new rule. Verified live against ticket 144844.
