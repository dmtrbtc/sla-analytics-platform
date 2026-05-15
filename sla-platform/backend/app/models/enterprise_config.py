"""Enterprise configuration model — admin-managed settings stored in DB."""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.domain.models import Base


class AppConfig(Base):
    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(JSONB, nullable=False, default=dict)
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True))
    updated_by = Column(String(255))
