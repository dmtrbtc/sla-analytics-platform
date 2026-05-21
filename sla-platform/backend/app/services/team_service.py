"""Team management service."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Team, UserTeam


class TeamService:

    @staticmethod
    def list_teams(db: Session, active_only: bool = False) -> list[Team]:
        q = select(Team)
        if active_only:
            q = q.where(Team.is_active == True)
        return list(db.execute(q.order_by(Team.name)).scalars().all())

    @staticmethod
    def get_team(db: Session, team_id: int) -> Optional[Team]:
        return db.get(Team, team_id)

    @staticmethod
    def create_team(
        db: Session,
        name: str,
        queue_prefix: str,
        description: Optional[str] = None,
        **extra,
    ) -> Team:
        # Forward v1.4 operational fields if provided (lead_user_id, color,
        # response_target_seconds, resolution_target_seconds, escalation_chain,
        # queues). Unknown keys ignored — Team only stores its real columns.
        allowed = {"lead_user_id", "color", "response_target_seconds",
                   "resolution_target_seconds", "escalation_chain", "queues",
                   "is_active"}
        kwargs = {k: v for k, v in extra.items() if k in allowed and v is not None}
        team = Team(name=name, queue_prefix=queue_prefix, description=description, **kwargs)
        db.add(team)
        db.commit()
        db.refresh(team)
        return team

    @staticmethod
    def update_team(db: Session, team_id: int, **kwargs) -> Optional[Team]:
        team = db.get(Team, team_id)
        if not team:
            return None
        for k, v in kwargs.items():
            if hasattr(team, k):
                setattr(team, k, v)
        db.commit()
        db.refresh(team)
        return team

    @staticmethod
    def delete_team(db: Session, team_id: int) -> bool:
        team = db.get(Team, team_id)
        if not team:
            return False
        db.delete(team)
        db.commit()
        return True

    # --- v1.4 team membership ----------------------------------------------

    @staticmethod
    def list_members(db: Session, team_id: int) -> list[dict]:
        from app.domain.models import User
        rows = db.execute(
            select(User.id, User.email, User.display_name, User.role, User.is_active)
            .join(UserTeam, UserTeam.user_id == User.id)
            .where(UserTeam.team_id == team_id)
        ).all()
        return [
            {
                "id": str(r[0]), "email": r[1], "display_name": r[2],
                "role": r[3], "is_active": r[4],
            }
            for r in rows
        ]

    @staticmethod
    def add_member(db: Session, team_id: int, user_id) -> bool:
        existing = db.get(UserTeam, (user_id, team_id))
        if existing:
            return True
        db.add(UserTeam(user_id=user_id, team_id=team_id))
        db.commit()
        return True

    @staticmethod
    def remove_member(db: Session, team_id: int, user_id) -> bool:
        m = db.get(UserTeam, (user_id, team_id))
        if not m:
            return False
        db.delete(m)
        db.commit()
        return True

    @staticmethod
    def cleanup_dummies(db: Session) -> int:
        """Remove rows that look like leftover test fixtures.

        Heuristic: name='Incomplete' OR queue_prefix='inc' OR description IS NULL
        AND no members. Returns count deleted. Admin-only — callers must gate.
        """
        # Find candidate IDs
        rows = db.execute(
            select(Team.id)
            .where(
                (Team.name == "Incomplete") |
                (Team.queue_prefix == "inc") |
                (Team.name == "Support Team")
            )
        ).scalars().all()
        ids = list(rows)
        if not ids:
            return 0
        # Drop their memberships first
        db.execute(
            UserTeam.__table__.delete().where(UserTeam.team_id.in_(ids))
        )
        # Then the teams themselves
        deleted = db.execute(
            Team.__table__.delete().where(Team.id.in_(ids))
        ).rowcount
        db.commit()
        return deleted or 0
