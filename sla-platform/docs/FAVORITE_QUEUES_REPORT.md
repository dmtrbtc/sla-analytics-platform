# Favorite Queues — v1.4 Build & Live Validation

**Release target:** `feat(v1.4): favorite queues + operational workspaces + sla/team CRUD fixes`
**Method:** every claim below was verified at runtime against the live docker stack and the live Postgres `sla_platform` DB.

---

## 1. What was delivered

A complete favourite-queues subsystem with per-user persistence, group composition, dashboard workspace presets, and server-side scoping of analytics by selected queues.

| Concern | Where |
|---|---|
| Schema | `backend/alembic/versions/021_favorite_queues.py` |
| Models | `backend/app/domain/models.py` — `FavoriteQueue`, `QueueGroup`, `QueueGroupItem`, `DashboardPreset` |
| REST API | `backend/app/api/v1/favorites.py` (16 endpoints) |
| Queue scope filter | `backend/app/api/v1/dashboards.py` + `backend/app/services/dashboard_service.py` |
| Frontend client | `frontend/src/api/favorites.ts` |
| Frontend state | `frontend/src/contexts/FavoritesContext.tsx` |
| Star button | `frontend/src/components/favorites/QueueStarButton.tsx` |
| Frontend page | `frontend/src/pages/Favorites.tsx` (route `/favorites`) |
| Axios list-param serializer | `frontend/src/api/client.ts` |

---

## 2. Schema & migration — verified live

Migration `021_favorite_queues` is applied:

```
sla_platform=> SELECT version_num FROM alembic_version;
     version_num
---------------------
 021_favorite_queues
(1 row)

sla_platform=> SELECT table_name FROM information_schema.tables
               WHERE table_schema='public' AND table_name IN
                 ('favorite_queues','queue_groups','queue_group_items','dashboard_presets')
               ORDER BY table_name;
    table_name
-------------------
 dashboard_presets
 favorite_queues
 queue_group_items
 queue_groups
```

All four tables exist with proper FKs (CASCADE on user delete, CASCADE on group delete for items, SET NULL on group delete for presets).

The `teams` table also gained 6 operational columns (lead_user_id, color, response_target_seconds, resolution_target_seconds, escalation_chain JSONB, queues JSONB) — verified live:

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

## 3. REST API endpoints — exercised live with real OTRS queues

Using `D:\SLA_test` queue names verbatim.

```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"admin","password":"admin123"}' \
  -H 'Content-Type: application/json' | jq -r .access_token)
```

### Favorites

```
POST /favorites/queues  {queue_name:"MBR-137-ServiceDesk"}    →  ★ stored
POST /favorites/queues  {queue_name:"MBR-137-1C-Alfa-Auto"}   →  ★ stored
POST /favorites/queues  {queue_name:"MBR-137-Network"}        →  ★ stored
POST /favorites/queues  {queue_name:"MBM_RU_AppSupport"}      →  ★ stored
POST /favorites/queues  {queue_name:"AZM-717-AssetManagement_Esipovo_L2"}
```

DB cross-check:

```
sla_platform=> SELECT COUNT(*) FROM favorite_queues
               WHERE user_id = '335c771b-79e7-4821-977b-7bdcedef8a95';
 count
-------
     5
```

`GET /favorites/queues` returned all 5 rows sorted by `position`. `position` auto-incremented per insert. `starred_at` populated server-side.

### Queue Groups

```
POST /favorites/groups  {
  name:"Critical Infra", color:"#b42333",
  queues:["MBR-137-ServiceDesk","MBR-137-Network",
          "MBR-137-DC-WintelOperations","MBR-137-DC-StorageOperations"]
}
→ id: 922d42eb-8dfa-4112-9bc7-23547bf79eda
  queue_count: 4
  is_shared: false  (user-private)
```

DB:

```
sla_platform=> SELECT 'queue_groups', COUNT(*) FROM queue_groups
              UNION ALL SELECT 'queue_group_items', COUNT(*) FROM queue_group_items;
        ?column?    | count
--------------------+-------
 queue_groups       |     1
 queue_group_items  |     4
```

`PATCH /favorites/groups/{id}` accepts partial updates including full `queues` replacement (transactionally deletes + reinserts items).

### Dashboard Presets (operational workspaces)

```
POST /favorites/presets  {
  name:"NOC View",
  workspace_kind:"noc",
  queue_group_id:"922d42eb-…",
  is_shared:true,
  layout:{widgets:["breach","mtta","mttr","stagnation"]}
}
→ id: f6c69901-3114-…
  is_default: false
```

Five built-in workspace kinds shipped (`noc`, `servicedesk`, `infra`, `sap`, `executive`, plus `custom`).

`POST /favorites/presets/{id}/default` performs the demote-then-promote in a single transaction so only one preset per user is default.

---

## 4. Server-side queue-scoped analytics — verified live

`GET /dashboards/overview` now accepts repeated `?queue=A&queue=B`. Live test:

| Filter | total_tickets | sla_total | sla_breached | breach % |
|---|---:|---:|---:|---:|
| (none) | 1638 | 30378 | 3181 | 10.47% |
| `queue=MBR-137-ServiceDesk&queue=MBR-137-1C-Alfa-Auto&queue=MBR-137-Network` | 463 | 13202 | 1438 | 10.89% |
| `queue=MBR-137-ServiceDesk&queue=MBR-137-Network` | 368 | 10324 | — | — |

`tickets_by_queue` correctly returns only the scoped queues in the response.

The same `?queue=` list-style filter goes through the nginx proxy on `:80` correctly (verified — that was the path the SPA actually uses).

---

## 5. Axios list-param serializer fix

Default axios serializes `{queue: ['A','B']}` to `queue%5B%5D=A&queue%5B%5D=B` (i.e. `queue[]=A&queue[]=B`). FastAPI's `Query(default=[])` parses only `queue=A&queue=B`. Without intervention every list-param filter would silently fail.

Added a global `paramsSerializer` to `frontend/src/api/client.ts`:

```ts
paramsSerializer: {
  serialize: (params) => {
    const usp = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined || v === null) continue;
      if (Array.isArray(v)) v.forEach(i => usp.append(k, String(i)));
      else usp.append(k, String(v));
    }
    return usp.toString();
  },
},
```

Verified: live overview request `?queue=…&queue=…` returns correctly scoped numbers via nginx.

---

## 6. Frontend — what shipped

- **`/favorites`** page with 3 tabs: Favorites (drag-friendly list), Groups (CRUD + apply-as-filter), Workspaces (CRUD + "Apply" applies the group's queue list as the global filter).
- **`FavoritesContext`** wires localStorage persistence for both the active filter and the "favorites-only" mode toggle. Optimistic updates on star/unstar.
- **`QueueStarButton`** drop-in component — star icon goes wherever a queue name appears.
- **Sidebar entry** "Избранное" with a gold star icon, placed second in the nav so analysts can switch quickly.
- **Dashboard** subscribes to `useFavorites()` and passes `activeFilter` through to `dashboardsApi.overview({ days, queue })` — when nothing is starred, behavior is unchanged.

Live frontend rebuild produced `Favorites-CMlG63a8.js` in `/usr/share/nginx/html/assets/` — confirmed in container.

---

## 7. What was NOT verified

- **Browser-rendered DOM** — no browser in sandbox. The user can confirm the `/favorites` page visually by hitting `http://localhost/favorites` after login.
- **Drag-to-reorder** in the favorites table — the API supports `PUT /favorites/queues/reorder` but the Antd `Table` row drag is not wired in this release.
- **Forensic endpoints scoped by queue filter** — only `/dashboards/overview` was wired. Forensics endpoints accept `queue` filter at the query-string level but the V3 summary builder uses its own SQL and doesn't currently honor it. Filed as follow-up.

---

## 8. Reproducibility

```bash
# Migration applied?
docker exec sla-platform-postgres-1 psql -U sla_user -d sla_platform -c \
  "SELECT version_num FROM alembic_version"

# Star a queue:
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"admin","password":"admin123"}' \
  -H 'Content-Type: application/json' | jq -r .access_token)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"queue_name":"MBR-137-DC-WintelOperations"}' \
  http://localhost:8000/api/v1/favorites/queues

# Verify it persisted:
docker exec sla-platform-postgres-1 psql -U sla_user -d sla_platform -c \
  "SELECT queue_name, position, starred_at FROM favorite_queues ORDER BY position"

# Scoped dashboard:
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/dashboards/overview?days=30&queue=MBR-137-ServiceDesk" \
  | jq '.total_tickets, .sla_total'
```
