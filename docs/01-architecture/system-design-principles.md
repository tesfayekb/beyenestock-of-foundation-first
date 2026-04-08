# System Design Principles

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines the non-negotiable design principles that govern all technical decisions.

These principles are **enforceable** and must be followed across all modules, code, and infrastructure.

## Scope

All code, architecture, services, and infrastructure.

## Enforcement Rule (CRITICAL)

- These principles are **mandatory**, not advisory
- Any violation results in an **INVALID** implementation
- No shortcuts or exceptions are allowed without explicit approval
- All changes must be evaluated against these principles

## Core Principles

### 1. Security First

Security is a primary constraint for all design decisions.

- Authentication, authorization, and validation must occur before data access
- Sensitive operations must occur server-side only

### 2. Least Privilege

All users, services, and components operate with minimal permissions.

- Service-role access must be restricted and justified
- Permissions must be explicit and auditable

### 3. Defense in Depth

Security must be layered:

- Input validation and sanitization at entry points
- Authorization checks at the API layer
- RLS at the database layer
- Audit logging for significant actions

No single layer is sufficient on its own.

### 4. Single Responsibility

- Each module, service, and function has a single purpose
- Multi-purpose components must be decomposed

### 5. DRY (Don't Repeat Yourself)

- Shared logic must be centralized and tracked in `function-index.md`
- Duplication is considered a defect

### 6. Fail Secure

- Default behavior is deny / restrict on failure
- Errors must not expose sensitive data
- Partial failures must not create inconsistent state

### 7. Observable

- All significant actions must be logged
- Errors must be surfaced, not suppressed
- Health and monitoring signals must be available

### 8. Idempotent Operations

- APIs and jobs must be safe to retry
- Side effects must be controlled and predictable

### 10. Permission-Driven Authorization

- Access decisions must be based on **permissions**, not hardcoded role names
- Business logic must not check for specific roles (e.g., `'admin'`)
- Roles are containers of permissions — permissions are the enforcement unit
- `superadmin` is the only exception (implicit all-permission grant)

### 9. Schema-Driven Design

- Database schema is the source of truth
- Types and contracts derive from schema
- No duplication of schema definitions across layers

## Anti-Patterns (FORBIDDEN)

- Client-side-only authorization
- Direct database access bypassing RLS
- Service-role usage in client code
- Hidden or undocumented dependencies
- Silent failure or suppressed errors
- Duplicate logic across modules
- Bypassing audit logging for significant actions
- Hardcoded permissions or roles

Violations = **INVALID** implementation.

## Cross-Layer Application

| Layer | Required Enforcement |
|-------|---------------------|
| Frontend | No business logic trust, no privileged operations |
| API / Edge | Authorization, validation, orchestration |
| Domain / Services | Business logic, audit integration |
| Database | RLS, schema integrity |
| Jobs | Idempotency, retry safety, audit logging |

## Consistency Rule

- Patterns must be consistent across modules
- Similar problems must use the same architectural approach
- New patterns require explicit approval

## Dependencies

- [Constitution](../00-governance/constitution.md)
- [Dependency Map](dependency-map.md)
- [Change Control Policy](../00-governance/change-control-policy.md)

## Used By / Affects

All modules, all implementation decisions, and all architectural reviews.

## Risks If Changed

HIGH — incorrect principles lead to systemic design flaws across the entire project.

## Related Documents

- [Architecture Overview](architecture-overview.md)
- [Security Architecture](../02-security/security-architecture.md)
- [Dependency Map](dependency-map.md)
