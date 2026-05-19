# Release Notes — v0.7.2

## Import Pipeline Recovery + SLA Validation

### Critical Bug Fixes

**Fix 1 — Dashboard crashes with 500 error on `/api/v1/dashboards/sla-trend`**
- `backend/app/api/v1/dashboards.py:70` — `SLAMetric.sla_breached.cast(type(1))` passed Python `int` to SQLAlchemy's `.cast()`, which expects a SQL type. SQLAlchemy calls `_type_from_args()` on the argument, and `int` has no `_isnull` attribute → `AttributeError`.
- Fix: replaced with `func.sum(case((SLAMetric.sla_breached == True, 1), else_=0))` — the same pattern used throughout the rest of the codebase.

**Fix 2 — Import pipeline cannot start: "Cannot start processing from status 'draft'"**
- `backend/app/services/import_service.py:116` — `start_processing()` only accepted `VALIDATING` or `FAILED` status. After upload, sessions with a single file (or files that didn't match both backlog/history patterns) stayed in `DRAFT`.
- Fix: added `ImportStatus.DRAFT.value` to the accepted statuses list.

**Fix 3 — Upload does not advance session status for single-file imports**
- `backend/app/services/import_service.py:100` — Status only advanced to `VALIDATING` when BOTH `backlog_file` AND `history_file` were set. Single-file uploads remained in `DRAFT`.
- Fix: advance to `VALIDATING` on ANY file upload (when status is `DRAFT`).

**Fix 4 — Reprocess endpoint bypasses start_processing with raw DB writes**
- `backend/app/api/v1/imports.py:141` — The reprocess endpoint manually set `status = "parsing"`, cleared errors/stats, committed to DB, then directly called `run_import_pipeline.delay()`. This duplicated logic from `ImportService.start_processing` and bypassed status validation.
- Fix: set status to `FAILED`, clear errors, then delegate to `ImportService.start_processing()` which handles validation, status transition, and pipeline dispatch.

### QA Results
- `tsc --noEmit`: 0 errors
- `pytest tests/`: 280 passed
- `vite build`: 3818 modules, clean build
- Backend import verification: `from app.api.v1.imports import router` — OK
- Backend dashboards verification: `from app.api.v1.dashboards import router` — OK
