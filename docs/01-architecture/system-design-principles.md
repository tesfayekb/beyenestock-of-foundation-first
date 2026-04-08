# System Design Principles

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines the non-negotiable design principles that govern all technical decisions.

## Scope

All code, architecture, and infrastructure decisions.

## Principles

### 1. Security First

Every feature must be designed with security as a primary constraint, not an afterthought. Authentication, authorization, and input validation are mandatory before any data operation.

### 2. Least Privilege

Every component, user, and service operates with the minimum permissions necessary. No broad grants; permissions are explicit and auditable.

### 3. Defense in Depth

Security is layered: RLS at the database level, authorization at the API level, validation at the input level, and audit logging at every level.

### 4. Single Responsibility

Each module, function, and component has one clearly defined purpose. If a component does two things, split it.

### 5. DRY (Don't Repeat Yourself)

Shared logic is extracted, indexed in `function-index.md`, and reused. Duplication is a defect.

### 6. Fail Secure

On any error or unexpected state, the system defaults to the most restrictive behavior. Deny by default.

### 7. Observable

Every significant action is logged. System health is monitored. Failures are detected and surfaced, not swallowed.

### 8. Idempotent Operations

API operations and jobs must be safe to retry without side effects.

### 9. Schema-Driven

Database schema is the source of truth for data shape. Types are derived from schema, not manually duplicated.

## Dependencies

- [Constitution](../00-governance/constitution.md) — Rules 3, 6

## Used By / Affects

All modules, all code.

## Risks If Changed

HIGH — changing principles affects all downstream decisions.

## Related Documents

- [Architecture Overview](architecture-overview.md)
- [Security Architecture](../02-security/security-architecture.md)
