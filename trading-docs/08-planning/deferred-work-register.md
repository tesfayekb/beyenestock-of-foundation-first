# Trading System — Deferred Work Register

> **Owner:** tesfayekb | **Version:** 1.0
> **Source:** MARKETMUSE_MASTER.md v4.0, Part 14

## Purpose

All features explicitly deferred to V2+. These are NOT forgotten — they are documented here to ensure carry-forward. Do not build these in V1.

---

## Register

### TDW-001: Multi-User Trade Mirroring
- **Description:** Async fan-out of operator trades to multiple user Tradier accounts
- **Reason Deferred:** V1 captures the full edge with a single account. Multi-user adds complexity without improving profitability. Build the edge first, add users once proven.
- **Future Phase:** V2
- **Dependencies:** Proven V1 system, user enrollment, per-user Tradier OAuth

### TDW-002: User Tier System
- **Description:** Free/Paper/Live/Premium tiers for mirrored users
- **Reason Deferred:** No users in V1 — single operator only (D-007)
- **Future Phase:** V2
- **Dependencies:** TDW-001 (multi-user mirroring)

### TDW-003: Subscription Pricing
- **Description:** Recurring payment system for mirror users
- **Reason Deferred:** No users in V1
- **Future Phase:** V2
- **Dependencies:** TDW-002 (user tiers)

### TDW-004: Mirror Fill Risk Score
- **Description:** Per-user risk score for mirrored trades based on account size and fill quality
- **Reason Deferred:** No mirroring in V1
- **Future Phase:** V2
- **Dependencies:** TDW-001 (multi-user mirroring)

### TDW-005: User-Side Slippage Model
- **Description:** Separate slippage model per mirrored user (distinct from operator's virtual model)
- **Reason Deferred:** No mirroring in V1
- **Future Phase:** V2
- **Dependencies:** TDW-001 (multi-user mirroring), TDW-004 (fill risk score)

### TDW-006: Mirror Health Dashboard
- **Description:** Per-user dashboard showing mirror fill quality, lag, and performance vs operator
- **Reason Deferred:** No mirroring in V1
- **Future Phase:** V2
- **Dependencies:** TDW-001 (multi-user mirroring)

### TDW-007: Feature-Level Input Drift Monitoring
- **Description:** Monitor individual feature distributions (93 features) for drift, not just aggregate model accuracy
- **Reason Deferred:** Aggregate drift detection (z-test) is sufficient for V1. Feature-level monitoring adds operational complexity.
- **Future Phase:** V2
- **Dependencies:** Stable V1 learning engine

### TDW-008: Black Swan Monte Carlo Scenario Injection
- **Description:** Inject historical black swan scenarios (flash crash, COVID, etc.) into Monte Carlo EV simulations
- **Reason Deferred:** Standard Monte Carlo with stressed loss is sufficient for V1. Black swan injection improves tail risk but is not critical for initial operation.
- **Future Phase:** V2
- **Dependencies:** Stable V1 strategy selector

### TDW-009: GEX-Lite Fallback Mode
- **Description:** Fallback GEX estimation using IV skew + VWAP when Databento feed drops
- **Reason Deferred:** V1 handles Databento outage by disabling GEX-dependent strategies. Full fallback adds complexity.
- **Future Phase:** V2
- **Dependencies:** Proven V1 GEX pipeline

### TDW-010: Calendar and Diagonal Spreads
- **Description:** Multi-expiration spread strategies
- **Reason Deferred:** V1 scope is 0DTE and short-term swing. Calendar/diagonal spreads introduce multi-expiration risk management complexity.
- **Future Phase:** V2+
- **Dependencies:** Proven V1 single-expiration strategies

### TDW-011: Futures Hedging
- **Description:** /ES futures as portfolio hedge
- **Reason Deferred:** V1 uses options-only strategies. Futures introduce different margin and settlement mechanics.
- **Future Phase:** V2+
- **Dependencies:** Proven V1 system, futures-capable broker integration

### TDW-012: Multi-Broker Routing
- **Description:** Route orders to multiple brokers for best execution
- **Reason Deferred:** V1 uses Tradier only (D-006). Multi-broker adds latency and complexity.
- **Future Phase:** V2+
- **Dependencies:** Proven V1 execution engine

### TDW-013: Social/Copy-Trading Features
- **Description:** Social features allowing users to follow and copy the operator's trades
- **Reason Deferred:** V1 is single operator (D-007). Social features are V2 scope.
- **Future Phase:** V2
- **Dependencies:** TDW-001 (multi-user mirroring)

### TDW-014: International Instruments
- **Description:** Non-US index options (DAX, FTSE, Nikkei, etc.)
- **Reason Deferred:** V1 scope is US Section 1256 contracts only (D-001). International instruments have different settlement, tax, and data requirements.
- **Future Phase:** V3+
- **Dependencies:** Proven V1+V2 system, international broker integration
