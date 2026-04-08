# Testing Strategy

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines the testing approach: what to test, how, and at what level.

## Scope

All application code: components, hooks, utilities, API, edge functions.

## Test Pyramid

| Level | Tool | Coverage Target | What to Test |
|-------|------|----------------|-------------|
| Unit | Vitest | 80%+ | Utilities, hooks, pure functions |
| Integration | Vitest + Testing Library | Key flows | Component interactions, API calls |
| E2E | Playwright | Critical paths | Auth flows, RBAC enforcement, admin actions |

## Rules

1. No feature merge without tests for new logic
2. RLS policies tested with multiple user roles
3. Edge functions tested with valid and invalid inputs
4. Auth flows tested E2E
5. Permission checks tested at every level

## Test File Convention

- Unit/Integration: `*.test.ts` or `*.test.tsx` co-located with source
- E2E: `e2e/*.spec.ts`

## Dependencies

- [Performance Strategy](../03-performance/performance-strategy.md) — performance budgets
- [Security Architecture](../02-security/security-architecture.md) — security test requirements

## Used By / Affects

All modules.

## Risks If Changed

MEDIUM — weakening test requirements increases regression risk.

## Related Documents

- [Regression Strategy](regression-strategy.md)
