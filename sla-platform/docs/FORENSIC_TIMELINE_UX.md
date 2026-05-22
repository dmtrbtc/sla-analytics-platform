# Forensic Timeline UX — v2.0.0

Visual queue-by-queue timeline strip for a single ticket. Page route: `/tickets/{id}/timeline`.

---

## VERIFIED

| What | How verified |
|---|---|
| Component file exists: `frontend/src/components/forensics/ForensicTimelineVisual.tsx` | direct file inspection |
| Page route registered: `/tickets/:id/timeline` | App.tsx grep + `curl http://localhost/tickets/144844/timeline` → HTTP 200 |
| Bundle `TicketTimelinePage-B6F_ueQn.js` shipped to nginx | `docker exec ... ls /assets/ | grep TicketTimeline` |
| Backend endpoint already exists (v1.7) | `curl /api/v1/analytics/forensics/timeline/144844` → live JSON with 25 segments |
| Hooks rules: useQuery + useMemo called BEFORE conditional returns | lint:hooks exit 0 across full src/ |
| Wrapped in RuntimeErrorBoundary | grep `RuntimeErrorBoundary label="timeline тикета ${props.ticketId}"` |
| Real ticket 144844 → 25 segments, total 6,242 wall-clock minutes | live response from `/analytics/forensics/timeline/144844` |
| First-response rule check returns `"ok"` for ticket 144844 | live API response |

---

## Component design (SVG-free; just CSS flex strip)

- **Horizontal track** of colored segments. Width per segment = proportional to wall minutes.
- **12 colors** rotate per distinct queue name (ColorBlind-friendly palette derived from Tailwind 500-shades).
- **Overlays per segment:**
  - `.seg.breach` (red) — deadline crossed inside this segment
  - `.seg.no-owner` (gray hatched) — ≥80% of segment was unowned
  - `.seg.paused` (orange diagonal) — at least one pending* state event during segment
  - `.seg.ok` (queue color)
- **Hover tooltip** lists: queue name, wall, response-loss, resolution-loss, no-owner, paused flag, breach flag, owners during the segment with seconds.
- **Header line** shows: ticket #, state, total segments, total wall, FR-rule check, breach queue.
- **Footer line:** first-response queue, top loss queue (with minutes), top bounces (queue × visits).

Why no chart library: ECharts adds 1MB; this is just a flex container with proportional widths. Renders identically without a chart dependency.

---

## Live test for ticket 144844

```
GET /api/v1/analytics/forensics/timeline/144844
  ticket: 2026042711001301
  created: 2026-05-04T08:45:22
  first_response_at: 2026-05-05T17:23:30   (1957 min into life)
  resolution_at: null   (still open)
  segments: 25
  total wall: 6242 min (4.3 days)
  response_passed_in_queue: MBR-137-ServiceDesk
  first_response_rule_check: "ok"   (post-fix verified in v1.7)
  top_loss_queue: MBR-137-ServiceDesk (1,497 min)
  breach_queue (at deadline): MBR-137-ServiceDesk
  bounces: ServiceDesk × 12, DC-WintelOperations × 10
```

The strip renders these 25 segments in chronological order. ServiceDesk segments appear in the queue's blue, DC-WintelOperations in green, etc. Hovering any segment reveals the owner who held it (mostly `root@localhost` for 144844 — that's the 93% accountability gap from the v1.5 contribution engine).

---

## NOT VERIFIED

| Item | Why |
|---|---|
| Visual DOM rendering (tooltip alignment, color contrast at small widths) | No browser in sandbox. The CSS rule `.v1-timeline .seg { min-width: 2 }` ensures even tiny segments stay visible. |
| Bounce arrows / re-entry loops as visual lines connecting segments | NOT built. The current strip is linear; loops are surfaced as "bounces" in the footer line and via segment count > distinct queues. A second SVG overlay layer would be the next iteration. |
| Owner-period overlay band (separate row below the strip) | NOT built — the owners are visible in the tooltip per segment. A second band would double page height. |
| First-response marker (gold pin) overlaid on the strip | NOT visually built — surfaced as text in the footer line. |
| The user navigation to this page | Add a "Timeline" button to `/tickets/{id}` (the existing TicketDetail page) as a follow-up. Or just paste the URL directly. |

---

## Reproducibility

```
http://localhost/tickets/144844/timeline
http://localhost/tickets/145460/timeline    (another hot-potato candidate)
```

API:
```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"admin","password":"admin123"}' \
  -H 'Content-Type: application/json' | jq -r .access_token)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/analytics/forensics/timeline/144844?response_target_seconds=1800&resolution_target_seconds=28800" \
  | jq '.summary'
```
