# Architecture Overview

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

High-level architecture of the application. Defines layers, boundaries, and communication patterns.

## Scope

The entire system: frontend, backend, database, external services.

## Architecture Layers

```
┌─────────────────────────────────┐
│         Frontend (React/Vite)   │
│  ┌───────────┐  ┌────────────┐ │
│  │  UI Layer  │  │  State Mgmt│ │
│  └───────────┘  └────────────┘ │
├─────────────────────────────────┤
│         API Layer               │
│  ┌───────────┐  ┌────────────┐ │
│  │  REST API  │  │  Edge Fns  │ │
│  └───────────┘  └────────────┘ │
├─────────────────────────────────┤
│         Backend Services        │
│  ┌────┐ ┌────┐ ┌─────┐ ┌────┐ │
│  │Auth│ │RBAC│ │Audit│ │Jobs│ │
│  └────┘ └────┘ └─────┘ └────┘ │
├─────────────────────────────────┤
│         Data Layer              │
│  ┌──────────┐  ┌─────────────┐ │
│  │ PostgreSQL│  │   Storage   │ │
│  └──────────┘  └─────────────┘ │
└─────────────────────────────────┘
```

## Key Principles

- Separation of concerns across layers
- Backend logic in edge functions, never in client
- All data access through API layer with RLS
- Stateless API design
- Module boundaries enforced (see [Dependency Map](dependency-map.md))

## Communication Patterns

| From | To | Method |
|------|----|--------|
| Frontend | API | REST via Supabase client |
| API | Database | SQL with RLS policies |
| API | Auth | Supabase Auth |
| Edge Functions | Database | Service role (server-side) |
| Jobs | Database | Service role (server-side) |

## Dependencies

None — this is the root architecture document.

## Used By / Affects

All module docs, security docs, performance docs.

## Risks If Changed

HIGH — architectural changes affect every module.

## Related Documents

- [System Design Principles](system-design-principles.md)
- [Project Structure](project-structure.md)
- [Dependency Map](dependency-map.md)
- [Security Architecture](../02-security/security-architecture.md)
