# Security Status — v0.3.0

## Authentication & Authorization
- JWT-based auth with access + refresh token rotation
- Refresh tokens stored in DB, revoked on logout, expired after 7 days
- Admin-only endpoints (team CRUD, user creation, report generation)
- Token-based WebSocket auth (`/ws?token=...`)

## Middleware
- **Rate Limiter**: Token bucket, 60 req/min per IP+path, excludes `/health`, `/api/docs`, `/api/openapi.json`
- **CORS**: Restricted to configured origins via `settings.CORS_ORIGINS`
- **Global Exception Handler**: All unhandled exceptions return 500 with no stack trace leakage
- **Request Validation**: Pydantic V2 validation on all inputs

## Data Protection
- **File Validator**: CSV uploads validated (size, extension, MIME type)
- **SQL Injection**: ORM throughout — raw SQL only in analytics aggregates (no user input in raw SQL)
- **Business Hours**: Default schedule prevents 24/7 misclassification

## Secrets Management
- DB credentials via `DATABASE_URL` environment variable
- JWT secret via `JWT_SECRET` environment variable
- Redis URL via `REDIS_URL` environment variable
- No secrets in code or config files

## Dependency Security
- `requirements.txt` with pinned versions
- Trivy security scan in CI (SARIF upload to GitHub)
- Recommended: regular `pip-audit` or `safety` scans

## Remaining Risks
| Risk | Severity | Mitigation |
|------|----------|------------|
| In-memory rate limiter | Medium | Replace with Redis-backed for multi-replica |
| No HTTPS termination | Medium | Caddy reverse proxy with auto TLS in prod |
| No vulnerability scanning CI gate | Low | Trivy scans for informational only |
| Minimal input sanitization on CSV | Low | File validator checks extension/MIME only |
