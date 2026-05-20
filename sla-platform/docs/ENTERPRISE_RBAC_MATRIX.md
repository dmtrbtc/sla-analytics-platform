# Enterprise RBAC Matrix

## Roles

| Role | Description |
|------|-------------|
| admin | Full system access, all permissions |
| team_lead | Queue management + team analytics + SLA editing |
| analyst | View + create reports, dashboards, exports |
| viewer | Read-only access to dashboards, tickets, SLA |

## Permission Groups

### SLA (sla.*)
| Permission | admin | team_lead | analyst | viewer |
|-----------|-------|-----------|---------|--------|
| sla.view | ✓ | ✓ | ✓ | ✓ |
| sla.edit | ✓ | ✓ | ✗ | ✗ |
| sla.manage | ✓ | ✗ | ✗ | ✗ |

### Tickets (tickets.*)
| Permission | admin | team_lead | analyst | viewer |
|-----------|-------|-----------|---------|--------|
| tickets.view | ✓ | ✓ | ✓ | ✓ |
| tickets.edit | ✓ | ✓ | ✗ | ✗ |
| tickets.manage | ✓ | ✗ | ✗ | ✗ |

### Reports (reports.*)
| Permission | admin | team_lead | analyst | viewer |
|-----------|-------|-----------|---------|--------|
| reports.view | ✓ | ✓ | ✓ | ✓ |
| reports.create | ✓ | ✓ | ✓ | ✗ |
| reports.export | ✓ | ✓ | ✓ | ✗ |
| reports.manage | ✓ | ✗ | ✗ | ✗ |

### Imports (imports.*)
| Permission | admin | team_lead | analyst | viewer |
|-----------|-------|-----------|---------|--------|
| imports.view | ✓ | ✓ | ✓ | ✓ |
| imports.start | ✓ | ✓ | ✓ | ✗ |
| imports.manage | ✓ | ✗ | ✗ | ✗ |

### Analytics (analytics.*)
| Permission | admin | team_lead | analyst | viewer |
|-----------|-------|-----------|---------|--------|
| analytics.view | ✓ | ✓ | ✓ | ✓ |
| analytics.edit | ✓ | ✗ | ✗ | ✗ |

### Users (users.*)
| Permission | admin | team_lead | analyst | viewer |
|-----------|-------|-----------|---------|--------|
| users.view | ✓ | ✓ | ✗ | ✗ |
| users.manage | ✓ | ✗ | ✗ | ✗ |

### Billing (billing.*)
| Permission | admin | team_lead | analyst | viewer |
|-----------|-------|-----------|---------|--------|
| billing.view | ✓ | ✗ | ✗ | ✗ |
| billing.manage | ✓ | ✗ | ✗ | ✗ |

### Admin (admin.*)
| Permission | admin | team_lead | analyst | viewer |
|-----------|-------|-----------|---------|--------|
| admin.access | ✓ | ✗ | ✗ | ✗ |

### Integrations / Security / Audit
| Permission | admin | team_lead | analyst | viewer |
|-----------|-------|-----------|---------|--------|
| integrations.manage | ✓ | ✗ | ✗ | ✗ |
| security.manage | ✓ | ✗ | ✗ | ✗ |
| audit.view | ✓ | ✓ | ✗ | ✗ |

### Support
| Permission | admin | team_lead | analyst | viewer |
|-----------|-------|-----------|---------|--------|
| support.ticket | ✓ | ✓ | ✓ | ✓ |

## API Usage

```python
# In endpoint:
from app.services.rbac.permissions import require_permission

@router.get("/sensitive")
async def sensitive_endpoint(user: User = Depends(require_permission("admin.access"))):
    ...
```

## Initialization

Permissions are enforced through:
1. `require_permission(perm)` — FastAPI dependency (rejects 403)
2. `has_permission(user, perm)` — Python check (returns bool)
3. `get_visible_queues(user)` — Filter queues by role
