# SLA Analytics Platform

Enterprise-grade SLA analytics platform for OTRS/Znuny 7.2 environments.

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy async, Celery
- **Frontend:** React 18, TypeScript, Ant Design 5, ECharts, AG Grid
- **Database:** PostgreSQL 16
- **Queue:** Redis 7 + Celery
- **Deployment:** Docker Compose

## Quick Start

```bash
cp .env.example .env
docker compose up -d
make migrate

# Frontend: http://localhost
# API Docs: http://localhost:8000/api/docs
```
