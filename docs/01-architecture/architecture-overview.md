# Architecture Overview

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines the high-level architecture of the application, including system layers, trust boundaries, communication paths, and non-negotiable interaction rules.

This document is the **top-level architectural contract** for the project.

## Scope

Applies to the entire system:

- Frontend
- Backend / edge functions
- Database
- Storage
- Background jobs
- External integrations
- Monitoring and audit paths

## Architectural Style

The system uses a **layered architecture** with strict boundary enforcement:

- **Presentation Layer** — React/Vite frontend
- **Application Layer** — API routes, edge functions, orchestration logic
- **Domain / Service Layer** — Auth, RBAC, audit, jobs, health, business services
- **Data Layer** — PostgreSQL, storage, caches, queues

No lower layer may be bypassed in ways that violate security, validation, or audit rules.

## Trust Boundaries

| Zone | Trust Level | Rules |
|------|------------|-------|
| Browser / Client | **Untrusted** | Never rely on for authorization or security decisions |
| Frontend application runtime | **Untrusted** for authorization | May render UI hints but must not enforce access |
| Edge functions / backend services | **Trusted** execution layer | All business logic, auth, and authorization enforced here |
| Database with RLS | **Protected** data layer | All access governed by RLS policies |
| Service role access | **Highly privileged** | Server-side only, never exposed to client |
| External services | **Conditionally trusted** | Must be validated at integration boundaries |

## Architecture Layers

```
┌──────────────────────────────────────────────┐
│  Presentation Layer                          │
│  React/Vite UI, client state, forms, views   │
├──────────────────────────────────────────────┤
│  Application Layer                           │
│  REST API, edge functions, request handling, │
│  orchestration, validation, response shaping │
├──────────────────────────────────────────────┤
│  Domain / Service Layer                      │
│  Auth, RBAC, Audit, User Mgmt, Jobs, Health, │
│  Settings, Notifications, shared services    │
├──────────────────────────────────────────────┤
│  Data Layer                                  │
│  PostgreSQL, RLS, storage, queues, indexes   │
└──────────────────────────────────────────────┘
```

## Canonical Request Flow

1. User action originates in frontend
2. Frontend sends request to approved API / edge function
3. Authentication context is resolved
4. Authorization / RBAC is enforced server-side
5. Input validation and sanitization are applied
6. Domain/service logic executes
7. Database/storage access occurs under approved policy
8. Audit logging occurs for significant actions
9. Response is returned to frontend
10. Monitoring / health signals are emitted where applicable

## Cross-Cutting Concerns

The following apply across all layers and modules:

- Authentication
- Authorization / RBAC
- Validation and sanitization
- Audit logging
- Error handling
- Monitoring / health reporting
- Configuration management
- Performance controls
- Change tracking and documentation alignment

## Communication Rules

| From | To | Method | Rules |
|------|----|--------|-------|
| Frontend | API / Edge | HTTP / Supabase client | No privileged logic in client |
| API / Edge | Auth | Supabase Auth / server checks | Auth resolved server-side |
| API / Edge | RBAC | Server-side permission checks | Never UI-only authorization |
| API / Edge | Database | SQL / ORM / query layer | RLS enforced |
| Edge Functions | Database | Service role only when required | Server-side only |
| Jobs | Database | Service role / scheduled execution | Must be auditable and retry-safe |
| Services | Audit | Structured events / writes | Significant actions logged |

## Security Boundary Rules

- Business logic must not rely on client-side trust
- Authorization must be enforced server-side
- Service role credentials must never reach client code
- Shared security logic must be centralized, not duplicated
- Sensitive operations must flow through auditable backend paths
- No direct bypass of RLS or approved authorization controls

## Dependency Rules

- Modules must communicate through defined interfaces or approved shared services
- Shared functions/services used across modules must be tracked in reference indexes
- No hidden coupling between modules
- Dependency direction must remain consistent with the layered architecture
- High-impact modules (Auth, RBAC, Security) require explicit review before changes

## Operational Rules

- Jobs must support retry/failure handling
- Important operations should be idempotent where practical
- Errors must propagate through approved handling patterns
- Health and audit signals must be available for critical subsystems
- Architectural changes require HIGH-impact review

## Dependencies

- [System Design Principles](system-design-principles.md)
- [Dependency Map](dependency-map.md)
- [Security Architecture](../02-security/security-architecture.md)

## Used By / Affects

All module docs, security docs, performance docs, and implementation planning.

## Risks If Changed

HIGH — architectural changes affect security boundaries, dependency flow, and execution safety across the entire project.

## Related Documents

- [System Design Principles](system-design-principles.md)
- [Project Structure](project-structure.md)
- [Dependency Map](dependency-map.md)
- [Security Architecture](../02-security/security-architecture.md)
- [Performance Strategy](../03-performance/performance-strategy.md)
