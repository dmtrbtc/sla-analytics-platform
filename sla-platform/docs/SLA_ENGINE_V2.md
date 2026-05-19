# SLA Engine V2 — Enterprise SLA Calculation Engine

## Architecture

```
timeline_engine.py    — Reconstruct full ticket lifecycle from events
business_hours.py     — Calendar-based, timezone-aware business time calculation
pause_engine.py       — Full SLA clock pause detection with audit trail
metrics_engine.py     — 16 SLA metrics with risk scoring and efficiency
rule_engine.py        — Enterprise SLA definition matching with conditions
predictive_engine.py  — Breach ETA, probability, queue overload prediction
risk_engine.py        — Risk level computation (low/medium/high/critical)
sla_engine.py         — Orchestrator coordinating all sub-engines
```

## New in V2

### Timeline Engine (`timeline_engine.py`)
- Reconstructs full ticket lifecycle from `ticket_events`
- Queue intervals: entered/exited per queue
- Owner intervals: start/end per owner
- Pending intervals: pause start/end with reason
- Working intervals: active SLA clock periods
- Event deduplication and normalization
- `explain_ticket_timeline()` — human-readable explanation

### Business Time Engine V2 (`business_hours.py`)
- `BusinessTimeEngine` class connects to `BusinessCalendar` ORM model
- Holiday support: date ranges and individual dates
- Timezone-aware calculations (DST-safe via `zoneinfo`)
- Working days per day of week
- Multiple time windows per day
- 24x7 calendar support
- Legacy backward-compatible API preserved

### Pause Engine V2 (`pause_engine.py`)
- `compute_pause_segments_v2()` returns typed `PauseSegment` objects with reasons
- Full pause audit trail: reason, trigger event, start/end
- Stacked pending state handling (nested pauses)
- System action filtering (`is_system_action`)
- `pending_until` boundary honored
- Legacy `compute_pause_segments()` preserved

### Metrics Engine V2 (`metrics_engine.py`)

**16 metric types:**

| Metric | Description |
|--------|-------------|
| `first_response_time` | Creation → first response (minus pauses) |
| `resolution_time` | Creation → resolution (minus pauses) |
| `assignment_time` | Creation → first owner assignment |
| `queue_time` | Per-queue active wait |
| `owner_time` | Per-owner handling time |
| `active_work_time` | Total non-paused ticket time |
| `paused_time` | Total paused time |
| `reopen_count` | Post-resolution reopens |
| `reassignment_count` | Owner changes |
| `queue_bounce_count` | Queue transitions |
| `touch_count` | Non-system events |
| `sla_efficiency_pct` | 100 × (1 − paused / total) |

**Enhancements:**
- `sla_risk_score`, `risk_level`, `risk_reason` now populated
- `team_prefix` now populated from queue/owner periods
- Risk level computation: medium ≥60%, high ≥80%, critical ≥95%

### Rule Engine V2 (`rule_engine.py`)
- Specificity scoring: queue_pattern (+10), priority match (+5)
- Condition evaluation for ticket matching
- Fallback to wildcard definitions
- Legacy `resolve_priority()` preserved

### Predictive Engine (`predictive_engine.py`)
- `compute_breach_eta()` — remaining seconds, breach probability (0-100%), elapsed ratio
- `compute_queue_overload()` — overload score (0-100), breach rate, severity

### API Endpoints (new)

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/sla/timeline/{ticket_id}` | Full SLA timeline explanation |
| `GET /api/v1/sla/efficiency` | List SLA efficiency metrics |
| `GET /api/v1/sla/predictive/breach-eta` | Breach ETA and probability |
| `GET /api/v1/sla/predictive/queue-overload` | Queue overload score |
| `GET /api/v1/sla/v2/metrics` | V2 metrics with risk/team filters |

## Database Changes

Migration `016_sla_engine_v2` adds 5 composite indexes:
- `ix_sla_metrics_metric_breached_time` — V2 metric filtering
- `ix_sla_metrics_risk_level_time` — risk-based queries
- `ix_sla_metrics_team_metric` — team SLA analytics
- `ix_sla_metrics_ticket_metric` — per-ticket V2 metrics
- `ix_sla_metrics_import_metric` — per-import V2 metrics

No schema changes — all columns existed from migration 012.
