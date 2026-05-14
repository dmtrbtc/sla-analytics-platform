"""Seed default SLA definitions and admin user into the database."""

import logging

from app.core.database import sync_session_factory
from app.core.security import get_password_hash
from app.domain.models import SLADefinition, User

logger = logging.getLogger(__name__)

DEFAULT_SLA_DEFINITIONS = [
    {
        "name": "Standard Support",
        "queue_pattern": "Support*",
        "priority": None,
        "response_target_seconds": 28800,
        "resolution_target_seconds": 144000,
        "pause_on_pending": True,
        "business_hours_only": False,
        "is_active": True,
    },
    {
        "name": "Critical Priority",
        "queue_pattern": "*",
        "priority": "5 critical",
        "response_target_seconds": 3600,
        "resolution_target_seconds": 28800,
        "pause_on_pending": True,
        "business_hours_only": False,
        "is_active": True,
    },
    {
        "name": "High Priority",
        "queue_pattern": "*",
        "priority": "4 high",
        "response_target_seconds": 14400,
        "resolution_target_seconds": 57600,
        "pause_on_pending": True,
        "business_hours_only": False,
        "is_active": True,
    },
    {
        "name": "Service Desk",
        "queue_pattern": "ServiceDesk*",
        "priority": None,
        "response_target_seconds": 7200,
        "resolution_target_seconds": 86400,
        "pause_on_pending": True,
        "business_hours_only": False,
        "is_active": True,
    },
]


def seed_sla_definitions() -> None:
    db = sync_session_factory()
    try:
        existing = db.query(SLADefinition).count()
        if existing > 0:
            logger.info("SLA definitions already seeded (%d found)", existing)
            return

        for data in DEFAULT_SLA_DEFINITIONS:
            sd = SLADefinition(**data)
            db.add(sd)

        db.commit()
        logger.info("Seeded %d SLA definitions", len(DEFAULT_SLA_DEFINITIONS))
    except Exception:
        logger.exception("Failed to seed SLA definitions")
        db.rollback()
    finally:
        db.close()


def seed_admin_user() -> None:
    db = sync_session_factory()
    try:
        existing = db.query(User).filter(User.role == "admin").first()
        if existing:
            logger.info("Admin user already exists (%s)", existing.email)
            return

        admin = User(
            email="admin@sla-platform.dev",
            display_name="Administrator",
            password_hash=get_password_hash("admin123"),
            role="admin",
        )
        db.add(admin)
        db.commit()
        logger.info("Created default admin user: admin@sla-platform.dev / admin123")
    except Exception:
        logger.exception("Failed to seed admin user")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_sla_definitions()
    seed_admin_user()
