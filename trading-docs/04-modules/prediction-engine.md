# Module: Prediction Engine

> **Owner:** tesfayekb | **Version:** 1.0
> **Source:** MARKETMUSE_MASTER.md v4.0, Part 5.2

## Location

`backend/prediction_engine.py` (Python, deployed on Railway)

## Purpose

Generate every-5-minute predictions covering market direction, expected move, regime classification, GEX context, and CV_Stress. Output drives all downstream strategy selection and risk decisions.

---

## Inputs

| Source | Data | Refresh |
|--------|------|---------|
| **Redis** | Latest GEX, regime state, position state, intraday cache | Every cycle (sub-ms) |
| **QuestDB** | 93-feature time series (rolling 90d) | Every cycle (sub-ms) |
| **Supabase** | Current `trading_sessions` row, prior `trading_prediction_outputs` | Per cycle |
| **Tradier WebSocket** | Real-time quotes, bid/ask | Streaming |
| **Databento OPRA** | Trade-by-trade option flow for GEX | Streaming |
| **Polygon** | VVIX, breadth, dark pool | Polled |

## Outputs

Written to `trading_prediction_outputs` table (Supabase):
- `p_bull`, `p_bear`, `p_neutral` — direction probabilities
- `direction`, `confidence` — top direction with confidence
- `expected_move_pts`, `expected_move_pct` — magnitude forecast
- `gex_net`, `gex_nearest_wall`, `gex_flip_zone`, `gex_confidence`
- `cv_stress_score`, `charm_velocity`, `vanna_velocity`
- `regime`, `rcs`, `regime_hmm`, `regime_lgbm`, `regime_agreement`
- `no_trade_signal`, `no_trade_reason`
- `capital_preservation_mode`, `execution_degraded`
- `vvix_z_score`, plus market context (`spx_price`, `vix`, `vvix`)

---

## Three-Layer Architecture

### Layer A — Regime Engine (9:00 AM pre-market + every 60s intraday)

**Day Type Classifier (LightGBM, pre-market only):**
Classifies the day into one of 5 types: `trend`, `open_drive`, `range`, `reversal`, `event`. Gates the entire session strategy universe.

**HMM 6-state + LightGBM 6-state Ensemble (every 60s intraday):**
Six regime states: `quiet_bullish`, `volatile_bullish`, `quiet_bearish`, `crisis`, `pin_range`, `panic`.

### Layer B — Path & Distribution Engine (every 5 min)

LightGBM ensemble using **93 features in 7 groups**:

| Group | Count | Features |
|-------|-------|----------|
| Price/Volume | 15 | OHLCV 1/5/15/30-min, VWAP deviation, opening range |
| GEX | 12 | Net GEX, sign, wall/zero-line/flip distances, change rate, confidence |
| Volatility Surface | 18 | ATM IV 0DTE/1DTE/7DTE, term slope, skew, RV 5/10d, VIX, VVIX |
| Options Flow | 20 | Net premium delta, unusual activity, dark pool, 0DTE P/C ratio |
| Cross-Asset | 14 | TLT, DXY, /ES premium, sector rotation, gold/oil |
| Calendar/Time | 8 | Time of day sin/cos, day of week, days to Fed/CPI |
| Charm/Vanna | 6 | CV_Stress_Score, charm_velocity, vanna_velocity, distances |

**No-trade signal is a first-class output** — treated the same as a trade signal, logged always.

### Layer C — Volatility Surface

Expected realized vs implied volatility, skew regime classification, straddle implied move vs forecast.

---

## CV_Stress Formula

```python
z_vanna = (vanna_velocity - regime_vanna_mean) / regime_vanna_std
z_charm = (charm_velocity - regime_charm_mean) / regime_charm_std
raw = 0.6 * z_vanna + 0.4 * z_charm
cv_stress = min(100, max(0, (raw / P99_HISTORICAL) * 100))
```

**Six separate regime calibration tables — never cross-contaminate.** Each regime has its own (mean, std) for vanna_velocity and charm_velocity. Computing CV_Stress with the wrong regime's calibration produces invalid scores.

---

## Regime Disagreement Guard (D-021)

```python
if regime_hmm != regime_lgbm:
    apply_penalty(size_reduction=0.50, rcs_adjustment=-15)
    log_to_audit(
        action='trading.regime_disagreement',
        metadata={
            'regime_hmm': regime_hmm,
            'regime_lgbm': regime_lgbm,
            'session_id': current_session_id,
        }
    )
    update_prediction_output(regime_agreement=False)
```

---

## Adaptive VVIX Circuit Breakers (D-018)

```python
vvix_z = (vvix_current - vvix_20d_mean) / vvix_20d_std

# Warning: z > 2.0 → reduce new sizes 50%
# Critical: z > 2.5 → close all short-gamma
# Emergency: z > 3.0 → 100% reserve, halt
```

Fallback to fixed thresholds (120/140/160) until 20-day history is available.

---

## Monitoring Requirements

- **Heartbeat:** Upsert to `trading_system_health` (service_name='prediction_engine') every **10 seconds** with status, latency_ms, and error_count_1h
- **Job tracking:** Each prediction cycle creates a `job_executions` row linked via `trading_prediction_outputs.job_execution_id`
- **Audit:** Significant events (regime disagreement, no-trade signal, capital preservation activation) logged to `audit_logs` with `correlation_id`
- **Alerts:** Triggered automatically via `alert_configs` for `trading.cv_stress_score`, `trading.vvix_z_score`, `trading.regime_disagreement`

---

## Failure Modes

| Failure | Detection | Response |
|---------|-----------|----------|
| LightGBM model load failure | Startup probe + heartbeat status='error' | Block predictions, alert critical |
| HMM model load failure | Startup probe + heartbeat status='error' | Block predictions, alert critical |
| QuestDB query timeout | Latency_ms > 1000 | Degraded mode, fall back to last-known features |
| Redis connection lost | Health check fail | Degraded mode, query Supabase directly (slower) |
| Databento feed disconnect | `data_lag_seconds` > 30 | GEX confidence drops, may trigger no-trade |
| Regime calibration drift | `regime_agreement_rate` < 70% over 20 cycles | Alert warning, force champion/challenger evaluation |
| CV_Stress regime cross-contamination | Manual code review + unit tests | Quarantine model, revert to prior version |
| Cycle latency > 30s | `trading_prediction_cycle` job timeout (30s) | Job marked failed, retry with exponential backoff |

---

## References

- MARKETMUSE_MASTER.md Part 5.2 — Prediction Engine (full spec)
- trading-docs/08-planning/approved-decisions.md — D-018, D-021
- trading-docs/04-modules/exit-engine.md — consumes CV_Stress for state transitions
- trading-docs/01-architecture/architecture-overview.md — data flow context
