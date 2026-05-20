# Enterprise File Storage — v1.2.1

## Architecture

```
Client (multipart/form-data)
    │
    ▼
POST /api/v1/attachments/upload
    │
    ├── File size validation (100MB max)
    ├── MIME type whitelist (CSV, XLSX, PDF, TXT, ZIP, JSON, MD, PNG, JPEG)
    ├── SHA-256 content hash
    ├── Store to disk (local) or S3 (future)
    ├── Insert metadata to `attachments` table
    └── Return attachment ID + metadata
```

## Storage Layer

`app/services/storage.py` provides:

- **StorageBackend** — abstract interface (store, retrieve, delete, exists, size, cleanup)
- **LocalStorage** — filesystem implementation
- `get_storage()` — factory for backend selection (local now, S3-ready)
- `compute_file_hash()` — SHA-256 integrity check
- `validate_file_size()` — max size enforcement
- `validate_mime_type()` — allowlist enforcement

## API Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/attachments/upload` | Any user | Upload file (multipart) |
| GET | `/attachments/{id}` | Any user | Download file |
| GET | `/attachments` | Any user | List attachments (filter by ticket_id, import_id) |
| DELETE | `/attachments/{id}` | Admin | Delete attachment |

## Supported File Types

| Extension | MIME Type |
|-----------|-----------|
| .csv | text/csv |
| .xlsx | application/vnd.openxmlformats...sheet |
| .xls | application/vnd.ms-excel |
| .pdf | application/pdf |
| .txt | text/plain |
| .zip | application/zip |
| .json | application/json |
| .md | text/markdown |
| .png | image/png |
| .jpg | image/jpeg |

## Storage Path

Files stored at: `{DATA_DIR}/attachments/{uuid}.{ext}`

## Migration

```bash
alembic upgrade 020_attachments
```
