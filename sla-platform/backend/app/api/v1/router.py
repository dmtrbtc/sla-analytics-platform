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
    analytics,
    ai_ops,
    incidents,
    diagnostics,
    organizations,
    operations,
    security,
    billing,
    rbac_api,
    integrations_api,
    compliance_api,
    ha,
    governance,
    executive,
    ai_ops_v3,
    enterprise_reports,
    operations_admin,
    attachments,
    queue_intelligence,
    forensics,
    favorites,
    queue_details,
    sla_governance,
)

api_router = APIRouter()

api_router.include_router(users.router, prefix="/auth", tags=["auth"])

protected_router = APIRouter(dependencies=[Depends(get_current_user)])

protected_router.include_router(imports.router, prefix="/imports", tags=["imports"])
protected_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
protected_router.include_router(dashboards.router, prefix="/dashboards", tags=["dashboards"])
protected_router.include_router(reports.router, prefix="/reports", tags=["reports"])
protected_router.include_router(teams.router, prefix="/teams", tags=["teams"])
protected_router.include_router(sla.router, prefix="/sla", tags=["sla"])
protected_router.include_router(audit.router, prefix="/audit", tags=["audit"])
protected_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
protected_router.include_router(ai_ops.router, prefix="/ai", tags=["ai"])
protected_router.include_router(incidents.router, prefix="/ops", tags=["incidents"])
protected_router.include_router(diagnostics.router, prefix="/system", tags=["system"])
protected_router.include_router(organizations.router, prefix="/admin", tags=["admin"])
protected_router.include_router(operations.router, prefix="/ops", tags=["operations"])
protected_router.include_router(security.router, prefix="/security", tags=["security"])
protected_router.include_router(billing.router, prefix="/billing", tags=["billing"])
protected_router.include_router(rbac_api.router, prefix="/rbac", tags=["rbac"])
protected_router.include_router(integrations_api.router, prefix="/integrations", tags=["integrations"])
protected_router.include_router(compliance_api.router, prefix="/compliance", tags=["compliance"])
protected_router.include_router(ha.router, prefix="/ha", tags=["ha"])
protected_router.include_router(governance.router, prefix="/sla", tags=["governance"])
protected_router.include_router(executive.router, prefix="/executive", tags=["executive"])
protected_router.include_router(ai_ops_v3.router, prefix="/ai", tags=["ai-v3"])
protected_router.include_router(enterprise_reports.router, prefix="/enterprise-reports", tags=["enterprise-reports"])
protected_router.include_router(operations_admin.router, prefix="/operations", tags=["operations-admin"])
protected_router.include_router(attachments.router, prefix="/attachments", tags=["attachments"])
protected_router.include_router(queue_intelligence.router, prefix="/queue-intelligence", tags=["queue-intelligence"])
protected_router.include_router(forensics.router, prefix="/analytics/forensics", tags=["forensics-v3"])
protected_router.include_router(favorites.router, prefix="/favorites", tags=["favorites-v14"])
protected_router.include_router(queue_details.router, prefix="/queues", tags=["queue-detail-v14"])
protected_router.include_router(sla_governance.contribution_router, prefix="/analytics/forensics", tags=["forensics-v3"])
# Mounted under /sla/v15 to avoid colliding with the older /sla/queue-rules/{rule_id}
# and /sla/simulate handlers in sla.py. These are the v1.5 governance additions.
protected_router.include_router(sla_governance.sla_governance_router, prefix="/sla/v15", tags=["sla-governance-v15"])
protected_router.include_router(sla_governance.team_dash_router, prefix="/teams", tags=["teams-v15"])

api_router.include_router(protected_router)
