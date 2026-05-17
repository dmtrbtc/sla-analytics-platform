"""Unit tests for file_validator.py — extension, MIME, CSV injection scanning."""

from app.utils.file_validator import (
    validate_csv_content,
    validate_extension,
    validate_mime,
    validate_upload,
)


def test_validate_extension_csv():
    assert validate_extension("report.csv") is True


def test_validate_extension_xlsx():
    assert validate_extension("data.xlsx") is True


def test_validate_extension_xls():
    assert validate_extension("old.xls") is True


def test_validate_extension_bad():
    assert validate_extension("evil.exe") is False


def test_validate_extension_no_ext():
    assert validate_extension("Makefile") is False


def test_validate_extension_uppercase():
    assert validate_extension("REPORT.CSV") is True


def test_validate_mime_csv():
    assert validate_mime("text/csv") is True


def test_validate_mime_xlsx():
    assert validate_mime("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") is True


def test_validate_mime_xls():
    assert validate_mime("application/vnd.ms-excel") is True


def test_validate_mime_octet():
    assert validate_mime("application/octet-stream") is True


def test_validate_mime_bad():
    assert validate_mime("text/html") is False


def test_validate_mime_case_insensitive():
    assert validate_mime("TEXT/CSV") is True


def test_csv_content_clean():
    assert validate_csv_content(b"ticket_id,title\n1,hello") == []


def test_csv_content_drop_table():
    warnings = validate_csv_content(b"ticket_id,title\n1,DROP TABLE users")
    assert len(warnings) >= 1
    assert any("DROP TABLE" in w for w in warnings)


def test_csv_content_powershell():
    warnings = validate_csv_content(b"ticket_id,title\n1,powershell -Command")
    assert len(warnings) >= 1
    assert any("powershell" in w for w in warnings)


def test_csv_content_script_tag():
    warnings = validate_csv_content(b"ticket_id,title\n1,<script>alert(1)</script>")
    assert len(warnings) >= 1
    assert any("script" in w for w in warnings)


def test_csv_content_php():
    warnings = validate_csv_content(b"ticket_id,title\n1,<?php system()")
    assert len(warnings) >= 1
    assert any("php" in w for w in warnings)


def test_csv_content_cmd():
    warnings = validate_csv_content(b"=CMD(calc)")
    assert len(warnings) >= 1
    assert any("=CMD(" in w for w in warnings)


def test_csv_content_exec():
    warnings = validate_csv_content(b"=EXEC(malicious)")
    assert len(warnings) >= 1


def test_csv_content_system():
    warnings = validate_csv_content(b"=SYSTEM('id')")
    assert len(warnings) >= 1


def test_csv_content_shell():
    warnings = validate_csv_content(b"=SHELL('ls')")
    assert len(warnings) >= 1


def test_csv_content_wscript():
    warnings = validate_csv_content(b"wscript.shell")
    assert len(warnings) >= 1


def test_csv_content_vba():
    warnings = validate_csv_content(b"VBA.Module")
    assert len(warnings) >= 1


def test_csv_content_delete_from():
    warnings = validate_csv_content(b"DELETE FROM users")
    assert len(warnings) >= 1


def test_csv_content_insert_into():
    warnings = validate_csv_content(b"INSERT INTO users VALUES")
    assert len(warnings) >= 1


def test_csv_content_mixed_clean_and_dirty():
    content = b"ticket_id,title,note\n1,hello,=CMD(calc)\n2,world,clean"
    warnings = validate_csv_content(content)
    assert len(warnings) >= 1


def test_validate_upload_full_pass():
    errors = validate_upload("data.csv", "text/csv", b"ticket_id,title\n1,test")
    assert errors == []


def test_validate_upload_bad_extension():
    errors = validate_upload("evil.exe", "application/octet-stream", b"data")
    assert any("extension" in e.lower() for e in errors)


def test_validate_upload_bad_mime():
    errors = validate_upload("data.csv", "text/html", b"ticket_id,title\n1,test")
    assert any("Content-Type" in e for e in errors)


def test_validate_upload_malicious_content():
    errors = validate_upload("data.csv", "text/csv", b"ticket_id,title\n1,=CMD(calc)")
    assert any("CMD" in e for e in errors)


def test_validate_upload_application_mime_skip():
    """application/* MIME types are allowed without specific check."""
    errors = validate_upload("data.bin", "application/octet-stream", b"data")
    assert not any("Content-Type" in e for e in errors)
