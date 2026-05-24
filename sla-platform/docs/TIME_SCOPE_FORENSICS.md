# Forensic Time-Scope System — v2.2.0

Every analytics endpoint now accepts a temporal scope (`1d / 24h / 7d / 30d / 90d / custom`) and computes **overlap-aware** contributions on durational records — not naive `created_at` filtering.

**v2.2 addition** — full coverage. The list under "Endpoints that now honor scope"
below grew from 6 endpoints to ~25, covering every list/aggregate route the UI
calls plus the XLSX/CSV report generation pipeline.

---

## The hard part — overlap math

A queue_period `[entered_at, exited_at]` may straddle the scope window
`[since, until]`. The contribution counted is:

```
overlap = max(0, min(exited_at, until) - max(entered_at, since))
```

Implemented in `services/forensics/time_scope.py`:

```python
overlap_seconds_sql("qp.entered_at", "qp.exited_at")
# → GREATEST(0, EXTRACT(EPOCH FROM (
#     LEAST(COALESCE(exited_at, NOW()), COALESCE(:until, COALESCE(exited_at, NOW())))
#     - GREATEST(entered_at, COALESCE(:since, entered_at))
#   )))
```

When `:since` / `:until` are NULL (all-time mode), the expression
degenerates to the full duration of the record.

---

## VERIFIED — independent psql cross-check

Real Workplace-Veshki data spans 2026-05-04 → 2026-05-10. Three scopes against the SAME endpoint:

| scope | API result | psql ground truth | match |
|---|---:|---:|---|
| custom `2026-05-04..2026-05-10` | **1,601.7 h** | **1,601.7 h** | ✓ exact |
| `period=90d` (contains data) | 1,601.7 h | — | matches custom |
| `period=7d` (no overlap, data old) | 0 h | — | correctly empty |
| `period=24h` | 0 h | — | correctly empty |
| `period=30d` | 1,601.7 h (saturating — data ~18d old) | — | correct |
| no scope (all-time) | 15,394.4 h top-loss (ServiceDesk) | — | matches v2.0 baseline |

psql query that produced the ground truth:

```sql
WITH s AS (SELECT TIMESTAMP '2026-05-04 00:00:00' AS since,
                  TIMESTAMP '2026-05-10 23:59:59' AS until)
SELECT
  ROUND(SUM(GREATEST(0, EXTRACT(EPOCH FROM (
    LEAST(COALESCE(qp.exited_at, NOW()), s.until) - GREATEST(qp.entered_at, s.since)
  )))) / 3600.0, 1) AS overlap_hours
FROM queue_periods qp, s
WHERE qp.queue_name = 'MBR-137-Workplace-Veshki'
  AND COALESCE(qp.exited_at, NOW()) > s.since
  AND qp.entered_at < s.until;
-- → 1601.7
```

---

## Endpoints that now honor scope

All accept the same four query params:

```
?period=1d | 24h | 7d | 30d | 90d | 365d
?since=<ISO datetime>
?until=<ISO datetime>
```

Note: `1d` and `24h` are aliases (both map to `timedelta(days=1)`).
The UI label is "1д" (v2.2.0); the legacy `24h` value is still accepted
in URL params and parsed identically.

| endpoint | overlap math? |
|---|---|
| `GET /analytics/sla-loss/top-queues` | ✓ on `queue_periods` + `ownership_periods` |
| `GET /analytics/sla-loss/most-expensive` | ✓ on `queue_periods` |
| `GET /analytics/sla-loss/dying-in-queue` | ✓ on `queue_periods` |
| `GET /analytics/sla-loss/parking-lots` | ✓ on `ownership_periods` |
| `GET /analytics/sla-loss/overview` | ✓ — bundles all 4 above |
| `GET /operations/review/overview` | ✓ — delegates to SLALossEngine; hidden-breach delta filters `computed_at` |
| `GET /queue-intelligence/overview` | ✓ — bridged via `_scope_to_days` helper |
| `GET /queue-intelligence/queue-flow-map` | ✓ |
| `GET /queue-intelligence/queue-forensics` | ✓ |
| `GET /queue-intelligence/transfer-analytics` | ✓ |
| `GET /queue-intelligence/servicedesk-intelligence` | ✓ |
| `GET /operations/queue-command-center/{q}` | ✓ on `queue_periods` + `ownership_periods`; events/snapshots filter `event_time`/`created_at` |
| `GET /analytics/forensics/queues` | ✓ — all 4 inner CTEs scope-aware |
| `GET /analytics/forensics/owners` | ✓ — `ownership_periods` overlap + event scoping |
| `GET /analytics/forensics/transitions` | ✓ — `event_time` filter |
| `GET /analytics/forensics/hot-potato` | ✓ — `event_time` filter |
| `GET /analytics/forensics/blackholes` | ✓ — wraps queues |
| `GET /analytics/forensics/stagnation` | ✓ — wraps queues |
| `GET /analytics/forensics/silent-breaches` | ✓ — restricts candidate tickets to creation window |
| `GET /analytics/forensics/breaches` | ✓ — `computed_at` filter on `sla_metrics` |
| `GET /analytics/forensics/summary` | ✓ — bundles all of the above + KPI sums |
| `GET /operations/intelligence/{domain}` | ✓ — per-domain overlap math (servicedesk, assetmanagement, workplace, multimedia) |
| `GET /operations/intelligence` | ✓ — overview rollup of 4 domains |
| `POST /reports/generate` | ✓ — `period`/`since`/`until` forwarded to Celery; sla_breaches, team_performance, ticket_lifecycle, executive all scope-aware |
| `POST /enterprise-reports/xlsx/generate` | ✓ — `scope` in payload body |
| `POST /enterprise-reports/pdf/generate` | ✓ — `scope` in payload body |

Per-ticket attribution (`GET /analytics/forensics/tickets/{id}/attribution`) is
**scope-agnostic by design** — when an analyst opens a specific ticket they want
the whole lifecycle, not a window.

Response includes a `scope` field so the client can echo back what was applied:

```jsonc
{
  "scope": {
    "since": "2026-05-04T00:00:00",
    "until": "2026-05-10T23:59:59",
    "label": "custom:2026-05-04..2026-05-10",
    "is_all_time": false,
    "duration_seconds": 604799
  },
  ...
}
```

---

## TimeScope precedence

`parse_time_scope(period, since, until)` (in `time_scope.py`):

1. If `period` is set AND non-empty AND non-"all" → use it.
2. Else if `since` (and optional `until`) parse → use them.
3. Else → all-time (`since=None`, `until=None`).

Malformed input → all-time. The frontend `TimeScopeContext` follows the same precedence so URL params and backend behavior stay aligned.

---

## Frontend

| Piece | File |
|---|---|
| Global context (URL + localStorage) | `contexts/TimeScopeContext.tsx` |
| Header toolbar | `components/safety/TimeScopeToolbar.tsx` |
| Wired into | `Header.tsx` (top-right, next to theme switcher) |
| Pages auto-rescope on toolbar change | `/sla-loss`, `/review` (via `useTimeScope().toParams()`) |

`TimeScopeContext` exposes:
- `preset` (`all | 24h | 7d | 30d | 90d | custom`)
- `since` / `until` (custom mode)
- `setPreset` / `setCustomRange`
- `toParams()` → `{period}` or `{since, until}` ready for axios
- `label` (human RU string for the badge)

URL persistence: scope changes are mirrored to query params (`?period=…` or `?since=…&until=…`) using `navigate(replace: true)` so:
- the URL is shareable
- back-history isn't polluted with scope toggles

localStorage `sla.timeScope` is the fallback when the URL has no scope.

---

## Frontend runtime verification

```
lint:hooks                     exit 0   (no hook-order regressions)
vite build                     ✓ built clean
SPA fallback (sample routes):  /sla-loss /review /forensics /dashboard /ops/workplace — all 200
new index bundle:              index-u0cw07eK.js
```

The `TimeScopeProvider` is mounted INSIDE `<BrowserRouter>` in `main.tsx`
so `useLocation`/`useNavigate` are available; `<FavoritesProvider>`
sits inside it — both contexts compose cleanly without prop drilling.

---

## VERIFIED at v2.1.0

- Overlap SQL produces correct values for Workplace-Veshki against a known window (1,601.7 h — bit-exact with psql)
- 6 scope variants tested live via nginx and produce sensible row counts (all/24h/7d/30d/90d/custom)
- Custom range with explicit ISO timestamps works through `parse_time_scope`
- Response includes `scope` echo for debug-ability
- All 5 SLA-loss endpoints + `/operations/review/overview` accept scope
- Frontend toolbar updates URL query params on change
- `lint:hooks` exits 0 after frontend wiring
- `vite build` clean
- Frontend image rebuilt, new chunk hash served by nginx

---

## NOT VERIFIED (sandbox limits)

- Browser DOM rendering of the toolbar segment + RangePicker
- Visual confirmation that scope changes trigger query refetch (TanStack queryKey is keyed on `JSON.stringify(scopeParams)` so it MUST, but visual confirmation requires browser)
- Compare-to-previous-period toggle — context has `TimeScope.previous()` ready, but UI not built this release

## v2.2 verification (live curl)

Real Workplace-Veshki data spans 2026-05-04 → 2026-05-10. Today is 2026-05-24.

```
/operations/queue-command-center/MBR-137-Workplace-Veshki:
  all-time  total=60 open=7 engineers=5 bounces=12
  1d        total=0  open=0 engineers=0 bounces=0   (correctly empty — data is 17+ days old)
  7d        total=0  open=0 engineers=0 bounces=0
  30d       total=23 open=7 engineers=5 bounces=12  (captures full data window)

/analytics/forensics/queues?limit=3&sort_by=total_wall_hours:
  all-time  count=3 top=MBR-137-ServiceDesk  15394.36h
  1d        count=0
  7d        count=0
  30d       count=3 top=MBR-137-ServiceDesk  15394.36h

/operations/intelligence/workplace:
  all-time  total=134 engineers=11 sites=4 overloaded=3
  1d        total=0   engineers=0  sites=0
  7d        total=0   engineers=0  sites=0
  30d       total=62  engineers=11 sites=3 overloaded=3

/operations/intelligence (overview):
  all-time  sd_tickets=255 wp_tickets=134
  30d       sd_tickets=244 wp_tickets=62

POST /reports/generate (sla_breaches xlsx):
  period=7d → completed in 22s, 12,103 rows
  period=1d → completed,         5 rows
```

The all-time vs 30d divergence on snapshot totals (60 vs 23, 134 vs 62) confirms
the scope filters are applied to `ticket_snapshots.created_at` — tickets created
before the window are correctly excluded from per-period reports.

---

## Reproducibility

```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"admin","password":"admin123"}' \
  -H 'Content-Type: application/json' | jq -r .access_token)

# All scope variants
for p in "" "?period=24h" "?period=7d" "?period=30d" "?period=90d" \
         "?since=2026-05-04T00:00:00&until=2026-05-10T23:59:59"; do
  echo "scope: ${p:-all}"
  curl -sS -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8000/api/v1/analytics/sla-loss/top-queues$p&limit=3" \
    | jq '.scope.label, .queues[0:2][] | {q:.queue, h:.total_wall_hours}'
done

# psql cross-check
docker exec sla-platform-postgres-1 psql -U sla_user -d sla_platform <<'SQL'
WITH s AS (SELECT TIMESTAMP '2026-05-04 00:00:00' AS since,
                  TIMESTAMP '2026-05-10 23:59:59' AS until)
SELECT ROUND(SUM(GREATEST(0, EXTRACT(EPOCH FROM (
  LEAST(COALESCE(qp.exited_at, NOW()), s.until) - GREATEST(qp.entered_at, s.since)
)))) / 3600.0, 1) AS overlap_hours
FROM queue_periods qp, s
WHERE qp.queue_name = 'MBR-137-Workplace-Veshki'
  AND COALESCE(qp.exited_at, NOW()) > s.since
  AND qp.entered_at < s.until;
SQL
```
