"""Enterprise Integrations API — API tokens, webhooks, Slack/Teams/Jira/OTRS."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, sync_session_factory
from app.core.dependencies import get_current_user, require_admin
from app.domain.models import User
from app.services.integrations.webhooks import (
    generate_api_token, validate_api_token, revoke_api_token,
    register_webhook, dispatch_webhook,
    send_slack_notification, send_teams_notification,
    create_jira_issue, query_otrs_ticket,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("/tokens")
async def create_token(data: dict[str, Any], current_user: User = Depends(get_current_user)):
    result = generate_api_token(current_user.id, data.get("name", "API Token"), data.get("permissions"))
    return {"token": result}


@router.delete("/tokens/{token_id}")
async def revoke_token(token_id: UUID, _: User = Depends(require_admin)):
    revoke_api_token(token_id)
    return {"revoked": True}


@router.get("/tokens")
async def list_tokens(current_user: User = Depends(get_current_user)):
    db = sync_session_factory()
    try:
        rows = db.execute(
            text("SELECT id, name, permissions, created_at, expires_at, is_active FROM api_tokens WHERE user_id = :uid"),
            {"uid": current_user.id},
        ).mappings().all()
        return {"tokens": [dict(r) for r in rows]}
    finally:
        db.close()


@router.get("/webhooks")
async def list_webhooks(current_user: User = Depends(get_current_user)):
    db = sync_session_factory()
    try:
        rows = db.execute(
            text("SELECT id, name, url, events, is_active, created_at FROM webhooks WHERE organization_id IN (SELECT organization_id FROM users WHERE id = :uid)"),
            {"uid": current_user.id},
        ).mappings().all()
        return {"webhooks": [dict(r) for r in rows]}
    finally:
        db.close()


@router.post("/webhooks")
async def create_webhook(data: dict[str, Any], _: User = Depends(require_admin)):
    org_id = data.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_id required")
    result = register_webhook(
        UUID(org_id) if isinstance(org_id, str) else org_id,
        data["name"], data["url"], data.get("events", ["*"]),
    )
    return {"webhook": result}


@router.post("/webhooks/test-slack")
async def test_slack(data: dict[str, str], _: User = Depends(require_admin)):
    result = send_slack_notification(data["url"], data.get("message", "Test from SLA Platform"))
    return result


@router.post("/webhooks/test-teams")
async def test_teams(data: dict[str, str], _: User = Depends(require_admin)):
    result = send_teams_notification(data["url"], data.get("title", "Test"), data.get("message", "Test from SLA Platform"))
    return result


@router.post("/jira/issue")
async def create_jira(data: dict[str, Any], _: User = Depends(require_admin)):
    result = create_jira_issue(data["base_url"], data["token"], data["project"], data["summary"], data.get("description", ""), data.get("issue_type", "Bug"))
    return result


@router.get("/otrs/ticket/{ticket_id}")
async def query_otrs(ticket_id: int, base_url: str = Query(...), token: str = Query(...), _: User = Depends(require_admin)):
    result = query_otrs_ticket(base_url, token, ticket_id)
    return {"ticket": result}
