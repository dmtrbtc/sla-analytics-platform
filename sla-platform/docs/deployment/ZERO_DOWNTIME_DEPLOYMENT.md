# Zero-Downtime Deployment

## Pre-Deployment Checklist

Before any production deployment, verify each item:

- [ ] **Database migration reviewed** — All migrations must be backward-compatible (no destructive column drops, no `NOT NULL` on existing rows without defaults)
- [ ] **Backup taken** — Latest pg_dump backup confirmed on disk:
      ```bash
      ls -la /data/backups/postgres/backup_latest.dump
      ```
- [ ] **Health endpoint responding** — Current production health check passes:
      ```bash
      curl -f https://app.example.com/health
      ```
- [ ] **Staging deployed & verified** — The exact same build/tag has been deployed to staging and passed integration tests
- [ ] **Feature flags reviewed** — All new feature flags default to `false` in production
- [ ] **Logging & monitoring online** — Grafana dashboards responsive, Loki receiving logs, alert rules configured for new endpoints
- [ ] **Rollback plan documented** — Steps to revert both code and database (see [Rollback Procedure](#rollback-procedure))
- [ ] **CI pipeline green** — All tests, linting, and security scans pass on the target branch
- [ ] **Communication sent** — Deploy window announced to stakeholders (expected duration, risk level)

## Rolling Update (Zero-Downtime)

The application supports rolling updates via Docker Compose with the HA overlay. This is the standard deploy method.

### Procedure

1. **Pull latest code & images**:
   ```bash
   git pull origin main
   docker compose -f docker-compose.yml -f docker-compose.ha.yml pull
   ```

2. **Run database migrations** (safe, additive only):
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.ha.yml run --rm backend \
     alembic upgrade head
   ```

3. **Rolling restart of backend** — Start new containers before stopping old ones:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d --no-deps \
     --scale backend=3 backend
   # Wait for new replicas to pass health checks
   docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d --no-deps \
     --scale backend=2 backend
   ```

4. **Rolling restart of worker**:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d --no-deps \
     --scale worker=3 worker
   docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d --no-deps \
     --scale worker=2 worker
   ```

5. **Update frontend & Caddy**:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d --no-deps frontend caddy
   ```

### Verification

After each step, confirm:

```bash
# Health check
curl -f https://app.example.com/health

# Replica count (should be at least 2)
curl -s https://app.example.com/health | jq '.replicas | length'

# Worker responsiveness
docker compose exec worker celery -A app.core.celery_app status

# Recent logs are error-free
docker compose logs --tail=20 backend
```

## Blue-Green Deployment

For high-risk releases or major version upgrades, use a blue-green strategy with a separate stack and a Caddy config swap.

### Setup

Two identical stacks run in parallel:

```
# Blue (current production)
docker compose -p sla-blue -f docker-compose.yml -f docker-compose.ha.yml up -d

# Green (staged release)
docker compose -p sla-green -f docker-compose.yml -f docker-compose.ha.yml up -d
```

### Caddy Router

Caddy (or a cloud load balancer) switches traffic by changing a single upstream variable:

```
# /etc/caddy/Caddyfile
@origin {
    header ?X-Deploy-Version "green"
}
reverse_proxy @origin sla-green_backend:8000
reverse_proxy                     sla-blue_backend:8000   # default
```

### Switchover

```bash
# 1. Run migrations on green
docker compose -p sla-green exec backend alembic upgrade head

# 2. Warm the green stack
curl -f http://sla-green_backend:8000/health

# 3. Switch traffic — update Caddyfile to point all traffic to green
#    Reload Caddy without downtime
docker compose -p sla-blue exec caddy caddy reload

# 4. Monitor blue for drain (in-flight requests complete)
docker compose -p sla-blue logs --tail=50 backend

# 5. After verification, tear down blue
docker compose -p sla-blue down
```

### Rollback during Blue-Green

Simply switch the Caddy upstream back to blue — green was never exposed to live traffic.

## Database Migration Safety

All migrations **must** be backward-compatible to allow code rollback without data loss.

### Safe patterns ✅

| Operation                    | Safe? | Guideline                                |
| ---------------------------- | ----- | ---------------------------------------- |
| `ADD COLUMN ... DEFAULT NULL` | Yes   | Old code ignores unknown columns         |
| `CREATE INDEX CONCURRENTLY`   | Yes   | No table lock, non-blocking              |
| `ADD COLUMN ... DEFAULT value` | Yes  | Use `ALTER TABLE ... ALTER COLUMN ... SET DEFAULT` in a separate step |
| `CREATE TABLE`               | Yes   | Old code never references new tables     |

### Unsafe patterns ❌

| Operation                  | Why it breaks                                          |
| -------------------------- | ------------------------------------------------------ |
| `DROP COLUMN`              | Old code still references the column                   |
| `ALTER COLUMN ... NOT NULL` | Existing rows may have NULLs, and old code may insert NULLs |
| `RENAME COLUMN`            | Old code references old name                           |
| `DROP TABLE`               | Old code references the table                          |

### Safe migration workflow

1. **Phase 1 (additive)** — Deploy code that can handle both old and new schema:
   ```sql
   ALTER TABLE contracts ADD COLUMN billing_cycle VARCHAR(20) DEFAULT NULL;
   CREATE INDEX CONCURRENTLY idx_contracts_billing_cycle ON contracts(billing_cycle);
   ```

2. **Phase 2 (populate)** — Backfill data in the background:
   ```python
   # celery task or batch job
   Contract.query.filter(Contract.billing_cycle.is_(None)).update({...})
   ```

3. **Phase 3 (enforce)** — After all old code is removed, add constraints:
   ```sql
   ALTER TABLE contracts ALTER COLUMN billing_cycle SET NOT NULL;
   ```

## Frontend Deployment

### Static Files

The frontend is an SPA served by an nginx container. Deploy new static assets without downtime:

```bash
# 1. Build the frontend image
docker compose build frontend

# 2. Push to registry
docker compose push frontend

# 3. Rolling update
docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d --no-deps frontend
```

The nginx container has a short startup time (< 2s), and the old container continues serving until the new one is healthy.

### CDN Integration

For faster global distribution:

1. Build frontend artifacts locally:
   ```bash
   cd frontend && npm run build
   ```

2. Upload to CDN bucket:
   ```bash
   aws s3 sync dist/ s3://sla-platform-cdn/releases/v1.2.3/ --cache-control "public, max-age=31536000, immutable"
   ```

3. Update Caddy to point to the new CDN release:
   ```
   @static path /assets/*
   header @static Cache-Control "public, max-age=31536000, immutable"
   reverse_proxy @static https://cdn.example.com/v1.2.3
   ```

## Rollback Procedure

### Code Rollback

```bash
# 1. Revert to previous tag
git checkout tags/v1.0.0

# 2. Rebuild and redeploy
docker compose -f docker-compose.yml -f docker-compose.ha.yml build backend worker
docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d --no-deps backend worker

# 3. Revert frontend
docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d --no-deps frontend
```

### Database Rollback

```bash
# Downgrade one migration
docker compose exec backend alembic downgrade -1

# Or restore from backup (if migrations are not cleanly reversible)
docker compose exec postgres /docker/scripts/restore.sh /data/backups/postgres/backup_latest.dump
```

### Full Rollback (Code + DB)

1. Stop services (except postgres):
   ```bash
   docker compose stop backend worker frontend caddy
   ```
2. Revert code to previous tag
3. Restore database from pre-deploy backup:
   ```bash
   docker compose exec postgres /docker/scripts/restore.sh /data/backups/postgres/backup_before_deploy.dump
   ```
4. Rebuild images and restart:
   ```bash
   docker compose build backend worker frontend
   docker compose up -d
   ```

## Post-Deployment Verification

- [ ] **Health endpoint** — `curl -f https://app.example.com/health` returns 200
- [ ] **API smoke test** — Create, read, update, delete a test entity
- [ ] **WebSocket connectivity** — Browser console shows successful WS handshake
- [ ] **Celery task processing** — Submit a test report task and confirm completion:
      ```bash
      docker compose exec backend celery -A app.core.celery_app inspect active
      ```
- [ ] **Database migrations** — Confirm alembic head matches expected:
      ```bash
      docker compose exec backend alembic current
      ```
- [ ] **Error rate** — Grafana dashboard shows no spike in 5xx responses
- [ ] **Latency** — P95 response time within baseline (check Datadog / Grafana)
- [ ] **Backup** — Take a fresh backup immediately after successful deployment:
      ```bash
      docker compose exec postgres /docker/scripts/backup.sh /data/backups/postgres
      ```
