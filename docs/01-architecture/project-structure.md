# Project Structure

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines the file and folder organization for the codebase.

## Scope

All source code and configuration files.

## Structure (Planned)

```
src/
├── components/           # Shared UI components
│   ├── ui/              # shadcn/ui base components
│   ├── layout/          # Layout components (header, sidebar, etc.)
│   └── common/          # Reusable domain-agnostic components
├── features/            # Feature modules (domain-specific)
│   ├── auth/            # Authentication flows
│   ├── rbac/            # Role-based access control
│   ├── admin/           # Admin panel
│   ├── user/            # User panel
│   ├── audit/           # Audit logging
│   └── monitoring/      # Health monitoring
├── hooks/               # Shared custom hooks
├── lib/                 # Utilities, clients, helpers
├── pages/               # Route-level page components
├── types/               # Shared TypeScript types
├── config/              # App configuration
└── test/                # Test setup and utilities

supabase/
├── migrations/          # Database migrations
└── functions/           # Edge functions

docs/                    # SSOT documentation (this system)
```

## Conventions

- Feature modules are self-contained: components, hooks, types, and utils together
- Shared code goes in `components/`, `hooks/`, `lib/`, or `types/`
- No circular imports between feature modules
- Page components are thin wrappers that compose feature components

## Dependencies

- [Architecture Overview](architecture-overview.md)

## Used By / Affects

All development tasks reference this for file placement.

## Risks If Changed

MEDIUM — affects file organization conventions.

## Related Documents

- [Architecture Overview](architecture-overview.md)
- [Dependency Map](dependency-map.md)
