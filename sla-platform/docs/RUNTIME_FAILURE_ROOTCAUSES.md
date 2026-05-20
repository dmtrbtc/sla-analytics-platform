# Runtime Failure Root Causes — Mapped

Each row is a real defect verified in code or against real data (not speculation). For each, the symptom maps to the root cause and the file/line that produced it.

---

## "Imports don't work / file doesn't attach"

| Symptom | Root cause | Location | Fixed in v1.3.1 |
|---|---|---|---|
| Upload returns 500 / nothing happens | `UploadFile.iter_chunks()` doesn't exist in starlette 0.37 — `AttributeError` on first byte | `app/api/v1/imports.py:_stream_upload_to_disk` | ✓ replaced with `await upload.read(CHUNK)` loop |
| Reprocess button → 500 | `background_tasks` referenced but never declared as endpoint param → `NameError` | `app/api/v1/imports.py:reprocess_session` | ✓ added `BackgroundTasks` parameter |
| Reported row count is too low | First 1 MiB chunk's newlines were thrown away as "the header" | same file, same function | ✓ count all newlines, subtract 1 for header |

## "Attachments don't work"

| Symptom | Root cause | Location | Fixed in v1.3.1 |
|---|---|---|---|
| Every attachment endpoint 404 | Router mounted at `/attachments`, but each `@router.post("/attachments/upload")` re-added the prefix → real URL was `/attachments/attachments/upload` | `app/api/v1/attachments.py` (4 handlers) | ✓ stripped duplicate prefix from each route |

## "Dashboards empty"

| Symptom | Root cause | Location | Fixed in v1.3.1 |
|---|---|---|---|
| SLA breach trend chart blank or single bar | `since` anchored at today's midnight; `days` parameter ignored. Query returns ≤ 1 row. | `app/api/v1/dashboards.py:sla_trend` | ✓ `since = now - timedelta(days=days)` |
| SLA trend chart never honors UI day filter | Frontend `slaTrend()` didn't pass `days` even though the React state changed | `frontend/src/api/dashboards.ts` + `frontend/src/pages/Dashboard.tsx` | ✓ accept params, pass `{ days }` |
| "Avg response time", "MTTA", "Response breaches" tiles all zero | V2 engine writes `metric_name = "first_response_time"`. Consumers filtered on the legacy name `"response_time"`. Zero rows match. | `services/dashboard_service.py:get_overview`, `services/dashboard_service.py:get_time_series`, `api/v1/dashboards.py:approaching_breach`, `api/v1/sla.py` (4 sites), `services/analytics/advanced_analytics.py:mtta_mttr`, `services/report_service.py` | ✓ all consumers updated; legacy name kept in `.in_(...)` for backward compat with existing rows |

## "V3 Forensic Command Center page broken"

| Symptom | Root cause | Location | Fixed in v1.3.1 |
|---|---|---|---|
| `npm run build` fails with 14 TS errors | Page invented APIs `spacing.lg/md/xs` and called `cardStyle(colors)` as a function. Real API: `spacing[6|4|2]`, `cardStyle` is a static object. | `frontend/src/pages/SLAForensicCommandCenter.tsx` | ✓ rewrote to actual design-token API |

---

## How I distinguished real bugs from "feels wrong"

- **Run the build.** TypeScript caught the V3 page's invented APIs. I would not have caught those without `vite build`.
- **Run pytest.** 285 unit tests pass after every change — if a fix breaks an assumption, tests catch it.
- **Introspect the actual library.** `hasattr(UploadFile, 'iter_chunks')` returned `False` — definitive, not a hunch.
- **Diff against ground truth.** For the row-count fix I compared against `sum(1 for _ in open(file,'rb'))` on the real OTRS files, not against a unit test.
- **Walk the route table.** For the attachments prefix bug I printed the FastAPI router's actual paths after the fix; the strings matched the frontend client.

This is the difference between *finding a bug* and *believing one exists.*

---

## Defects I considered but did NOT fix (and why)

| Suspected | Why I left it | What you'd need to confirm |
|---|---|---|
| Chart rerender storms on dashboards with many queries | I could not see the React render tree | DevTools profiler against a running stack |
| WebSocket spam / zombie subscriptions | `websocket_manager.py` reads as fine; no static evidence of leak | Running app + a stress harness |
| Stale materialized views | Refresh task is cron-driven; not obviously broken in code | Postgres + Celery beat up |
| Memory leaks | Cannot tell from static reading | py-spy / Node memory profiler |
| "Visual UX overload" | Highly subjective; rewriting 25 pages on speculation would do more harm than good | A focused design pass with screenshots and stakeholder input |

These belong in a follow-up runtime session.
