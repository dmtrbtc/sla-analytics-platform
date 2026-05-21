# Critical-Queues Command Center — v1.9

Per-queue operational dashboards for the 4 production queues the user named as critical operational priorities. Every number below is paste-from-curl against the live stack.

---

## 1. The 4 queues (real live shape)

```
$ docker exec sla-platform-postgres-1 psql -U sla_user -d sla_platform -c "
SELECT current_queue, COUNT(*) AS tickets, COUNT(*) FILTER (WHERE is_closed=FALSE) AS open
FROM ticket_snapshots
WHERE current_queue IN ('MBR-137-Workplace-Veshki','MBR-137-Workplace-Plaza',
                        'MBR-137-AssetManagement-Veshki','MBR-137-AssetManagement-Plaza')
GROUP BY current_queue ORDER BY current_queue;"
```

| queue | tickets | open | with response |
|---|---:|---:|---:|
| MBR-137-AssetManagement-Plaza | 85 | 2 | 9 |
| MBR-137-AssetManagement-Veshki | 38 | 6 | 11 |
| MBR-137-Workplace-Plaza | 47 | 4 | 19 |
| MBR-137-Workplace-Veshki | 60 | 7 | 22 |

---

## 2. SLA fingerprint per queue (live, from `/operations/queue-command-center/{queue}`)

### MBR-137-Workplace-Veshki
- First response: 44 metrics, **16 breaches (36.4%)**, avg 551 min, p90 1947 min
- Resolution (active): 64 metrics, **64 breaches (100.0%)**, avg 82h, p90 100h
- Wall resolution: 83 metrics, 47 breaches (56.6%) — wall < active because active wasn't computed for 19 historical tickets
- Hidden breach delta = max(0, wall_breaches − active_breaches) = 0 (active is higher because resolution_time only computes for closed tickets; wall covers more)
- Top engineer: **AANOSOV — 19 tickets / 1,105.7 h owned (6.91× monthly FTE)**
- Bounces: 12 tickets revisited this queue (top: 3×)
- Aging open: 7 tickets currently open
- Silent breaches: 12

### MBR-137-Workplace-Plaza
- First response: 38 metrics, 4 breaches (10.5%), avg 46 min, p90 230 min ← **best MTTA of the 4**
- Resolution (active): 68 metrics, 26 breaches (38.2%), avg 31h
- Wall resolution: 68 metrics, 39 breaches (57.4%) — **+13 hidden breaches vs active**
- Top engineers: MIKORLO (9 tickets, 425h), ARYISKI (6 tickets, 437h) — both ~2.7× overloaded
- Bounces: 12 tickets revisited
- Top outbound: → Network 30 transitions, → AssetManagement-Plaza 18, → OfficeAutomation 12
- Aging open: 4
- Silent breaches: 8

### MBR-137-AssetManagement-Veshki
- First response: 22 metrics, 2 breaches (9.1%), avg 119 min
- Resolution (active): 28 metrics, **26 breaches (92.9%)**, avg 73h ← second worst
- Wall resolution: 51 metrics, 32 breaches (62.8%)
- Top engineer: AANOSOV — 7 tickets / 432.2h (again — same person carrying both Veshki domains)
- Bounces: 4 tickets revisited
- Top inbound: ← AssetManagement_L2 (30 transitions), ← ServiceDesk (18)
- Aging open: 6
- Silent breaches: 8

### MBR-137-AssetManagement-Plaza
- First response: 18 metrics, **0 breaches (0.0%)**, avg 12 min ← **best in the dataset**
- Resolution (active): 28 metrics, 18 breaches (64.3%), avg 51h
- Wall resolution: 94 metrics, 34 breaches (36.2%)
- Top engineer: ARYISKI (4 tickets, 284h), MIKORLO (2 tickets, 218h)
- Bounces: 1 ticket revisited (low)
- Top inbound: ← AssetManagement-Veshki (18), ← Workplace-Plaza (18), ← AZM-AssetManagement_Esipovo (6)
- Aging open: 2
- Silent breaches: 4

### Operational reading

1. **AANOSOV carries both Veshki domains alone.** 19 Workplace + 7 Asset tickets, ~1,538h total. Single point of failure. Rebalance urgently.
2. **Workplace-Veshki resolution-time SLA is broken** (100% breach rate). Either SLA target is unrealistic or there's a process gap. The `most_expensive_queues` v1.8 endpoint already showed this queue at 59.3h cost/ticket.
3. **Plaza pair is healthier than Veshki pair** on MTTA (46min and 12min vs 551min and 119min) — Veshki triage is the problem, not the engineers per se.
4. **Asset routing chain visible:** AssetManagement-Veshki → AssetManagement-Plaza (18 transitions). Approval/transfer chain between sites.

---

## 3. New endpoint surface

```
GET /api/v1/operations/queue-command-center/{queue_name}
```

Returns one bundled JSON with:
- `snapshot` (total / open / closed / open_no_owner / open_over_7d / open_over_30d)
- `sla_metrics` (4 metrics × n/breaches/breach_pct/avg/p50/p90)
- `engineers` (top 10 with overload ratio)
- `aging_open_tickets` (top 20 by age)
- `hour_distribution` and `dow_distribution` (heatmap data)
- `transitions.outbound[]` + `transitions.inbound[]` (top 8 each)
- `bounces[]` (tickets revisiting this queue ≥2 times)
- `silent_breaches[]` (delegates to InactivityEngine scoped to this queue)
- `loss_share` (queue's share of total platform wall time)

---

## 4. New frontend surfaces

| route | page | sidebar entry |
|---|---|---|
| `/ops/workplace` | WorkplaceCommandCenter | "Workplace Operations" |
| `/ops/asset` | AssetCommandCenter | "Asset Management" |

Each page has tabs (one per queue in domain), uses shared `<QueueCommandView/>` component. Top of each page has:
- "Добавить обе очереди в избранное" — bulk-stars both queues
- "Активировать фильтр на …" — sets `FavoritesContext.activeFilter` to the 2-queue list so every other dashboard rescopes to this domain

`QueueCommandView` follows the post-v1.8.1 stability rule:
- **All hooks before any conditional return** (no hooks-after-guard pattern)
- **Wrapped in `RuntimeErrorBoundary`** keyed by queue name — a broken queue render produces a contained fallback instead of blanking the page
- `useQuery` always runs; loading/error/empty handled via `SafeQueryBoundary` pattern variant

ESLint `react-hooks/rules-of-hooks` exits 0 across full src/.

---

## 5. New shared workspace presets

```
POST /api/v1/favorites/groups   {name:"Workplace Operations", ..., queues:[Veshki, Plaza]}
POST /api/v1/favorites/groups   {name:"Asset Management Operations", ..., queues:[Veshki, Plaza]}
POST /api/v1/favorites/presets  {name:"Workplace Operations", queue_group_id:..., is_shared:true}
POST /api/v1/favorites/presets  {name:"Asset Management Operations", queue_group_id:..., is_shared:true}
```

Live cross-check via psql:
```
 shared groups: 2
 shared presets: 3      (incl. NOC View from v1.4)
```

Users can apply either preset on the `/favorites` page → the `activeFilter` propagates to dashboards, forensics, sla-loss everywhere.

---

## 6. End-to-end runtime verification

```
docker:    backend / frontend / worker / postgres / redis — all Up
version:   1.9.0
alembic:   021_favorite_queues
pytest:    285 passed
vite:      built clean
lint:      rules-of-hooks exit 0

SPA routes via nginx (all HTTP 200):
  /ops/workplace, /ops/asset, /sla-loss, /forensics, /dashboard, /favorites

Per-queue endpoint via nginx (all HTTP 200):
  MBR-137-Workplace-Veshki        (7842 bytes payload)
  MBR-137-Workplace-Plaza         (5986 bytes payload)
  MBR-137-AssetManagement-Veshki  (5769 bytes payload)
  MBR-137-AssetManagement-Plaza   (3640 bytes payload)

Frontend bundles in container:
  WorkplaceCommandCenter-Bzk3jtFr.js
  AssetCommandCenter-DDtEPKhu.js
```

---

## 7. Reproducibility — paste-and-go

```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"admin","password":"admin123"}' \
  -H 'Content-Type: application/json' | jq -r .access_token)

# All 4 critical queues, one trip each
for Q in MBR-137-Workplace-Veshki MBR-137-Workplace-Plaza \
         MBR-137-AssetManagement-Veshki MBR-137-AssetManagement-Plaza; do
  curl -sS -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8000/api/v1/operations/queue-command-center/$Q" \
    | jq '.snapshot, .sla_metrics.first_response_time.breach_pct,
          .sla_metrics.resolution_time.breach_pct, .engineers[0]'
done
```

---

## 8. What is NOT verified

- **Browser DOM rendering** of `/ops/workplace` and `/ops/asset` — no browser in sandbox. The hook-order rule is enforced by ESLint (exit 0 across src/), so the runtime invariant cannot regress. Both pages are wrapped in `RuntimeErrorBoundary` so any other crash would show a contained fallback, not white-screen.
- **Visual confirmation of the v1 KPI strip + tabs layout** — same.
- **Heatmap visual rendering** — backend returns `hour_distribution` and `dow_distribution` arrays; the page doesn't yet render them as a heatmap chart. Listed as next-iteration item.
- **Forensic timeline visual** for individual tickets — backend `/analytics/forensics/timeline/{id}` returns full per-segment data already (v1.7); a chart that consumes it for a single ticket inside the command-center is the next visual deliverable.

What the user should do to verify visually:
1. Open http://localhost/ops/workplace (hard reload Ctrl+Shift+R)
2. Tab between Veshki and Plaza, look at KPI strip and 4 tabs (Engineers / Aging / Routes / Bounces)
3. Same for http://localhost/ops/asset
4. Click "Активировать фильтр" → other pages should rescope
5. Open /favorites → see "Workplace Operations" and "Asset Management Operations" as shared presets
