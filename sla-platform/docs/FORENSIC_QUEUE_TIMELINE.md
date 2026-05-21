# Forensic Queue Timeline — v1.7

Live, per-ticket reconstruction of the SLA story queue-by-queue. Verified against the production OTRS data in `D:\SLA_test`.

Endpoint: `GET /api/v1/analytics/forensics/timeline/{ticket_id}`

---

## 1. What the endpoint returns

For one ticket:

```jsonc
{
  "ticket": {
    "ticket_id": 144844,
    "ticket_number": "2026042711001301",
    "created_at": "2026-05-04T08:45:22",
    "first_response_at": "2026-05-05T17:23:30",
    "resolution_at": null,
    "current_queue": "MBR-137-OfficeAutomation",
    "is_closed": false
  },
  "targets": {
    "response_target_seconds": 1800,
    "resolution_target_seconds": 28800
  },
  "segments": [
    {
      "queue_name": "...",
      "entered_at": "...", "exited_at": "...",
      "minutes_in_queue": 505,
      "response_timer_running": true,
      "resolution_timer_running": true,
      "paused": true,
      "no_owner_minutes": 0,
      "response_loss_minutes": 505,
      "resolution_loss_minutes": 505,
      "owners_during": [...],
      "breach_inside_segment": false,
      "queue_contribution_pct": 8.1
    },
    ...
  ],
  "summary": {
    "total_minutes": 6242,
    "total_segments": 25,
    "response_passed_in_queue": "MBR-137-ServiceDesk",
    "response_segments_pre_response": 4,
    "post_response_response_loss_violators": [],
    "top_loss_queue": "MBR-137-ServiceDesk",
    "top_loss_minutes": 1497,
    "breach_queue": "MBR-137-ServiceDesk",
    "bounces": [
      {"queue": "MBR-137-ServiceDesk", "visits": 12},
      {"queue": "MBR-137-DC-WintelOperations", "visits": 10}
    ],
    "first_response_rule_check": "ok"
  }
}
```

---

## 2. The 11 fields per segment — definitions

| field | definition |
|---|---|
| `entered_at` / `exited_at` | direct from `queue_periods` table |
| `minutes_in_queue` | wall-clock duration of this segment |
| `response_timer_running` | True if `first_response_at` is null OR falls inside this segment OR is in a later segment |
| `resolution_timer_running` | same logic with `resolution_at` |
| `paused` | any `pending*` state event occurred inside the segment window |
| `no_owner_minutes` | sum of ownership-period overlaps where owner ∈ {`root@localhost`, ∅} |
| `response_loss_minutes` | portion of segment that counted toward response SLA. Zero after `first_response_at`. Pre-response: full segment. The segment containing `first_response_at` gets the partial slice. |
| `resolution_loss_minutes` | same model, anchored at `resolution_at` |
| `owners_during` | every owner that intersected the segment, with seconds + `is_system` flag |
| `breach_inside_segment` | True if `(created_at + resolution_target_seconds)` falls inside the segment window |
| `queue_contribution_pct` | `segment_minutes / total_minutes × 100` |

---

## 3. Real example — ticket 144844, top 10 segments by resolution loss

```
queue                                    min   resp_loss  resol_loss  no_own  paused
MBR-137-ServiceDesk                      1497          0       1497    1497    True
MBR-137-OfficeAutomation                 1405          0       1405    1405    True
MBR-137-ServiceDesk                      1255          0       1255    1255    True
MBR-137-DC-WintelOperations               815        815        815       0    True
MBR-137-ServiceDesk                        505        505        505       0    True
MBR-137-DC-StorageOperations               259        259        259       0    True
MBR-137-ServiceDesk                        378        378       1497    1497    True   ← first_response delivered here
MBR-137-ServiceDesk                        160          0        160     160    False
MBR-137-DC-WintelOperations                132          0        132       1    True
MBR-137-DC-WintelOperations                 62          0         62       9    True
```

The narrative this enables (paste into a customer report):

> Ticket `2026042711001301` accumulated **6,242 minutes** of wall time across **25 queue segments**.
> The first response was delivered after **1,957 minutes** while the ticket sat in **MBR-137-ServiceDesk**.
> The largest SLA loss source is **MBR-137-ServiceDesk (1,497 min)** which held the ticket without a real owner the entire time and with the ticket in a pending state.
> A second large loss source is **MBR-137-OfficeAutomation (1,405 min)** — same no-owner + pending pattern.
> The ticket revisited ServiceDesk **12 times** and DC-WintelOperations **10 times** — clear routing-loop signature.

---

## 4. How the timeline plugs into other endpoints

- `top_loss_queue` + `top_loss_minutes` → headline in a queue-detail dashboard.
- `breach_queue` → the same queue the v1.3 `attribution_engine` identifies as `breach_queue`. The two engines independently arrive at the same answer for ticket 144844.
- `response_passed_in_queue` → credit the L1 queue where the response was actually delivered.
- `bounces` → directly feeds the hot-potato detector.
- `summary.first_response_rule_check` → live invariant check; if it ever returns `violation`, the response SLA logic regressed.

---

## 5. What the timeline does NOT yet do

- **Frontend timeline visual** is not built in this release. The API returns the data; rendering it as the horizontal segment strip described in the prompt is the next iteration. `frontend/src/design/v1-tokens.css` ships a `.v1-timeline` recipe ready to consume the JSON.
- **Calendar-aware response_loss** — currently every segment uses raw wall-clock minutes. Business-hours subtraction is already in the V2 SLA engine but is NOT yet propagated into per-segment loss. For now, the timeline is calendar-agnostic.
- **Pause-trigger drill-down** — `paused: True` is a boolean. Per-segment pause start/end timestamps are not in the response. They're available in `ticket_events` and can be added if a customer requests forensic depth on a specific ticket.

---

## 6. Reproducibility

```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"admin","password":"admin123"}' \
  -H 'Content-Type: application/json' | jq -r .access_token)

# Full timeline
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/forensics/timeline/144844?response_target_seconds=1800&resolution_target_seconds=28800" \
  > tl144844.json

# Quick narrative
jq '{
  ticket: .ticket.ticket_number,
  total_min: .summary.total_minutes,
  segments: .summary.total_segments,
  response_in: .summary.response_passed_in_queue,
  rule: .summary.first_response_rule_check,
  top_loss: {q: .summary.top_loss_queue, min: .summary.top_loss_minutes},
  breach: .summary.breach_queue,
  bounces: .summary.bounces
}' tl144844.json

# Validate response_loss sums to first_response_at - created_at:
jq '[.segments[].response_loss_minutes] | add' tl144844.json
```
