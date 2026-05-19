# v0.7.0 — Enterprise SLA Governance Engine

**Release date:** 2026-05-19

---

## Overview

Complete rewrite of the SLA calculation engine. The system now provides explainable, audit-grade SLA intelligence with full ticket lifecycle reconstruction, calendar-aware business time, stacked pause detection, 16 metric types, predictive breach analysis, and risk scoring.

---

## What's New

### SLA Engine V2
- **Timeline Engine** — Full ticket lifecycle reconstruction from events
- **Business Time Engine V2** — Connects `BusinessCalendar` model with holiday, timezone, and multi-shift support
- **Pause Engine V2** — Stacked pause handling, pending_until boundary, full audit trail with reasons
- **Metrics Engine V2** — 16 metric types with risk scoring and efficiency computation
- **Rule Engine V2** — Condition-based matching with specificity scoring
- **Predictive Engine** — Breach ETA, probability, queue overload prediction

### New Metrics
- `first_response_time`, `resolution_time`, `assignment_time`
- `queue_time`, `owner_time`, `active_work_time`, `paused_time`
- `reopen_count`, `reassignment_count`, `queue_bounce_count`, `touch_count`
- `sla_efficiency_pct`, `response_breach_delta`, `resolution_breach_delta`

### Enhanced Columns
- `sla_risk_score`, `risk_level`, `risk_reason` — now populated by MetricsEngine V2
- `team_prefix` — now populated from queue/owner periods

### New API Endpoints
- `GET /api/v1/sla/timeline/{ticket_id}` — SLA timeline explanation
- `GET /api/v1/sla/efficiency` — SLA efficiency metrics
- `GET /api/v1/sla/predictive/breach-eta` — breach ETA/probability
- `GET /api/v1/sla/predictive/queue-overload` — queue overload score
- `GET /api/v1/sla/v2/metrics` — V2 metrics with risk/team filters

### Database
- New migration `016_sla_engine_v2` — 5 composite indexes for V2 queries

---

## QA
- `pytest tests/` — 280 passed, 0 failed
- Legacy backward compatibility: all original tests pass unchanged
- `tsc --noEmit` — 0 errors
- `vite build` — clean production build

---

## Breaking Changes
None. All existing API contracts preserved. V2 engine is additive — V1 functions retained as legacy wrappers.

---

## Migration
```bash
alembic upgrade head
docker compose restart backend
```
