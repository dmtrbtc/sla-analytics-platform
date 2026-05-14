from fastapi import APIRouter

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

api_router.include_router(users.router, prefix="/auth", tags=["auth"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(dashboards.router, prefix="/dashboards", tags=["dashboards"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(teams.router, prefix="/teams", tags=["teams"])
api_router.include_router(sla.router, prefix="/sla", tags=["sla"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
