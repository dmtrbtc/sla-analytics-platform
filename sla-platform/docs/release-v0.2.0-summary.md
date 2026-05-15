# v0.2.0 — Production Hardening Summary

## Test Coverage
- **74 tests passing** across 11 test files
- Auth (login, register, refresh, logout)
- Imports (end-to-end workflow with CSV/Excel)
- Parser (data extraction, metric formatting)
- SLA metrics (breach detection, OnTime, SLA%, AtRisk, business hours, pause/resume)
- Dashboard (summary stats, trend data)
- Tickets (CRUD, search, status transitions)
- Teams (CRUD, search)
- Audit (event logging, filtering)
- Reports (generation, retrieval)

## Performance Findings (from audit)
| Issue | Location | Impact |
|-------|----------|--------|
| N+1 queries | `report_service.py` | O(n) DB calls per report row |
| N+1 queries | `reconstructor.py` | O(n) per session group |
| N+1 queries | `normalizer.py` | O(n) per ticket import |
| N+1 queries | `dashboard_service.py` | O(n) per time bucket |
| Missing FK indexes | 12 columns in 5 tables | Full table scans on JOINs |
| SELECT * | Multiple services | 2–10x unnecessary data transfer |
| Cache bypass | `metrics_engine.py` | Redundant SLA recalculations |

## Security Improvements
- **Rate limiting**: 60 req/min for general, 5 req/min for auth, excludes `/health` and docs
- **CORS hardening**: Explicit allowlist, not `*`
- **Global exception handler**: No stack trace leakage in production
- **Request validation**: Structured `RequestValidationError` responses
- **Trivy scan**: Container image vulnerability scanning in CI

## Remaining Risks
1. **N+1 queries** — high-impact performance issue under load; needs eager-loading refactor
2. **Missing FK indexes** — will degrade as data grows; needs migration
3. **No integration test coverage** — tests hit real endpoints but don't test cross-service workflows
4. **Redis not clustered** — single-node Redis is a SPOF for Celery broker + cache
5. **No backup testing** — backup scripts written but untested in CI
6. **No secrets rotation** — SECRET_KEY rotation procedure undocumented
7. **Frontend not tested** — no frontend tests exist (tsc only)
