"""Seed default SLA definitions and admin user into the database."""

import logging
from datetime import datetime, timezone

from app.core.database import sync_session_factory
from app.core.security import get_password_hash, verify_password
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


ADMIN_EMAIL = "admin"
ADMIN_PASSWORD = "admin123"


def seed_admin_user() -> None:
    db = sync_session_factory()
    try:
        user = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        expected_hash = get_password_hash(ADMIN_PASSWORD)

        if user is None:
            user = User(
                email=ADMIN_EMAIL,
                display_name="Administrator",
                password_hash=expected_hash,
                role="admin",
            )
            db.add(user)
            db.commit()
            logger.info("Created default admin user: %s / %s", ADMIN_EMAIL, ADMIN_PASSWORD)
            return

        needs_update = False
        if not verify_password(ADMIN_PASSWORD, user.password_hash):
            logger.warning("Admin password hash mismatch — updating")
            user.password_hash = expected_hash
            needs_update = True
        if user.role != "admin":
            logger.warning("Admin role was '%s' — resetting to 'admin'", user.role)
            user.role = "admin"
            needs_update = True
        if not user.is_active:
            logger.warning("Admin was inactive — reactivating")
            user.is_active = True
            needs_update = True

        if needs_update:
            user.updated_at = datetime.now(timezone.utc)
            db.add(user)
            db.commit()
            logger.info("Admin user updated (%s)", ADMIN_EMAIL)
        else:
            logger.info("Admin user OK (%s)", ADMIN_EMAIL)
    except Exception:
        logger.exception("Failed to seed admin user")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_sla_definitions()
    seed_admin_user()
