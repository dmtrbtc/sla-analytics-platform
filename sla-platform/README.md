# SLA Analytics Platform

Enterprise-grade SLA analytics platform for OTRS/Znuny 7.2 environments.

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy async, Celery
- **Frontend:** React 18, TypeScript, Ant Design 5, ECharts, AG Grid
- **Database:** PostgreSQL 16
- **Queue:** Redis 7 + Celery
- **Deployment:** Docker Compose (Caddy reverse proxy)

## Quick Start (Development)

```bash
cp .env.example .env
docker compose up -d
make migrate

# Frontend: http://localhost:80
# API Docs: http://localhost:8000/api/docs
```

## Production Deployment

```bash
cp .env.example .env
docker compose -f docker-compose.prod.yml up -d

# Set DOMAIN env var for automatic HTTPS (optional):
#   DOMAIN=api.example.com docker compose -f docker-compose.prod.yml up -d
```

Uses [Caddy](https://caddyserver.com/) reverse proxy with automatic HTTPS,
WebSocket support, gzip/zstd compression, and 100MB upload limit.
