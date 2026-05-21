# Team Management — Live Audit & v1.4 Additions

**Method:** I exercised every `/teams` endpoint live against the running stack and verified persistence in Postgres before claiming a fix.

---

## 1. Real state before this pass

Live DB had **44 team rows** — almost all of them were leftover test fixtures:

```
sla_platform=> SELECT COUNT(*) AS n, name FROM teams GROUP BY name ORDER BY n DESC LIMIT 5;
 n  |     name
----+--------------
 14 | Support Team
  4 | Incomplete
  …
```

The original `Team` model was minimal: only `id`, `name`, `queue_prefix`, `description`, `is_active`, `created_at`. The user's prompt requires lead, color, SLA targets, escalation chain, and queue list per team — none of those existed.

There was no API to manage team membership at all (a `user_teams` join table existed but had no routes).

---

## 2. Schema extensions (migration 021)

The `021_favorite_queues` migration also adds six operational columns to `teams`:

```sql
ALTER TABLE teams
  ADD COLUMN lead_user_id UUID REFERENCES users(id),
  ADD COLUMN color VARCHAR(20),
  ADD COLUMN response_target_seconds INTEGER,
  ADD COLUMN resolution_target_seconds INTEGER,
  ADD COLUMN escalation_chain JSONB DEFAULT '[]',
  ADD COLUMN queues JSONB DEFAULT '[]';
```

All are nullable / default-populated so existing rows survive.

Verified live after the migration:

```
sla_platform=> \d teams
…
 lead_user_id              | uuid
 color                     | character varying(20)
 response_target_seconds   | integer
 resolution_target_seconds | integer
 escalation_chain          | jsonb
 queues                    | jsonb
```

---

## 3. Defects fixed

### A — `PUT /teams/{id}` was the only update verb; PATCH returned 405

Same root cause as SLA Config. **Fix:** changed to `@router.api_route(..., methods=["PUT","PATCH"])`. Frontend HTTP clients that send PATCH for partial updates now work.

### B — `TeamCreate` and `TeamUpdate` schemas were skinny

They didn't accept `lead_user_id`, `color`, `response_target_seconds`, `resolution_target_seconds`, `escalation_chain`, `queues`. Even if a UI sent them, they'd be dropped silently.

**Fix:** all six new optional fields added to both schemas with proper types. `TeamService.create_team` now forwards `**extra` kwargs through to the model (whitelisted by an `allowed` set so unknown keys can't crash the constructor).

### C — Membership had no API surface

The `user_teams` table existed but no endpoints touched it. Built three new endpoints:

| Verb | Path | Behavior |
|---|---|---|
| GET | `/teams/{id}/members` | JOIN `users` ⨝ `user_teams`, return user list |
| POST | `/teams/{id}/members` | `{user_id}` → INSERT `user_teams`, idempotent |
| DELETE | `/teams/{id}/members/{user_id}` | DELETE row |

Service helpers `TeamService.list_members` / `add_member` / `remove_member` implement these in pure SQL/ORM.

### D — Dummy team cleanup

44 rows of leftover fixtures cluttered the team list, hiding any real teams. Added admin-only `POST /teams/cleanup-dummies` that deletes rows where `name='Incomplete' OR queue_prefix='inc' OR name='Support Team'` (and their memberships first to avoid orphan FKs).

---

## 4. CRUD now verified end-to-end

```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"admin","password":"admin123"}' \
  -H 'Content-Type: application/json' | jq -r .access_token)

# CREATE with operational fields
curl -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"NOC Infrastructure","queue_prefix":"MBR-137-DC-",
       "color":"#b42333","response_target_seconds":900,
       "resolution_target_seconds":14400,
       "queues":["MBR-137-DC-WintelOperations","MBR-137-DC-LinuxOperations"]}' \
  http://localhost:8000/api/v1/teams
```

Live response shape (verified):

```json
{
  "id": 30,
  "name": "NOC Infrastructure",
  "queue_prefix": "MBR-137-DC-",
  "is_active": true,
  "lead_user_id": null,
  "color": "#b42333",
  "response_target_seconds": 900,
  "resolution_target_seconds": 14400,
  "escalation_chain": [],
  "queues": ["MBR-137-DC-WintelOperations","MBR-137-DC-LinuxOperations"]
}
```

`PATCH /teams/30 {"lead_user_id":"335c771b-…"}` updates lead, persisted in DB. `DELETE /teams/30` removes row + memberships cascade.

---

## 5. Frontend status

The existing `Teams.tsx` page renders against the now-extended response. **The UI does not yet expose all the new fields in forms** — that's a frontend feature task, not a backend reliability one. The backend is the source of truth and admins can drive these fields via the API directly today. The next UI iteration should:

- show team color as a swatch in the team list
- add "Lead" picker (dropdown of `/auth/users`)
- add SLA target inputs
- add multi-queue selector (auto-complete from live queue list)

---

## 6. What was NOT verified

- **Team SLA inheritance into ticket compute** — the V2 SLA engine uses `sla_definitions` and `sla_queue_rules`, not `teams.response_target_seconds`. If teams should override SLA rules, that's a separate engine integration; out of scope here.
- **Team workload metrics / dashboards** — there's a `/dashboards/teams` endpoint but it computes from `team_prefix` matching, not from `user_teams` membership. The richer view requested by Phase 2.6 is a follow-up.
- **Browser UI rendering** — no browser in sandbox. The user can verify `/teams` after login.

---

## 7. Reproducibility

```bash
# List
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/teams | jq '.teams | length'

# Create with all operational fields
curl -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"SAP Support","queue_prefix":"MBR-137-SAP_","color":"#5a3eb0",
       "response_target_seconds":1800,"resolution_target_seconds":86400,
       "escalation_chain":[{"after_seconds":3600,"notify":"manager@example.com"}],
       "queues":["MBR-137-SAP_Basis_support","MBR-137-SAP_Parts_logistics"]}' \
  http://localhost:8000/api/v1/teams

# Verify in DB
docker exec sla-platform-postgres-1 psql -U sla_user -d sla_platform -c \
  "SELECT name, color, response_target_seconds, escalation_chain FROM teams WHERE name='SAP Support'"

# Cleanup dummies (admin only)
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/teams/cleanup-dummies
```
