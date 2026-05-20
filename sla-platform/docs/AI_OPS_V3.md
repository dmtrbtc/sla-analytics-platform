# AI Operations Copilot V3

## Architecture

AI Ops V3 adds three major capabilities over V2:

### 1. Natural Language Analytics

Understands Russian operational questions:

| Question | Returns |
|----------|---------|
| "Почему выросли нарушения SLA?" | Queue-level breach breakdown with root cause |
| "Какие очереди деградируют?" | Lists queues with breach rates > 0% |
| "Что будет через 2 часа?" | Count-based extrapolation forecast |
| "Кого не хватает в Support?" | Staffing recommendations |
| "Сводка за сегодня" | 24h summary with compliance rate |

### 2. AI Incident Commander

When an incident is detected, it provides:
- **Root cause** — Correlation analysis
- **Timeline** — Events leading to incident
- **Impacted queues** — Which queues affected
- **Recommendations** — Actionable steps
- **Predicted outcome** — ETA to recovery

### 3. Anomaly Detection

Detects:
- Queue spike anomalies (>20% breach rate in queues with 100+ tickets)
- Abnormal reassignment patterns
- Hidden bottlenecks
- Staffing anomalies

### 4. AI-Generated Reports

- Executive Summary (daily/weekly/monthly)
- Operations Summary
- Weekly SLA Digest with key findings and recommendations

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/ai/v3/analytics` | Natural language query |
| POST | `/api/v1/ai/v3/incident-commander` | Incident analysis |
| GET | `/api/v1/ai/v3/anomalies` | Anomaly detection |
| POST | `/api/v1/ai/v3/reports/generate` | AI report generation |
