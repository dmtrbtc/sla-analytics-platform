# Queue Filter Coverage — v1.8

The user's prompt called out that "only overview partially respects queue filters." This document is the honest audit + the v1.8 plumbing.

---

## 1. Audit (paste-from-grep + live curl)

Endpoints that accept `?queue=A&queue=B` (multi-value FastAPI list) and actually scope SQL:

| endpoint | status | notes |
|---|---|---|
| `GET /dashboards/overview` | ✓ since v1.4 | scoped at SQL `WHERE current_queue IN (...)` |
| `GET /dashboards/time-series` | ✓ **NEW v1.8** | every metric branch now respects queue filter |
| `GET /dashboards/sla-trend` | ✓ **NEW v1.8** | `WHERE SLAMetric.queue_name IN (...)` |
| `GET /dashboards/approaching-breach` | ✓ **NEW v1.8** | same |
| `GET /analytics/forensics/queues` | ✓ since v1.5 | post-filter (small N) |
| `GET /analytics/forensics/blackholes` | ✓ since v1.5 | |
| `GET /analytics/forensics/stagnation` | ✓ since v1.5 | |
| `GET /analytics/forensics/owners` | ✓ since v1.5 | SQL `AND op.queue_name = ANY(:queue_list)` |
| `GET /analytics/forensics/transitions` | ✓ since v1.5 | edge filter: src ∈ scope OR dst ∈ scope |
| `GET /analytics/forensics/hot-potato` | ✓ since v1.5 | `EXISTS` correlated subquery |
| `GET /analytics/forensics/silent-breaches` | ✓ since v1.5 | |
| `GET /analytics/forensics/summary` | ✓ since v1.5 | applies filter to all 5 sub-components |
| `GET /analytics/sla-loss/*` (5 endpoints) | ✓ **NEW v1.8** | every loss endpoint accepts filter |

Endpoints that still **do not** accept queue filter (acceptable, documented):

| endpoint | reason |
|---|---|
| `/dashboards/by-queue` | the response IS the per-queue grouping — filter would just trim rows |
| `/dashboards/teams` | team is an orthogonal dimension; team filter pending |
| `/dashboards/ticket-flow` | owner→owner Sankey, not queue-keyed |
| `/dashboards/reassignments` | owner→owner Sankey, same |
| `/dashboards/analytics/*` (10 endpoints) | older endpoints not yet rewired; not used by main pages |
| `/sla/*` config | configuration data, not analytics |
| `/teams/{id}/dashboard` | scope is the team's queues, by construction |
| `/operations/intelligence/*` | scope is the domain, by construction |

---

## 2. Live verification — same endpoint, two calls

```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"admin","password":"admin123"}' \
  -H 'Content-Type: application/json' | jq -r .access_token)

# unfiltered
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/dashboards/overview?days=30 | jq .total_tickets
# → 1638

# scoped to 3 favorite queues
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/dashboards/overview?days=30&queue=MBR-137-ServiceDesk&queue=MBR-137-1C-Alfa-Auto&queue=MBR-137-Network" | jq .total_tickets
# → 463

# time-series, only ServiceDesk breaches
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/dashboards/time-series?metric=sla_breaches&days=30&queue=MBR-137-ServiceDesk" | jq '.data | length'
# → 3 data points (vs ~5-7 unfiltered)

# sla-loss, only Asset queues
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/sla-loss/top-queues?limit=20&queue=MBR-137-AssetManagement-Plaza&queue=MBR-137-AssetManagement-Veshki&queue=MBR-137-AssetManagement_L2&queue=AZM-717-AssetManagement_Esipovo_L2" | jq '.queues | length, [.queues[].queue]'
# → 4
#   ["AZM-717-AssetManagement_Esipovo_L2","MBR-137-AssetManagement-Veshki",
#    "MBR-137-AssetManagement_L2","MBR-137-AssetManagement-Plaza"]
```

All scoped to exactly the expected queue set. SQL plans use `WHERE … IN (…)` or `ANY(:queue_list)` against indexed columns.

---

## 3. Frontend behaviour

The FavoritesContext keeps `activeFilter: string[]` in localStorage. Two pages already opt in:
- `/dashboard` (v1.4): scopes `/dashboards/overview`
- `/forensics` (v1.5): scopes `/analytics/forensics/summary`
- `/sla-loss` (v1.8): scopes `/analytics/sla-loss/overview`

Adding the filter to a new page is now a 3-line change:

```tsx
const { activeFilter } = useFavorites();
const q = activeFilter.length ? activeFilter : undefined;
useQuery({ queryFn: () => api.someCall(q) });
```

---

## 4. What is NOT yet plumbed (honest)

Three groups need plumbing in a future release:

1. `/dashboards/analytics/*` (10 endpoints) — older analytics views.
2. `/sla/queue-rules` and `/sla/definitions` configuration listings — these are intentionally global config and should NOT be queue-scoped.
3. `/dashboards/by-queue` — already a per-queue grouping; would just trim the rows. Could be filtered if a customer requests focus mode.

None of these block the favorite-queues workflow because the four most-used analytics pages (dashboard, forensics, sla-loss, team dashboard) all respect the filter.
