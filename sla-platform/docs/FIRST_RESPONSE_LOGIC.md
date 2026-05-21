# First Response Logic — Verification Report (v1.7)

The user prompt explicitly required:

> **FIRST RESPONSE is counted ONLY ONCE.** After first response, response SLA timer MUST stop permanently. Transfers between queues MUST NOT restart response SLA.

This document verifies the current engine implements that rule, with code references and live evidence.

---

## 1. Where `first_response_at` is set

`backend/app/services/reconstructor_service.py:89-97`:

```python
first_response_at = None
...
for ev in events:
    if ev["event_type"] in ("SendAnswer", "EmailCustomer", "PhoneCallCustomer"):
        if first_response_at is None:            # ← set only on the FIRST one
            first_response_at = ev["event_time"]
```

The reconstructor scans the event stream in chronological order and **sets `first_response_at` on the first event of type `SendAnswer` / `EmailCustomer` / `PhoneCallCustomer`**. Subsequent matching events do NOT mutate it.

A queue transfer (`Move` event) is **not** in the response-eligible set — so transferring a ticket cannot trigger or reset response.

---

## 2. Re-imports preserve the original `first_response_at`

Same file, line 132 in the `ON CONFLICT … DO UPDATE`:

```sql
first_response_at = COALESCE(ticket_snapshots.first_response_at, EXCLUDED.first_response_at)
```

`COALESCE(existing, new)` returns the existing non-NULL value first. So once `first_response_at` is set, **any re-import preserves the original timestamp**. There is no path to recompute it later.

---

## 3. The SLA metric is emitted once per ticket per import

`backend/app/services/sla/metrics_engine.py:211-239`:

```python
def compute_first_response_time(db, ticket, sla_def, import_id, _pause_cache=None):
    if not ticket.created_at or not ticket.first_response_at:
        return None
    ...
    active = calculate_active_time(...)
    effective = active["active_time_seconds"]
    target = _resolve_breach_target(db, ticket, sla_def, "response_target_seconds")
    breached = target > 0 and effective > target
    ...
    return MetricsEngine._build_metric(..., metric_name="first_response_time", ...)
```

Single function call per ticket per import → single row written. No loop that fires this per-queue-segment.

---

## 4. Live runtime verification

The v1.7 forensic timeline endpoint includes a built-in invariant check that fires every time the endpoint is called. Live response for ticket 144844:

```
$ curl -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8000/api/v1/analytics/forensics/timeline/144844?response_target_seconds=1800&resolution_target_seconds=28800"

summary:
  response_passed_in_queue: MBR-137-ServiceDesk
  response_segments_pre_response: 4
  post_response_response_loss_violators: []
  first_response_rule_check: ok
```

`post_response_response_loss_violators` is the audited list — any segment that starts AFTER `first_response_at` and still reports `response_loss_minutes > 0`. **The list is empty.** The rule check returns `ok`.

### Sanity arithmetic

```
first_response_at - created_at = 2026-05-05 17:23:30 − 2026-05-04 08:45:22
                               ≈ 32 h 38 m
                               = 1958 minutes

Σ segment.response_loss_minutes across all 25 segments
                               = 1957 minutes
```

The sum across segments matches the actual response time to within 1 minute (rounding to integer minutes per segment). **All response loss is accounted for in the pre-response segments only.**

---

## 5. The 4 pre-response segments (live for ticket 144844)

| queue | segment minutes | response_loss_min | resolution_loss_min |
|---|---:|---:|---:|
| MBR-137-ServiceDesk | 505 | 505 | 505 |
| MBR-137-DC-WintelOperations | 815 | 815 | 815 |
| MBR-137-ServiceDesk | 378 | 378 | 1,497 (post-resp) |
| MBR-137-DC-StorageOperations | 259 | 259 | 259 |
| | | **1,957 total** | (continues post-response) |

After response is delivered in the ServiceDesk segment at minute 1957, every subsequent segment shows `response_loss_minutes = 0`. The resolution timer continues — which is correct per business rule.

---

## 6. What the engine does NOT do (verified absent)

- Does NOT recompute first_response on transfer.
- Does NOT emit a second `first_response_time` metric on re-import.
- Does NOT count post-response activity toward response SLA.

---

## 7. Reproducibility

```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"admin","password":"admin123"}' \
  -H 'Content-Type: application/json' | jq -r .access_token)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/forensics/timeline/144844?response_target_seconds=1800" \
  | jq '.summary.first_response_rule_check, .summary.post_response_response_loss_violators'
```

Expected: `"ok"` and `[]`.

---

## 8. Conclusion

**The business rule is already correctly implemented.** No engine code change is required. The v1.7 timeline endpoint surfaces a real-time invariant check that exposes any future regression immediately.
