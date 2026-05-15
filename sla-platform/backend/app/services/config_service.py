"""Enterprise configuration service — reads from DB + cache."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.cache import cache_key, get, set
from app.core.database import sync_session_factory
from app.models.enterprise_config import AppConfig

logger = logging.getLogger(__name__)

CONFIG_TTL = 600


def _get_all_configs(db: Session) -> dict[str, Any]:
    rows = db.query(AppConfig).all()
    return {r.config_key: r.config_value for r in rows}


def get_config(key: str, default: Any = None) -> Any:
    """Get a config value by key (cached)."""
    cache_key_val = cache_key("config", key)
    cached = get(cache_key_val)
    if cached is not None:
        return cached
    db = sync_session_factory()
    try:
        row = db.query(AppConfig).filter(AppConfig.config_key == key).first()
        val = row.config_value if row else default
        set(cache_key_val, val, CONFIG_TTL)
        return val
    finally:
        db.close()


def set_config(key: str, value: Any, updated_by: str = "system") -> bool:
    """Update a config value and invalidate cache."""
    db = sync_session_factory()
    try:
        row = db.query(AppConfig).filter(AppConfig.config_key == key).first()
        if row:
            row.config_value = value
            row.updated_at = datetime.now(timezone.utc)
            row.updated_by = updated_by
        else:
            db.add(AppConfig(
                config_key=key,
                config_value=value,
                updated_at=datetime.now(timezone.utc),
                updated_by=updated_by,
            ))
        db.commit()
        # Invalidate cache
        from app.core.cache import delete as del_cache
        del_cache(cache_key("config", key))
        return True
    except Exception as exc:
        db.rollback()
        logger.error("Failed to set config %s: %s", key, exc)
        return False
    finally:
        db.close()


def get_all_configs() -> dict[str, Any]:
    """Get all config values."""
    db = sync_session_factory()
    try:
        return _get_all_configs(db)
    finally:
        db.close()
