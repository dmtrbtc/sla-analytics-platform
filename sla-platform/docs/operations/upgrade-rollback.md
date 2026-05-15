# Upgrade & Rollback

## Upgrade

1. Pull latest images:
   ```bash
   git pull origin main
   ```

2. Rebuild and restart:
   ```bash
   docker compose build backend
   docker compose up -d
   ```

3. Run migrations:
   ```bash
   docker compose exec backend alembic upgrade head
   ```

4. Verify health:
   ```bash
   curl http://localhost:8000/health
   ```

## Rollback

1. Revert code:
   ```bash
   git revert HEAD
   ```

2. Rebuild previous image:
   ```bash
   docker compose build backend
   docker compose up -d
   ```

3. Revert DB migration:
   ```bash
   docker compose exec backend alembic downgrade -1
   ```

## Database-Only Rollback

If code change was additive only (no schema change), reverting the migration may be unnecessary.
Always verify with staging before production rollback.
