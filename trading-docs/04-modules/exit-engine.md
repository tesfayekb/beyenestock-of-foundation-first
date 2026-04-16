# Module: Exit Engine

> **Owner:** tesfayekb | **Version:** 1.0
> **Source:** MARKETMUSE_MASTER.md v4.0, Part 5.5

## Location

Exit logic is enforced in three places:
- `backend/execution_engine.py` — state machine + Tradier order placement
- `backend/risk_engine.py` — position monitoring + exit triggers
- Scheduled jobs: `trading_time_stop_230pm`, `trading_time_stop_345pm`, `trading_position_monitor`

## Purpose

Execute timely, risk-aware exits for every open position. The exit engine is the last line of capital preservation — it must always succeed.

---

## Mandatory Exit Times

| Time | Job | Position Type | Override |
|------|-----|--------------|----------|
| **2:30 PM EST** | `trading_time_stop_230pm` (cron `30 14 * * 1-5`) | All short-gamma positions | NONE — automated, no override (D-010) |
| **3:45 PM EST** | `trading_time_stop_345pm` (cron `45 15 * * 1-5`) | All long-gamma positions | NONE — automated, no override (D-011) |

Both jobs use `execution_guarantee: exactly_once` and `concurrency_policy: single` to prevent missed or duplicate exits.

---

## First-Passage Touch Probability

The probability that SPX touches the short strike before the position exits — using the **first-passage barrier formula**, NOT N(d2) terminal probability.

```python
from math import log, sqrt, exp
from scipy.stats import norm

def touch_prob(S, K, mu, sigma, T):
    """
    First-passage barrier touch probability.

    S     : current SPX price
    K     : short strike
    mu    : drift (per year)
    sigma : effective volatility (per year)
    T     : time to exit, in years (NOT to expiry)
    """
    d1 = (log(S/K) + (mu + 0.5*sigma**2)*T) / (sigma*sqrt(T))
    d2 = d1 - sigma*sqrt(T)
    exponent = max(min((2*mu*log(K/S))/(sigma**2), 50), -50)
    return max(0.0, min(1.0, norm.cdf(-d2) + exp(exponent)*norm.cdf(-d1)))
```

Output written to `trading_positions.current_touch_prob` and `trading_calibration_log.touch_prob_max` every cycle.

---

## Hybrid Volatility — sigma_effective (D-016)

```python
sigma_effective = max(
    sigma_30m_realized,
    sigma_10m_realized * 0.85,
    sigma_5m_realized  * 0.75,
    sigma_atm_implied  * 0.70,    # prevents regime-shift lag (D-016)
)

# Override: sudden vol expansion forces use of 5-min realized
if vvix_change_30m > 0.20 or spx_5m > 0.0035:
    sigma_effective = max(sigma_effective, sigma_5m_realized)
```

**D-016 note:** The `0.70 × implied` floor prevents the touch probability from underestimating risk when realized vol is artificially low ahead of a regime shift.

---

## State-Based Exit Model

| State | Condition | Automated Action |
|-------|-----------|-----------------|
| **1 — Entry Validation** | Position open < 15 min | No action (settling) |
| **2 — Early Confirmation** | Thesis intact, P&L favorable but < 40% max profit | Monitor — no change |
| **3 — Mature Winner** | P&L ≥ 40% of max profit | Take 50% off, trail stop on remainder |
| **4 — Degrading Thesis** | Any State 3→4 trigger fires (see below) | Exit 50%, evaluate full exit |
| **5 — Forced Exit** | Hard stop, time stop, or circuit breaker | Exit 100% immediately |

State stored in `trading_positions.current_state` (1–5).

---

## State 3 → State 4 Triggers

ANY of these triggers a state transition from 3 to 4:

1. **Confidence drop:** `current_confidence < entry_confidence - 15`
2. **GEX wall breached:** SPX has crossed the entry-time positive GEX wall
3. **Touch probability:** `current_touch_prob > 0.25`
4. **CV_Stress conditional (D-017):**
   ```python
   if cv_stress > 70 and unrealized_pnl >= 0.50 * max_profit:
       transition_to_state_4(reason='cv_stress_trigger')
   ```
   **D-017:** CV_Stress only triggers exits when the position is at ≥ 50% of max profit. Premature CV_Stress exits at a loss waste the signal.

---

## OCO Order Requirement (D-006)

**Every fill must have an OCO (One-Cancels-Other) order pre-submitted within 2 seconds.**

```python
def on_fill(fill):
    # Pre-submit OCO immediately — invariant I-2
    oco = build_oco(
        position=fill.position,
        profit_target=fill.position.profit_target,
        stop_loss=fill.position.stop_loss_level,
    )
    tradier_client.submit_oco(oco)
    audit_log(
        action='trading.oco_submitted',
        target_id=fill.position.id,
        correlation_id=fill.correlation_id,
        metadata={'oco_id': oco.id, 'fill_price': fill.price},
    )
```

Sentinel verifies OCO presence on every position via independent Tradier poll. Missing OCO → critical alert.

---

## Exit Reason Vocabulary (Audit Trail)

Every closed position writes `trading_positions.exit_reason` from this enum:

| exit_reason | Source |
|-------------|--------|
| `profit_target` | OCO profit leg filled |
| `stop_loss` | OCO stop leg filled |
| `time_stop_230pm` | `trading_time_stop_230pm` job |
| `time_stop_345pm` | `trading_time_stop_345pm` job |
| `touch_prob_threshold` | `current_touch_prob > 0.25` (State 3→4 trigger 3) |
| `cv_stress_trigger` | D-017 condition met (State 3→4 trigger 4) |
| `state4_degrading` | Multiple State 3→4 triggers, full exit |
| `portfolio_stop` | Portfolio-level risk breach |
| `circuit_breaker` | VVIX Z, SPX drop, drawdown circuit breaker |
| `capital_preservation` | D-022 capital preservation halt |
| `manual` | Operator kill-switch or manual close |

---

## Calibration Log Write Requirement

Every exit decision and every 5-min monitoring cycle writes to `trading_calibration_log`:

```python
calibration_log.insert({
    'position_id': position.id,
    'signal_type': 'cv_stress' or 'touch_prob' or 'slippage',
    'strategy_type': position.strategy_type,
    'regime': current_regime,
    'cv_stress_score': cv_stress,
    'charm_velocity': charm_v,
    'vanna_velocity': vanna_v,
    'z_vanna': z_v, 'z_charm': z_c,
    'exit_triggered': bool,
    'exit_reason': reason or None,
    'touch_prob_put': p_put, 'touch_prob_call': p_call,
    'touch_prob_max': max(p_put, p_call),
    'sigma_realized': sigma_r, 'sigma_implied': sigma_i,
    'sigma_effective': sigma_eff,
    't_years_to_exit': t_years,
    'predicted_slippage': pred_slip, 'actual_slippage': None,
    'position_state': position.current_state,
    'unrealized_pnl': pnl, 'pct_max_profit': pnl / max_profit,
    'spx_price': spx, 'vix': vix, 'vvix': vvix,
})
```

The reconciliation job (post-session) fills `put_touched_by_exit`, `call_touched_by_exit`, `forward_pnl_20m`, `was_correct_exit`, `fp_flag`, `fn_flag` for the learning engine to detect false positives / false negatives.

---

## Failure Modes

| Failure | Detection | Response |
|---------|-----------|----------|
| OCO submission fails | No `trading.oco_submitted` audit within 2s of fill | Critical alert + retry; if persistent, kill-switch |
| Time stop job missed | `trading_time_stop_*` no execution in `job_executions` | Sentinel detects open positions after 4:00 PM, force-closes |
| Touch probability NaN | Sigma or T invalid | Use prior cycle's value, log warning |
| Tradier order rejected | Tradier API error | Walk-the-book retry, then market order if forced exit |
| Position monitor lag | `trading_position_monitor` job > 25s | Log warning, but state machine is idempotent |

---

## References

- MARKETMUSE_MASTER.md Part 5.5 — Exit Strategy Engine (full spec)
- trading-docs/08-planning/approved-decisions.md — D-006, D-010, D-011, D-016, D-017
- trading-docs/04-modules/prediction-engine.md — produces CV_Stress
- trading-docs/01-architecture/architecture-overview.md — invariants I-2 (OCO), I-6 (time stops)
