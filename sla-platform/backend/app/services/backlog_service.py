import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.models import ImportSession
from app.utils.csv_parser import read_backlog_chunks, validate_backlog_columns

logger = logging.getLogger(__name__)

BATCH_SIZE = 2000


class BacklogService:

    @staticmethod
    def load_backlog(db: Session, import_id: UUID) -> dict:
        imp = db.query(ImportSession).filter_by(id=import_id).first()
        if not imp:
            raise ValueError(f"ImportSession {import_id} not found")

        if not imp.backlog_file:
            return {"backlog_loaded": 0, "skipped": True}

        import_dir = Path(settings.DATA_DIR) / "imports" / str(import_id)
        backlog_path = import_dir / imp.backlog_file

        if not backlog_path.exists():
            return {"backlog_loaded": 0, "skipped": True}

        errs = validate_backlog_columns(str(backlog_path))
        if errs:
            raise ValueError(f"Backlog validation errors: {errs}")

        loaded = 0

        for chunk in read_backlog_chunks(str(backlog_path), BATCH_SIZE):
            param_rows = []
            for row in chunk:
                ticket_id = int(row["ticket_id"])
                created_raw = row.get("ticket_created_time")
                updated_raw = row.get("ticket_last_change_time")
                state = row.get("current_state_name") or ""
                is_closed = state.lower() in ("closed successful", "closed unsuccessful", "merged")

                param_rows.append({
                    "ticket_id": ticket_id,
                    "ticket_number": row.get("ticket_number"),
                    "title": row.get("title"),
                    "created_at": _parse_backlog_ts(created_raw),
                    "updated_at": _parse_backlog_ts(updated_raw),
                    "current_queue": row.get("current_queue_name"),
                    "current_state": state,
                    "is_closed": is_closed,
                    "is_merged": state.lower() == "merged",
                    "confidence": "minimal",
                    "last_import_id": import_id,
                    "updated_at_ts": datetime.utcnow(),
                })

            if param_rows:
                db.execute(
                    text(
                        """
                        INSERT INTO ticket_snapshots (
                            ticket_id, ticket_number, title,
                            created_at, updated_at,
                            current_queue, current_state,
                            is_closed, is_merged, confidence,
                            last_import_id, updated_at_ts
                        ) VALUES (
                            :ticket_id, :ticket_number, :title,
                            :created_at, :updated_at,
                            :current_queue, :current_state,
                            :is_closed, :is_merged, :confidence,
                            :last_import_id, :updated_at_ts
                        )
                        ON CONFLICT (ticket_id) DO UPDATE SET
                            ticket_number = COALESCE(ticket_snapshots.ticket_number, EXCLUDED.ticket_number),
                            title = COALESCE(ticket_snapshots.title, EXCLUDED.title),
                            created_at = COALESCE(ticket_snapshots.created_at, EXCLUDED.created_at),
                            current_queue = EXCLUDED.current_queue,
                            current_state = EXCLUDED.current_state,
                            is_closed = EXCLUDED.is_closed,
                            is_merged = EXCLUDED.is_merged,
                            last_import_id = EXCLUDED.last_import_id,
                            updated_at_ts = EXCLUDED.updated_at_ts
                        """
                    ),
                    param_rows,
                )
                loaded += len(param_rows)

            db.commit()
            logger.info("Loaded backlog batch (%s total)", loaded)

        return {"backlog_loaded": loaded, "skipped": False}


def _parse_backlog_ts(val) -> datetime | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(val), fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None