# Forensic Time-Scope System — v2.1.0

Every analytics endpoint now accepts a temporal scope (`24h / 7d / 30d / 90d / custom`) and computes **overlap-aware** contributions on durational records — not naive `created_at` filtering.

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
?period=24h | 7d | 30d | 90d | 365d
?since=<ISO datetime>
?until=<ISO datetime>
```

| endpoint | overlap math? |
|---|---|
| `GET /analytics/sla-loss/top-queues` | ✓ on `queue_periods` + `ownership_periods` |
| `GET /analytics/sla-loss/most-expensive` | ✓ on `queue_periods` |
| `GET /analytics/sla-loss/dying-in-queue` | ✓ on `queue_periods` |
| `GET /analytics/sla-loss/parking-lots` | ✓ on `ownership_periods` |
| `GET /analytics/sla-loss/overview` | ✓ — bundles all 4 above |
| `GET /operations/review/overview` | ✓ — delegates to SLALossEngine; hidden-breach delta filters `computed_at` |

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
- Plumbing into `/dashboards/overview`, `/operations/queue-command-center/{q}`, `/analytics/forensics/*`, `/operations/engineer-load`, `/operations/comparison` — those endpoints still use the old all-time aggregation. The pattern is now established; each endpoint is a 3-line change (add `parse_time_scope` + `scope=` arg). Deferred to a focused follow-up to keep this commit reviewable.

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
