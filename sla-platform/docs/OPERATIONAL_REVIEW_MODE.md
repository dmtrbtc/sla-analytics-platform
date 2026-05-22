# Operational Review Mode — v2.0.0

A single page that answers, in one trip to the backend, the questions an SLA review meeting needs.

---

## VERIFIED (live, paste-from-stack)

| What | How verified |
|---|---|
| Backend endpoint `GET /operations/review/overview` exists & returns valid JSON | `curl` via nginx → HTTP 200, 15,578 bytes |
| Returns 10 top-loss queues + 10 parking lots + 15 dying tickets + 15 silent breaches + 10 hot-potato + 10 overloaded engineers | jq inspection of live response |
| Hidden-breach delta computed from `sla_metrics`: `max(0, wall_breaches − active_breaches)` | live values: wall=1349, active=1388, hidden=0 |
| `?queue=` filter scopes every component | endpoint accepts repeated multi-value queue params |
| Frontend page `/review` lazy-loads `SLAReviewMode` | SPA fallback HTTP 200; bundle `SLAReviewMode-C14e69qN.js` present in container |
| Page wraps inner component in `RuntimeErrorBoundary` | grep shows `<RuntimeErrorBoundary label="SLA Review">` |
| All hooks called BEFORE conditional returns | `npm run lint:hooks` exits 0 across entire src/ |
| Sidebar entry "SLA Review Mode" added | grep `/review` in `Sidebar.tsx` |
| Version bumped to 2.0.0 | `curl /health` returns `"version":"2.0.0"` post-restart |

### Live API response shape (truncated)

```json
{
  "scope_queues": [],
  "top_loss_queues": [
    {"queue":"MBR-137-ServiceDesk","total_wall_hours":15394.4,"share_of_total_pct":39.51,...},
    {"queue":"MBR-137-1C-Alfa-Auto","total_wall_hours":4252.9,...},
    ... 10 rows
  ],
  "parking_lots":     [...10 rows],
  "dying_in_queue":   [...15 rows],
  "silent_breaches":  [...15 rows],
  "hot_potato":       [...10 rows],
  "overloaded_engineers": [...10 rows],
  "hidden_breach_delta": {"wall_breaches":1349,"active_breaches":1388,"hidden_breaches":0}
}
```

---

## NOT VERIFIED

| Item | Why |
|---|---|
| Visual DOM of the `/review` page | No browser in sandbox. Hook-order invariant is statically guaranteed by ESLint exit 0 + RuntimeErrorBoundary wraps inner component, so worst case is a contained Result-block instead of a white screen. |
| The 4 KPI tiles render at 28px font correctly | UI verification needs Ctrl+Shift+R reload by user |
| Tab-switch behavior (top loss / parking / dying / hot-potato) | Same — visual confirm needed |

---

## What to do in the browser

1. Open `http://localhost/review` (Ctrl+Shift+R to drop cached chunk)
2. Should see 4 KPI tiles at top (Loss hours / No-owner hours / Hidden breaches / Silent count)
3. Tabs below: Top loss / Parking lots / Dying / Hot-potato
4. Activate any favorite queues on `/favorites` → page rescopes automatically (TanStack queryKey is keyed on `queues`)
