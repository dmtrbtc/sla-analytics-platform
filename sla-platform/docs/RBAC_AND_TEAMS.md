# RBAC & Teams Management — v1.2.1

## User Management

**Route:** `/admin/users` (admin only)

Features:
- Full user list with role badges (red=admin, blue=analyst, orange=team_lead, green=viewer)
- Search by name or email
- Filter by role (admin, analyst, team_lead, viewer)
- Filter by status (active/inactive)
- Create user with name, email, password, role
- Edit user display name and role
- Soft-deactivate users
- Pagination with page size options

## Team Management

**Route:** `/teams` (admin only)

Features:
- List all teams with name, queue prefix, description, active status
- Create team with name, queue prefix, description
- Edit team details
- Delete team with confirmation
- Status tags (active/inactive)

## Sidebar Navigation

Restructured with three sections:
1. **Навигация** — Command Center, Dashboard, Executive, Analytics, Team Dashboard
2. **Операции** — Tickets, Imports, Reports, SLA Config, SLA Monitor, Incidents
3. **Admin** (admin only) — Users, Teams, Operations, Diagnostics, Settings

## Permission Model

| Role | Users | Teams | Settings | Diagnostics | Operations |
|------|-------|-------|----------|-------------|------------|
| admin | Full CRUD | Full CRUD | Full access | Full access | Full access |
| analyst | View only | View only | View only | View only | View only |
| team_lead | View only | View team | View only | View only | View only |
| viewer | None | None | None | View only | None |
