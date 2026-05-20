# Kubernetes Architecture v1.1.0

## Namespace: `sla-platform`

### Deployments

| Deployment | Replicas | HPA | Resources | Port |
|-----------|----------|-----|-----------|------|
| backend | 2 | CPU 70% | 512Mi/1CPU | 8000 |
| frontend | 2 | CPU 70% | 256Mi/512mCPU | 80 |
| celery-default | 1 | - | 512Mi/1CPU | - |
| celery-imports | 2 | CPU 70% + queue depth > 100 | 1Gi/2CPU | - |
| celery-sla-compute | 2 | CPU 70% + queue depth > 50 | 2Gi/4CPU | - |
| celery-analytics | 1 | CPU 70% | 1Gi/2CPU | - |
| celery-exports | 1 | CPU 70% | 512Mi/1CPU | - |

### StatefulSets

| StatefulSet | Replicas | Storage | Port |
|------------|----------|---------|------|
| postgres | 2 (primary + replica) | 50Gi each | 5432 |
| redis | 3 | 10Gi each | 6379 |

### ConfigMap
- `app-config`: Backend env vars, CORS origins, feature flags

### Secret
- `app-secrets`: DB password, Redis password, SECRET_KEY, API tokens

### Ingress
- Host: `sla-platform.example.com`
- TLS: cluster-issuer (Let's Encrypt)
- Paths:
  - `/api/*` → backend:8000
  - `/ws/*` → backend:8000
  - `/grafana/*` → grafana:3000
  - `/` → frontend:80

### Autoscaling Rules

```yaml
backend:
  metric: CPU
  target: 70%
  min: 2
  max: 10

sla_compute:
  metric: CPU + celery_queue_length{sla_compute}
  target: 70% CPU or queue > 50
  min: 1
  max: 20
```

## Networking

- All internal: ClusterIP services
- Ingress: Traefik with TLS termination
- WebSocket: Sticky sessions via ingress annotations
- Inter-service: DNS via Kubernetes service discovery
