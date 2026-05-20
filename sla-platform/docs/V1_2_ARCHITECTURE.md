# v1.2.0 — Enterprise Operations Command Platform

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   ENTERPRISE DESIGN SYSTEM V3               │
│  Light theme · Inter typography · Dark mode · AA+ colors    │
└─────────────────────────────────────────────────────────────┘

┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  SLA Command     │  │  Executive       │  │  AI Copilot V3   │
│  Center (Hub)    │  │  Intelligence    │  │  NL Analytics    │
│  · KPI cards     │  │  · Health score  │  │  · Questions     │
│  · Queue health  │  │  · Financial     │  │  · Commander     │
│  · Breach map    │  │  · Forecast      │  │  · Anomalies     │
│  · Risk table    │  │  · MTTR/MTTA     │  │  · Reports       │
└──────────────────┘  └──────────────────┘  └──────────────────┘

┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  SLA Governance  │  │  Enterprise      │  │  Operations      │
│  · Rule builder  │  │  Reporting V2    │  │  Admin Center    │
│  · Conflict      │  │  · Branded XLSX  │  │  · Diagnostics   │
│  · Simulator     │  │  · PDF executive │  │  · Queue lag     │
│  · Calendar      │  │  · Cover pages   │  │  · Profiler      │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## New Backend Endpoints (30+)

| Module | Prefix | Endpoints |
|--------|--------|-----------|
| Governance | `/sla/governance/` | conflicts, bulk-simulate, rule-graph, calendar-preview |
| Executive | `/executive/` | health-score, financial-impact, cost-per-queue, forecast, mttr, efficiency-score, compliance-trend |
| AI V3 | `/ai/v3/` | analytics, incident-commander, anomalies, reports/generate |
| Ops Admin | `/operations/` | tenant-diagnostics, queue-lag-monitor, sla-profiler, live-logs, tracing-explorer |
| Enterprise Reports | `/enterprise-reports/` | xlsx/generate, xlsx/download, pdf/generate, pdf/download, list |

## New Frontend Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/command-center` | SLACommandCenter | Mission control — KPI cards, queue health, SLA trend, breach risk, AI recommendations |
| `/admin/operations` | OperationsAdmin | Infrastructure diagnostics, queue lag monitor, SLA profiler, live logs |
| `/dashboard/executive` | DashboardExecutive | Executive intelligence suite |

## Visualization Engine (ECharts)

| Component | Type | Use Case |
|-----------|------|----------|
| SLAHeatmap | Heatmap | Queue activity by hour/day |
| SLAScatter | Scatter | Response vs Resolution time |
| SLABurnDown | Line | SLA burn-down chart |
| QueueSankey | Sankey | Queue transition flow |
| TicketLifecycle | Bar | Ticket phase timeline |
| RiskPropagation | Graph | Risk dependency network |

## Design System Changes

- **Colors**: Neutral corporate palette (#1b1f23, #586069, #0969da)
- **Typography**: Inter, clear hierarchy (xs-7xl), KPI preset
- **Shadows**: Softer, enterprise-grade (card, kpi, hover)
- **Dark Mode**: Full dark theme via `data-theme` attribute, auto/system/manual
- **Theme Provider**: React context with `useTheme()` hook
- **Chart Theme**: Light + dark ECharts themes
- **Table Theme**: Light + dark Ant Design overrides

## Key Metrics

- 296+ unit tests passing
- 180+ API endpoints
- 30+ new frontend components
- 5 new backend modules
- 4 new architecture docs
