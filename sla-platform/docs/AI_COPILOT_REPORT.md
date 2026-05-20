# AI Copilot — Enterprise SLA Intelligence Assistant

## Overview

The AI Copilot provides natural language analytics, root cause analysis,
and executive summaries — all in Russian. No ML models required;
everything is powered by real-time SQL aggregation and statistical heuristics.

## Supported Natural Language Queries

| Type | Example | Source |
|------|---------|--------|
| Breach Analysis | "Почему выросли нарушения SLA?" | `_answer_why_breach_spike` |
| Queue Analysis | "Какие очереди самые проблемные?" | `_answer_worst_queues` |
| Workload | "Какие сотрудники перегружены?" | `_answer_overloaded_agents` |
| Degradation | "Что ухудшило SLA вчера?" | `_answer_degraded_sla` |
| Trend | "Тренд SLA за месяц" | `_answer_trend` |
| Root Cause | "Основные причины нарушений" | `_answer_root_causes` |
| Stalled | "Зависшие тикеты" | `_answer_stalled_tickets` |
| Recommendations | "Рекомендации по улучшению" | `_answer_recommendations` |

## Root Cause Engine

The root cause engine (`_find_root_causes`) analyzes:
- Breaches by queue + owner across last 24h
- Event type distribution for overloaded queues
- Anomaly detector hints for additional context

## Executive Summary

Generated at `GET /ai/executive-summary?period=daily|weekly|monthly`

Metrics reported:
- SLA Health Score (0-100%)
- Breach rate and total count
- Avg response/resolution time
- Tickets at risk
- Worst-performing queue
- Key insights (3-5 auto-generated bullet points)

## Incident Summary

`POST /ai/incident-summary` enriches incidents with:
- AI-generated description in Russian
- Root cause analysis
- Actionable recommendations with priority
- Business impact assessment
- Related active incidents

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/ai/copilot/query` | Natural language query |
| GET | `/api/v1/ai/copilot/queries` | List supported queries |
| GET | `/api/v1/ai/executive-summary` | Executive report |
| POST | `/api/v1/ai/incident-summary` | Incident enrichment |
| GET | `/api/v1/ai/predict/{ticket_id}` | Breach prediction |
| POST | `/api/v1/ai/predict/batch` | Batch prediction |
| GET | `/api/v1/ai/anomalies` | Detect anomalies |
| GET | `/api/v1/ai/staffing` | Staffing recommendations |
| GET | `/api/v1/ai/hints` | Operational hints |
