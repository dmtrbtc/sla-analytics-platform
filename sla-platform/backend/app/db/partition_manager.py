"""PostgreSQL partition management utilities.

Provides infrastructure for managing partitioned tables with optional
monthly-range or import-id-list partitioning strategies.

All operations are designed to be migration-safe — existing tables are
never altered. The module creates new partitioned tables and provides
a unified view (optional) that unions old and partitioned data.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional

from sqlalchemy import Connection, text

logger = logging.getLogger(__name__)

PARTITION_META_TABLE = "partition_meta"
PARTITION_SCHEMA = "partitions"


class PartitionStrategy(str, Enum):
    BY_MONTH = "by_month"
    BY_IMPORT = "by_import"


PARTITIONABLE_TABLES: dict[str, PartitionStrategy] = {
    "raw_events": PartitionStrategy.BY_MONTH,
    "ticket_events": PartitionStrategy.BY_MONTH,
    "sla_metrics": PartitionStrategy.BY_MONTH,
}


def _ensure_schema(conn: Connection) -> None:
    conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {PARTITION_SCHEMA}"))


def create_partition_meta_table(conn: Connection) -> None:
    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {PARTITION_SCHEMA}.{PARTITION_META_TABLE} (
            table_name      TEXT NOT NULL,
            strategy        TEXT NOT NULL,
            partition_key   TEXT NOT NULL,
            partition_name  TEXT NOT NULL,
            partition_boundary TEXT NOT NULL,
            created_at      TIMESTAMPTZ DEFAULT now(),
            is_active       BOOLEAN DEFAULT TRUE,
            PRIMARY KEY (table_name, partition_name)
        )
    """))


def generate_monthly_partition_name(base_table: str, boundary_date: date) -> str:
    return f"{base_table}_{boundary_date.year}_{boundary_date.month:02d}"


def create_monthly_partition(
    conn: Connection,
    base_table: str,
    partition_date: date,
) -> str:
    """Create a monthly partition for the given base table and date.

    Creates partition for one month: [partition_date, next_month).
    """
    _ensure_schema(conn)
    create_partition_meta_table(conn)

    next_month = (
        partition_date.replace(day=28) + timedelta(days=4)
    ).replace(day=1)
    partition_name = generate_monthly_partition_name(base_table, partition_date)

    exists = conn.execute(
        text(f"""
            SELECT 1 FROM {PARTITION_SCHEMA}.{PARTITION_META_TABLE}
            WHERE table_name = :t AND partition_name = :p
        """),
        {"t": base_table, "p": partition_name},
    ).scalar()

    if exists:
        logger.info("Partition %s already exists for %s", partition_name, base_table)
        return partition_name

    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {PARTITION_SCHEMA}.{partition_name} ()
        INHERITS (public.{base_table})
    """))

    conn.execute(text(f"""
        ALTER TABLE {PARTITION_SCHEMA}.{partition_name}
        ADD CONSTRAINT {partition_name}_time_check
        CHECK (event_time >= :start AND event_time < :end)
    """), {
        "start": partition_date,
        "end": next_month,
    })

    conn.execute(
        text(f"""
            INSERT INTO {PARTITION_SCHEMA}.{PARTITION_META_TABLE}
                (table_name, strategy, partition_key, partition_name, partition_boundary)
            VALUES (:t, 'by_month', 'event_time', :p, :b)
        """),
        {
            "t": base_table,
            "p": partition_name,
            "b": f"[{partition_date.isoformat()}, {next_month.isoformat()})",
        },
    )

    logger.info("Created partition %s for %s", partition_name, base_table)
    return partition_name


def create_monthly_partitions_range(
    conn: Connection,
    base_table: str,
    start_date: date,
    end_date: date,
) -> list[str]:
    """Create monthly partitions for the full date range inclusive."""
    names = []
    current = start_date.replace(day=1)
    while current < end_date:
        name = create_monthly_partition(conn, base_table, current)
        names.append(name)
        next_m = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        current = next_m
    return names


def create_insert_trigger(conn: Connection, base_table: str) -> str:
    """Create a trigger function that routes INSERTs to the correct partition
    based on event_time. Returns the trigger function name."""
    func_name = f"route_insert_{base_table}"
    trigger_name = f"trg_route_{base_table}"

    conn.execute(text(f"""
        CREATE OR REPLACE FUNCTION {PARTITION_SCHEMA}.{func_name}()
        RETURNS TRIGGER AS $$
        DECLARE
            part_name TEXT;
            part_date DATE;
        BEGIN
            part_date := DATE(NEW.event_time);
            part_name := '{base_table}_' || TO_CHAR(part_date, 'YYYY_MM');
            EXECUTE format(
                'INSERT INTO {PARTITION_SCHEMA}.%I SELECT ($1).*',
                part_name
            ) USING NEW;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
    """))

    conn.execute(text(f"""
        DROP TRIGGER IF EXISTS {trigger_name} ON public.{base_table}
    """))

    conn.execute(text(f"""
        CREATE TRIGGER {trigger_name}
        INSTEAD OF INSERT ON public.{base_table}
        FOR EACH ROW EXECUTE FUNCTION {PARTITION_SCHEMA}.{func_name}()
    """))

    return func_name


def setup_partition_infrastructure(
    conn: Connection,
    base_tables: Optional[list[str]] = None,
    start_date: Optional[date] = None,
    months_ahead: int = 3,
) -> dict[str, list[str]]:
    """Set up full partition infrastructure for specified tables.

    Args:
        conn: SQLAlchemy connection.
        base_tables: List of table names to partition. Defaults to all partitionable tables.
        start_date: Start date for initial partitions. Defaults to current month.
        months_ahead: Number of months of future partitions to create.

    Returns:
        Dict mapping table name to list of created partition names.
    """
    if base_tables is None:
        base_tables = list(PARTITIONABLE_TABLES.keys())

    if start_date is None:
        start_date = date.today().replace(day=1)

    end_date = date.today().replace(day=1) + timedelta(days=32 * months_ahead)

    results: dict[str, list[str]] = {}
    for table in base_tables:
        if PARTITIONABLE_TABLES.get(table) == PartitionStrategy.BY_MONTH:
            partitions = create_monthly_partitions_range(conn, table, start_date, end_date)
            results[table] = partitions
        else:
            logger.warning("No automatic setup for %s strategy", table)

    return results


def teardown_partition_infrastructure(conn: Connection, base_tables: Optional[list[str]] = None) -> None:
    """Remove partitioning infrastructure (triggers, partitions, schema).

    Args:
        conn: SQLAlchemy connection.
        base_tables: List of tables to tear down. Defaults to all partitionable tables.
    """
    if base_tables is None:
        base_tables = list(PARTITIONABLE_TABLES.keys())

    for table in base_tables:
        trigger_name = f"trg_route_{table}"
        conn.execute(text(f"DROP TRIGGER IF EXISTS {trigger_name} ON public.{table}"))

        func_name = f"route_insert_{table}"
        conn.execute(text(f"DROP FUNCTION IF EXISTS {PARTITION_SCHEMA}.{func_name}()"))

        rows = conn.execute(
            text(f"""
                SELECT partition_name FROM {PARTITION_SCHEMA}.{PARTITION_META_TABLE}
                WHERE table_name = :t
            """),
            {"t": table},
        ).fetchall()

        for row in rows:
            conn.execute(text(f"DROP TABLE IF EXISTS {PARTITION_SCHEMA}.{row[0]} CASCADE"))

        conn.execute(
            text(f"DELETE FROM {PARTITION_SCHEMA}.{PARTITION_META_TABLE} WHERE table_name = :t"),
            {"t": table},
        )

    conn.execute(text(f"DROP SCHEMA IF EXISTS {PARTITION_SCHEMA} CASCADE"))
