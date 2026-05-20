# Dashboard Data-Flow Map

How a number on a dashboard tile traces back to the database. Generated from
reading the v1.3.1 codebase end-to-end (frontend → API → service → SQL).
Each row shows the actual function names and what `metric_name` (if any) the
SQL filters on, so future regressions can be diagnosed quickly.

---

## Dashboard.tsx (`/dashboard`)

| UI element | Frontend call | Backend route | Service / function | SQL filter / source | Notes |
|---|---|---|---|---|---|
| KPI: total tickets | `dashboardsApi.overview({days})` | `GET /dashboards/overview` | `DashboardService.get_overview` | `count(TicketSnapshot)` | — |
| KPI: open vs closed | same | same | same | `where is_closed=false` | — |
| KPI: breach % | same | same | same | `count(SLAMetric where sla_breached=true) / count(SLAMetric)` | — |
| KPI: avg response time, p50/p90/p95/p99 | same | same | `_metric_stats("first_response_time")` | `SLAMetric.metric_name='first_response_time'` | **was `response_time` — never produced** ✓ fixed |
| KPI: avg resolution time, p50/p90/p95/p99 | same | same | `_metric_stats("resolution_time")` | `metric_name='resolution_time'` | — |
| Time-series: tickets created | `dashboardsApi.timeSeries({metric:"tickets_created", granularity:"daily", days})` | `GET /dashboards/time-series` | `DashboardService.get_time_series` | `TicketSnapshot.created_at >= since` | — |
| Time-series: tickets closed | same with `metric="tickets_closed"` | same | same | `is_closed=true AND updated_at >= since` | — |
| Time-series: sla breaches | same with `metric="sla_breaches"` | same | same | `SLAMetric.sla_breached=true AND computed_at >= since` | — |
| Time-series: response_time | same with `metric="response_time"` | same | same | `metric_name='first_response_time'` | **server accepts legacy name, translates internally** ✓ fixed |
| Time-series: resolution_time | same with `metric="resolution_time"` | same | same | `metric_name='resolution_time'` | — |
| SLA breach trend chart | `dashboardsApi.slaTrend({days})` | `GET /dashboards/sla-trend` | inline in endpoint | `computed_at >= now - days` grouped by day | **was anchored at today midnight — only ever showed today** ✓ fixed |
| Top breached queues | `slaApi.getQueueBreaches()` | `GET /sla/queue-breaches` | `BreachService` | aggregations over `sla_metrics` | not touched in this release |

## DashboardOps.tsx (`/dashboard/ops`)

| Tile | Endpoint | Status |
|---|---|---|
| Advanced analytics: SLA forecast | `GET /dashboards/analytics/sla-forecast` | `AdvancedAnalytics.sla_trend_forecast` — unchanged |
| Queue overload | `GET /dashboards/analytics/queue-overload` | unchanged |
| MTTR / MTTA | `GET /dashboards/analytics/mttr-mtta` | **MTTA now reads `first_response_time`** ✓ fixed |
| Problematic queues | `GET /dashboards/analytics/problematic-queues` | unchanged |
| Aging tickets | `GET /dashboards/analytics/aging-tickets` | unchanged |

## SLA Forensic Command Center (`/forensics`) — V3

| Section | Endpoint | Source |
|---|---|---|
| Whole page | `GET /analytics/forensics/summary` | `forensics_api.forensic_summary` → bundles queue/owner/transition/silent/hot-potato data |
| Black-hole tab | summary `queues_top_blackholes` | `QueueForensicsService.compute_all`, sorted by `black_hole_score` |
| Routing chaos tab | summary `queues_top_chaos` | sorted by raw `entropy_bits` (ServiceDesk leads at 4.14 bits) |
| Breach rate tab | summary `queues_top_breach` | sorted by `breach_rate` |
| Silent breaches tab | summary `silent_breaches` | `InactivityEngine.detect_silent_breaches` (open tickets, no events in ≥50% SLA target) |
| Hot-potato tab | summary `hot_potato` | `QueueForensicsService.hot_potato_tickets` (≥3 moves) |
| Owners tab | summary `owners_top_load` + `owners_idle` | `OwnerForensicsService.compute_all` |
| Queue silence tab | summary `queue_silence` | `InactivityEngine.compute_queue_silence` |
| KPI: wall vs active breach delta | summary `kpis.wall_breached` − `kpis.active_breached` | sums on `sla_metrics` |
| KPI: no-owner hours | summary `kpis.no_owner_total / 3600` | `SUM(metric_seconds)` where `metric_name='no_owner_seconds'` |

## Import flow

```
POST /imports/sessions              create_session()            ImportService.create_session()
   ├─ multipart backlog                                          → _stream_upload_to_disk (await upload.read(CHUNK)) ✓ fixed
   └─ multipart history                                          → same

POST /imports/sessions/{id}/start   start_processing()          ImportService.start_processing()
                                                                 → Celery: process_import_session
                                                                   → ParserService.parse_and_load (uses csv_parser.read_history_chunks)
                                                                   → NormalizerService.normalize (writes ticket_events)
                                                                   → ReconstructionService.reconstruct (writes queue_periods, ownership_periods, ticket_snapshots)
                                                                   → SLAEngine.compute_for_import
                                                                       ├─ MetricsEngine.compute_all  → V2 metrics
                                                                       └─ ForensicAttributionEngine.compute_wall_clock_metrics → V3 metrics
                                                                   → invalidate_dashboard_cache(), invalidate_analytics_cache()
GET  /imports/sessions/{id}/progress  → polling
```

## Attachments

```
POST /attachments/upload            upload_attachment()         hash + write to STORAGE_DIR + INSERT attachments
GET  /attachments                   list_attachments()          paginated list
GET  /attachments/{id}              get_attachment()            FileResponse from STORAGE_DIR
DELETE /attachments/{id}            delete_attachment()         remove file + DELETE row
```
All four URLs now match what `frontend/src/api/attachments.ts` calls. ✓ fixed in v1.3.1.

---

## How to add a new dashboard tile without breaking the chain

1. **Pick the metric the V2 engine actually emits.** Inspect:
   ```bash
   grep -n 'metric_name=' backend/app/services/sla/metrics_engine.py
   ```
   The full set: `first_response_time, resolution_time, assignment_time,
   queue_time, owner_time, active_work_time, paused_time, reopen_count,
   reassignment_count, queue_bounce_count, touch_count, sla_efficiency_pct`,
   plus V3 additions: `wall_response_time, wall_resolution_time,
   pause_seconds, idle_seconds, no_owner_seconds, ownership_gap_seconds,
   transfer_wait_seconds, stagnation_seconds`.

2. **Filter SQL on the exact emitted name.** If you accept a legacy public name
   from the API, translate it server-side before hitting SQL (see how
   `get_time_series` handles `response_time` → `first_response_time`).

3. **Pass user filters through the chain.** Every API client function takes a
   `params` arg; pass `{ days }` etc. through (don't hardcode in queryKey only).

4. **Run `npm run build` and `pytest tests/`** before claiming a fix.
