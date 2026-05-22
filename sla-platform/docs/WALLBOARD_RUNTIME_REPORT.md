# Wallboard Runtime Report — v2.0.0

Fullscreen TV-safe operations wallboard for Workplace and Asset Management domains. Routes: `/wallboard-ops/workplace`, `/wallboard-ops/asset`.

---

## VERIFIED

| What | How verified |
|---|---|
| Route `/wallboard-ops/workplace` serves the SPA | `curl -o /dev/null -w "%{http_code}"` → 200 via nginx |
| Route `/wallboard-ops/asset` serves the SPA | same → 200 |
| Bundle `WallboardOps-8ckJ70mp.js` present in container | `docker exec ... ls /usr/share/nginx/html/assets/ | grep WallboardOps` |
| Backend `/operations/review/overview?queue=...` returns scoped data | live curl |
| Domain → queues mapping is correct | `DOMAINS.workplace.queues = ["MBR-137-Workplace-Veshki","MBR-137-Workplace-Plaza"]` matches what the user named as critical queues |
| 30-second auto-refresh interval | `useQuery({ refetchInterval: 30_000 })` in source |
| Hooks-safe (no early return before hooks) | `npm run lint:hooks` exits 0 |
| Wrapped in RuntimeErrorBoundary | direct grep |

---

## Design choices (intentional)

- **Dark background `#0a0e1a`**, not the v1 light palette, because the wallboard targets a TV / external monitor in a real ops room. Light-on-light is harder to read at 3m distance. This is the *only* page on dark; everything else stays on v1 light tokens.
- **Single very-large KPI font (64px)** — readable across a meeting room.
- **No charts**, only numbers — charts at distance are unreadable; KPIs work.
- **No clicks, no tabs, no filters** — it's a screen, not an interaction surface.
- **Auto-refresh every 30s** — fast enough to be useful, slow enough to not hammer the backend.
- **2 KPI rows × 4 tiles, plus 2 highlight panels** — fits 1080p and 1440p TVs without scroll.

---

## NOT VERIFIED

| Item | Why |
|---|---|
| Actual TV rendering | I cannot open a browser/TV. Visual confirm depends on the user opening `http://<server>/wallboard-ops/workplace` on the target display. |
| 30s refresh behavior in a long-running tab | Real-world test requires hours of unattended runtime. |
| Red-flash animation on critical KPI changes | Not built — flashes were in the prompt as "nice to have"; defer until a customer confirms it's wanted (gives screen flicker on TVs at distance). |
| Aging-ticket ticker | Same — adds horizontal scrolling that some TVs render badly. Headlines KPIs were chosen instead. |

---

## Reproducibility

In any browser:
- `http://localhost/wallboard-ops/workplace`
- `http://localhost/wallboard-ops/asset`

Both render headlines from `/operations/review/overview` scoped to the 2 critical queues per domain. Press F11 for fullscreen TV mode.
