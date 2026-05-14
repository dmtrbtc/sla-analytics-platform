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
    def create_team(db: Session, name: str, queue_prefix: str, description: Optional[str] = None) -> Team:
        team = Team(name=name, queue_prefix=queue_prefix, description=description)
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
