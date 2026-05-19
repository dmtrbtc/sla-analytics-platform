# v0.6.0 — Enterprise Commercial UX Redesign

**Release date:** 2026-05-18

---

## Overview

Complete visual transformation of SLA Analytics Platform from "internal analytics tool" to "commercial enterprise SaaS platform". Redesigned design system, executive dashboard, SLA monitor, and supporting components.

---

## What's New

### Design System V2 (`frontend/src/design/`)
- **`tokens.ts`** — Central design tokens, card/page header/toolbar/section styles
- **`typography.ts`** — Full type scale, font weights, heading presets
- **`spacing.ts`** — Spacing scale, border radii, breakpoints, layout constants
- **`colors.ts`** — Brand palette, accent colors, severity colors, chart colors
- **`shadows.ts`** — Subtle enterprise shadow system (no heavy shadows)
- **`chartTheme.ts`** — Unified ECharts theme (muted lines, clean tooltips)
- **`tableTheme.ts`** — Enterprise table styling constants

### Shared Components
- **`KpiCard`** — Premium KPI card with sparkline, trend %, compact mode
- **`EnterpriseTable`** — Unified enterprise table wrapper
- **`Sparkline`** — Inline SVG sparkline with area fill
- **`PageSkeleton`** — Premium skeleton loader matching card layouts
- **`EnterpriseFilters`** — Compact, sticky, enterprise filter toolbar
- **`ProgressBar`** — Clean progress bar with color thresholds
- **`SlaTrendSparkline`** — Persistent trend sparkline for queue metrics
- **`DemoModeToggle`** — Demo mode switch for client presentations

### Executive Dashboard (DashboardOps) — Complete Redesign
- Premium KPI row: SLA Response, SLA Resolution, Breaches, At Risk, Avg Response, Avg Resolution — each with sparkline, trend %, and prev-period comparison
- SLA Trend line chart with ECharts (smooth, muted palette)
- Queue Health horizontal bar chart
- Risk Heatmap (24×7 grid)
- Bottleneck queue list
- Live Incidents feed from approaching-breaches API
- Tickets at Risk enterprise table
- Worst Agents enterprise table
- Percentiles table with custom styling
- All using design system tokens

### SLA Monitor V2
- KPI strip converted to `KpiCard` components
- Matrix view: card-style container with design tokens, cleaner table headers
- Split view: card-style left/right panels, muted severity colors
- Feed view: animated row insertion (`feedRowIn` keyframes), severity pulse, design tokens throughout

### Reports UX Upgrade
- Report type selector: visual presets grid with icons
- Design system tokens applied throughout
- Cleaner table, improved layout

### Enterprise Polish
- **Demo Mode** — Global store (`stores/demoMode.ts`), toggle in header with visual indicator
- **Command Palette** — Planned infra (global search keyboard shortcut)
- Keyboard navigation support via toolbar conventions

### Visual Rules
- No neon, no gradients, no giant shadows
- White space, subtle borders, elegant hierarchy
- Premium B2B SaaS feel (Atlassian/Datadog level)

---

## Files Changed

### New
- `frontend/src/design/tokens.ts`
- `frontend/src/design/typography.ts`
- `frontend/src/design/spacing.ts`
- `frontend/src/design/colors.ts`
- `frontend/src/design/shadows.ts`
- `frontend/src/design/chartTheme.ts`
- `frontend/src/design/tableTheme.ts`
- `frontend/src/components/common/KpiCard.tsx`
- `frontend/src/components/common/EnterpriseTable.tsx`
- `frontend/src/components/common/Sparkline.tsx`
- `frontend/src/components/common/PageSkeleton.tsx`
- `frontend/src/components/common/EnterpriseFilters.tsx`
- `frontend/src/components/common/ProgressBar.tsx`
- `frontend/src/components/common/SlaTrendSparkline.tsx`
- `frontend/src/components/common/DemoModeToggle.tsx`
- `frontend/src/components/common/NotificationCenter.tsx`
- `frontend/src/stores/demoMode.ts`
- `docs/release-notes-v0.6.0.md`
- `docs/ENTERPRISE_UX_REPORT.md`

### Modified
- `frontend/src/pages/DashboardOps.tsx` — Complete executive redesign
- `frontend/src/pages/SLAMonitor.tsx` — Design system application, feed animation
- `frontend/src/pages/Reports.tsx` — Design system, report presets
- `frontend/src/components/layout/Header.tsx` — Demo mode toggle
- `frontend/src/i18n/locales/ru/common.json` — Executive dashboard labels
- `frontend/src/i18n/locales/en/common.json` — Executive dashboard labels
- `backend/app/core/version.py` — 0.5.0 → 0.6.0

---

## QA
- `tsc --noEmit` — 0 errors
- `vite build` — Clean production build
- No new dependencies
- Design system backward compatible
- All existing API contracts preserved

---

## Breaking Changes
None. All existing functionality preserved. Design system is additive.
