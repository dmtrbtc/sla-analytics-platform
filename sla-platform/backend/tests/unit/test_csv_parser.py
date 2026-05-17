"""Unit tests for csv_parser.py — schema validation."""

import polars as pl

from app.utils.csv_parser import (
    validate_backlog_columns,
    validate_history_columns,
    BACKLOG_EXPECTED_COLS,
    HISTORY_EXPECTED_COLS,
)


def _make_df(cols: list[str]) -> pl.DataFrame:
    data = {c: [] for c in cols}
    return pl.DataFrame(data)


def test_backlog_all_columns():
    df = _make_df(list(BACKLOG_EXPECTED_COLS))
    assert validate_backlog_columns(df) == []


def test_backlog_missing_column():
    cols = list(BACKLOG_EXPECTED_COLS)
    cols.remove("ticket_id")
    df = _make_df(cols)
    errors = validate_backlog_columns(df)
    assert len(errors) == 1
    assert "ticket_id" in errors[0]


def test_backlog_missing_multiple():
    df = _make_df(["ticket_id", "title"])
    errors = validate_backlog_columns(df)
    assert len(errors) == 1
    assert "Missing backlog columns" in errors[0]


def test_backlog_extra_column():
    cols = list(BACKLOG_EXPECTED_COLS) + ["extra_col"]
    df = _make_df(cols)
    assert validate_backlog_columns(df) == []


def test_backlog_empty_dataframe():
    df = _make_df(list(BACKLOG_EXPECTED_COLS))
    assert validate_backlog_columns(df) == []


def test_backlog_no_columns():
    df = _make_df([])
    errors = validate_backlog_columns(df)
    assert len(errors) == 1


def test_history_all_columns():
    df = _make_df(list(HISTORY_EXPECTED_COLS))
    assert validate_history_columns(df) == []


def test_history_missing_column():
    cols = list(HISTORY_EXPECTED_COLS)
    cols.remove("event_time")
    df = _make_df(cols)
    errors = validate_history_columns(df)
    assert len(errors) == 1
    assert "event_time" in errors[0]


def test_history_missing_multiple():
    df = _make_df(["ticket_id", "event_name"])
    errors = validate_history_columns(df)
    assert len(errors) == 1


def test_history_extra_column():
    cols = list(HISTORY_EXPECTED_COLS) + ["extra"]
    df = _make_df(cols)
    assert validate_history_columns(df) == []


def test_history_empty_dataframe():
    df = _make_df(list(HISTORY_EXPECTED_COLS))
    assert validate_history_columns(df) == []


def test_backlog_vs_history_schemas_different():
    """Backlog and history have different expected columns."""
    assert BACKLOG_EXPECTED_COLS != HISTORY_EXPECTED_COLS
