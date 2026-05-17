"""Data lifecycle management: archiving, purging, and retention policies."""
from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import sync_session_factory
from app.domain.enums import ImportStatus
from app.domain.models import (
    ImportSession,
    OwnershipPeriod,
    QueuePeriod,
    RawEvent,
    SLAMetric,
    TicketEvent,
    TicketSnapshot,
)

logger = logging.getLogger(__name__)
ARCHIVE_DIR = os.path.join(settings.DATA_DIR, "archives")

os.makedirs(ARCHIVE_DIR, exist_ok=True)


def archive_import(import_id: str) -> dict:
    """Archive an import: export raw_events + ticket_events + sla_metrics to JSON."""
    db = sync_session_factory()
    try:
        imp = db.query(ImportSession).filter_by(id=import_id).first()
        if not imp:
            return {"error": "Import not found"}

        archive = {
            "import_session": {c.name: str(getattr(imp, c.name)) for c in imp.__table__.columns},
            "raw_events": [dict(r.__dict__) for r in db.query(RawEvent).filter(RawEvent.import_id == import_id).yield_per(5000)],
            "ticket_events": [dict(r.__dict__) for r in db.query(TicketEvent).filter(TicketEvent.import_id == import_id).yield_per(5000)],
            "sla_metrics": [dict(r.__dict__) for r in db.query(SLAMetric).filter(SLAMetric.import_id == import_id).yield_per(5000)],
        }

        # Clean non-serializable fields
        for table_key in ["raw_events", "ticket_events", "sla_metrics"]:
            for row in archive[table_key]:
                row.pop("_sa_instance_state", None)

        archive_path = os.path.join(ARCHIVE_DIR, f"import_{import_id}.json")
        with open(archive_path, "w") as f:
            json.dump(archive, f, default=str, indent=2)

        imp.stats = dict(imp.stats or {})
        imp.stats["archived"] = True
        imp.stats["archive_path"] = archive_path
        imp.stats["archived_at"] = datetime.now(timezone.utc).isoformat()
        db.commit()

        logger.info("Archived import %s to %s", import_id, archive_path)
        return {"import_id": import_id, "archive_path": archive_path, "size_bytes": os.path.getsize(archive_path)}
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to archive import %s", import_id)
        return {"error": str(exc)}
    finally:
        db.close()


def purge_import(import_id: str, archive_first: bool = True) -> dict:
    """Purge all data for an import session."""
    db = sync_session_factory()
    try:
        if archive_first:
            result = archive_import(import_id)
            if "error" in result:
                return result

        tables = [RawEvent, TicketEvent, SLAMetric]
        deleted = {}
        for table in tables:
            count = db.query(table).filter(table.import_id == import_id).delete()
            deleted[table.__tablename__] = count

        # Also clean up ownership/queue periods linked via tickets from this import
        ticket_ids = [r[0] for r in db.query(TicketSnapshot.ticket_id).filter(TicketSnapshot.last_import_id == import_id).all()]
        if ticket_ids:
            qp = db.query(QueuePeriod).filter(QueuePeriod.ticket_id.in_(ticket_ids)).delete()
            op = db.query(OwnershipPeriod).filter(OwnershipPeriod.ticket_id.in_(ticket_ids)).delete()
            ts = db.query(TicketSnapshot).filter(TicketSnapshot.last_import_id == import_id).delete()
            deleted["queue_periods"] = qp
            deleted["ownership_periods"] = op
            deleted["ticket_snapshots"] = ts

        imp = db.query(ImportSession).filter_by(id=import_id).first()
        if imp:
            imp.status = "purged"
            db.commit()

        logger.info("Purged import %s: %s", import_id, deleted)
        return {"import_id": import_id, "deleted": deleted}
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to purge import %s", import_id)
        return {"error": str(exc)}
    finally:
        db.close()


def restore_import(import_id: str) -> dict:
    """Restore an import from its archive file."""
    archive_path = os.path.join(ARCHIVE_DIR, f"import_{import_id}.json")
    if not os.path.exists(archive_path):
        return {"error": f"Archive not found: {archive_path}"}

    db = sync_session_factory()
    try:
        with open(archive_path) as f:
            archive = json.load(f)

        # Re-insert raw events
        restored = {}
        for event_data in archive.get("raw_events", []):
            event_data.pop("id", None)
            db.execute(text("""INSERT INTO raw_events (import_id, ticket_id, ticket_number, title, event_time, event_name, queue_name, state_name, event_owner_name, event_raw_name, src_queue, dest_queue, old_state, new_state, new_owner, pending_until, sla_name, duplicate_key, is_duplicate) VALUES (:import_id, :ticket_id, :ticket_number, :title, :event_time, :event_name, :queue_name, :state_name, :event_owner_name, :event_raw_name, :src_queue, :dest_queue, :old_state, :new_state, :new_owner, :pending_until, :sla_name, :duplicate_key, :is_duplicate)"""), event_data)
        restored["raw_events"] = len(archive.get("raw_events", []))

        for event_data in archive.get("ticket_events", []):
            event_data.pop("id", None)
            db.execute(text("""INSERT INTO ticket_events (ticket_id, ticket_number, event_seq, event_time, event_type, queue_name, state_name, owner_name, src_queue, dest_queue, old_state, new_state, new_owner, old_owner, pending_until, is_system_action, import_id, raw_event_id) VALUES (:ticket_id, :ticket_number, :event_seq, :event_time, :event_type, :queue_name, :state_name, :owner_name, :src_queue, :dest_queue, :old_state, :new_state, :new_owner, :old_owner, :pending_until, :is_system_action, :import_id, :raw_event_id)"""), event_data)
        restored["ticket_events"] = len(archive.get("ticket_events", []))

        for metric_data in archive.get("sla_metrics", []):
            metric_data.pop("id", None)
            db.execute(text("""INSERT INTO sla_metrics (ticket_id, metric_name, metric_seconds, sla_breached, queue_name, owner, team_prefix, sla_definition_id, import_id, confidence, computed_at) VALUES (:ticket_id, :metric_name, :metric_seconds, :sla_breached, :queue_name, :owner, :team_prefix, :sla_definition_id, :import_id, :confidence, :computed_at)"""), metric_data)
        restored["sla_metrics"] = len(archive.get("sla_metrics", []))

        imp = db.query(ImportSession).filter_by(id=import_id).first()
        if imp:
            imp.status = ImportStatus.COMPLETED.value
            db.commit()

        logger.info("Restored import %s: %s", import_id, restored)
        return {"import_id": import_id, "restored": restored}
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to restore import %s", import_id)
        return {"error": str(exc)}
    finally:
        db.close()


def apply_retention_policy(retention_days: int = 365) -> dict:
    """Archive and purge imports older than retention_days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    db = sync_session_factory()
    try:
        old_imports = (
            db.query(ImportSession)
            .filter(ImportSession.created_at < cutoff)
            .all()
        )
        results = []
        for imp in old_imports:
            import_id = str(imp.id)
            arch = archive_import(import_id)
            if "error" not in arch:
                purged = purge_import(import_id, archive_first=False)
                results.append({"import_id": import_id, "archived": True, "purged": purged.get("deleted")})
            else:
                results.append({"import_id": import_id, "error": arch["error"]})
        return {"retention_days": retention_days, "processed": len(results), "results": results}
    finally:
        db.close()
