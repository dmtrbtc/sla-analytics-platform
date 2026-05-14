# Release Notes — v0.1.0

**Release Date:** 2026-05-14  
**Version:** 0.1.0  
**Status:** Initial Public Release

---

## Overview

SLA Analytics Platform v0.1.0 is the first public release — a production-ready analytics platform for OTRS/Znuny environments. The platform automates SLA computation, provides real-time dashboards, team analytics, and exportable reports.

## Features

### Import Pipeline
- Full 7-step Celery chain: Validate → Backlog → Parse → Normalize → Rebuild → SLA → Complete
- CSV import via Polars with deduplication
- 20+ event types normalized from OTRS vCustomerTimeline exports
- Idempotent reprocessing — zero duplicates on re-run
- Bulk INSERT via executemany (30k rows in ~13s)

### SLA Engine
- 4 metric types: response_time, resolution_time, queue_time, owner_time
- Flexible SLA definitions: queue_pattern (fnmatch) + priority scoring
- Business hours: 24/7, weekday-only, custom JSON schedules
- Pause engine: pending-state time excluded from metrics
- 4 seeded definitions: Critical Priority (1h/8h), High Priority (4h/16h), Service Desk (2h/24h), Standard Support (8h/40h)

### Analytics & Dashboards
- 14 aggregated KPI metrics on dashboard overview
- Queue, state, priority, confidence distributions
- Ticket trends (daily/weekly/monthly)
- Team performance analytics with SLA breach comparison
- Ticket flow Sankey diagrams (queue transitions)
- Approaching-breach detection
- 30s auto-refresh on dashboard

### Reports
- 4 report types: SLA breaches, team performance, ticket lifecycle, imports summary
- XLSX and CSV export via async Celery tasks
- Download via FileResponse

### Operations
- Full audit log for SLA definitions, reprocess, reports
- Import session detail with pipeline steps, stats, errors
- 3 database performance indexes for <30s cleanup on 30k events

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12, FastAPI 0.115, SQLAlchemy 2.0 async |
| Frontend | React 18, TypeScript 5.5, Vite 5 |
| UI | Ant Design 5, ECharts 5, AG Grid 32 |
| Database | PostgreSQL 16 |
| Queue | Redis 7 + Celery 5.4 |
| Processing | Polars 1.5 |
| Export | openpyxl 3.1 |
| Auth | JWT (python-jose) + bcrypt (passlib) |

## Installation

```bash
# Requirements: Docker 24+, Docker Compose v2+
git clone https://github.com/your-org/sla-analytics-platform.git
cd sla-analytics-platform

# Configure environment
cp .env.example .env
# Edit .env (set SECRET_KEY, DB credentials)

# Start
cd sla-platform
docker compose up -d
docker compose exec backend alembic upgrade head

# Access
# Frontend: http://localhost
# API Docs: http://localhost:8000/api/docs
# Health:   http://localhost:8000/health
```

## Known Limitations

1. **Timezone handling**: All timestamps stored as naive UTC. Business hours engine works with naive datetimes only.
2. **Tests**: Placeholder tests only — real test suite pending Phase 4.
3. **Multi-tenancy**: Not supported. Single-org deployment only.
4. **Scalability**: Celery concurrency limited to single worker per queue. Horizontal scaling not configured.
5. **Monitoring**: No Prometheus/Grafana integration (planned Phase 6).
6. **Confidence**: ticket confidence levels are `full`, `partial`, `minimal` — inherited from pipeline heuristics.
7. **OTRS version**: Tested with OTRS/Znuny 7.2 vCustomerTimeline CSV export only.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full changelog.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for upcoming phases:
- Phase 4: Automated tests
- Phase 5: Webhooks & integrations
- Phase 6: Prometheus/Grafana observability
- Phase 7: Multi-tenant & RBAC
- Phase 8: ML predictions & anomaly detection

## Credits

Developed for OTRS/Znuny environments. Built with FastAPI, React, PostgreSQL, and Celery.
