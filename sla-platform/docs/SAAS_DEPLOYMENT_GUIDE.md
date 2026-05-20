# SaaS Deployment Guide v1.1.0

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Ingress    │────▶│  Backend API  │────▶│  PostgreSQL  │
│  (Traefik)  │     │  (FastAPI)    │     │  (HA + Rep)  │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────▼───────┐     ┌──────────────┐
                    │  Redis       │◀────│  Celery      │
                    │  (Cluster)   │     │  Workers     │
                    └──────────────┘     └──────────────┘
```

## Components

### 1. Backend API (FastAPI)
- 2+ replicas, HPA at 70% CPU
- Routes: `/api/v1/*`
- WebSocket: `/ws/*`
- Health: `/health`

### 2. Celery Workers
| Queue | Min Replicas | Max | Description |
|-------|-------------|-----|-------------|
| default | 1 | 5 | Generic tasks |
| imports | 1 | 10 | Ticket imports |
| sla_compute | 1 | 20 | SLA computation |
| analytics | 1 | 5 | Analytics refresh |
| exports | 1 | 3 | Report exports |
| notifications | 0 | 3 | Notifications |

### 3. PostgreSQL HA
- Primary + 1 replica (async streaming)
- PVC: 50Gi primary, 50Gi replica
- Automated failover

### 4. Redis Cluster
- 3 nodes (1 master + 2 replicas)
- PVC: 10Gi each
- Sentinel for HA

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL async URL | postgresql+asyncpg://... |
| REDIS_HOST | Redis host | redis |
| CELERY_BROKER_URL | Redis broker | redis://redis:6379/0 |
| SECRET_KEY | JWT signing key | (required) |
| ENCRYPTION_ENABLED | Export encryption | true |
| REDIS_SENTINEL_HOSTS | HA Redis sentinels | [] |
| POSTGRES_REPLICA_URL | Read replica | "" |

## Deployment

```bash
# Create namespace
kubectl apply -f deploy/k8s/01-namespace.yaml

# Deploy infrastructure
kubectl apply -f deploy/k8s/02-configmap.yaml
kubectl apply -f deploy/k8s/03-secret.yaml
kubectl apply -f deploy/k8s/10-postgres-ha.yaml
kubectl apply -f deploy/k8s/11-pvc.yaml

# Deploy application
kubectl apply -f deploy/k8s/04-backend.yaml
kubectl apply -f deploy/k8s/05-frontend.yaml
kubectl apply -f deploy/k8s/06-celery.yaml
kubectl apply -f deploy/k8s/07-ingress.yaml

# Configure autoscaling
kubectl apply -f deploy/k8s/08-autoscaling.yaml

# Via Helm
helm install sla-platform deploy/helm/sla-platform/ --values deploy/helm/sla-platform/values/prod.yaml
```

## Monitoring

- Grafana: `deploy/grafana/dashboards/`
- Prometheus rules: `deploy/prometheus/rules/`
- Alerts: SLA breaches, queue depth, worker health, failover
