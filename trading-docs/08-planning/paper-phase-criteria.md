# Trading System — Paper Phase Go-Live Criteria

> **Owner:** tesfayekb | **Version:** 1.0
> **Source:** MARKETMUSE_MASTER.md v4.0, Part 10
> **Governing Decision:** D-013 (45 days, 12 criteria, all required)

## Purpose

All 12 go-live criteria that must be satisfied before live trading is enabled. No partial passes. No early graduation. The Configuration page (`/admin/trading/config`) must show live status of all 12 criteria.

---

## Criteria

### GLC-001: Aggregate Prediction Accuracy
- **Target:** ≥ 58% over full 45 days
- **How Measured:** `trading_model_performance.accuracy_60d` computed from all prediction cycles vs actual outcomes
- **Status:** ⬜ Not evaluated

### GLC-002: Per-Regime Accuracy
- **Target:** ≥ 55% for every day type with ≥ 8 observations
- **How Measured:** `trading_model_performance.accuracy_*_day` fields (range, trend, reversal, event). Each day type with ≥ 8 observations must individually meet ≥ 55%.
- **Status:** ⬜ Not evaluated

### GLC-003: Training Examples Per Cell
- **Target:** Minimum 50 training examples per regime-strategy cell
- **How Measured:** Count of `trading_positions` grouped by regime × strategy_type. Each cell with < 50 examples is flagged.
- **Status:** ⬜ Not evaluated

### GLC-004: Under-Sampled Cell Handling
- **Target:** Under-sampled cells flagged — live trading at 25% sizing until 50 examples
- **How Measured:** System automatically detects cells with < 50 examples and enforces 25% sizing cap for those combinations.
- **Status:** ⬜ Not evaluated

### GLC-005: Paper Sharpe Ratio
- **Target:** ≥ 1.5
- **How Measured:** `trading_model_performance.sharpe_20d` computed from virtual P&L over the 45-day paper period, annualized.
- **Status:** ⬜ Not evaluated

### GLC-006: Zero Unhandled Exceptions
- **Target:** Zero unhandled exceptions in final 20 paper sessions
- **How Measured:** Application error logs and `trading_system_health` error counts. Any `error` or `offline` status in the final 20 sessions fails this criterion.
- **Status:** ⬜ Not evaluated

### GLC-007: Circuit Breaker Scenarios
- **Target:** All 6 circuit breaker scenarios tested and verified in Tradier sandbox
- **How Measured:** Manual test execution with documented evidence. Scenarios: SPX −2% 30min, VVIX Z>2.0, VVIX Z>2.5, VVIX Z>3.0, −3% drawdown, heartbeat loss >120s.
- **Status:** ⬜ Not evaluated

### GLC-008: Kill-Switch Response Time
- **Target:** < 5 seconds from mobile activation to all positions closed
- **How Measured:** Timed test from mobile device → kill-switch activation → Tradier sandbox confirms all positions closed.
- **Status:** ⬜ Not evaluated

### GLC-009: Sentinel Operational
- **Target:** Independent Sentinel verified operational on GCP
- **How Measured:** Sentinel running on GCP with separate Tradier credentials (close-only). Verified it detects primary app heartbeat failure and triggers close-all independently.
- **Status:** ⬜ Not evaluated

### GLC-010: WebSocket Heartbeat
- **Target:** Disconnect triggers degraded mode within 3 seconds
- **How Measured:** Intentional WebSocket disconnect test → `trading_system_health` status changes to `degraded` within 3 seconds → new entries blocked.
- **Status:** ⬜ Not evaluated

### GLC-011: Slippage Model Calibration
- **Target:** Minimum 200 fill observations for predictive slippage model
- **How Measured:** `trading_model_performance.slippage_observations` ≥ 200. Slippage MAE within acceptable range.
- **Status:** ⬜ Not evaluated

### GLC-012: GEX Tracking Error
- **Target:** ≤ ±15% vs OCC actuals (CBOE DataShop validation)
- **How Measured:** Compare synthesized GEX (from Databento OPRA via Lee-Ready) against OCC official open interest data from CBOE DataShop. Tracking error = abs(synthesized − actual) / actual.
- **Status:** ⬜ Not evaluated

---

## Summary

| ID | Criterion | Target | Status |
|----|-----------|--------|--------|
| GLC-001 | Prediction accuracy | ≥ 58% | ⬜ |
| GLC-002 | Per-regime accuracy | ≥ 55% per type | ⬜ |
| GLC-003 | Training examples | ≥ 50 per cell | ⬜ |
| GLC-004 | Under-sampled handling | 25% sizing cap | ⬜ |
| GLC-005 | Sharpe ratio | ≥ 1.5 | ⬜ |
| GLC-006 | Exception-free | 0 in final 20 sessions | ⬜ |
| GLC-007 | Circuit breakers | 6/6 tested | ⬜ |
| GLC-008 | Kill-switch | < 5 seconds | ⬜ |
| GLC-009 | Sentinel | Operational on GCP | ⬜ |
| GLC-010 | Heartbeat failover | < 3 seconds | ⬜ |
| GLC-011 | Slippage model | ≥ 200 observations | ⬜ |
| GLC-012 | GEX tracking | ≤ ±15% error | ⬜ |
