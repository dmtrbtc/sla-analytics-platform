# Release Notes — v0.7.1

## SLA Config Center Stabilization + Explainability UX

### Critical Bug Fixes

**Root cause #1 — `parseHumanDuration()` returns 0 for spaced input**
- `frontend/src/utils/format.ts:11` — The function split on whitespace then tried to regex-match each token separately. Input `"15 мин"` (with space) → parts `["15", "мин"]` → neither token matches `^\d+\D+$` → returns **0**.
- Fix: replaced with a single global regex `/(\d+)\s*([дdчhмmсs])/gi` that handles any whitespace between number and unit.

**Root cause #2 — `calendar_id` can never be cleared once set**
- `backend/app/api/v1/sla.py:348` — The `update_fields` loop used `val is not None` as guard, which silently skips `None` values. Setting `calendar_id` to `None` was impossible.
- Fix: introduced `_UNSET = object()` sentinel to distinguish "not provided" from "explicitly set to None". Applied to `update_queue_rule`, `update_calendar`, and `update_escalation`.

**Root cause #3 — `form.setFieldsValue` sends hidden fields to backend**
- `frontend/src/pages/SLAConfig.tsx:78` — `openEdit()` spread `...rule` into `setFieldsValue`, which included `id`, `created_by`, `created_at`, `updated_at`. These phantom fields were submitted with the form.
- Fix: only set fields that have corresponding `Form.Item` declarations.

**Root cause #4 — `POST/PUT /definitions` accept raw `dict` with no Pydantic validation**
- `backend/app/api/v1/sla.py:52,116` — Endpoints used `payload: dict` instead of typed schemas, bypassing type coercion, `gt=0` validation, and max_length checks.
- Fix: switched to `SLADefinitionCreate` / `SLADefinitionUpdate` Pydantic schemas. Added missing fields (`queue_pattern`, `priority`, `pause_on_pending`, `business_hours`) to schemas.

**Root cause #5 — `SLADefinition.priority` type mismatch**
- `backend/app/domain/models.py:151` — Column defined as `String(50)` but API passes integer.
- Fix: cast `str(payload.priority)` in `create_sla_definition` endpoint.

**Root cause #6 — Missing `resolution_must_exceed_response` on update**
- `backend/app/domain/schemas.py:345` — `SLAQueueRuleUpdate` lacked the validator that `SLAQueueRuleCreate` had.
- Fix: added the same `@field_validator("resolution_target_seconds")` to `SLAQueueRuleUpdate`.

**Root cause #7 — `_sync_audit` commits before async transaction**
- `backend/app/api/v1/sla.py:689` — `_sync_audit()` used a synchronous session to write audit logs *before* the async transaction committed. On rollback, phantom audit entries would remain.
- Fix: migrated all `_sync_audit` calls to `background_tasks.add_task(...)`, ensuring audit logging happens after the async transaction succeeds.

### Enterprise SLA Config UX

- **Queue Rules Table Redesign**: SLA targets as compact dual-line cells, calendar + escalation indicators, health dot with efficiency/breach %, severity-colored badges.
- **Human SLA Editor**: All durations use `response_human` / `resolution_human` fields with `parseHumanDuration` and `formatHumanDuration` helpers. No raw seconds.
- **Live Validation**: Input validation before save — duration > 0 check, descriptive error messages for 422 responses.
- **Error Handling**: `saveRule` wrapped in try/catch with detailed error display.

### SLA Explainability Center

- **New `SLAExplainer` component** (`frontend/src/components/sla/SLAExplainer.tsx`): 1019 lines of enterprise-grade explainability.
  - **Header**: ticket ID, breach status badge, risk score/level, breach probability.
  - **SLA Policy Applied**: which rule matched, why, response/resolution targets, calendar, escalation rules.
  - **Timeline Visualization**: horizontal bars for queue intervals (colored), pending/pause sections (gray), working time (teal), breach moment indicator.
  - **Metric Breakdown**: for each metric — raw elapsed, business hours excluded, paused time, final counted time, target, delta, status.
  - **Breach Root Cause** (conditional): which queue caused breach, where most time lost, longest owner, longest pause, reassignment impact, business-hour effect.
  - **Who Delayed**: owner analysis with duration, % of lifecycle, progress bars.
- **Integrated into `TicketDetail.tsx`**: new "SLA Explanation" tab with `InfoCircleOutlined` icon.

### Files Changed

```
 M sla-platform/backend/app/core/version.py                  (0.7.0 → 0.7.1)
 M sla-platform/backend/app/api/v1/sla.py                    (BackgroundTasks, _UNSET sentinel, Pydantic validation)
 M sla-platform/backend/app/domain/schemas.py                 (SLADefinitionCreate/Update fields, SLAQueueRuleUpdate validator)
 M sla-platform/frontend/src/utils/format.ts                  (parseHumanDuration regex rewrite)
 M sla-platform/frontend/src/pages/SLAConfig.tsx              (queue rules redesign, error handling)
 M sla-platform/frontend/src/pages/TicketDetail.tsx            (SLA Explanation tab)
 M sla-platform/frontend/src/api/tickets.ts                   (slaTimeline, slaMetrics, slaBreachEta endpoints)
 A sla-platform/frontend/src/components/sla/SLAExplainer.tsx  (NEW — 1019 lines)
```

### QA Results
- `tsc --noEmit`: 0 errors
- `pytest tests/`: 280 passed
- `vite build`: 3818 modules, clean build
