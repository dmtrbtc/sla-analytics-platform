# Архитектура платформы

## Общая архитектура

```mermaid
graph TB
    subgraph "Frontend (React 18)"
        UI[Ant Design 5 + ECharts]
        RQ[React Query]
        API_CLIENT[API Client Layer]
    end

    subgraph "Backend (FastAPI)"
        REST[REST API v1]
        AUTH[JWT Auth]
        SVC[Services Layer]
        SLA[SLA Engine]
        TASKS[Celery Tasks]
    end

    subgraph "Database (PostgreSQL 16)"
        RAW[raw_events]
        EV[ticket_events]
        SNAP[ticket_snapshots]
        OWN[ownership_periods]
        QP[queue_periods]
        SLA_M[sla_metrics]
        SLA_D[sla_definitions]
        TEAMS[teams]
        AUDIT[audit_log]
        IMP[import_sessions]
    end

    subgraph "Queue & Workers"
        REDIS[Redis 7]
        CELERY[Celery Workers]
        IMPORT_W[Import Queue]
        REPORT_W[Report Queue]
    end

    UI --> API_CLIENT
    API_CLIENT --> REST
    REST --> AUTH
    REST --> SVC
    REST --> SLA
    SVC --> DB[(PostgreSQL)]
    SLA --> DB
    TASKS --> CELERY
    CELERY --> IMPORT_W
    CELERY --> REPORT_W
    IMPORT_W --> DB
    REPORT_W --> DB
    REDIS --> CELERY
```

## Схема базы данных

```mermaid
erDiagram
    import_sessions ||--o{ raw_events : "has"
    import_sessions ||--o{ ticket_events : "has"
    import_sessions ||--o{ sla_metrics : "has"
    raw_events ||--o| ticket_events : "produces"
    ticket_events ||--|| ticket_snapshots : "builds"
    ticket_snapshots ||--o{ ownership_periods : "has"
    ticket_snapshots ||--o{ queue_periods : "has"
    ticket_snapshots ||--o{ sla_metrics : "evaluated"
    sla_metrics ||--o| sla_definitions : "uses"
    teams ||--o{ ownership_periods : "owns"
    users ||--o{ import_sessions : "imports"
    users ||--o{ sla_definitions : "creates"
    users ||--o{ audit_log : "audits"
```

## Пайплайн обработки данных

```mermaid
flowchart LR
    CSV[CSV Files] --> PARSER[Parser Service]
    PARSER --> RAW[raw_events]
    RAW --> NORM[Normalizer Service]
    NORM --> TE[ticket_events]
    TE --> RECON[Reconstructor Service]
    RECON --> SNAP[ticket_snapshots]
    RECON --> OWN[ownership_periods]
    RECON --> QP[queue_periods]
    SNAP --> SLA_ENG[SLA Engine]
    QP --> SLA_ENG
    OWN --> SLA_ENG
    SLA_ENG --> METRICS[sla_metrics]
    SLA_DEF[sla_definitions] --> SLA_ENG
```

## Celery Workflow

```mermaid
sequenceDiagram
    participant API as FastAPI
    participant CHAIN as Celery Chain
    participant DB as PostgreSQL
    participant REDIS as Redis

    API->>CHAIN: run_import_pipeline(import_id)
    CHAIN->>DB: validate_step
    CHAIN->>DB: backlog_step
    CHAIN->>DB: parse_step
    CHAIN->>DB: normalize_step
    CHAIN->>DB: rebuild_step
    CHAIN->>DB: compute_sla_step
    CHAIN->>DB: complete_step
    CHAIN->>REDIS: store result
    API->>REDIS: poll status
```

## SLA Computation Flow

```mermaid
flowchart TD
    START([Start]) --> GET_TICKETS[Get tickets for import]
    GET_TICKETS --> MATCH_SLA[Match SLA definitions]
    MATCH_SLA --> RULES{Rule Engine}
    RULES --> |queue_pattern| FNMATCH[fnmatch match]
    RULES --> |priority| SCORE[Priority scoring]
    FNMATCH --> DEF[Select SLA definition]
    SCORE --> DEF
    DEF --> BH[Business Hours Engine]
    BH --> PAUSE[Pause Engine]
    PAUSE --> METRICS_COMP[Compute metrics]
    METRICS_COMP --> RESP[response_time]
    METRICS_COMP --> RESOL[resolution_time]
    METRICS_COMP --> QT[queue_time]
    METRICS_COMP --> OT[owner_time]
    RESP --> BREACH{Breached?}
    RESOL --> BREACH
    BREACH --> |Yes| STORE_B[sla_metric.breached=True]
    BREACH --> |No| STORE_OK[sla_metric.breached=False]
    STORE_B --> NEXT[Next ticket]
    STORE_OK --> NEXT
    NEXT --> |more| GET_TICKETS
    NEXT --> |done| END([END])
```

## Компоненты SLA Engine

| Компонент | Файл | Назначение |
|-----------|------|------------|
| Business Hours | `services/sla/business_hours.py` | Определение рабочих часов (24/7, weekday, custom) |
| Pause Engine | `services/sla/pause_engine.py` | Исключение pending-времени из метрик |
| Rule Engine | `services/sla/rule_engine.py` | Сопоставление тикетов с SLA-определениями |
| Metrics Engine | `services/sla/metrics_engine.py` | Расчёт 4 типов метрик с кэшированием пауз |
| Orchestrator | `services/sla_engine.py` | Координация и идемпотентность |

## Безопасность

- JWT аутентификация с access/refresh токенами
- Password hashing через bcrypt
- Ролевая модель: admin, analyst, team_lead, viewer
- Все пароли и ключи только через переменные окружения
- CORS настройки для frontend origin
