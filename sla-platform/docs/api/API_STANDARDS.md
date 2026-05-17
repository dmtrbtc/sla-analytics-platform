# API Standards

## Response Format
All responses use standard HTTP status codes with JSON bodies.

### Success (2xx)
```json
{
  "data": { ... },
  "message": "OK"
}
```

### Error (4xx/5xx)
```json
{
  "detail": "Human-readable error message",
  "errors": [
    {"field": "email", "message": "Field required", "type": "missing"}
  ]
}
```

## Status Codes
| Method | Success | Notes |
|--------|---------|-------|
| GET | 200 | List or single resource |
| POST | 201 | Resource created |
| PUT | 200 | Resource updated |
| DELETE | 200 | Resource deleted |
| Auth errors | 401 | Missing/invalid token |
| Permission errors | 403 | Insufficient role |
| Not found | 404 | Resource doesn't exist |

## Pagination
List endpoints use `limit`/`offset` pagination style:

Query params: `?limit=50&offset=0`
Response: `{"items": [...], "total": N, "limit": 50, "offset": 0}`

Maximum `limit`: 200 (configurable per endpoint)

## Authentication
- JWT Bearer token in `Authorization` header
- Access token: 30 min expiry
- Refresh token: 7 days, one-time use
- Public endpoints: `/health`, `/api/docs`, `/api/openapi.json`

## Request ID
Every request should carry `X-Request-Id` header for tracing.

## Rate Limiting
- 60 requests per minute per IP+path
- Excludes `/health`, `/api/docs`, `/api/openapi.json`
- Response: 429 with `Retry-After: 60`

## Versioning
API version prefix: `/api/v1/`
Backward-compatible changes within version.
Breaking changes require new version prefix.
