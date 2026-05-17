# Monitoring Setup

## Prometheus
Metrics endpoint: `/metrics` (exposed by prometheus-fastapi-instrumentator)

### Custom Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `celery_task_duration_seconds` | Histogram | Duration of Celery tasks by name and status |
| `celery_tasks_total` | Counter | Total Celery tasks by name and status |
| `db_query_duration_seconds` | Histogram | Database query latency |
| `sla_metrics_processed_total` | Counter | SLA metrics processed |
| `import_pipeline_duration_seconds` | Histogram | Import pipeline stage duration |
| `imports_total` | Counter | Total imports by status |
| `active_imports` | Gauge | Currently active imports |
| `queue_backlog` | Gauge | Queue backlog by queue name |
| `app_errors_total` | Counter | Application errors by type and endpoint |

### Scrape Config
Add to prometheus.yml:
```yaml
scrape_configs:
  - job_name: 'sla-platform'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

## Grafana
Dashboard template: `grafana-dashboard.json`
Import into Grafana via UI or provisioning.

## Flower
Celery monitoring: http://flower:5555
Launched via: `docker compose -f docker-compose.observability.yml up -d`

## Alerting
Prometheus alert rules: `prometheus-alerts.yml`
