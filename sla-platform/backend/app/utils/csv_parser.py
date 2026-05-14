from typing import Iterator

import polars as pl

BACKLOG_SCHEMA = {
    "ticket_id": pl.Int64,
    "ticket_number": pl.Utf8,
    "title": pl.Utf8,
    "customer_id": pl.Utf8,
    "customer_user_id": pl.Utf8,
    "ticket_created_time": pl.Utf8,
    "ticket_last_change_time": pl.Utf8,
    "current_queue_name": pl.Utf8,
    "current_state_name": pl.Utf8,
}

HISTORY_SCHEMA = {
    "ticket_id": pl.Int64,
    "ticket_number": pl.Utf8,
    "title": pl.Utf8,
    "event_time": pl.Utf8,
    "event_name": pl.Utf8,
    "event_raw_name": pl.Utf8,
    "queue_name": pl.Utf8,
    "state_name": pl.Utf8,
    "event_owner_name": pl.Utf8,
}

BACKLOG_EXPECTED_COLS = set(BACKLOG_SCHEMA.keys())
HISTORY_EXPECTED_COLS = set(HISTORY_SCHEMA.keys())


def read_backlog_csv(file_path: str, chunk_size: int = 10_000) -> pl.DataFrame:
    return pl.scan_csv(
        file_path,
        schema=BACKLOG_SCHEMA,
        null_values=[""],
        truncate_ragged_lines=True,
        encoding="utf8-lossy",
        low_memory=True,
    ).collect(streaming=True)


def read_history_csv(file_path: str, chunk_size: int = 10_000) -> pl.DataFrame:
    return pl.scan_csv(
        file_path,
        schema=HISTORY_SCHEMA,
        null_values=[""],
        truncate_ragged_lines=True,
        encoding="utf8-lossy",
        low_memory=True,
    ).collect(streaming=True)


def read_backlog_chunks(
    file_path: str, chunk_size: int = 5_000
) -> Iterator[pl.DataFrame]:
    lazy = pl.scan_csv(
        file_path,
        schema=BACKLOG_SCHEMA,
        null_values=[""],
        truncate_ragged_lines=True,
        encoding="utf8-lossy",
        low_memory=True,
    )
    for batch in lazy.collect(streaming=True).iter_slices(chunk_size):
        yield batch


def read_history_chunks(
    file_path: str, chunk_size: int = 5_000
) -> Iterator[pl.DataFrame]:
    lazy = pl.scan_csv(
        file_path,
        schema=HISTORY_SCHEMA,
        null_values=[""],
        truncate_ragged_lines=True,
        encoding="utf8-lossy",
        low_memory=True,
    )
    for batch in lazy.collect(streaming=True).iter_slices(chunk_size):
        yield batch


def validate_backlog_columns(df: pl.DataFrame) -> list[str]:
    actual = set(df.columns)
    missing = BACKLOG_EXPECTED_COLS - actual
    if missing:
        return [f"Missing backlog columns: {missing}"]
    return []


def validate_history_columns(df: pl.DataFrame) -> list[str]:
    actual = set(df.columns)
    missing = HISTORY_EXPECTED_COLS - actual
    if missing:
        return [f"Missing history columns: {missing}"]
    return []
