# Trading System — Risk Register

> **Owner:** tesfayekb | **Version:** 1.0

## Purpose

Active risks that could compromise the trading system's profitability, capital preservation, or foundation stability. Each risk is scored, monitored, and mitigated.

## Scoring

- **Likelihood:** 1 (rare) – 5 (almost certain)
- **Impact:** 1 (negligible) – 5 (catastrophic)
- **Score:** Likelihood × Impact (max 25)
- **Severity:** LOW (1–6), MEDIUM (7–12), HIGH (13–19), CRITICAL (20–25)

---

## Active Risks

### T-RISK-001 — Silent Trading Engine Failure
- **Type:** Operational / Reliability
- **Likelihood:** 3 | **Impact:** 5 | **Score:** 15 | **Severity:** CRITICAL
- **Description:** A module in the prediction, strategy, risk, or execution chain fails silently — no exception thrown, no alert raised, but the system stops generating valid signals or stops monitoring positions.
- **Detection Method:**
  - `trading_system_health` heartbeat upsert every 10s — any service > 30s stale triggers alert
  - `trading_heartbeat_check` job runs every 1 min, alerts if any service offline > 120s
  - Independent Sentinel monitors primary heartbeat via Supabase replica
- **Mitigation:**
  - All Python services upsert heartbeat every 10s (mandatory in cursorrules-trading.md silent failure rule #3)
  - All exceptions explicitly caught and logged to `audit_logs`
  - Sentinel triggers panic close-all if primary heartbeat > 120s
- **Residual Risk:** LOW — three independent monitoring layers make undetected failure very unlikely

### T-RISK-002 — GEX Data Staleness on Trend Day
- **Type:** Data quality / Edge degradation
- **Likelihood:** 4 | **Impact:** 5 | **Score:** 20 | **Severity:** CRITICAL
- **Description:** Databento OPRA feed lag or disconnect causes GEX values to become stale. On a trend day, stale GEX leads to mis-placed short strikes near negative gamma flip zones, materially increasing tail risk.
- **Detection Method:**
  - `trading_system_health.gex_staleness_seconds` updated every 5 min
  - Alert at staleness > 600s (warning) and trend-day GEX confidence < 0.7 (block immediately)
  - `trading_prediction_outputs.gex_confidence` recorded every prediction cycle
- **Mitigation:**
  - Block all new entries when GEX staleness > 10 min
  - Trend-day GEX confidence < 0.7 → block all entries immediately
  - Hard veto: no short strike within 0.3% of negative GEX flip zone (Stage 2)
- **Residual Risk:** MEDIUM — staleness detection works, but a fast feed degradation between checks could allow one bad signal

### T-RISK-003 — Slippage Model Cold Start
- **Type:** Model / Execution quality
- **Likelihood:** 5 | **Impact:** 3 | **Score:** 15 | **Severity:** HIGH
- **Description:** Predictive LightGBM slippage model (D-015) requires ≥ 200 fill observations to be calibrated. During paper phase startup, the model is untrained and falls back to static slippage estimates.
- **Detection Method:**
  - `trading_system_health.slippage_model_observations` tracks observation count
  - `trading_model_performance.slippage_observations` shows current training count
  - Alert when observations < 200 (cold start mode)
- **Mitigation:**
  - Static slippage as fallback during paper phase (TPLAN-VIRTUAL-002-J)
  - GLC-011 paper phase criterion: minimum 200 observations before live trading
  - 25% sizing cap on under-sampled regime-strategy cells until calibrated
- **Residual Risk:** LOW — paper phase explicitly addresses this; cannot enter Phase 5 without calibration

### T-RISK-004 — VVIX Baseline Unavailable at Startup
- **Type:** Model / Risk management
- **Likelihood:** 3 | **Impact:** 4 | **Score:** 12 | **Severity:** HIGH
- **Description:** Adaptive VVIX Z-score circuit breaker (D-018) requires 20-day rolling baseline (mean + std). At cold start, baseline is incomplete and adaptive thresholds cannot be computed.
- **Detection Method:**
  - `trading_sessions.vvix_20d_mean` and `vvix_20d_std` populated each session
  - Alert if baseline freshness > 24h or insufficient history
- **Mitigation:**
  - Fallback to fixed thresholds (120/140/160) until 20-day history available (per D-018)
  - Pre-market job `trading_pre_market_scan` validates baseline before session open
- **Residual Risk:** LOW — fixed-threshold fallback is conservative

### T-RISK-005 — Regime Misclassification
- **Type:** Model / Capital exposure
- **Likelihood:** 4 | **Impact:** 5 | **Score:** 20 | **Severity:** CRITICAL
- **Description:** HMM and LightGBM regime classifiers disagree, or both agree on the wrong regime. System sizes positions based on incorrect regime expectations, leading to outsized losses.
- **Detection Method:**
  - `trading_prediction_outputs.regime_hmm` vs `regime_lgbm` comparison every cycle
  - `trading_model_performance.regime_agreement_rate` tracked rolling
  - Alert when agreement rate < 70%
- **Mitigation:**
  - D-021 Regime Disagreement Guard: HMM ≠ LightGBM → 50% size reduction + RCS −15
  - Capital preservation mode (D-022) provides additional brake on losing streaks
  - Fast-loop weekly retraining detects model drift early
- **Residual Risk:** MEDIUM — guard reduces but does not eliminate exposure to systematically wrong regime calls

### T-RISK-006 — Live Tradier API Key Exposure
- **Type:** Security / Catastrophic
- **Likelihood:** 2 | **Impact:** 5 | **Score:** 10 | **Severity:** CRITICAL (impact-driven)
- **Description:** Tradier API key leaked via client-side code, logs, screenshots, or audit metadata. Attacker gains live trading access to operator account.
- **Detection Method:**
  - Code review on every PR touching `trading_operator_config` or `execution_engine`
  - `trading_operator_config.tradier_key_preview` shows last 4 chars only — full key never returned
  - Audit log scan for accidental key inclusion in `metadata`
- **Mitigation:**
  - Key stored encrypted in `trading_operator_config.encrypted_key` (pgcrypto)
  - Never exposed to frontend — only `tradier_key_preview` (last 4 chars) is readable
  - Sentinel uses separate close-only key (different scope)
  - All API keys from environment variables on Railway, never hardcoded
  - MFA enforced on `/admin/trading/config` via AdminLayout
- **Residual Risk:** LOW — multiple defenses in depth

### T-RISK-007 — Foundation Module Regression
- **Type:** Operational / Trust
- **Likelihood:** 3 | **Impact:** 5 | **Score:** 15 | **Severity:** CRITICAL
- **Description:** Trading work accidentally breaks a foundation feature (auth, RBAC, profile, audit, health, jobs). Foundation stability is compromised, blocking all users.
- **Detection Method:**
  - Post-migration verification checklist (regression-strategy.md section 5)
  - Critical foundation queries (regression-strategy.md section 4)
  - End-to-end smoke tests after every trading change
- **Mitigation:**
  - T-Rule 1: Foundation Isolation — trading code in isolated paths only
  - Only approved foundation modification is `profiles` ALTER (Part 4.1)
  - All inserts to existing foundation tables use `ON CONFLICT DO NOTHING`
  - Forbidden actions list in cursorrules-trading.md and ai-operating-model.md
- **Residual Risk:** LOW — strong isolation rules + verification checklist

### T-RISK-008 — AI Plan Drift
- **Type:** Governance / Scope
- **Likelihood:** 4 | **Impact:** 4 | **Score:** 16 | **Severity:** HIGH
- **Description:** AI agent (Lovable, Cursor) introduces features outside the locked V1 scope, modifies locked decisions, or skips paper phase requirements. Scope creep increases attack surface and delays go-live.
- **Detection Method:**
  - Constitution check at start of every AI session
  - Approved decisions registry (D-001 through D-022) referenced in cursorrules-trading.md
  - master-plan.md + deferred-work-register.md as canonical scope sources
  - Feature proposal protocol — unplanned features require explicit approval
- **Mitigation:**
  - Mandatory reading order in ai-operating-model.md
  - Prohibited actions list with 10 explicit DO-NOT items
  - 22 locked decisions are immutable without owner approval
  - V2 features explicitly registered in deferred-work-register.md (TDW-001 through TDW-014)
- **Residual Risk:** MEDIUM — depends on AI agent compliance; periodic governance audits required

---

## Risk Summary

| ID | Risk | Severity | Score |
|----|------|----------|-------|
| T-RISK-001 | Silent trading engine failure | CRITICAL | 15 |
| T-RISK-002 | GEX data staleness on trend day | CRITICAL | 20 |
| T-RISK-003 | Slippage model cold start | HIGH | 15 |
| T-RISK-004 | VVIX baseline unavailable at startup | HIGH | 12 |
| T-RISK-005 | Regime misclassification | CRITICAL | 20 |
| T-RISK-006 | Live Tradier API key exposure | CRITICAL | 10 |
| T-RISK-007 | Foundation module regression | CRITICAL | 15 |
| T-RISK-008 | AI plan drift | HIGH | 16 |
