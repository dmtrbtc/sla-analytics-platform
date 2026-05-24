"""Operations Intelligence API — domain-aware queue analytics (v2.2 scope-aware).

Endpoints:
  GET /operations/intelligence/servicedesk
  GET /operations/intelligence/assetmanagement
  GET /operations/intelligence/workplace
  GET /operations/intelligence/multimedia
  GET /operations/intelligence/overview   # rolls up all four

All four domain endpoints + the overview accept:
  ?period=24h|1d|7d|30d|90d|365d
  ?since=<ISO>  ?until=<ISO>
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import sync_session_factory
from app.core.dependencies import get_current_user
from app.services.forensics.domain_intelligence import DomainIntelligence
from app.services.forensics.time_scope import parse_time_scope

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


_DISPATCH = {
    "servicedesk":     DomainIntelligence.servicedesk,
    "assetmanagement": DomainIntelligence.assetmanagement,
    "workplace":       DomainIntelligence.workplace,
    "multimedia":      DomainIntelligence.multimedia,
}


@router.get("/{domain}")
def domain_intelligence(
    domain: str,
    period: Optional[str] = Query(None, description="24h | 1d | 7d | 30d | 90d"),
    since: Optional[str] = Query(None),
    until: Optional[str] = Query(None),
):
    fn = _DISPATCH.get(domain.lower())
    if not fn:
        raise HTTPException(404, f"Unknown domain '{domain}'. "
                            f"Allowed: {sorted(_DISPATCH.keys())}")
    sc = parse_time_scope(period=period, since=since, until=until)
    with sync_session_factory() as db:
        result = fn(db, scope=sc)
        if isinstance(result, dict):
            result.setdefault("scope", sc.to_dict())
        return result


@router.get("")
def domain_overview(
    period: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    until: Optional[str] = Query(None),
):
    """All four domains in one trip, for the operational landing screen."""
    sc = parse_time_scope(period=period, since=since, until=until)
    with sync_session_factory() as db:
        return {
            "scope": sc.to_dict(),
            "servicedesk":     DomainIntelligence.servicedesk(db, scope=sc),
            "assetmanagement": DomainIntelligence.assetmanagement(db, scope=sc),
            "workplace":       DomainIntelligence.workplace(db, scope=sc),
            "multimedia":      DomainIntelligence.multimedia(db, scope=sc),
        }
