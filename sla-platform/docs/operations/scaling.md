# Scaling

## Horizontal Scaling (Backend)

Increase backend replicas:
```bash
docker compose up -d --scale backend=3 backend
```

A reverse proxy (Caddy in production) distributes requests across replicas.

## Worker Scaling

Increase Celery worker concurrency or instances:
```bash
docker compose up -d --scale worker=2 worker
```

## Database

- PostgreSQL is containerized with persistent volume.
- For production, use a managed PostgreSQL (RDS, Cloud SQL) with connection pooling (PgBouncer).
- Set `DATABASE_URL` env var to point to external database.

## Caching

Current rate limiter is in-memory. For multi-replica deployments:
- Replace with Redis-based rate limiter.
- Set `REDIS_HOST` env var for external Redis.

## Frontend

Frontend is nginx serving static files. For scale:
- Use CDN for static assets.
- Increase nginx worker processes in Caddy config.
