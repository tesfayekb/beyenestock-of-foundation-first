# Regression Strategy

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines how regressions are prevented, detected, and tracked.

## Scope

All changes classified as MEDIUM or HIGH impact.

## Regression Protection Loop

Before completing any MEDIUM or HIGH impact change:

1. **Check** `regression-watchlist.md` for known risks in the affected area
2. **Verify** affected flows are not broken (run relevant tests)
3. **If new risk discovered** → add to `regression-watchlist.md`

## Regression Prevention

- All shared functions tracked in `function-index.md`
- All module dependencies mapped in `dependency-map.md`
- Impact classification required for every change
- HIGH impact changes require full regression check

## Regression Detection

- Automated tests catch known regressions
- E2E tests cover critical user flows
- Manual verification for UI regressions
- Health monitoring detects runtime regressions

## Dependencies

- [Change Control Policy](../00-governance/change-control-policy.md)
- [Dependency Map](../01-architecture/dependency-map.md)

## Used By / Affects

All MEDIUM/HIGH impact changes.

## Risks If Changed

HIGH — weakening regression strategy directly increases defect rate.

## Related Documents

- [Testing Strategy](testing-strategy.md)
- [Regression Watchlist](../06-tracking/regression-watchlist.md)
- [Change Control Policy](../00-governance/change-control-policy.md)
