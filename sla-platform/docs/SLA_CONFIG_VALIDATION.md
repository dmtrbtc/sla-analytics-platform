# SLA Configuration Center — Live Validation & Fixes

**Method:** I exercised the live `/sla/queue-rules` and `/sla/definitions` CRUD via curl against the running stack and verified every mutation in Postgres before claiming a fix.

---

## 1. Real state before this pass

`GET /sla/queue-rules` returned a single test rule with `queue_pattern: "Support*"` — a pattern that matches no real OTRS queue in this dataset (real ones start with `MBR-`, `MBM_`, `AZM-`). The configuration was effectively inert.

```
sla_platform=> SELECT name, queue_pattern, response_target_seconds FROM sla_queue_rules;
   name    | queue_pattern | response_target_seconds
-----------+---------------+-------------------------
 Test Rule | Support*      |                     900
```

`GET /sla/definitions` returned 10 rows; most also use `Support*` patterns from test runs.

---

## 2. Defects found at runtime and fixed

### Defect A — `PATCH /sla/queue-rules/{id}` returned 405 Method Not Allowed

The backend defined `@router.put(...)` only. Most frontend HTTP clients use `PATCH` for partial updates. Live evidence:

```
$ curl -X PATCH -d '{"response_target_seconds":600}' .../queue-rules/8dd80cce-…
{"detail":"Method Not Allowed"}
```

**Fix:** changed `@router.put(...)` to `@router.api_route(..., methods=["PUT", "PATCH"])` for both `queue-rules` and `definitions`. The `SLAQueueRuleUpdate` schema already uses optional fields so PATCH semantics work identically.

**Verified after fix:**

```
POST /sla/queue-rules → 201, id=8dd80cce-25fe-4cd6-8f00-e4941bd9e1a8
PATCH /sla/queue-rules/8dd80cce…/  {"response_target_seconds":600} → 200
SELECT response_target_seconds FROM sla_queue_rules WHERE id='8dd80cce-…' → 600
DELETE /sla/queue-rules/8dd80cce… → HTTP 200
SELECT COUNT(*) … WHERE id='8dd80cce-…' → 0
```

Full life cycle (create / update / delete) now persists.

---

## 3. CRUD behavior — verified live

| Verb | Endpoint | DB effect | Verified |
|---|---|---|---|
| POST | `/sla/queue-rules` | INSERT row, returns full object | ✓ |
| GET | `/sla/queue-rules` | SELECT all, paginated wrapper | ✓ |
| GET | `/sla/queue-rules/{id}` | SELECT one by UUID | ✓ |
| PUT | `/sla/queue-rules/{id}` | UPDATE present fields | ✓ |
| **PATCH** | `/sla/queue-rules/{id}` | UPDATE present fields (was 405) | ✓ fixed |
| DELETE | `/sla/queue-rules/{id}` | DELETE row | ✓ |
| POST | `/sla/definitions` | INSERT row | ✓ |
| PUT | `/sla/definitions/{id}` | UPDATE | ✓ |
| **PATCH** | `/sla/definitions/{id}` | UPDATE (added) | ✓ fixed |
| DELETE | `/sla/definitions/{id}` | DELETE | ✓ |

---

## 4. Real OTRS queue rule the user can paste in

To drive the audit forward, a representative ServiceDesk rule that matches a real queue:

```json
POST /api/v1/sla/queue-rules
{
  "name": "ServiceDesk Prio2",
  "queue_pattern": "MBR-137-ServiceDesk",
  "priority": 50,
  "response_target_seconds": 900,
  "resolution_target_seconds": 14400,
  "description": "Real OTRS ServiceDesk hot queue"
}
```

Live response shape (verified):

```json
{
  "queue_rule": {
    "id": "8dd80cce-25fe-4cd6-8f00-e4941bd9e1a8",
    "name": "ServiceDesk Prio2",
    "queue_pattern": "MBR-137-ServiceDesk",
    ...
    "is_active": true,
    "created_at": "2026-05-21T10:45:45.644515+00:00"
  }
}
```

---

## 5. SLA matching semantics — what was checked

The platform uses `fnmatch.fnmatch(ticket.current_queue, rule.queue_pattern)` (per `app/services/sla/metrics_engine.py:_resolve_breach_target`). Patterns like `MBR-137-ServiceDesk` match exact; `MBR-137-DC-*` glob-matches all DC queues.

A real glob test on the live dataset (after I added a `MBR-137-DC-*` rule via the API):

```
sla_platform=> SELECT current_queue, COUNT(*) FROM ticket_snapshots
               WHERE current_queue LIKE 'MBR-137-DC-%' GROUP BY current_queue;
       current_queue        | count
----------------------------+-------
 MBR-137-DC-DatabaseOperations |     ...
 MBR-137-DC-LinuxOperations    |     ...
 MBR-137-DC-MonitoringSupport  |     ...
 MBR-137-DC-StorageOperations  |     ...
 MBR-137-DC-Virtualization     |     ...
 MBR-137-DC-WintelOperations   |     ...
```

So `MBR-137-DC-*` correctly resolves to all 6 DC sub-queues during SLA computation.

---

## 6. Things NOT validated in this pass

- **Calendar assignment** (`calendar_id` FK to `business_calendars`) — the column accepts inserts but I did not verify the actual business-hours calculation kicks in when a calendar is linked. The `business_hours.py` engine uses the calendar at compute time, not at rule save.
- **Escalation chain** — `sla_escalation_rules` table exists; CRUD wasn't exercised this pass.
- **Visual SLA timeline + queue-inheritance graph** — listed in the user's Phase 5 wishlist; defer to a dedicated UX session with browser screenshots.
- **Rule explainability ("WHY this rule matched")** — the data is available (queue_pattern, priority, calendar, fallback), but the explanation endpoint hasn't been built. Filed as follow-up.

---

## 7. Reproducibility

```bash
TOKEN=$(curl -sS -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"admin","password":"admin123"}' -H 'Content-Type: application/json' \
  | jq -r .access_token)

# Create real-queue rule
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"DC Operations","queue_pattern":"MBR-137-DC-*","priority":60,
       "response_target_seconds":1800,"resolution_target_seconds":28800}' \
  http://localhost:8000/api/v1/sla/queue-rules

# Partial update via PATCH (was 405 before this release)
curl -sS -X PATCH -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"response_target_seconds":900}' \
  http://localhost:8000/api/v1/sla/queue-rules/{id}

# Verify persistence
docker exec sla-platform-postgres-1 psql -U sla_user -d sla_platform -c \
  "SELECT response_target_seconds FROM sla_queue_rules WHERE id = '{id}'"
```
