import csv
import os
import tempfile

from app.utils.csv_parser import (
    validate_backlog_columns,
    validate_history_columns,
    BACKLOG_EXPECTED_COLS,
    HISTORY_EXPECTED_COLS,
)


def _make_csv(cols: list[str], tmpdir: str) -> str:
    path = os.path.join(tmpdir, "test.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
    return path


def test_backlog_all_columns():
    with tempfile.TemporaryDirectory() as td:
        path = _make_csv(list(BACKLOG_EXPECTED_COLS), td)
        assert validate_backlog_columns(path) == []


def test_backlog_missing_column():
    with tempfile.TemporaryDirectory() as td:
        cols = list(BACKLOG_EXPECTED_COLS)
        cols.remove("ticket_id")
        path = _make_csv(cols, td)
        errors = validate_backlog_columns(path)
        assert len(errors) == 1
        assert "ticket_id" in errors[0]


def test_backlog_missing_multiple():
    with tempfile.TemporaryDirectory() as td:
        path = _make_csv(["ticket_id", "title"], td)
        errors = validate_backlog_columns(path)
        assert len(errors) == 1
        assert "Missing columns" in errors[0]


def test_backlog_extra_column():
    with tempfile.TemporaryDirectory() as td:
        cols = list(BACKLOG_EXPECTED_COLS) + ["extra_col"]
        path = _make_csv(cols, td)
        assert validate_backlog_columns(path) == []


def test_backlog_no_columns():
    with tempfile.TemporaryDirectory() as td:
        path = _make_csv([], td)
        errors = validate_backlog_columns(path)
        assert len(errors) == 1


def test_history_all_columns():
    with tempfile.TemporaryDirectory() as td:
        path = _make_csv(list(HISTORY_EXPECTED_COLS), td)
        assert validate_history_columns(path) == []


def test_history_missing_column():
    with tempfile.TemporaryDirectory() as td:
        cols = list(HISTORY_EXPECTED_COLS)
        cols.remove("event_time")
        path = _make_csv(cols, td)
        errors = validate_history_columns(path)
        assert len(errors) == 1
        assert "event_time" in errors[0]


def test_history_missing_multiple():
    with tempfile.TemporaryDirectory() as td:
        path = _make_csv(["ticket_id", "event_name"], td)
        errors = validate_history_columns(path)
        assert len(errors) == 1


def test_history_extra_column():
    with tempfile.TemporaryDirectory() as td:
        cols = list(HISTORY_EXPECTED_COLS) + ["extra"]
        path = _make_csv(cols, td)
        assert validate_history_columns(path) == []


def test_backlog_vs_history_schemas_different():
    assert BACKLOG_EXPECTED_COLS != HISTORY_EXPECTED_COLS
