# Item 9: Exit Optimizer — LOCKED SPECIFICATION

**Status:** 🔒 LOCKED
**Locked:** 2026-04-25
**Tier:** V0.3 advisory / V0.4 strategy-specific authority (graduated)
**Sources:** Claude opening proposal + GPT-5.5 Pro Round 1 + Claude verification round + GPT verification accept
**Expected ROI contribution at maturity (months 7-12):** +2% to +5% base case, +5% to +7% bull case
**Architectural role:** Deterministic forward-EV Exit Advisor. Reuses Item 5 distribution machinery. NEVER overrides constitutional gates. Earns authority slowly, strategy-by-strategy.

---

## Architectural Commitment

The exit optimizer is a deterministic adaptive layer that recommends EARLIER exits than static rules when forward EV signals justify it. It NEVER:
- Causes later exits than static rules
- Overrides constitutional gates (14:30 close, -3% halt, hard stops)
- Rolls or reopens positions
- Operates on every tick (would create noise-driven exits)

The locked architectural commitment from Round 2 holds: AI controls admissibility and size ceilings, deterministic systems handle execution. Exit optimizer respects this by ADVISING in V0.3 and EARNING limited authority in V0.4 only after rigorous validation.

**Critical principle:** A bad entry filter skips one trade. A bad exit optimizer can damage every open trade. Promotion to production authority must reflect this asymmetry.

---

## 1. Forward EV Computation

**Reuse Item 5's distribution machinery as a current-state forward-EV adapter.** Do NOT build a separate vol model.

### Inputs At Time t

```
S_t = current SPX
position = known strikes, quantities, entry credit/debit
T_remaining = min(expiry, mandatory_14_30_close, static_time_stop) - t
current_close_cost = live mid/mark to close position
```

### Two-Side Computation

```
EV_exit_now =
    realized_pnl_if_closed_now
  - exit_slippage  (adaptive premium applies — see §6)
  - fees

For EV_hold:
  Simulate forward paths from current state using Item 5's
  distribution machinery with CURRENT inputs:
    updated_rv_forecast_remaining
    current_implied_move
    current_skew_z
    current_surface_scores
    current_iv_rv_ratio
    current_time_bucket
    current_OPRA_flow_features (Item 8)
    current_VIX / vol state

  Apply existing static exit rules inside each simulated path:
    profit target
    stop loss
    Greek breach
    time stop
    14:30 mandatory close
    daily halt

  EV_hold =
      average(final_pnl_under_static_exit_policy)
    - expected_future_slippage (also adaptive — see §6)
    - fees
```

### Decision Variables

```
exit_advantage = EV_exit_now - EV_hold
exit_advantage_R = exit_advantage / max_risk
```

### Item 8 Flow Integration

OPRA flow features modify the forward distribution conservatively:

```
if vol_demand_pressure high:
    increase forward RV multiplier

if flow direction is adverse to position:
    increase bad-tail probability

if flow_persistence_15m is adverse:
    increase confidence in adverse drift

if flow_price_divergence is high:
    reduce confidence, do not overreact
```

**No LLM reads raw OPRA. The optimizer consumes deterministic Item 8 features only.**

---

## 2. Path Dependence (Trajectory Features)

A trade currently at 40% profit reached via smooth path has different forward dynamics than the same trade reached via 60% peak → 40%. History matters.

### Trajectory Features

```
giveback_R =
  max(0, peak_unrealized_pnl - current_unrealized_pnl) / max_risk

giveback_pct_of_peak =
  max(0, peak_unrealized_pnl - current_unrealized_pnl)
  / max(abs(peak_unrealized_pnl), ε)

pnl_path_vol =
  std(1-minute position_pnl_changes / max_risk)

profit_velocity =
  current_unrealized_pnl_R / max(time_in_trade_minutes, 1)
```

### Uncertainty Adjustment (Multiplicative)

```
EV_uncertainty_R_adjusted =
  EV_uncertainty_R
  * (1
     + 0.50 * giveback_R
     + 0.30 * pnl_path_vol
     + 0.20 * adverse_profit_velocity_flag)
```

A smooth 40% profit trade has uncertainty multiplier near 1.0. A roller-coaster 40% profit trade has multiplier 1.3-1.5+. The exit threshold widens proportionally per §3.

### Critical Distinction: Confidence vs Trigger

Trajectory features adjust **confidence in EV computation**, not raw EV value. This prevents the optimizer from becoming a hidden trailing stop (which static rules already provide).

---

## 3. Evaluation Cadence

### Hybrid Schedule

**Normal state:** evaluate every 120 seconds

**Stress state:** evaluate every 30-60 seconds

### Stress Triggers (State-Change Signals)

Trigger immediate reevaluation on:
```
short strike delta jumps materially
SPX moves > 0.25 * forecast_move since last check
position P&L changes > 10% of max risk
VIX / implied move spikes
Item 8 flow flips materially
OPRA adverse persistence appears
price approaches short strike / butterfly breakeven
```

### NOT a Stress Trigger (Behavioral Signal)

Per Verification 2 lock: giveback from peak does NOT trigger immediate reevaluation. It modifies confidence only (per §4). This prevents the optimizer from becoming a backdoor trailing stop.

### Latency Targets

```
p50 < 250 ms
p95 < 750 ms
hard timeout = 1.5 sec
```

**No LLM call should be in the exit loop.** Pure deterministic computation.

---

## 4. Decision Thresholds

### Core Rule

```
exit if:
    exit_advantage_R > threshold
    AND confidence >= confidence_required
```

### Initial Thresholds

```
normal_threshold = max(0.03R, 0.25 * EV_uncertainty_R_adjusted)
high_stress_threshold = max(0.02R, 0.20 * EV_uncertainty_R_adjusted)
confidence_required = 0.65
```

### Confidence Modifiers

```
if giveback_pct_of_peak >= 0.25:
    optimizer_confidence -= 0.15

if giveback_pct_of_peak >= 0.40:
    optimizer_confidence -= 0.30

if data quality flags present:
    optimizer_confidence -= 0.10 to 0.30 (depending on severity)

if Item 5 engine_confidence is low:
    optimizer_confidence -= 0.20

if Item 8 unknown_aggressor_share_5m > 0.40:
    optimizer_confidence -= 0.10
```

### Profit Protection Rule

```
if current_profit >= 40% of max_profit
   AND exit_advantage_R > 0.015
   AND adverse_flow_or_vol_shift = true:
       recommend exit / reduce
```

This is the "lock in profit when forward EV collapses on a winner" case.

### Scenario Handling

| State | Forward EV | Default Action |
|---|---|---|
| Profitable | Slightly negative | Hold static plan |
| Profitable | Strongly negative + adverse flow | Recommend exit/reduce |
| Breakeven | Strongly positive | Hold |
| Losing | Slightly positive | Hold static plan |
| Losing | Strongly negative + matches strategy failure mode | Recommend early exit |

---

## 5. Confidence Handling Default

**When optimizer confidence is low, default to original static plan.**

Phrased carefully:
- Low confidence ≠ hold forever
- Low confidence = do not use adaptive exit
- Constitutional and static exits still execute

### Behavior By Cause

```
Low confidence due to model uncertainty:
  Follow static plan

Low confidence due to data corruption / staleness:
  Do not trust adaptive EV
  Follow static risk gates
  Alert operator if position risk is elevated
```

The counter-view ("exit because we cannot justify holding") sounds conservative but produces death by a thousand premature exits. The trade was already approved by entry filters. A weak adaptive signal should not override that plan.

---

## 6. Strategy-Specific Logic

### Iron Condor

```
Primary concern: theta benefit vs short-strike breach / tail risk

Exit triggers (when above thresholds):
  short strike breach probability rises
  adverse OPRA directional pressure persists
  vol demand spikes
  profit already >= 40-60% and remaining EV is small
  one side becomes dominant risk

Forward EV focus:
  remaining credit capture
  probability of touching short strikes
  probability of max-loss-zone pressure
  expected giveback

Failure mode: exiting too early on normal intraday noise
```

### Iron Butterfly

```
Primary concern: pin thesis deterioration

Exit triggers:
  spot moves outside breakeven with persistence
  pin probability falls
  flow confirms directional break
  realized vol exceeds forecast
  time left is enough for gamma damage

Forward EV focus:
  probability of finishing inside breakevens
  distance from body
  wing stress probability
  remaining theta vs gamma risk

Failure mode: holding after pin thesis is dead
```

### Put Credit Spread

```
Primary concern: downside acceleration

Exit triggers:
  short put delta expands
  downside OPRA pressure persists
  put sweeps / aggressive put imbalance rises
  spot approaches short strike
  vol/skew expands against position

Forward EV focus:
  probability short put breached
  expected downside tail loss
  credit remaining vs max risk

Failure mode: waiting for static stop after downside regime has already changed
```

### Long Straddle

```
Primary concern: realized move vs remaining theta bleed

Exit triggers:
  realized move stalls
  vol demand collapses
  implied vol crushes
  forward RV drops below remaining debit requirement
  profit achieved AND flow weakens

Forward EV focus:
  expected absolute move
  remaining theta cost
  probability of move beyond breakeven
  vol expansion / contraction

Failure mode: exiting before the convex move starts
(Long straddles need stronger evidence before exit)
```

### Debit Call Spread

```
Primary concern: bullish continuation vs stall

Exit triggers:
  bullish flow fades
  price fails after breakout
  bearish OPRA divergence appears
  remaining upside to short strike is small
  profit capture is high AND forward EV flattens

Forward EV focus:
  probability of reaching short call
  time-to-move
  remaining upside vs theta decay

Failure mode: holding a spread after directional thesis has stalled
```

---

## 7. Adaptive Exit Slippage Modeling

Adaptive exits face higher friction than planned exits. The EV computation must reflect this.

### Adaptive Exit Slippage Formula

```
adaptive_exit_slippage = static_exit_slippage * adjustment_factor

adjustment_factor =
  1.0
  + 0.50 * max(0, current_iv_z - 1.0)         # vol stress
  + 0.30 * (1 - time_remaining_pct)            # time pressure
  + 0.25 * spread_z                            # bid-ask widening
  + 0.25 * stress_exit_flag                    # explicit stress condition

Cap: adjustment_factor = min(adjustment_factor, 3.0)
```

Applied to: `EV_exit_now`

### EV_hold Slippage (Per Simulated Path)

EV_hold also applies friction based on simulated exit condition:

```
Planned profit target exit:
  normal/slightly elevated slippage (1.0-1.2x base)

Static stop exit during stress:
  elevated slippage (per stress conditions in simulated path)

14:30 forced close:
  time-stop slippage model (1.5-2.0x base typical)
```

Both EV computations now reflect actual friction. No apples-to-oranges comparison.

---

## 8. Constitutional Gate Interaction

### Exit Decision Arbiter

```
exit_now =
    constitutional_exit
 OR static_exit
 OR authorized_optimizer_early_exit
 OR operator_manual_exit
```

### 14:30 Mandatory Close (Critical)

The forward EV simulation must explicitly include 14:30 ET as a forced terminal exit.

```
simulation_end_time =
  min(
    option_expiry,
    mandatory_14_30_close,
    existing_static_time_stop,
    strategy_specific_latest_exit
  )
```

Every simulated path applies:
```
if path_time >= 14:30:
    close position at simulated mark
    apply forced_close_slippage
```

Between 14:00 and 14:30, the optimizer can only compare:
```
exit_now
vs
hold until at most 14:30
```

If computed forward EV depends on post-14:30 continuation, the simulation is **invalid and must be rejected**.

### Other Examples

```
Optimizer says "hold past profit target"
  → Ignored. Static profit target exits.

Optimizer says "exit at 20% profit" before static 50% target
  → V0.3: log recommendation only
  → V0.4: exit if validated threshold passes

Optimizer says exit but operator override active
  → V0.3 advisory: operator decides, log override
  → V0.4 production: operator override may suppress optimizer exit
                      but cannot suppress constitutional exits

Hard gates remain absolute.
```

---

## 9. Integration With Items 5 And 8

### Item 5 Fields Reused (Current-State Versions)

```
rv_forecast_remaining
implied_move_remaining
iv_rv_ratio
skew_z
smile_asymmetry_score
smile_width_score
tail_width_score
engine_confidence
authority_level
forecast_error_recent
```

Used for:
- Current forward distribution
- Remaining expected move
- Short-gamma danger
- Long-vol continuation

### Item 8 Fields Consumed (Most Exit-Relevant)

```
directional_pressure_5m
directional_pressure_accel
flow_persistence_15m
vol_demand_pressure_5m
aggressive_put_call_imbalance_5m
sweep_directional_pressure_1m
dealer_hedge_pressure_z_5m
flow_price_divergence_5m
unknown_aggressor_share_5m  (quality flag)
```

Used as:
- Distribution adjustment
- Danger score
- Confidence modifier

### Data Pipeline (No New Infrastructure)

The optimizer reads:
```
Redis latest snapshots (Item 5 + Item 8 outputs)
Current option marks
Current position state
Supabase for logging/replay
```

---

## 10. Replay Validation

### Process

For each historical trade:
```
1. Replay the actual entry
2. At each evaluation time, reconstruct only data available then
3. Compute optimizer recommendation
4. Simulate two paths:
   A. static exit policy
   B. adaptive exit policy
5. Apply realistic slippage and fees
6. Compare outcomes
```

### Metrics

```
avg P&L delta per trade
median P&L delta
R-multiple delta
max drawdown delta
worst-day delta
profit factor
premature_exit_cost
loss_avoidance_value
average hold time
slippage cost
strategy-specific deltas
```

### Promotion Gates

```
adaptive exits improve total P&L by >= 5%
OR improve avg R by >= 0.03 per trade

max drawdown not worse
worst day not worse
profit factor improves (or stays equal)
positive in at least 2 of 3 walk-forward windows
no major strategy bucket degraded by > 5%
slippage does not consume > 30% of improvement
```

If only one strategy improves, production authority is strategy-specific.

---

## 11. V0.3 vs V0.4 Sequencing

### V0.3 (Advisory / Shadow Only)

**Build:**
- Forward EV calculator
- Recommendation engine
- Logging
- Counterfactual static-vs-adaptive ledger
- Strategy-specific diagnostics
- Operator review dashboard

**Authority:**
- Advisory only
- Logs recommendations
- CANNOT auto-exit
- Static rules execute exits

### V0.4 (Limited Production Authority)

**Promotion gates (ALL required):**
```
200 replayed/closed trades minimum
40 trades per enabled strategy bucket
60+ paper-shadow sessions
positive adaptive_exit_value over rolling 60 sessions
realized P&L improvement > 5% versus static exits
max drawdown not worse
worst day not worse
profit factor not worse
slippage consumes < 30% of improvement
Wilson_lower_95(useful_exit_rate) > 0.30
adaptive_exit_value > 0
```

**Wilson definition:**
```
useful_exit_rate =
  useful_adaptive_exits / total_adaptive_exit_recommendations
```

Note: dollar/R-value improvement remains the **primary** metric. Wilson is a secondary check. A few avoided large losses can matter more than many small premature exits.

### V0.4 Authority Limits

Even with V0.4 promotion, the optimizer:
- Can only close/reduce
- Cannot roll
- Cannot reopen
- Cannot delay static exits
- Cannot override constitutional gates

**Static exits remain the safety net.** Adaptive exits become an earlier-risk-reduction overlay.

### Strategy-Specific Promotion

```
IC may graduate while straddle remains advisory
PCS may graduate while IB remains advisory
Each strategy meets its own bar
```

---

## 12. Expected ROI Trajectory

| Period | Expected Contribution | Authority |
|---|---|---|
| Months 1-3 | 0% | Paper calibration, advisory only |
| Months 4-6 | 0% to +1% | V0.3 advisory mode |
| Months 7-12 | +2% to +5% (base), +5% to +7% (bull) | V0.4 if validated, strategy-specific |

### ROI Mechanism

**Lower bound (+2%) from:**
- Cuts a few losers before static stop
- Locks profit when forward EV collapses on winners
- Avoids giveback on short-gamma trades

**Upper bound (+5% to +7%) from:**
- Correctly exits IC/IB/PCS when flow/vol shifts before static rules react
- Reduces late-day gamma losses
- Captures straddle profits before IV/realized move decay

### Negative Case (Deprecation Triggered)

- Premature exits on noisy EV dips
- Overreacts to OPRA flow
- Slippage consumes advantage
- Cuts winners before theta/profit target develops

**The main risk: premature exit churn.** This is why V0.3 advisory is mandatory — the data must prove the optimizer beats static exits before it gets authority.

---

## 13. Concrete Examples

### Normal IC at 40% profit, 2 hours left, modest EV degradation

```
Inputs:
  profit = 40% max profit
  flow neutral
  iv_rv stable
  short strikes safe
  exit_advantage_R = small
  confidence = medium

Recommendation: HOLD static plan

Reason: do not exit on a small noisy EV dip.
```

### Same IC, 40% profit, 2 hours left, bearish flow shift

```
Inputs:
  profit = 40%
  short put risk rising
  bearish flow_persistence_15m
  aggressive_put_call_imbalance elevated
  vol_demand_pressure positive
  breach probability rising
  exit_advantage_R clears threshold

V0.3 Recommendation: log advisory exit
V0.4 Recommendation (validated): authorized early exit
```

### Long straddle at -30%, strong move signal from Item 5 + Item 8

```
Inputs:
  current P&L = -30%
  iv_rv_ratio favorable
  forward RV positive
  OPRA vol demand strong
  directional pressure persistent
  remaining time adequate
  EV_hold > EV_exit_now
  confidence high

Recommendation: HOLD

Reason: do not exit on mark-to-market loss alone. For long gamma,
the question is whether the move is still likely before theta
kills the trade.
```

---

## 14. Failure Modes And Mitigations

| Failure Mode | Mitigation |
|---|---|
| Premature exits on noise | Confidence-adjusted thresholds, default-to-static on low confidence |
| Trailing-stop conflation | Giveback as confidence modifier only, NOT exit trigger |
| Path-blind decisions | Trajectory features in uncertainty calculation |
| Adverse slippage | Adaptive exit slippage premium, capped at 3x |
| Apples-to-oranges EV comparison | Both EV_exit_now AND EV_hold include realistic friction |
| 14:30 boundary errors | Mandatory close embedded in every simulation |
| Strategy-blind logic | Strategy-specific failure modes and exit triggers |
| Premature production authority | V0.3 advisory, V0.4 strategy-specific promotion with high bar |
| Overreaction to OPRA flow | Flow features modify distribution, never directly trigger exits |
| LLM in critical path | NO LLM calls in exit loop; deterministic only |

---

## 15. V0.3 Build Scope

**Build:**
- Forward EV calculator (reusing Item 5 distribution machinery)
- Trajectory features (giveback, path_vol, profit_velocity)
- Multiplicative uncertainty adjustment
- Hybrid evaluation cadence (120s normal + stress triggers)
- Strategy-specific decision rules
- Constitutional gate respect (esp. 14:30 close in simulation)
- Adaptive exit slippage model
- Recommendation logging
- Counterfactual static-vs-adaptive ledger
- Operator review dashboard
- Replay validation harness

**Do not build in V0.3:**
- Production exit authority (V0.4 only after validation)
- Reinforcement learning on exit policies
- Continuous tick-frequency evaluation
- Position rolling
- Position re-opening
- LLM-driven exit decisions

---

## 16. Final Architectural Statement

The exit optimizer is **worth building, but it must earn authority slower than entry-side components.** Premature exits can quietly destroy expectancy. Static exits remain the execution backbone; adaptive exits become an earlier-risk-reduction overlay only after proving positive value strategy-by-strategy.

The architectural commitments hold:
- AI controls admissibility and size ceilings, not trade execution
- Constitutional gates remain non-overridable
- Adaptive exits can ONLY cause earlier exits, never later
- Static exits remain the safety net even after V0.4 promotion

---

*Spec produced through Claude opening + GPT-5.5 Pro Round 1 + Claude verification + GPT verification accept over 2026-04-25. Locked after one full round plus verification. No code changes during specification.*
