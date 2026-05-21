# Future Platform Ideas — backlog after v1.7

A grounded backlog of operational, governance, AI, and automation extensions that the existing v1.7 data model and APIs already support. Each item lists the concrete primitives that already exist so it stays small-scope and runtime-verifiable.

---

## 1. Roadmap candidates

### 1.1 Personal Settings page (Phase 1 prompt unfinished)
**What:** UI page `/settings/personal` driving `user_preferences` JSONB column.
**Needs:** Migration `022_user_preferences`; backend `GET/PATCH /auth/me/preferences`; React form.
**Primitives already in place:** Auth flow + user model.
**Effort:** 1 day.

### 1.2 Forensic Timeline visual (Phase 6 prompt unfinished)
**What:** Horizontal segment strip on `/tickets/{id}` rendering the `/analytics/forensics/timeline/{id}` payload.
**Needs:** React component that maps `segments[]` to CSS-variable widths; tooltip with all 11 segment fields.
**Primitives already in place:** Timeline endpoint + `.v1-timeline` CSS recipe.
**Effort:** ½ day.

### 1.3 Calendar-aware response/resolution loss
**What:** Per-segment business-hours subtraction. Currently the timeline uses wall minutes.
**Needs:** Wire `services/sla/business_hours.calculate_business_seconds` into `TimelineEngine.for_ticket`.
**Risk:** Business-hours calendar resolution may differ across tenants; needs admin UI for calendar selection per ticket.
**Effort:** 1 day backend + tests; 1 day UI surface.

### 1.4 Auto-escalation on bounce_count ≥ N
**What:** Automatic incident creation when a ticket revisits the same queue ≥3 times.
**Needs:** Celery beat task that queries `queue_periods` GROUP BY ticket_id, queue_name HAVING count ≥ 3.
**Primitives:** `services/operations/incident_service.py` + `routing_instability_score` from contribution_engine.
**Effort:** ½ day.

### 1.5 Dormant-ticket auto-poke
**What:** Daily job that posts an internal note on any open ticket with no events for N days (Asset queues: 30 days; others: 7 days).
**Needs:** Celery beat task + integration with OTRS write API (currently read-only).
**Primitives:** `dormant_open_tickets` query in `domain_intelligence.py:assetmanagement`.
**Effort:** depends on OTRS write API access.

---

## 2. Operational improvements

### 2.1 Hidden queues per user
**What:** Inverse of favorites — list of queue names the user wants excluded from all dashboards.
**Needs:** `hidden_queues` table (same shape as `favorite_queues`), one new context flag, filter inversion in dashboards.
**Effort:** ½ day.

### 2.2 Workspace handoff
**What:** Share a workspace preset link with a colleague (shareable URL → import).
**Needs:** Token-signed URL encoding `preset_id`. `is_shared` already exists.
**Effort:** ½ day.

### 2.3 "Was this rule helpful?" feedback on SLA conflicts
**What:** Track which conflicts the operations team accepted vs ignored; tune the detector.
**Needs:** `sla_rule_feedback` table; UI hooks on the conflict-detector endpoint.
**Effort:** ½ day.

### 2.4 Real-time WebSocket push for KPI changes
**What:** When a new breach lands, push to `/ws/dashboard` instead of TanStack polling.
**Needs:** Wire `websocket_manager.broadcast()` from the SLA compute pipeline.
**Effort:** 1 day; needs browser verification.

### 2.5 ServiceDesk routing-rule recommender
**What:** Based on `outbound_transitions` data, suggest auto-routing rules for the top 5 high-volume channels (ServiceDesk → 1C-Alfa-Auto has 516 transitions on 86 tickets — automate the dispatch).
**Effort:** 1 day backend (proposal endpoint); 1 day UI panel.

---

## 3. AI ideas (grounded — not gimmicks)

### 3.1 Ticket-narrative summarizer (Russian)
**What:** Given a timeline payload, generate a 4-sentence operations summary in Russian for executive reports.
**Needs:** Existing AI Copilot infrastructure + a focused prompt template using `top_loss_queue`, `breach_queue`, `bounces`, `routing_instability_score`.
**Effort:** ½ day prompt + endpoint; needs LLM access cost approval.

### 3.2 SLA-rule auto-tuner
**What:** Take the conflict-detector + dead-rule output and propose new targets that would have produced X% fewer breaches against the historical dataset.
**Needs:** Run simulator against every closed ticket; gradient-descent target proposal.
**Effort:** 1 day; uses existing `/sla/v15/simulate` endpoint.

### 3.3 Anomaly classifier for ticket titles
**What:** Find recurring infrastructure-instability signatures (e.g. the "TULA room" pattern in Multimedia).
**Needs:** Light NLP — already partially in `domain_intelligence.multimedia.criticality_markers`.
**Effort:** 1 day.

---

## 4. SLA governance ideas

### 4.1 Dual-SLA reporting in customer-facing exports
**What:** Every customer report shows active-time SLA AND wall-clock SLA side-by-side. The "hidden breach delta" becomes a first-class number.
**Needs:** Update XLSX templates in `enterprise_reports`.
**Effort:** 1 day.

### 4.2 SLA aging policy
**What:** Configurable rule: "any ticket older than X days auto-escalates regardless of pending state."
**Needs:** New table `sla_aging_policy`; daily Celery job.
**Effort:** 1 day.

### 4.3 Per-queue SLA realism dashboard
**What:** For each `sla_queue_rule`, show historical breach rate. Flag any rule with >40% breach as "unrealistic".
**Needs:** Cron-refreshed materialized view; UI page.
**Effort:** ½ day.

---

## 5. Automation ideas

### 5.1 Re-import diff
**What:** When the same OTRS export period is re-imported, surface a diff: tickets added, owner changes, SLA recompute drift.
**Needs:** Store import-level fingerprint per ticket.
**Effort:** 1 day.

### 5.2 Slack / Telegram bridge for hot-potato alerts
**What:** When a ticket crosses `routing_instability_score ≥ 80`, ping a channel.
**Needs:** Existing webhook/telegram tasks (already wired in `notification_tasks.py`).
**Effort:** ½ day.

---

## 6. Predictive analytics

### 6.1 Time-to-breach forecaster
**What:** For every currently-open ticket, predict probability of breach in next 24 h based on its queue-bounce rate and ownership pattern.
**Needs:** Lightweight model (logistic regression on features already computed by `contribution_engine`).
**Effort:** 2 days; needs domain validation.

### 6.2 Workload forecast for next week
**What:** "Veshki is expected to get 80 ± 12 Workplace tickets next Monday based on day-of-week pattern."
**Needs:** Aggregate `ticket_snapshots.created_at` by day-of-week; simple seasonal model.
**Effort:** 1 day.

### 6.3 Engineer-load early warning
**What:** When an engineer's `hours_owned / 160` would cross 2.0× within the next 7 days at current intake rate, surface the alert.
**Needs:** Tracking ownership_period deltas over time.
**Effort:** 1 day.

---

## 7. Quick wins worth doing first (under ½ day each)

1. Frontend timeline visual using existing endpoint + `.v1-timeline` CSS.
2. Hidden queues table + inverse filter.
3. Per-queue SLA realism table from existing data.
4. Slack alert on `routing_instability_score ≥ 80`.
5. Re-route the `/` root to `dashboard_presets WHERE is_default AND user_id = me` if it exists.

---

## 8. What this backlog deliberately omits

- "AI command center" / "AI chat for operations" — not grounded in real data signals; deferred until the smaller AI ideas (3.1-3.3) prove value.
- "Full enterprise visual redesign" — already explicitly out of scope per `DESIGN_V1_APPLICATION_REPORT.md`. Page-by-page incremental migration only.
- "Multi-tenant per-org configuration UI" — multi-tenant schema exists (`019_saas_tables`) but no UI; needs a clear customer demand before building.
- "Real-time dashboard for >100 concurrent users" — current scale is single-team operations; sharded WS isn't justified yet.
