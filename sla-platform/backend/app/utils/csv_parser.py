import csv
from typing import Iterator

import polars as pl

BACKLOG_EXPECTED_COLS = {
    "ticket_id", "ticket_number", "title",
    "customer_id", "customer_user_id",
    "ticket_created_time", "ticket_last_change_time",
    "current_queue_name", "current_state_name",
}

HISTORY_EXPECTED_COLS = {
    "ticket_id", "ticket_number", "title",
    "event_time", "event_name", "event_raw_name",
    "queue_name", "state_name", "event_owner_name",
}


def _validate_csv_headers(file_path: str, expected: set[str]) -> list[str]:
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return ["Empty file"]
    actual = set(h.strip() for h in header)
    missing = expected - actual
    if missing:
        return [f"Missing columns: {missing}"]
    return []


def validate_backlog_columns(file_path: str) -> list[str]:
    return _validate_csv_headers(file_path, BACKLOG_EXPECTED_COLS)


def validate_history_columns(file_path: str) -> list[str]:
    return _validate_csv_headers(file_path, HISTORY_EXPECTED_COLS)


def read_backlog_chunks(
    file_path: str, chunk_size: int = 5_000
) -> Iterator[list[dict]]:
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        batch = []
        for row in reader:
            row["ticket_id"] = int(row["ticket_id"]) if row.get("ticket_id") else 0
            batch.append(row)
            if len(batch) >= chunk_size:
                yield batch
                batch = []
        if batch:
            yield batch


def read_history_chunks(
    file_path: str, chunk_size: int = 5_000
) -> Iterator[list[dict]]:
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        batch = []
        for row in reader:
            row["ticket_id"] = int(row["ticket_id"]) if row.get("ticket_id") else 0
            batch.append(row)
            if len(batch) >= chunk_size:
                yield batch
                batch = []
        if batch:
            yield batch
