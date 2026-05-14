from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.api.v1 import (
    imports,
    tickets,
    dashboards,
    reports,
    teams,
    sla,
    users,
    audit,
)

api_router = APIRouter()

# Public auth endpoints (no auth required)
api_router.include_router(users.router, prefix="/auth", tags=["auth"])

# All other routes require authentication
protected_router = APIRouter(dependencies=[Depends(get_current_user)])

protected_router.include_router(imports.router, prefix="/imports", tags=["imports"])
protected_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
protected_router.include_router(dashboards.router, prefix="/dashboards", tags=["dashboards"])
protected_router.include_router(reports.router, prefix="/reports", tags=["reports"])
protected_router.include_router(teams.router, prefix="/teams", tags=["teams"])
protected_router.include_router(sla.router, prefix="/sla", tags=["sla"])
protected_router.include_router(audit.router, prefix="/audit", tags=["audit"])

api_router.include_router(protected_router)
