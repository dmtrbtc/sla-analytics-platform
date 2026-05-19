# HOTFIX v0.6.1 — Runtime Crash Recovery

**Release date:** 2026-05-19

---

## Overview

Critical hotfix to restore platform runtime after v0.6.0 enterprise release introduced two blocking crashes: backend `ImportError` on startup and frontend ECharts `NaN` crash rendering blank pages.

---

## Root Causes

### 1. Backend ImportError — `ai_ops.py` & `incidents.py`

**Affected files:**
- `backend/app/api/v1/ai_ops.py:8`
- `backend/app/api/v1/incidents.py:13`

**Error:** `from app.domain.schemas import User` → `ImportError: cannot import name 'User' from 'app.domain.schemas'`

**Why:** `User` is a SQLAlchemy ORM model defined in `app.domain.models`, not a Pydantic schema in `app.domain.schemas`. The `get_current_user` dependency returns the DB model (see `app/core/dependencies.py:19`). Both files were using the wrong import path.

**Impact:** Backend process crashes on any `--reload` event. Nginx reverse proxy returns 504 Gateway Timeout on all `/api/` requests. Entire platform becomes unusable.

### 2. Frontend Chart `NaN` Crash — `DashboardOps.tsx`

**Affected file:** `frontend/src/pages/DashboardOps.tsx`

**Error:** `Uncaught TypeError: ECharts visualMap.max cannot be NaN`

**Why:** The risk heatmap dataset contained entries where `breach_count` was `undefined`. The expression `Math.max(...data.map(d => d.breach_count || 0), 1)` evaluated as `Math.max(undefined, ..., 1)` → `Math.max(NaN, 1)` → `NaN`. ECharts `visualMap.max = NaN` throws a render-time exception, causing the entire page to crash.

**Impact:** Frontend renders blank white page on DashboardOps route. All ECharts instances in the page fail silently with no user-visible error.

### 3. SLAMonitor `NaN` Bar Width

**Affected file:** `frontend/src/pages/SLAMonitor.tsx`

**Error:** `Math.max(...breached || 0, 1)` where `breached` is an array — evaluates to `Math.max(0, 1)` = `1`, producing a zero-width invisible bar.

**Why:** Spread operator on an array coerced via `|| 0` returns `0` instead of spreading individual values. Additionally, overdue fallback logic was inverted.

---

## Changes

### Fixed
- `backend/app/api/v1/ai_ops.py` — `from app.domain.models import User` (was `schemas`)
- `backend/app/api/v1/incidents.py` — `from app.domain.models import User` (was `schemas`)
- `frontend/src/pages/DashboardOps.tsx` — Heatmap data filtered for null entries, `breach_count || 0` safe default, typed `.filter()` guard
- `frontend/src/pages/SLAMonitor.tsx` — Split view bar width: `Math.max(...(breached || [0]), 1)`; overdue fallback: fixed inverted boolean logic

### Added
- `frontend/src/components/common/SafeChart.tsx` — Error boundary wrapping all 3 ECharts components (risk heatmap, SLA trend, queue health), catches chart render failures gracefully

### Wrapped
- `DashboardOps.tsx` — All 3 ECharts instances wrapped in `<SafeChart>` error boundary
- Removed unused `worstAgent` variable (TypeScript lint)

---

## Affected Files

### Modified
- `backend/app/api/v1/ai_ops.py` — Import fix
- `backend/app/api/v1/incidents.py` — Import fix
- `frontend/src/pages/DashboardOps.tsx` — NaN guard + SafeChart wrappers
- `frontend/src/pages/SLAMonitor.tsx` — Bar width NaN guard + overdue fix

### Added
- `frontend/src/components/common/SafeChart.tsx` — Error boundary component

---

## QA
- `tsc --noEmit` — 0 errors (3817 modules)
- `vite build` — Clean, 3817 modules, 0 warnings (except vendor chunk size)
- Docker full clean rebuild — 3 images rebuilt, 5 containers healthy
- `GET /health` — `{"status":"healthy","version":"0.6.0"}`
- `GET /` — 200 (frontend index.html)
- `GET /api/v1/dashboards/overview` — 401 (expected, auth required)
- Backend logs — no ImportError, clean startup
- `pytest backend/` — 221 tests passing

---

## Breaking Changes
None.

---

## How to Deploy

```bash
docker compose build --no-cache
docker compose up -d
docker compose logs backend --tail=20
```

Verify health:
```bash
curl http://localhost:8000/health
# {"status":"healthy","version":"0.6.0"}
```

Hard refresh browser cache (Ctrl+Shift+R) to load new frontend chunks.
