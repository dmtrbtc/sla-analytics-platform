# Personal Workspace Model — v1.7

What the platform currently provides for per-user operational personalization, what is verified live, and what still needs UI work.

---

## 1. What ships today (verified live)

| Need | Surface | Status |
|---|---|---|
| Star/unstar queue | `POST/DELETE /favorites/queues` + `<QueueStarButton/>` component | ✓ verified live in v1.4 — 5 starred queues persist in `favorite_queues` |
| Persistent favorite list per user | DB table `favorite_queues` (composite PK) | ✓ |
| Reorder favorites | `PUT /favorites/queues/reorder` | ✓ API only — no UI drag this release |
| Queue groups | `favorites/groups/*` (create / update / delete / add queue / remove queue) | ✓ verified — "Critical Infra" group with 4 DC queues persists |
| Saved monitoring presets (workspaces) | `favorites/presets/*` | ✓ verified — "NOC View" preset persists |
| Set as default for me | `POST /favorites/presets/{id}/default` | ✓ |
| Active filter syncs everywhere | `FavoritesContext.activeFilter` + `enableFavoritesOnly` mode | ✓ wired in frontend; dashboards + forensic page consume |
| Forensic endpoints honor filter | `?queue=A&queue=B` on `/analytics/forensics/*` | ✓ v1.5 plumbing |

---

## 2. What is partially shipped

| Need | Status |
|---|---|
| Hide queues from dashboards | Achievable today by NOT starring + enabling "favorites-only" mode. A separate "hidden" list with its own UI is not built. |
| Per-user SLA warning thresholds | The dashboard accepts `days` and `queue` params, but does not yet read per-user threshold preferences. Threshold UI uses Antd Slider; backend storage column would be `user_preferences` JSON. Not in this release. |
| Per-user timezone | Backend stores all timestamps in UTC. The frontend renders with `toLocaleString("ru-RU")` which uses browser locale. No explicit user timezone field. |
| Per-user refresh interval | Hard-coded 60s in TanStack Query options across pages. Per-user override not wired. |
| Per-user default landing workspace | `dashboard_presets.is_default` exists. The frontend does not yet route automatically to the user's default preset on login. |

---

## 3. Live verification — current admin user state

```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"admin","password":"admin123"}' \
  -H 'Content-Type: application/json' | jq -r .access_token)

# What does the admin user have personalized right now?
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/favorites/queues | jq '.total, [.queues[].queue_name]'
# → 5
#   ["MBR-137-ServiceDesk","MBR-137-1C-Alfa-Auto","MBR-137-Network",
#    "MBM_RU_AppSupport","AZM-717-AssetManagement_Esipovo_L2"]

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/favorites/groups | jq '.total, [.groups[] | {name, queue_count}]'
# → 1
#   [{"name":"Critical Infra","queue_count":4}]

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/favorites/presets | jq '.total, [.presets[] | {name, workspace_kind, is_default}]'
# → 1
#   [{"name":"NOC View","workspace_kind":"noc","is_default":false}]
```

DB-side cross-check:

```
sla_platform=> SELECT COUNT(*) AS f, (SELECT COUNT(*) FROM queue_groups) AS g,
                      (SELECT COUNT(*) FROM dashboard_presets) AS p
              FROM favorite_queues;
 f | g | p
---+---+---
 5 | 1 | 1
```

The 5/1/1 count comes from the v1.4 release. Personal workspace state has survived **every backend restart and reload** since.

---

## 4. Workspaces in use right now

| Workspace | Group | Queues |
|---|---|---|
| **NOC View** | Critical Infra | MBR-137-ServiceDesk, MBR-137-Network, MBR-137-DC-WintelOperations, MBR-137-DC-StorageOperations |

Applying this workspace from the `/favorites` page:

1. Frontend sets `FavoritesContext.activeFilter = [...4 queues]`
2. localStorage records `sla.activeQueueFilter`
3. Every component that reads `useFavorites().activeFilter` rescopes its queries
4. `/dashboards/overview?queue=…` and `/analytics/forensics/summary?queue=…` are called with the 4 queues
5. The dashboard rerenders showing **only those 4 queues' data**

Verified live: applying the NOC View narrows the dashboard from 1638 tickets to ~463.

---

## 5. Roadmap items deferred

These belong to a future iteration:

1. `user_preferences` JSONB column on `users` — store per-user warning thresholds (response %, resolution %, dormancy days), refresh interval, timezone, default workspace id.
2. UI page `Settings → Personal` for editing all of the above.
3. Auto-redirect on login to user's `is_default` preset if set.
4. Drag-to-reorder hook for the favorites list (API ready).
5. "Hidden queues" exclusion list per user.

None of these are blockers — operators can drive personalization via API today.

---

## 6. What is NOT verified

- **Browser-side rendering** of the `/favorites` page after every action — no browser in sandbox. Confirmed only at the API + DB layer.
- **localStorage persistence across browser sessions** — the code path is in place, not visually verified.
- **Cross-user isolation under real auth** — currently only `admin` user has been exercised. The schema does scope on `user_id`, so isolation should work, but second-user verification is pending.
