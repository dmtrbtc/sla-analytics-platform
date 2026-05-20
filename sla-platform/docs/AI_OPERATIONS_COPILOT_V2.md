# AI Operations Copilot V2

## Overview

Conversational AI layer over the SLA Intelligence Cloud. Provides natural language querying, anomaly explanation, staffing forecasts, queue comparisons, and AI-generated dashboards.

## Endpoints

### `/api/v1/ai/copilot/conversation`
Multi-turn conversational analytics with session persistence.

```json
POST /api/v1/ai/copilot/conversation
{
  "session_id": "user-session-123",
  "question": "Why did SLA drop last week?"
}
```

### `/api/v1/ai/copilot/conversation/clear`
Clear conversation history for a session.

### `/api/v1/ai/dashboard/generate?focus=general`
Generate an AI-recommended dashboard configuration.

## Query Types

| Type | Trigger Words | Response |
|------|--------------|----------|
| Anomaly | "why", "drop", "spike", "anomaly" | Anomaly explanation with root cause |
| Staffing | "agents", "staffing", "team" | Agent requirement forecast |
| Comparison | "compare", "vs", "versus" | Side-by-side queue comparison |
| Trend | "trend", "trending", "over time" | Trend analysis with direction |
| Mitigation | "mitigate", "improve", "fix" | Actionable recommendations |
| General | (default) | Conversational response |

## Architecture

```
User Query
    │
    ▼
conversational_query(session_id, question)
    │
    ├── Anomaly → _explain_anomaly() → SQL → metrics
    ├── Staffing → _staffing_forecast() → SQL → projection
    ├── Compare → _compare_queues() → SQL → comparison
    ├── Trend → _explain_trend() → SQL → trend
    ├── Mitigation → _suggest_mitigation() → SQL → actions
    └── General → NL response with context
```

## Dashboard Generation

`generate_ai_dashboard(focus)` produces:
- Panel definitions (stat, timeseries, pie, table)
- PromQL expressions
- Grid layout (12-column)
- Auto-refresh intervals
