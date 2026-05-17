# Disaster Recovery

## Overview

This document defines procedures for restoring the SLA Analytics Platform after catastrophic failure, data loss, or region-level outage.

**Prerequisites:**
- Off-site backups (S3, GCS, or Azure Blob)
- Infrastructure-as-code (compose files, Terraform, or CloudFormation)
- Documented secrets (stored in a secure vault — 1Password, Vault, AWS Secrets Manager)
- Access to cloud console or API credentials

---

## Disaster Recovery Checklist

Use this ordered checklist during any recovery event. Do **not** skip steps.

### Phase 1 — Assessment

- [ ] **Declare incident** — Notify stakeholders: "We are executing DR procedure."
- [ ] **Determine scope** — Is this a single-service failure, data corruption, or full region outage?
- [ ] **Identify RTO / RPO** — Based on severity:
  - Tier 1 (full outage): RTO < 1 hour, RPO < 15 min
  - Tier 2 (data corruption): RTO < 4 hours, RPO < 1 hour
  - Tier 3 (single service): RTO < 30 min, no data loss expected
- [ ] **Check backups** — Verify latest backup exists and is not corrupt:
      ```bash
      aws s3 ls s3://sla-platform-backups/daily/backup_latest.dump
      sha256sum -c /data/backups/postgres/checksums.txt
      ```
- [ ] **Snapshot status** — Record current state: what is running, what is down, what data is affected.

### Phase 2 — Isolation

- [ ] **Stop all non-essential services** — Prevent further damage:
      ```bash
      docker compose stop backend worker frontend caddy
      ```
- [ ] **Disable incoming traffic** — Update DNS TTL to 60s and point to a maintenance page, or close load balancer ports:
      ```bash
      # AWS ALB example
      aws elbv2 modify-listener --listener-arn arn:... --default-actions Type=fixed-response,FixedResponseConfig={StatusCode=503,ContentType=text/plain,MessageBody="Under maintenance"}
      ```
- [ ] **Snapshot the current (corrupted) state** — Retain for post-mortem analysis:
      ```bash
      docker compose exec postgres pg_dump -U sla_user -d sla_platform --format=custom \
        --file=/tmp/corrupted_state.dump
      docker cp $(docker compose ps -q postgres):/tmp/corrupted_state.dump /data/forensics/
      ```

### Phase 3 — Restore Infrastructure

- [ ] **Provision new hosts** — If the entire environment is lost:
      ```bash
      # Terraform example
      cd terraform/environments/production
      terraform init
      terraform apply -auto-approve
      ```
- [ ] **Recreate Docker network and volumes**:
      ```bash
      docker network create sla_network
      docker volume create postgres_data
      docker volume create caddy_data
      docker volume create caddy_config
      ```
- [ ] **Pull infrastructure images**:
      ```bash
      docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
      ```

### Phase 4 — Restore Database

- [ ] **Start postgres only**:
      ```bash
      docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d postgres
      docker compose exec postgres pg_isready -U sla_user
      ```
- [ ] **Restore from latest clean backup**:
      ```bash
      # Download from off-site storage if needed
      aws s3 cp s3://sla-platform-backups/daily/backup_latest.dump /data/backups/postgres/

      docker compose exec -T postgres /docker/scripts/restore.sh /data/backups/postgres/backup_latest.dump
      ```
- [ ] **Verify data integrity**:
      ```bash
      docker compose exec postgres psql -U sla_user -d sla_platform -c "
        SELECT 'users' AS tbl, count(*) AS cnt FROM users
        UNION ALL
        SELECT 'organizations', count(*) FROM organizations
        UNION ALL
        SELECT 'contracts', count(*) FROM contracts
        UNION ALL
        SELECT 'sla_definitions', count(*) FROM sla_definitions;
      "
      ```
- [ ] **Run any pending migrations** (if backup is older than current schema):
      ```bash
      docker compose run --rm backend alembic upgrade head
      ```

### Phase 5 — Restore Application

- [ ] **Start Redis**:
      ```bash
      docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d redis
      ```
- [ ] **Start backend** (single replica first):
      ```bash
      docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d backend
      curl -f http://localhost:8000/health
      ```
- [ ] **Start worker**:
      ```bash
      docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d worker
      ```
- [ ] **Start frontend and Caddy**:
      ```bash
      docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d frontend caddy
      ```
- [ ] **Scale up backend and worker**:
      ```bash
      docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale backend=2 --scale worker=2
      ```

### Phase 6 — Verification

- [ ] **Health check passes**:
      ```bash
      curl -f https://app.example.com/health
      ```
- [ ] **API functional test**:
      ```bash
      # Login
      TOKEN=$(curl -s -X POST https://app.example.com/api/v1/auth/login \
        -H "Content-Type: application/json" \
        -d '{"email":"admin@example.com","password":"..."}' | jq -r '.access_token')

      # Fetch dashboard data
      curl -s -H "Authorization: Bearer $TOKEN" https://app.example.com/api/v1/dashboard/stats | jq .
      ```
- [ ] **Celery worker responsive**:
      ```bash
      docker compose exec backend celery -A app.core.celery_app status
      ```
- [ ] **WebSocket connection confirmed** — Open browser DevTools → Network → WS → `wss://app.example.com/ws?token=...`
- [ ] **Alerting restored** — Verify Prometheus targets are UP, Grafana datasources connected, alert rules firing as expected
- [ ] **DNS / Load balancer traffic restored** — Remove maintenance redirect

### Phase 7 — Post-Recovery

- [ ] **Take a fresh backup** of the recovered state:
      ```bash
      docker compose exec postgres /docker/scripts/backup.sh /data/backups/postgres
      ```
- [ ] **Document the incident** — Root cause, recovery duration, data loss (if any), improvements needed
- [ ] **Schedule post-mortem** — Within 48 hours
- [ ] **Update DR runbook** — Incorporate lessons learned

---

## Database Restore from Backup

### Full Restore (custom format)

```bash
docker compose exec -T postgres /docker/scripts/restore.sh /data/backups/postgres/backup_20260515_020000.dump
```

### Point-in-Time Recovery (PITR)

Requires WAL archiving to be configured. With continuous WAL archiving:

```bash
# 1. Restore base backup
docker compose exec postgres /docker/scripts/restore.sh /data/backups/postgres/base_backup.dump

# 2. Configure recovery.conf or use pg_rewind
# 3. Set recovery target time
#    restore_command = 'cp /data/wal_archive/%f %p'
#    recovery_target_time = '2026-05-15 01:45:00 UTC'

# 4. Start postgres in recovery mode
docker compose restart postgres
```

### Restore to a Point Before a Known Bad Migration

```bash
# 1. Identify the migration to revert
docker compose exec backend alembic history

# 2. Downgrade
docker compose exec backend alembic downgrade <previous_revision>

# 3. Restore data that was affected (if any)
#    Import from a table-level backup or re-run idempotent seed scripts
```

---

## Full Infrastructure Rebuild from Scratch

When all infrastructure is lost (cloud account compromise, region failure, physical disaster):

1. **Recreate cloud resources**:
   ```bash
   terraform -chdir=terraform/production init
   terraform -chdir=terraform/production apply
   ```

2. **Clone repository**:
   ```bash
   git clone https://github.com/org/sla-platform.git
   cd sla-platform
   git checkout v1.0.0  # or latest stable tag
   ```

3. **Restore secrets** — Pull from vault:
   ```bash
   op inject -i .env.example -o .env
   ```

4. **Provision Docker environment**:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d postgres redis
   ```

5. **Download and restore database**:
   ```bash
   aws s3 sync s3://sla-platform-backups/ /data/backups/
   docker compose exec -T postgres /docker/scripts/restore.sh /data/backups/postgres/backup_latest.dump
   ```

6. **Build and start all services**:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml build
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

7. **Verify** — Run Phase 6 verification steps above.

---

## Data Integrity Verification

### Automated checks (run post-recovery and on a schedule)

```bash
# Row counts match expected baselines
docker compose exec postgres psql -U sla_user -d sla_platform -f /docker/scripts/verify_integrity.sql

# Foreign key integrity
docker compose exec postgres psql -U sla_user -d sla_platform -c "
  SELECT
    'orphan_contracts' AS check_name,
    count(*) AS violations
  FROM contracts c
  LEFT JOIN organizations o ON o.id = c.organization_id
  WHERE o.id IS NULL;
"

# No duplicate primary keys
docker compose exec postgres psql -U sla_user -d sla_platform -c "
  SELECT schemaname, tablename, string_agg(column_name, ',') AS pk_columns
  FROM pg_indexes i
  JOIN pg_class c ON c.relname = i.tablename
  WHERE i.indexdef LIKE '%UNIQUE%' OR i.indexdef LIKE '%PRIMARY KEY%'
  GROUP BY schemaname, tablename;
"
```

### Manual verification tasks

- [ ] Login as an admin user — all menus render
- [ ] Create a test contract — validates write path
- [ ] Generate an SLA report — validates Celery + DB read path
- [ ] Trigger a notification — validates Redis pub/sub
- [ ] Upload a test file — validates import pipeline

---

## Recovery Time Objectives (RTO) / Recovery Point Objectives (RPO)

| Disaster Scenario                  | Target RTO | Target RPO | Recovery Strategy                  |
| ---------------------------------- | ---------- | ---------- | ---------------------------------- |
| Single backend container crash     | < 5 min    | None       | Docker auto-restart + health check |
| Worker failure / task queue backup | < 15 min   | None       | Scale up workers, restart Celery   |
| Redis primary failure              | < 2 min    | < 5 sec    | Sentinel auto-failover             |
| PostgreSQL corruption              | < 2 hours  | < 1 hour   | Restore from latest backup + WAL   |
| Full region outage                 | < 4 hours  | < 15 min   | Terraform rebuild + offsite backup |
| Accidental data deletion           | < 1 hour   | < 5 min    | PITR to just before deletion       |
| Security compromise / data breach  | < 4 hours  | Point of compromise | Forensics snapshot + clean rebuild |

### Improving RTO/RPO

- **WAL archiving every 60s** (reduces RPO to < 1 min)
- **Synchronous replication to a warm standby** (reduces RTO for DB failure to < 30s)
- **Multi-region active-active** (eliminates RTO for region failure, but adds complexity)
- **Pre-warmed Docker images** — `docker compose pull` in a cron job ensures images are cached locally
- **Regular DR drills** — Execute this checklist quarterly and measure actual RTO/RPO against targets
