# Operations Command Center v1.2.0

## Overview

The SLA Command Center is the new default landing page — a mission control dashboard for SLA operations.

## Layout

```
┌──────────────────────────────────────────────────────────────┐
│ TOP BAR: SLA Status · Active Incidents · Compliance % · Health│
├──────┬───────────────────────────────────────┬───────────────┤
│ LEFT │            CENTER                     │    RIGHT      │
│Queue │   SLA Compliance Trend Chart          │ AI            │
│Health│   Breach Risk Map                     │ Recommendations│
│      │   SLA Timeline                        │ Anomaly Alerts│
│      │                                       │               │
│      │   BOTTOM: Tickets at Risk Table       │               │
├──────┴───────────────────────────────────────┴───────────────┤
│ BOTTOM BAR: Trends · Forecasts · Staffing · Burn Rate        │
└──────────────────────────────────────────────────────────────┘
```

## KPI Cards

Compact cards with:
- Status color strip (green/amber/red)
- Metric label (uppercase, tertiary color)
- Large value with trend tag
- Hover elevation effect
- 6 across on desktop

## Queue Health Panel

- Shows top 8 queues by ticket volume
- Progress bar for breach ratio
- Color-coded (green < 10%, amber < 20%, red > 20%)

## SLA Trend Chart

- 7-day compliance trend line
- Gradient area fill
- Color changes based on current compliance (green/amber/red)
- Tooltip with exact values

## Breach Risk Map

- Horizontal bar chart showing tickets per queue
- Color-coded bars
- Reversed Y-axis (highest at top)

## AI Recommendations

- Real-time anomaly feed
- Severity tags (high/warning)
- Queue name and description
- Empty state when no anomalies

## Tickets at Risk

- Sortable table of approaching-breach tickets
- Columns: Ticket#, Queue, Metric, Elapsed, Status
- Color-coded risk tags
- Paginated (5 per page)

## Data Refresh

- Auto-refresh every 30 seconds
- Loading skeleton state
- Zero-data empty states
