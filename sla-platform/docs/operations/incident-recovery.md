# Incident Recovery

## Application Crash

1. Check container status:
   ```bash
   docker compose ps
   docker compose logs --tail=50 backend
   ```

2. Restart failed service:
   ```bash
   docker compose restart backend
   ```

3. If persistent, rebuild:
   ```bash
   docker compose build backend && docker compose up -d backend
   ```

## Database Corruption

1. Stop all services except postgres:
   ```bash
   docker compose stop backend worker frontend
   ```

2. Restore from latest backup:
   ```bash
   docker compose exec postgres /scripts/restore.sh /data/backups/postgres/backup_latest.dump
   ```

3. Verify data integrity:
   ```bash
   docker compose exec postgres psql -U sla_user -d sla_platform -c "SELECT count(*) FROM users;"
   ```

4. Restart all services:
   ```bash
   docker compose up -d
   ```

## Redis Failure

- Celery tasks will retry automatically (default: 3 retries, exponential backoff).
- To reset Redis:
  ```bash
  docker compose restart redis
  ```

## Full Outage Recovery

1. Ensure postgres is healthy:
   ```bash
   docker compose exec postgres pg_isready -U sla_user
   ```

2. Re-run DB migrations:
   ```bash
   docker compose exec backend alembic upgrade head
   ```

3. Seed default data:
   ```bash
   docker compose exec backend python -c "from app.seeds import seed_admin_user, seed_sla_definitions; seed_admin_user(); seed_sla_definitions()"
   ```
