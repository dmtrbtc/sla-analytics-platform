# API Документация

Полная документация API доступна через Swagger UI после запуска:

```
http://localhost:8000/api/docs
```

## Основные эндпоинты

### Health

```http
GET /health
```

Ответ:
```json
{"status": "healthy", "version": "0.1.0"}
```

### Импорт данных

#### Создание сессии импорта
```http
POST /api/v1/imports/sessions
Content-Type: multipart/form-data

backlog: <CSV файл backlog>
history: <CSV файл history>
```

#### Запуск пайплайна
```http
POST /api/v1/imports/sessions/{session_id}/start
```

#### Получение статуса
```http
GET /api/v1/imports/sessions/{session_id}
```

#### Повторная обработка
```http
POST /api/v1/imports/sessions/{session_id}/reprocess
```

### SLA

#### Определения SLA
```http
GET    /api/v1/sla/definitions
POST   /api/v1/sla/definitions
GET    /api/v1/sla/definitions/{id}
PUT    /api/v1/sla/definitions/{id}
DELETE /api/v1/sla/definitions/{id}
```

#### Метрики
```http
GET /api/v1/sla/metrics?ticket_id=&metric_name=&sla_breached=&import_id=&limit=&offset=
```

#### Нарушения
```http
GET /api/v1/sla/breaches?import_id=&metric_name=&limit=&offset=
```

#### Сводка
```http
GET /api/v1/sla/summary?import_id=
```

### Дашборды

#### Обзор
```http
GET /api/v1/dashboards/overview?days=30
```

#### Командная аналитика
```http
GET /api/v1/dashboards/teams?days=90
```

#### Временные ряды
```http
GET /api/v1/dashboards/time-series?metric=tickets_created&granularity=daily&days=30
```

#### Ticket Flow
```http
GET /api/v1/dashboards/ticket-flow?days=90
```

### Тикеты

```http
GET /api/v1/tickets?page=1&page_size=50&search=&queue=&state=&confidence=&is_closed=
GET /api/v1/tickets/{ticket_id}
GET /api/v1/tickets/{ticket_id}/timeline
GET /api/v1/tickets/{ticket_id}/ownership
GET /api/v1/tickets/{ticket_id}/queue-periods
GET /api/v1/tickets/{ticket_id}/sla
```

### Отчёты

```http
POST /api/v1/reports/generate?report_type=sla_breaches&fmt=xlsx
GET  /api/v1/reports/status/{task_id}
GET  /api/v1/reports
GET  /api/v1/reports/{filename}/download
```

### Команды

```http
GET    /api/v1/teams
POST   /api/v1/teams
GET    /api/v1/teams/{id}
PUT    /api/v1/teams/{id}
DELETE /api/v1/teams/{id}
```

### Аудит

```http
GET /api/v1/audit/log?limit=100&offset=0&action=&resource_type=
```

## Форматы данных

### CSV импорт

Ожидаемый формат — vCustomerTimeline экспорт из OTRS/Znuny:

```csv
TicketID,TicketNumber,Title,EventTime,EventName,EventRawName,Queue,State,Owner,...
```

### SLA Definition

```json
{
  "name": "Critical Priority",
  "queue_pattern": "*",
  "priority": "1 critical",
  "response_target_seconds": 3600,
  "resolution_target_seconds": 28800,
  "pause_on_pending": true,
  "business_hours_only": false
}
```

### Dashboard Overview Response

```json
{
  "total_tickets": 776,
  "open_tickets": 456,
  "closed_tickets": 320,
  "sla_breach_pct": 11.36,
  "avg_response_time_seconds": 45600,
  "avg_resolution_time_seconds": 345600,
  "imports_processed": 12,
  "tickets_by_queue": { "Support": 300, "Service Desk": 200 },
  "tickets_by_state": { "open": 400, "closed": 320 },
  "tickets_by_confidence": { "full": 500, "partial": 200, "minimal": 76 },
  "tickets_by_priority": { "1 critical": 50, "2 high": 150 },
  "breach_trend": [{"date": "2026-05-01", "count": 5}],
  "import_trend": [{"date": "2026-05-01", "count": 2}]
}
```
