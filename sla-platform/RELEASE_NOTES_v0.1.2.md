# Release v0.1.2 — Authentication & RBAC

## Summary

Added complete authentication system with JWT access + refresh tokens, password hashing,
role-based access control (admin/analyst/viewer), protected frontend routes, login/logout UI,
refresh token rotation, permission middleware, and audit logging.

## Changes

### Backend — Auth
- **JWT tokens**: HS256 access (30 min) + refresh (7 days) tokens with type validation
- **Password hashing**: bcrypt via passlib (bcrypt 4.0.1 pinned for compatibility)
- **Refresh token rotation**: Old token revoked before issuing new pair (prevents replay)
- **User CRUD**: Full admin-only user management (create, read, update, deactivate)
- **Role middleware**: `RequireRole` class for granular RBAC (`require_admin`, `require_analyst`, `require_viewer`)
- **Route protection**: Router split into public (`/auth/login`, `/auth/refresh`) and protected (all other routes via `Depends(get_current_user)`)
- **RBAC on all modify routes**: `require_admin` added to POST/PUT/DELETE on teams, SLA definitions, imports, and reports
- **Admin seed**: Default admin user (`admin@sla-platform.dev` / `admin123`) created on startup
- **Audit logging**: `AuditService.log_sync()` for async-compatible audit trail on auth events

### Backend — Infrastructure
- **Migration 004**: `refresh_tokens` table with indexes on `user_id` and `expires_at`
- **bcrypt pin**: `bcrypt==4.0.1` in `requirements.txt` and `PASSLIB_BCRYPT_COMPAT=1` env var
- **Tests volume**: `./backend/tests:/app/tests` added to `docker-compose.yml`

### Frontend
- **Auth store**: Zustand store with token + refresh token + user persisted in localStorage
- **Axios interceptor**: Automatic 401 → refresh rotation with request queue
- **ProtectedRoute**: Redirects to `/login` if no valid token
- **RoleGuard**: Shows 403 or redirects based on user role
- **Login page**: Form with validation, error display, default credentials hint
- **Admin users page**: Full CRUD table with create/edit modal, deactivate, role tags
- **Sidebar**: Admin menu item conditionally visible for admin role
- **Header**: User dropdown with role badge + logout

### Tests
- **12 auth tests**: Login, refresh rotation, logout, admin-only endpoints, RBAC enforcement, duplicate email — all passing via real HTTP to running server

### Version
- Backend API version bumped to `0.1.2`

## Files Changed

| File | Action |
|------|--------|
| `backend/app/core/security.py` | **NEW** — JWT create/decode, password hash |
| `backend/app/core/dependencies.py` | **NEW** — `get_current_user`, `RequireRole` |
| `backend/app/services/user_service.py` | **NEW** — user/token management service |
| `backend/app/services/audit_service.py` | **MODIFIED** — added `log_sync()` |
| `backend/app/domain/models.py` | **MODIFIED** — added `RefreshToken` model |
| `backend/app/domain/schemas.py` | **MODIFIED** — added `RefreshRequest`, `MeResponse`, `UserUpdate` |
| `backend/app/api/v1/users.py` | **NEW** — 9 auth endpoints (login, refresh, me, logout, users CRUD) |
| `backend/app/api/v1/router.py` | **MODIFIED** — public + protected router split |
| `backend/app/api/v1/teams.py` | **MODIFIED** — admin protection on modify routes |
| `backend/app/api/v1/sla.py` | **MODIFIED** — admin protection on modify routes |
| `backend/app/api/v1/imports.py` | **MODIFIED** — admin protection on modify routes |
| `backend/app/api/v1/reports.py` | **MODIFIED** — admin protection on modify routes |
| `backend/app/main.py` | **MODIFIED** — seed_admin_user on startup |
| `backend/app/seeds.py` | **MODIFIED** — seed_admin_user() added |
| `backend/app/core/version.py` | **MODIFIED** — 0.1.1 → 0.1.2 |
| `backend/alembic/versions/004_add_refresh_tokens.py` | **NEW** — migration for refresh_tokens table |
| `backend/requirements.txt` | **MODIFIED** — added bcrypt==4.0.1 |
| `docker-compose.yml` | **MODIFIED** — tests volume, PASSLIB_BCRYPT_COMPAT=1 |
| `backend/tests/test_auth.py` | **NEW** — 12 auth integration tests |
| `frontend/src/components/auth/ProtectedRoute.tsx` | **NEW** — auth-gated routing |
| `frontend/src/components/auth/RoleGuard.tsx` | **NEW** — role-based rendering |
| `frontend/src/stores/authStore.ts` | **MODIFIED** — token + user persistence |
| `frontend/src/api/client.ts` | **MODIFIED** — refresh rotation interceptor |
| `frontend/src/api/auth.ts` | **MODIFIED** — full auth API |
| `frontend/src/pages/Login.tsx` | **REWRITTEN** — form with validation |
| `frontend/src/pages/AdminUsers.tsx` | **NEW** — CRUD user management table |
| `frontend/src/App.tsx` | **MODIFIED** — ProtectedRoute wrapping |
| `frontend/src/components/layout/Sidebar.tsx` | **MODIFIED** — role-based menu |
| `frontend/src/components/layout/Header.tsx` | **MODIFIED** — user dropdown + logout |

## Deployment

```bash
# Rebuild and start
docker compose build backend
docker compose up -d

# Run migration (auto on startup) & seed creates default admin
# Default admin: admin@sla-platform.dev / admin123

# Verify
curl -s http://localhost:8000/health
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@sla-platform.dev","password":"admin123"}'
```

## Auth API Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/login` | Public | Login with email + password |
| POST | `/api/v1/auth/refresh` | Public | Refresh token rotation |
| GET | `/api/v1/auth/me` | Bearer | Current user info |
| POST | `/api/v1/auth/logout` | Bearer | Revoke all refresh tokens |
| GET | `/api/v1/auth/users` | Admin | List users |
| POST | `/api/v1/auth/users` | Admin | Create user |
| GET | `/api/v1/auth/users/{id}` | Admin | Get user |
| PUT | `/api/v1/auth/users/{id}` | Admin | Update user |
| DELETE | `/api/v1/auth/users/{id}` | Admin | Deactivate user |

## Rollback

```bash
git checkout v0.1.1 -- backend/app
git checkout v0.1.1 -- docker-compose.yml
docker compose build backend
docker compose up -d
# Manual: DROP TABLE refresh_tokens;
# Manual: DELETE FROM alembic_version WHERE version_num LIKE '%004%';
```
