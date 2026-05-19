import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.utils.raw_parser import is_system_owner, extract_team_prefix

logger = logging.getLogger(__name__)

BATCH_SIZE = 2000


class NormalizerService:

    @staticmethod
    def normalize(db: Session, import_id: UUID) -> dict:
        raw_count = db.execute(
            text("SELECT COUNT(*) FROM raw_events WHERE import_id = :import_id"),
            {"import_id": import_id},
        ).scalar()

        if not raw_count:
            return {"normalized": 0, "deduplicated": 0}

        NormalizerService._clear_normalized(db, import_id)
        db.commit()

        ticket_ids = db.execute(
            text(
                "SELECT DISTINCT ticket_id FROM raw_events "
                "WHERE import_id = :import_id ORDER BY ticket_id"
            ),
            {"import_id": import_id},
        ).scalars().all()

        total_normalized = 0
        total_dedup = 0

        for tid in ticket_ids:
            raw_events = db.execute(
                text(
                    "SELECT id, ticket_number, event_time, event_name, "
                    "queue_name, state_name, event_owner_name, src_queue, "
                    "dest_queue, old_state, new_state, new_owner, "
                    "pending_until, duplicate_key, event_raw_name "
                    "FROM raw_events "
                    "WHERE import_id = :import_id AND ticket_id = :tid "
                    "ORDER BY event_time, id"
                ),
                {"import_id": import_id, "tid": tid},
            ).mappings().all()

            seen_keys = set()
            unique_events = []
            for ev in raw_events:
                dk = ev.get("duplicate_key") or "{}|{}|{}".format(
                    ev["event_time"], ev["event_name"], ev["event_raw_name"]
                )
                if dk in seen_keys:
                    total_dedup += 1
                    continue
                seen_keys.add(dk)
                unique_events.append(ev)

            norm_events = NormalizerService._build_normalized(
                tid, unique_events, import_id
            )
            total_normalized += len(norm_events)

            for offset in range(0, len(norm_events), 2000):
                batch = norm_events[offset:offset + 2000]
                db.execute(
                    text("""
                        INSERT INTO ticket_events (
                            ticket_id, ticket_number, event_seq, event_time,
                            event_type, queue_name, state_name, owner_name,
                            src_queue, dest_queue, old_state, new_state,
                            new_owner, old_owner, pending_until,
                            is_system_action, import_id, raw_event_id
                        ) VALUES (
                            :ticket_id, :ticket_number, :event_seq, :event_time,
                            :event_type, :queue_name, :state_name, :owner_name,
                            :src_queue, :dest_queue, :old_state, :new_state,
                            :new_owner, :old_owner, :pending_until,
                            :is_system_action, :import_id, :raw_event_id
                        )
                    """),
                    batch,
                )

            db.commit()

        return {
            "normalized": total_normalized,
            "deduplicated": total_dedup,
            "tickets": len(ticket_ids),
        }

    @staticmethod
    def _clear_normalized(db: Session, import_id: UUID) -> None:
        db.execute(
            text("DELETE FROM ticket_events WHERE import_id = :import_id"),
            {"import_id": import_id},
        )

    @staticmethod
    def _build_normalized(
        ticket_id: int, raw_events: list[dict], import_id: UUID
    ) -> list[dict]:
        current_owner: Optional[str] = None
        result = []

        for idx, ev in enumerate(raw_events):
            owner_name = ev.get("event_owner_name") or ""
            old_owner = current_owner

            if ev["event_name"] == "OwnerUpdate":
                new_owner = ev.get("new_owner")
                if new_owner:
                    current_owner = new_owner

            if ev["event_name"] in ("Lock", "Unlock"):
                if owner_name and owner_name != "root@localhost":
                    current_owner = owner_name

            if ev["event_name"] == "Move" and ev.get("dest_queue"):
                if owner_name and owner_name != "root@localhost":
                    current_owner = owner_name

            result.append(
                {
                    "ticket_id": ticket_id,
                    "ticket_number": ev.get("ticket_number"),
                    "event_seq": idx + 1,
                    "event_time": _parse_ts(ev.get("event_time")),
                    "event_type": ev["event_name"],
                    "queue_name": ev.get("queue_name"),
                    "state_name": ev.get("state_name"),
                    "owner_name": current_owner or owner_name or None,
                    "src_queue": ev.get("src_queue"),
                    "dest_queue": ev.get("dest_queue"),
                    "old_state": ev.get("old_state"),
                    "new_state": ev.get("new_state"),
                    "new_owner": ev.get("new_owner"),
                    "old_owner": old_owner,
                    "pending_until": ev.get("pending_until"),
                    "is_system_action": is_system_owner(
                        ev.get("event_owner_name")
                    ),
                    "import_id": import_id,
                    "raw_event_id": ev.get("id"),
                }
            )

        return result


def _parse_ts(val) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(val), fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None
