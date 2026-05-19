import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.utils.raw_parser import extract_team_prefix, is_system_owner

logger = logging.getLogger(__name__)


class ReconstructorService:

    @staticmethod
    def rebuild(db: Session, import_id: UUID) -> dict:
        ticket_ids = db.execute(
            text(
                "SELECT DISTINCT ticket_id FROM ticket_events "
                "WHERE import_id = :import_id ORDER BY ticket_id"
            ),
            {"import_id": import_id},
        ).scalars().all()

        total_snapshots = 0
        total_ownership = 0
        total_queue = 0
        COMMIT_EVERY = 50

        for idx, tid in enumerate(ticket_ids):
            events = db.execute(
                text(
                    "SELECT ticket_number, title, event_time, event_type, "
                    "queue_name, state_name, owner_name, "
                    "dest_queue, new_owner, new_state "
                    "FROM ticket_events "
                    "WHERE import_id = :import_id AND ticket_id = :tid "
                    "ORDER BY event_seq"
                ),
                {"import_id": import_id, "tid": tid},
            ).mappings().all()

            if not events:
                continue

            ReconstructorService._build_ticket_snapshot(db, tid, events, import_id)

            own_count = ReconstructorService._build_ownership_periods(
                db, tid, events
            )
            total_ownership += own_count

            queue_count = ReconstructorService._build_queue_periods(
                db, tid, events
            )
            total_queue += queue_count

            total_snapshots += 1

            if (idx + 1) % COMMIT_EVERY == 0:
                db.commit()

        db.commit()

        return {
            "snapshots": total_snapshots,
            "ownership_periods": total_ownership,
            "queue_periods": total_queue,
            "tickets": len(ticket_ids),
        }

    @staticmethod
    def _build_ticket_snapshot(
        db: Session,
        ticket_id: int,
        events: list[dict],
        import_id: UUID,
    ) -> None:
        first = events[0]
        last = events[-1]

        first_response_at = None
        resolution_at = None
        is_closed = False
        is_merged = False

        for ev in events:
            if ev["event_type"] in ("SendAnswer", "EmailCustomer", "PhoneCallCustomer"):
                if first_response_at is None:
                    first_response_at = ev["event_time"]

            if ev["event_type"] == "StateUpdate" and ev.get("new_state") in (
                "closed successful",
                "closed unsuccessful",
            ):
                resolution_at = ev["event_time"]
                is_closed = True

            if ev["event_type"] == "Merged":
                is_merged = True

        db.execute(
            text(
                """
                INSERT INTO ticket_snapshots (
                    ticket_id, ticket_number, title,
                    created_at, updated_at,
                    current_queue, current_state, current_owner,
                    first_response_at, resolution_at,
                    is_closed, is_merged, confidence,
                    last_import_id, updated_at_ts
                ) VALUES (
                    :ticket_id, :ticket_number, :title,
                    :created_at, :updated_at,
                    :current_queue, :current_state, :current_owner,
                    :first_response_at, :resolution_at,
                    :is_closed, :is_merged, :confidence,
                    :last_import_id, :updated_at_ts
                )
                ON CONFLICT (ticket_id) DO UPDATE SET
                    current_queue = EXCLUDED.current_queue,
                    current_state = EXCLUDED.current_state,
                    current_owner = EXCLUDED.current_owner,
                    updated_at = EXCLUDED.updated_at,
                    first_response_at = COALESCE(ticket_snapshots.first_response_at, EXCLUDED.first_response_at),
                    resolution_at = COALESCE(ticket_snapshots.resolution_at, EXCLUDED.resolution_at),
                    is_closed = EXCLUDED.is_closed,
                    is_merged = EXCLUDED.is_merged,
                    last_import_id = EXCLUDED.last_import_id,
                    updated_at_ts = EXCLUDED.updated_at_ts
                """
            ),
            {
                "ticket_id": ticket_id,
                "ticket_number": first.get("ticket_number"),
                "title": first.get("title"),
                "created_at": first["event_time"],
                "updated_at": last["event_time"],
                "current_queue": last.get("queue_name"),
                "current_state": last.get("state_name"),
                "current_owner": last.get("owner_name"),
                "first_response_at": first_response_at,
                "resolution_at": resolution_at,
                "is_closed": is_closed,
                "is_merged": is_merged,
                "confidence": "partial",
                "last_import_id": import_id,
                "updated_at_ts": datetime.utcnow(),
            },
        )

    @staticmethod
    def _build_ownership_periods(
        db: Session, ticket_id: int, events: list[dict]
    ) -> int:
        db.execute(
            text("DELETE FROM ownership_periods WHERE ticket_id = :tid"),
            {"tid": ticket_id},
        )

        current_owner: Optional[str] = None
        period_start: Optional[datetime] = None
        count = 0

        for ev in events:
            ev_time = ev["event_time"]
            new_owner: Optional[str] = None

            if ev["event_type"] == "OwnerUpdate" and ev.get("new_owner"):
                new_owner = ev["new_owner"]

            if new_owner is not None and new_owner != current_owner:
                if current_owner is not None and period_start is not None:
                    _insert_ownership_period(
                        db, ticket_id, current_owner, ev.get("queue_name"),
                        period_start, ev_time,
                    )
                    count += 1

                current_owner = new_owner
                period_start = ev_time

        if current_owner is not None and period_start is not None:
            last_time = events[-1]["event_time"]
            _insert_ownership_period(
                db, ticket_id, current_owner, events[-1].get("queue_name"),
                period_start, last_time, is_active=True,
            )
            count += 1

        return count

    @staticmethod
    def _build_queue_periods(
        db: Session, ticket_id: int, events: list[dict]
    ) -> int:
        db.execute(
            text("DELETE FROM queue_periods WHERE ticket_id = :tid"),
            {"tid": ticket_id},
        )

        current_queue: Optional[str] = None
        period_start: Optional[datetime] = None
        owners_in_queue = set()
        count = 0

        for ev in events:
            ev_time = ev["event_time"]
            qname = ev.get("queue_name")

            if ev.get("dest_queue"):
                qname = ev["dest_queue"]

            if qname and qname != current_queue:
                if current_queue is not None and period_start is not None:
                    _insert_queue_period(
                        db, ticket_id, current_queue,
                        period_start, ev_time, len(owners_in_queue),
                    )
                    count += 1

                current_queue = qname
                period_start = ev_time
                owners_in_queue = set()

            owner = ev.get("owner_name")
            if owner and not is_system_owner(owner):
                owners_in_queue.add(owner)

        if current_queue is not None and period_start is not None:
            last_time = events[-1]["event_time"]
            _insert_queue_period(
                db, ticket_id, current_queue,
                period_start, last_time, len(owners_in_queue),
                is_active=True,
            )
            count += 1

        return count


def _insert_ownership_period(
    db: Session,
    ticket_id: int,
    owner: str,
    queue_name: Optional[str],
    start_time: datetime,
    end_time: datetime,
    is_active: bool = False,
) -> None:
    dur = int((end_time - start_time).total_seconds()) if end_time and start_time else 0
    db.execute(
        text(
            """
            INSERT INTO ownership_periods (
                ticket_id, owner, queue_name, team_prefix,
                start_time, end_time, duration_seconds, is_active
            ) VALUES (
                :ticket_id, :owner, :queue_name, :team_prefix,
                :start_time, :end_time, :duration_seconds, :is_active
            )
            """
        ),
        {
            "ticket_id": ticket_id,
            "owner": owner,
            "queue_name": queue_name,
            "team_prefix": extract_team_prefix(queue_name),
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": max(0, dur),
            "is_active": is_active,
        },
    )


def _insert_queue_period(
    db: Session,
    ticket_id: int,
    queue_name: str,
    entered_at: datetime,
    exited_at: datetime,
    owner_count: int,
    is_active: bool = False,
) -> None:
    dur = int((exited_at - entered_at).total_seconds()) if exited_at and entered_at else 0
    db.execute(
        text(
            """
            INSERT INTO queue_periods (
                ticket_id, queue_name, team_prefix,
                entered_at, exited_at, duration_seconds, owner_count
            ) VALUES (
                :ticket_id, :queue_name, :team_prefix,
                :entered_at, :exited_at, :duration_seconds, :owner_count
            )
            """
        ),
        {
            "ticket_id": ticket_id,
            "queue_name": queue_name,
            "team_prefix": extract_team_prefix(queue_name),
            "entered_at": entered_at,
            "exited_at": exited_at,
            "duration_seconds": max(0, dur),
            "owner_count": owner_count,
        },
    )
