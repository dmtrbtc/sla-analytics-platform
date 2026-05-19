import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.models import ImportSession, RawEvent
from app.utils.csv_parser import read_history_chunks, validate_history_columns
from app.utils.raw_parser import parse_event_raw

logger = logging.getLogger(__name__)

BATCH_SIZE = 2000


class ParserService:

    @staticmethod
    def parse_and_load(db: Session, import_id: UUID) -> dict:
        imp = db.query(ImportSession).filter_by(id=import_id).first()
        if not imp:
            raise ValueError(f"ImportSession {import_id} not found")

        import_dir = Path(settings.DATA_DIR) / "imports" / str(import_id)
        history_path = import_dir / imp.history_file if imp.history_file else None

        stats = {
            "backlog_rows": imp.backlog_rows or 0,
            "history_rows": 0,
            "events_parsed": 0,
            "errors": [],
        }

        if not (history_path and history_path.exists()):
            return stats

        errs = validate_history_columns(str(history_path))
        if errs:
            stats["errors"].extend(errs)
            return stats

        ParserService._clear_import_events(db, import_id)
        db.commit()

        for chunk in read_history_chunks(str(history_path), BATCH_SIZE):
            rows = ParserService._chunk_to_raw_rows(chunk, import_id)
            ParserService._bulk_insert(db, rows)
            db.commit()
            stats["events_parsed"] += len(rows)
            logger.info("Parsed history batch (%s total)", stats["events_parsed"])

        stats["history_rows"] = stats["events_parsed"]

        return stats

    @staticmethod
    def _clear_import_events(db: Session, import_id: UUID) -> None:
        import_id_str = str(import_id)
        db.execute(
            text(
                "DELETE FROM ownership_periods "
                "WHERE ticket_id IN ("
                "  SELECT ticket_id FROM ticket_snapshots WHERE last_import_id = :i"
                ")"
            ),
            {"i": import_id_str},
        )
        db.execute(
            text(
                "DELETE FROM queue_periods "
                "WHERE ticket_id IN ("
                "  SELECT ticket_id FROM ticket_snapshots WHERE last_import_id = :i"
                ")"
            ),
            {"i": import_id_str},
        )
        db.execute(
            text("DELETE FROM sla_metrics WHERE import_id = :i"),
            {"i": import_id_str},
        )
        db.execute(
            text("DELETE FROM ticket_events WHERE import_id = :i"),
            {"i": import_id_str},
        )
        db.execute(
            text("DELETE FROM raw_events WHERE import_id = :i"),
            {"i": import_id_str},
        )

    @staticmethod
    def _chunk_to_raw_rows(rows: list[dict], import_id: UUID) -> list[dict]:
        result = []
        for row in rows:
            parsed = parse_event_raw(
                row.get("event_name") or "",
                row.get("event_raw_name") or "",
            )
            ev_time = row.get("event_time")
            ev_name = row.get("event_name", "")
            ev_raw = row.get("event_raw_name", "")
            result.append(
                {
                    "import_id": import_id,
                    "ticket_id": int(row["ticket_id"]) if row.get("ticket_id") else 0,
                    "ticket_number": row.get("ticket_number"),
                    "title": row.get("title"),
                    "event_time": ev_time,
                    "event_name": ev_name,
                    "event_raw_name": ev_raw,
                    "queue_name": row.get("queue_name"),
                    "state_name": row.get("state_name"),
                    "event_owner_name": row.get("event_owner_name"),
                    "src_queue": parsed.get("src_queue"),
                    "dest_queue": parsed.get("dest_queue"),
                    "old_state": parsed.get("old_state"),
                    "new_state": parsed.get("new_state"),
                    "new_owner": parsed.get("new_owner"),
                    "pending_until": parsed.get("pending_until"),
                    "sla_name": parsed.get("sla_name"),
                    "duplicate_key": f"{ev_time}|{ev_name}|{ev_raw}",
                }
            )
        return result

    @staticmethod
    def _bulk_insert(db: Session, rows: list[dict]) -> None:
        stmt = text(
            """
            INSERT INTO raw_events (
                import_id, ticket_id, ticket_number, title,
                event_time, event_name, event_raw_name,
                queue_name, state_name, event_owner_name,
                src_queue, dest_queue, old_state, new_state,
                new_owner, pending_until, sla_name,
                duplicate_key
            ) VALUES (
                :import_id, :ticket_id, :ticket_number, :title,
                :event_time, :event_name, :event_raw_name,
                :queue_name, :state_name, :event_owner_name,
                :src_queue, :dest_queue, :old_state, :new_state,
                :new_owner, :pending_until, :sla_name,
                :duplicate_key
            )
            """
        )
        db.execute(stmt, rows)
