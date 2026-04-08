# Route Index

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Maps all application routes with their access requirements.

## Scope

All frontend routes and API endpoints.

## Frontend Routes

| Route | Page | Module | Auth Required | Role Required |
|-------|------|--------|--------------|--------------|
| `/` | Landing | — | No | — |
| `/login` | Login | auth | No | — |
| `/signup` | Sign Up | auth | No | — |
| `/forgot-password` | Password Reset | auth | No | — |
| `/dashboard` | User Dashboard | user-panel | Yes | user |
| `/settings` | User Settings | user-panel | Yes | user |
| `/settings/security` | MFA Settings | user-panel | Yes | user |
| `/admin` | Admin Dashboard | admin-panel | Yes | admin |
| `/admin/users` | User Management | admin-panel | Yes | admin |
| `/admin/roles` | Role Management | admin-panel | Yes | admin |
| `/admin/audit` | Audit Logs | admin-panel | Yes | admin |
| `/admin/monitoring` | Health Dashboard | admin-panel | Yes | admin |
| `/admin/config` | System Config | admin-panel | Yes | admin |

## API Endpoints (Edge Functions)

| Endpoint | Method | Module | Auth | Purpose |
|----------|--------|--------|------|---------|
| `/health` | GET | health-monitoring | No | Health check |

> Additional API endpoints will be added as modules are implemented.

## Dependencies

- [Architecture Overview](../01-architecture/architecture-overview.md)

## Used By / Affects

Frontend routing, auth guards, navigation.

## Related Documents

- [Auth Module](../04-modules/auth.md)
- [Permission Index](permission-index.md)
