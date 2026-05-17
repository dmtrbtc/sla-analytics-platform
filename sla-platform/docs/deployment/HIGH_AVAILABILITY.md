# High Availability

## Overview

This document covers production-grade high-availability configuration for the SLA Analytics Platform. Apply the HA overlay alongside the base compose file:

```bash
docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d
```

## Horizontal Scaling

### Backend

The backend API (FastAPI/Uvicorn) is stateless and scales horizontally. Run multiple replicas behind the Caddy reverse proxy:

```bash
docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d --scale backend=3 backend
```

Caddy distributes requests across healthy replicas automatically (round-robin). No session affinity is needed because JWT tokens carry all session state.

### Worker

Celery workers process background tasks (imports, SLA reports, notifications). Multiple workers consume from the same Redis broker:

```yaml
# docker-compose.ha.yml
worker:
  deploy:
    replicas: 2
    resources:
      limits:
        cpus: "4"
        memory: "4G"
```

Worker queues are consumed fairly — adding replicas increases throughput for long-running jobs without task duplication.

### Caddy

Caddy itself can be scaled behind a cloud load balancer (ELB, HAProxy) for multi-AZ deployments:

```yaml
caddy:
  deploy:
    replicas: 2
```

## Database Replication

### Primary / Replica Setup

A `postgres-replica` service provides a read-only copy for reporting and analytics queries:

```yaml
postgres-replica:
  image: postgres:16-alpine
  environment:
    - PGREPL_MODE=replica
    - PGREPL_PRIMARY_HOST=postgres
```

**Configuration steps:**

1. Set up the replication user on the primary:
   ```sql
   CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'strong_password';
   ```

2. Configure `pg_hba.conf` to allow replication:
   ```
   host replication replicator postgres-replica md5
   ```

3. Reference the replica in read-only code paths (e.g., reporting endpoints) via a separate `DATABASE_URL_REPLICA` environment variable.

### Streaming Replication

- PostgreSQL 16 native streaming replication
- Synchronous commit mode for zero data loss (tunable)
- Automatic failover requires an external tool (Patroni, repmgr, or a managed cloud provider)

## Redis Sentinel

Redis Sentinel provides automatic failover for the Redis broker/cache layer:

```yaml
redis-sentinel:
  image: redis:7-alpine
  command: >
    sh -c "echo 'sentinel monitor mymaster redis 6379 2
    sentinel down-after-milliseconds mymaster 5000
    sentinel failover-timeout mymaster 60000
    sentinel parallel-syncs mymaster 1' > /tmp/sentinel.conf &&
    redis-sentinel /tmp/sentinel.conf"
```

- **Quorum**: 2 — at least 2 sentinels must agree before failover
- **Down-after**: 5s — marks primary as down after 5s unavailability
- **Failover-timeout**: 60s — failover must complete within 60s

When the Redis primary fails, Sentinel promotes a replica. The application should connect via the Sentinel **host** and port **26379** to discover the current primary.

## Resource Limits

All services include CPU/memory limits and reservations to prevent resource starvation:

| Service    | CPU Limit | Memory Limit | CPU Reservation | Memory Reservation |
| ---------- | --------- | ------------ | --------------- | ------------------ |
| backend    | 2         | 2G           | 0.5             | 512M               |
| worker     | 4         | 4G           | 1               | 1G                 |
| postgres   | 4         | 4G           | 1               | 1G                 |
| postgres-replica | 4  | 4G           | 1               | 1G                 |
| redis      | 1         | 1G           | 0.25            | 256M               |
| redis-sentinel | 0.5   | 512M         | 0.1             | 128M               |
| frontend   | 0.5       | 512M         | 0.1             | 128M               |
| caddy      | 1         | 512M         | 0.25            | 128M               |

Reservations guarantee the minimum resources. Limits prevent any single service from consuming all host resources.

## Health Checks

Every service has a health check that Docker uses to determine container readiness:

| Service    | Check                                | Interval | Timeout | Start Period |
| ---------- | ------------------------------------ | -------- | ------- | ------------ |
| backend    | `curl -f http://localhost:8000/health` | 30s      | 10s     | 40s          |
| worker     | `celery -A app.core.celery_app status` | 30s      | 10s     | 60s          |
| postgres   | `pg_isready -U sla_user`              | 10s      | 5s      | —            |
| redis      | `redis-cli ping`                      | 10s      | 5s      | —            |
| frontend   | `wget -qO- http://localhost:80`       | 30s      | 10s     | —            |
| caddy      | `wget -qO- http://localhost:80/health` | 30s      | 10s     | —            |

Services with `depends_on` + `condition: service_healthy` (backend, worker) will not start until their dependencies pass health checks.

## Rolling Update Strategy

Deploy changes with zero downtime using rolling updates:

```yaml
deploy:
  update_config:
    order: start-first
    failure_action: rollback
    monitor: 30s
    max_failure_ratio: 0.3
```

- **start-first**: new container starts before the old one is stopped (requires service port mapping or overlay networking)
- **rollback**: if the update fails, Docker automatically reverts to the previous configuration
- **monitor 30s**: waits 30s to verify the new container is healthy

To perform a rolling update:

```bash
# Rebuild the image
docker compose build backend

# Push to registry (if using)
docker compose push backend

# Update with zero downtime
docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d --no-deps --scale backend=2 backend
```

## External PostgreSQL Configuration

For managed PostgreSQL (RDS, Cloud SQL, Azure DB), disable the containerized postgres and configure via environment:

```yaml
services:
  postgres:
    profile: donotstart
    # Not started — external DB handles persistence

  backend:
    environment:
      DATABASE_URL: postgresql://sla_user:password@host:5432/sla_platform
      DATABASE_URL_REPLICA: postgresql://sla_user:password@replica-host:5432/sla_platform
      POOL_SIZE: 20
      POOL_OVERFLOW: 10
    depends_on:
      postgres:  # Remove this dependency when using external DB
        condition: service_healthy  # Comment out
```

Recommended managed DB settings:
- **Instance class**: db.r6g.large (or equivalent)
- **Storage**: 100 GB minimum, provisioned IOPS (3000+)
- **Multi-AZ**: enabled for automatic failover
- **Backup retention**: 30 days
- **Connection pool**: PgBouncer sidecar or RDS Proxy

## External Redis Configuration

For managed Redis (ElastiCache, Memorystore), disable containerized Redis and sentinel:

```yaml
services:
  redis:
    profile: donotstart

  backend:
    environment:
      REDIS_HOST: primary-redis.xxxxx.ng.0001.use1.cache.amazonaws.com
      REDIS_PORT: 6379
      REDIS_SENTINEL_HOSTS: sentinel-1:26379,sentinel-2:26379,sentinel-3:26379
      REDIS_SENTINEL_MASTER: mymaster
```

## Backup Verification Procedure

1. **Daily automated validation** — Restore the latest backup to a staging DB and run integrity checks:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.observability.yml run --rm postgres \
     /docker/scripts/restore.sh /data/backups/postgres/backup_latest.dump sla_platform_verify
   docker compose exec -T postgres psql -U sla_user -d sla_platform_verify \
     -c "SELECT count(*) AS user_count FROM users; SELECT count(*) AS contracts FROM contracts;"
   docker compose exec -T postgres psql -U sla_user -d sla_platform_verify \
     -c "VACUUM ANALYZE;"
   ```

2. **Restore test** — Every 7 days, run a full restore to an isolated environment and confirm the application starts:
   ```bash
   docker compose exec postgres /docker/scripts/restore.sh /data/backups/postgres/backup_latest.dump
   docker compose exec backend alembic upgrade head
   curl -f http://localhost:8000/health
   ```

3. **Backup integrity** — Verify checksums on compressed backups:
   ```bash
   sha256sum /data/backups/postgres/*.dump > /data/backups/postgres/checksums.txt
   sha256sum -c /data/backups/postgres/checksums.txt
   ```

## Disaster Recovery Checklist

See [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) for the full step-by-step disaster recovery procedure.
