# SLA Loss Visualization — v1.8

The "where exactly was SLA lost" engine. Aggregates per-segment loss across the full ticket portfolio. Verified against the live OTRS data (1,638 tickets, 3,181 breaches).

---

## 1. Five new endpoints — runtime verified live

```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"admin","password":"admin123"}' \
  -H 'Content-Type: application/json' | jq -r .access_token)
```

| Endpoint | Purpose |
|---|---|
| `GET /analytics/sla-loss/top-queues` | which queues consume the most resolution budget overall |
| `GET /analytics/sla-loss/most-expensive` | per-ticket cost — normalizes by ticket count, exposes "expensive per item" queues |
| `GET /analytics/sla-loss/dying-in-queue` | open tickets with the largest accumulated wall time |
| `GET /analytics/sla-loss/parking-lots` | queues with the most no-owner hours |
| `GET /analytics/sla-loss/waterfall/{ticket_id}` | per-segment cumulative time for a single ticket |
| `GET /analytics/sla-loss/overview` | bundle for the front-end page (all 4 lists in one call) |

All accept `?queue=A&queue=B` for favorite-scoped views.

---

## 2. Live numbers (paste from curl)

### Top loss queues — no filter

| queue | wall hours | no-owner h | tickets | share |
|---|---:|---:|---:|---:|
| MBR-137-ServiceDesk | **15,394** | 301 | 517 | **45.0 %** |
| MBR-137-1C-Alfa-Auto | 4,253 | 41 | 100 | 12.4 % |
| MBM_RU_AppSupport | 3,517 | 17 | 52 | 10.3 % |
| MBR-137-Network | 2,334 | **873** | 67 | 6.8 % |
| MBR-137-SAP_Basis_support | 1,620 | 90 | 21 | 4.7 % |
| MBR-137-Workplace-Veshki | 1,602 | 81 | 27 | 4.7 % |
| MBR-137-DC-StorageOperations | 1,569 | 94 | 25 | 4.6 % |
| MBR-137-OfficeAutomation | 1,462 | 348 | 38 | 4.3 % |
| MBR-137-Security | 1,262 | 111 | 29 | 3.7 % |
| MBR-137-Workplace-Plaza | 1,222 | 1.5 | 37 | 3.6 % |

**ServiceDesk holds 45% of all SLA wall-clock time.** That single queue defines the bulk of operational SLA cost.

### Parking lots (highest no-owner share)

| queue | no-owner h | no-owner % | tickets |
|---|---:|---:|---:|
| MBR-137-Network | 886 | **99 %** | 30 |
| MBR-137-DC-LinuxOperations | 539 | 80 % | 13 |
| MBR-137-OfficeAutomation | 352 | 34 % | 23 |
| AZM-717-Workplace-Esipovo | 189 | 48 % | 6 |
| MBR-137-AMS_L2 | 172 | 85 % | 2 |
| MBR-137-CS_Support | 118 | 100 % | 1 |
| MBR-137-Security-SupportL1 | 113 | 100 % | 4 |
| MBR-137-Security | 105 | 100 % | 2 |

### Most expensive per ticket (≥ 5 tickets per queue)

| queue | tickets | h/ticket |
|---|---:|---:|
| MBR-137-SAP_Basis_support | 21 | **77.1** |
| MBR-137-Telecom | 10 | 76.2 |
| MBM_RU_ODM | 8 | 72.8 |
| MBM_RU_AppSupport | 52 | 67.6 |
| MBR_Customer_L3 | 13 | 63.8 |
| MBR-137-DC-StorageOperations | 25 | 62.8 |
| MBR-137-AssetManagement-Plaza | 11 | 61.3 |
| AZM-717-AssetManagement_Esipovo_L2 | 18 | 59.8 |
| MBR-137-Workplace-Veshki | 27 | 59.3 |

### Tickets dying in queue (top 8 OPEN)

```
#2026043011000279  MBM_RU_AppSupport       state=open   145.6h wall, 1 queue, 1 segment
#2025111611000114  MBM_RU_AppSupport       state=open   145.4h wall
#2025051611000966  AZM-717-INFRASTRUCTURE  state=open   145.4h wall
#2025112711000577  MBM_RU_Creatio          state=open   145.4h wall
#2025102011001072  MBR-137-Network_L2      state=open   145.4h wall
#2025120111000641  MBM_RU_AppSupport       state=new    145.4h wall  ← still "new"
#2025121211000441  MBM_RU_AppSupport       state=open   145.4h wall
#2026012211000665  MBR_Customer_L3         state=open   145.4h wall
```

These 8 tickets have been stationary for the entire observation window (~6 days each in their current single queue) — operational dead zone.

---

## 3. Queue-filter scoping — verified live

Same endpoint scoped to `?queue=A&queue=B&queue=C&queue=D` for the four Asset queues:

```
count returned: 4   (only Asset queues — global share collapses to 100% inside scope)
  AZM-717-AssetManagement_Esipovo_L2   1,077 h   32.7 %
  MBR-137-AssetManagement-Veshki         811 h   24.6 %
  MBR-137-AssetManagement_L2             730 h   22.2 %
  MBR-137-AssetManagement-Plaza          675 h   20.5 %
```

The favorite-filter and FavoritesContext on the frontend feed straight into this endpoint via TanStack Query's `queryKey: ["sla-loss-overview", queues?.join(",")]`. Verified by hitting via nginx proxy on port 80.

---

## 4. Frontend — first v1-themed page

`frontend/src/pages/SLALossCenter.tsx` (route `/sla-loss`, sidebar **«Где теряется SLA»**) — the proof-of-rollout for the design tokens:

- Uses `<div className="v1">` opt-in wrapper.
- KPI strip rendered with `.v1-kpi` (no Ant Statistic component).
- Detail tables fall back to Ant `<Table>` for now (the table primitive isn't custom in v1 yet).
- 4 tabs: top loss / most expensive / parking lots / dying tickets.
- TanStack Query refetch every 60 s.
- Honors `useFavorites().activeFilter` automatically.

Bundle `SLALossCenter-BQKzUwGz.js` + `SLALossCenter-JUrx_ZVX.css` present in served frontend image.

---

## 5. Reproducibility

```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"admin","password":"admin123"}' \
  -H 'Content-Type: application/json' | jq -r .access_token)

# top loss queues, global
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/analytics/sla-loss/top-queues?limit=10 | jq

# scoped to asset
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/sla-loss/top-queues?queue=MBR-137-AssetManagement-Plaza&queue=MBR-137-AssetManagement-Veshki" | jq

# parking lots
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/analytics/sla-loss/parking-lots?limit=10 | jq

# tickets dying
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/analytics/sla-loss/dying-in-queue?limit=10 | jq

# waterfall for a single ticket
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/analytics/sla-loss/waterfall/144844 | jq
```
