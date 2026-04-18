# Trading System Constitution

> **Owner:** tesfayekb | **Version:** 1.0 | **Status:** ACTIVE
> **Authority:** trading-docs/08-planning/MASTER_PLAN.md v3.2 is the single source of truth. MARKETMUSE_MASTER.md v4.0 is historical reference only.

## The Prime Directive

Every architectural decision, every feature, every line of code must answer: **does this make the system more profitable or better protect capital?** If the answer is not a clear yes, it does not belong in V1.

---

## 10 Trading Rules (T-Rules) — Non-Negotiable

### T-Rule 1: Foundation Isolation
The foundation at `beyenestock-of-foundation-first` is production-grade and must be preserved exactly as built. Trading code extends the foundation — it never modifies foundation tables, docs, or governance. The only approved foundation modification is the `profiles` ALTER (Part 4.1).

### T-Rule 2: Table Prefix Isolation
All new trading tables use the `trading_` prefix. Trading tables are completely isolated from foundation tables. `trading_system_health` is NOT `system_health_snapshots`. Never mix infrastructure health with trading engine health.

### T-Rule 3: Controlled Multi-User — Invitation Only
The system supports 1-3 invited users maximum with read-only access and optional paper trade mirroring. No public enrollment, no subscription billing, no social features. Real-broker mirroring for non-admin users requires a governance/disclaimer review before implementation. Revenue model and public SaaS features are deferred to Year 2.

### T-Rule 4: Locked Decisions Are Final
All locked decisions (D-001 through D-022) in trading-docs/08-planning/approved-decisions.md are binding. They cannot be modified, deferred, or reinterpreted without explicit owner approval and a new decision record.

### T-Rule 5: Capital Preservation Is Absolute
The −3% daily loss limit (D-005) is hardcoded. No override. No configuration. No exception. The consecutive loss rules (D-022) are automated and mandatory. Capital preservation mode cannot be disabled.

### T-Rule 6: Mandatory Time Stops
Short-gamma exits at 2:30 PM EST and long-gamma exits at 3:45 PM EST are automated and cannot be overridden (D-010, D-011). These are not configurable.

### T-Rule 7: Security Inheritance
All trading pages inherit the foundation's security model: RLS on every table, permission gates on every page, MFA enforcement via AdminLayout, audit logging for every automated action. Trading does not define its own security model — it extends the existing one.

### T-Rule 8: Build Order Is Sequential
Implementation follows the 5-phase build order in trading-docs/08-planning/MASTER_PLAN.md v3.2. New strategy modules require paper trading validation (20+ trades with feature flag enabled) before enabling in production. The 90-day A/B gate is mandatory before deploying real capital. No shortcuts on capital safety.

### T-Rule 9: Paper Phase Is Mandatory
45 days of paper trading with all 12 go-live criteria (Part 10) must be satisfied before live trading is enabled. No early graduation. No partial passes.

### T-Rule 10: Silent Failures Are Forbidden
Nothing in the trading engine may fail silently. Every failure mode has a detection mechanism and a defined response. Every automated action is logged to `audit_logs`. Every health check writes to `trading_system_health`. The Sentinel is an independent safety net.

---

## Scope Reference

- **In scope (V1):** SPX, XSP, NDX, RUT options. 0DTE primary, 1–5 day swing secondary. Single operator. Tradier API. Fully automated with kill-switch.
- **Out of scope (V2):** Multi-user mirroring, subscriptions, social features, futures, crypto, international instruments.
- **Deferred features:** See trading-docs/08-planning/deferred-work-register.md and the Year-2/Year-3+ backlog in trading-docs/08-planning/MASTER_PLAN.md.

## Authority Hierarchy

1. trading-docs/08-planning/MASTER_PLAN.md v3.2 — single source of truth
2. trading-docs/00-governance/constitution.md — non-negotiable rules
3. trading-docs/00-governance/system-state.md — current phase and gates
4. trading-docs/08-planning/approved-decisions.md — binding decisions
5. MARKETMUSE_MASTER.md v4.0 — historical reference only, not authoritative
