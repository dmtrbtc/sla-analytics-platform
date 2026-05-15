# Troubleshooting

## Backend won't start

Check logs:
```bash
docker compose logs backend
```

Common causes:
- DB not ready: wait for postgres health check
- Migration failure: run `docker compose exec backend alembic upgrade head`
- Port conflict: ensure port 8000 is free

## DB connection errors

Verify postgres is healthy:
```bash
docker compose exec postgres pg_isready -U sla_user
```

Check connection string (DATABASE_URL env var).

## Celery tasks not executing

Check worker logs:
```bash
docker compose logs worker
```

Verify Redis connectivity:
```bash
docker compose exec redis redis-cli ping
```

## Frontend shows blank page

Check nginx logs:
```bash
docker compose logs frontend
```

Verify backend is reachable from frontend container:
```bash
docker compose exec frontend wget -qO- http://backend:8000/health
```

## Prometheus metrics not appearing

Verify `/metrics` endpoint:
```bash
curl http://localhost:8000/metrics | head -5
```

## Rate limiting too aggressive

Adjust requests per minute in `app/core/security_middleware.py`:
```python
_rate_limiter = RateLimiter(requests_per_minute=120)  # default: 60
```
