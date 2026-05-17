# Security Audit — v0.4.0

## Scope
All security-related changes in Phase 6 hardening pass.

## Issues Found & Fixed

### 1. Exception Leakage (HIGH)
- **Before**: `POST /imports/sessions` and `POST /imports/sessions/{id}/start` passed `str(e)` to clients via HTTPException
- **After**: Generic messages ("Upload failed", "Invalid session state"); actual exceptions logged server-side

### 2. Silent Audit Failures (MEDIUM)
- **Before**: `_sync_audit()` in sla.py, reports.py, imports.py used `except Exception: pass`
- **After**: Logs via `logger.warning` so audit failures are visible

### 3. Path Traversal (MEDIUM)
- **Before**: Report download served files from EXPORT_DIR without validating resolved path
- **After**: Resolved path normalized and verified to stay within EXPORT_DIR

### 4. CSV Injection (MEDIUM)
- **Before**: CSV exports included raw values starting with `=`, `+`, `-`, `@`
- **After**: Dangerous prefixes sanitized with leading `'`

### 5. Filename Sanitization (LOW)
- **Before**: Uploaded filenames used as-is
- **After**: Directory separators stripped, `os.path.basename()` applied

### 6. JWT Secret Length (LOW)
- **Before**: No validation of SECRET_KEY length
- **After**: Warning logged if SECRET_KEY < 32 characters

### 7. Security Headers (LOW)
- **Before**: No security headers on responses
- **After**: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, HSTS, CSP, Referrer-Policy

### 8. Validation Error Exposure (LOW)
- **Before**: Pydantic ValidationError text leaked to client
- **After**: Structured response with field, message, type only

## Not Changed (Already Secure)
- JWT: HS256, 30-min access, 7-day refresh, bcrypt passwords
- CORS: Restricted to configured origins
- SQL injection: ORM throughout; raw SQL uses bound parameters
- File validator: Checks extension, MIME type, CSV content patterns
- Rate limiter: 60 req/min per IP+path, excludes health/docs
