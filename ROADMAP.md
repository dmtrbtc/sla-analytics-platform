# Дорожная карта

## Текущий релиз: v0.1.0

### Phase 1 — Core Pipeline ✅
- [x] CSV import (backlog + history)
- [x] Raw event parser с дедупликацией
- [x] Нормализатор событий (20+ типов)
- [x] Реконструктор жизненного цикла тикетов
- [x] Ownership и queue периоды

### Phase 2 — SLA Engine ✅
- [x] Business hours engine
- [x] Pause engine
- [x] Rule engine (queue + priority matching)
- [x] Metrics engine (response, resolution, queue, owner time)
- [x] SLA definitions CRUD
- [x] Seed definitions (4 стандартных)

### Phase 3 — Analytics & Dashboards ✅
- [x] Dashboard overview с KPI
- [x] Team analytics
- [x] Ticket flow (Sankey, transitions, reassignments)
- [x] Time-series (daily/weekly/monthly)
- [x] Reports XLSX/CSV (Celery async)
- [x] Audit log
- [x] Full frontend with ECharts

## Планируется

### Phase 4 — Testing & Quality (Next)
- [ ] Unit tests: parser, normalizer, SLA engine
- [ ] Integration tests: pipeline, API
- [ ] Property-based testing для нормализатора
- [ ] Load testing (100k+ events)
- [ ] Test coverage > 80%

### Phase 5 — Integrations
- [ ] Webhook-уведомления о нарушениях SLA
- [ ] Email-отчёты по расписанию
- [ ] Интеграция с Jira/ServiceNow
- [ ] API-ключи для внешнего доступа

### Phase 6 — Observability
- [ ] Prometheus метрики
- [ ] Grafana дашборды
- [ ] Structured logging (structlog)
- [ ] OpenTelemetry tracing
- [ ] Метрики производительности пайплайна

### Phase 7 — Enterprise
- [ ] Multi-tenant (разделение по организациям)
- [ ] RBAC с granular permissions
- [ ] Scheduled imports
- [ ] Data retention policies
- [ ] Audit trail retention

### Phase 8 — Advanced Analytics
- [ ] ML-предсказание нарушений SLA
- [ ] Anomaly detection
- [ ] Capacity planning
- [ ] Trend forecasting
- [ ] Custom report builder
