"""File upload validation: extension, MIME, and CSV malicious payload protection."""

import os

ALLOWED_EXTENSIONS = frozenset({".csv", ".xlsx", ".xls"})
ALLOWED_MIME_TYPES = frozenset({
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
})

CSV_DANGEROUS_PATTERNS = [
    b"=CMD(",
    b"=cmd(",
    b"=EXEC(",
    b"=exec(",
    b"=SYSTEM(",
    b"=system(",
    b"=SHELL(",
    b"=shell(",
    b"powershell",
    b"wscript.shell",
    b"VBA.",
    b"<script>",
    b"<?php",
    b"DROP TABLE",
    b"DROP TABLE IF EXISTS",
    b"DELETE FROM",
    b"INSERT INTO",
    b"CREATE TABLE",
    b"ALTER TABLE",
]


def validate_extension(filename: str) -> bool:
    """Check file extension is allowed."""
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS


def validate_mime(content_type: str) -> bool:
    """Validate MIME type is allowed."""
    return content_type.lower() in ALLOWED_MIME_TYPES


def validate_csv_content(content: bytes) -> list[str]:
    """Scans CSV content for malicious payloads. Returns list of warnings."""
    warnings: list[str] = []
    content_lower = content.lower()
    for pattern in CSV_DANGEROUS_PATTERNS:
        if pattern in content or pattern in content_lower:
            warnings.append(f"Suspicious pattern detected: {pattern.decode()}")
    return warnings


def validate_upload(filename: str, content_type: str, content: bytes) -> list[str]:
    """Run all validations. Returns list of errors (empty = pass)."""
    errors: list[str] = []

    if not validate_extension(filename):
        errors.append(f"File extension not allowed: {filename}")

    if content_type and not validate_mime(content_type):
        if not content_type.startswith("application/"):
            errors.append(f"Content-Type not allowed: {content_type}")

    warnings = validate_csv_content(content)
    if warnings:
        errors.extend(warnings)

    if len(content) > 100 * 1024 * 1024:
        errors.append("File exceeds maximum size of 100MB")

    return errors
