# Dependency Map

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Maps dependencies between all modules. Used to assess impact of changes.

## Scope

All modules defined in `docs/04-modules/`.

## Module Dependency Matrix

| Module | Depends On | Depended On By |
|--------|-----------|---------------|
| auth | — | rbac, user-management, admin-panel, user-panel, api, audit-logging |
| rbac | auth | admin-panel, user-panel, api, user-management |
| user-management | auth, rbac | admin-panel, user-panel |
| admin-panel | auth, rbac, user-management, audit-logging | — |
| user-panel | auth, rbac, user-management | — |
| audit-logging | auth | admin-panel, health-monitoring |
| health-monitoring | audit-logging | admin-panel |
| api | auth, rbac | all frontend modules |
| jobs-and-scheduler | auth, audit-logging | health-monitoring |

## Shared Services

| Service | Used By | Tracked In |
|---------|---------|-----------|
| Auth client | All modules | `function-index.md` |
| Permission checker | rbac, admin-panel, user-panel, api | `function-index.md` |
| Audit logger | All write operations | `function-index.md` |
| API error handler | api, edge functions | `function-index.md` |

## Reading This Map

- Before changing a module, check its "Depended On By" column
- If the module appears in the "Shared Services" table, it is HIGH impact
- Cross-reference with `function-index.md` for specific function usage

## Dependencies

- [Architecture Overview](architecture-overview.md)

## Used By / Affects

AI Operating Model (mandatory reading for shared logic changes). Change Control Policy (impact classification).

## Risks If Changed

MEDIUM — inaccurate dependency map leads to missed impact assessment.

## Related Documents

- [Architecture Overview](architecture-overview.md)
- [Function Index](../07-reference/function-index.md)
- [Constitution](../00-governance/constitution.md) — Rule 6 (shared component protection)
