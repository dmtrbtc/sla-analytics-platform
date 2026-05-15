# Database Maintenance

## Regular Backups

Schedule daily backups via cron:
```bash
0 2 * * * /docker/scripts/backup.sh /data/backups/postgres
```

Backups are retained for 30 days by default (configurable via `RETENTION_DAYS`).

## Vacuum & Analyze

PostgreSQL autovacuum runs by default. To manually vacuum:
```bash
docker compose exec postgres psql -U sla_user -d sla_platform -c "VACUUM ANALYZE;"
```

## Reindexing

For high-traffic tables:
```bash
docker compose exec postgres psql -U sla_user -d sla_platform -c "REINDEX DATABASE sla_platform;"
```

## Monitoring

Check DB size:
```bash
docker compose exec postgres psql -U sla_user -d sla_platform -c "
SELECT pg_size_pretty(pg_database_size('sla_platform'));
"
```

Check table sizes:
```bash
docker compose exec postgres psql -U sla_user -d sla_platform -c "
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 10;
"
```
