"""Operations Intelligence API — domain-aware queue analytics (v1.6).

Endpoints:
  GET /operations/intelligence/servicedesk
  GET /operations/intelligence/assetmanagement
  GET /operations/intelligence/workplace
  GET /operations/intelligence/multimedia
  GET /operations/intelligence/overview   # rolls up all four
"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.database import sync_session_factory
from app.core.dependencies import get_current_user
from app.services.forensics.domain_intelligence import DomainIntelligence

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


_DISPATCH = {
    "servicedesk":     DomainIntelligence.servicedesk,
    "assetmanagement": DomainIntelligence.assetmanagement,
    "workplace":       DomainIntelligence.workplace,
    "multimedia":      DomainIntelligence.multimedia,
}


@router.get("/{domain}")
def domain_intelligence(domain: str):
    fn = _DISPATCH.get(domain.lower())
    if not fn:
        raise HTTPException(404, f"Unknown domain '{domain}'. "
                            f"Allowed: {sorted(_DISPATCH.keys())}")
    with sync_session_factory() as db:
        return fn(db)


@router.get("")
def domain_overview():
    """All four domains in one trip, for the operational landing screen."""
    with sync_session_factory() as db:
        return {
            "servicedesk":     DomainIntelligence.servicedesk(db),
            "assetmanagement": DomainIntelligence.assetmanagement(db),
            "workplace":       DomainIntelligence.workplace(db),
            "multimedia":      DomainIntelligence.multimedia(db),
        }
