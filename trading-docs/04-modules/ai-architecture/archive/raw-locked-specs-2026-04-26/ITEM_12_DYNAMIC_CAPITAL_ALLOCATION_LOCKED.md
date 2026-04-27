# Item 12: Dynamic Capital Allocation with Regime-Stability Check — LOCKED SPECIFICATION

**Status:** 🔒 LOCKED
**Locked:** 2026-04-26
**Tier:** V0.4 Maturation (6-12 months after V0.3)
**Architectural Role:** Daily/intraday capital-budget allocator. Not trade selector.
**Sources:** GPT Round 2 + Items 1-11 dependencies + Claude verification + GPT verification accept

---

## Architectural Commitment

**Item 12 is a budget allocator, not a trade selector.**

It decides HOW MUCH total risk the system is allowed to deploy today/this window. Items 1, 6, 7, and 11 continue to decide WHETHER each individual trade is admissible and HOW LARGE that trade can be.

**Strongest commitment:**

> Item 12 may reduce or ration risk, but it NEVER creates permission. It allocates capital only among trades already allowed by constitutional gates, event playbooks, Governor, Meta-Labeler, and Adversarial Review.

**Composition formula:**

```
effective_daily_budget =
  phase_session_ceiling
  × stability_multiplier
  × performance_multiplier

effective_daily_budget = min(effective_daily_budget, item11_event_budget_cap)

deployable_budget = effective_daily_budget × 0.80
```

**Per-trade composition (Item 12 adds remaining_budget cap):**

```
trade_size = min(
  constitutional_cap,
  phase_cap,
  rules_cap,
  governor_cap,
  meta_labeler_cap,
  event_playbook_cap,
  adversarial_cap_if_present,
  remaining_item12_budget
)
```

---

## 1. Decision Space (Combined with Hierarchy)

### Levers Item 12 Controls

```
1. Total daily/session risk budget (PRIMARY)
2. Per-strategy-class budget caps (CONCENTRATION LIMITS)
3. Dynamic concurrent-position cap (CORRELATION LIMITS)
4. Reserve / dry-powder requirement (TAIL PROTECTION)
```

### Levers Item 12 Does NOT Control

```
exact strikes
strategy selection
per-trade conviction labels
trade execution
exit timing
```

### Risk Definition

```
position_risk_pct = max_loss_after_credit_and_slippage / account_equity

For debit trades:
  position_risk_pct = debit_paid_after_slippage / account_equity

For spreads/condors:
  position_risk_pct = max_possible_loss_after_credit_and_slippage / account_equity
```

### Budget Enforcement

```
System may not open new positions if:
  open_risk_pct + proposed_position_risk_pct > effective_daily_budget_pct
```

### Per-Strategy-Class Caps (Concentration Limits)

```
neutral_short_gamma_cap = 60% of effective budget
single_side_credit_cap  = 60%
directional_debit_cap   = 50%
long_vol_convex_cap     = 25% until validated
calendar_cap            = 25% until validated
```

These are NOT independent budgets. They are concentration limits within the total budget.

### Concurrent Position Cap

```
stability >= 0.80: max 3 positions
0.60–0.80: max 2 positions
0.40–0.60: max 1 position
<0.40: no new positions, except operator-approved defensive trades
```

Three small correlated trades can behave like one oversized trade. The dynamic cap addresses this directly.

---

## 2. Regime Stability Score

### Definition

> Regime stability means: the system's current classification, volatility state, dealer structure, news state, flow, and cross-asset behavior are internally coherent and not rapidly changing.

It is NOT "low volatility." A trend day can be stable if the trend is coherent.

### Component Formula

```
regime_stability_score =
    0.25 * regime_consistency
  + 0.20 * vol_state_persistence
  + 0.20 * gex_key_strike_stability
  + 0.15 * news_event_calm
  + 0.10 * cross_asset_coherence
  + 0.10 * flow_price_coherence
```

All components 0–1. Weights sum to 1.0.

### Component 1: regime_consistency

Lookback: last 4 decision cycles (~20–60 minutes).

```
regime_consistency = count(most_common_regime) / total_regime_observations

Examples:
  range, range, range, range = 1.00
  range, range, trend, range = 0.75
  range, trend, event, unknown = 0.25
```

### Component 2: vol_state_persistence

VIX bucket / implied-vol bucket stability.

```
1.0 if VIX bucket unchanged over last 60 min
0.7 if adjacent bucket change only
0.4 if two bucket changes
0.2 if VIX spike z-score > 2
0.0 if VIX spike z-score > 3
```

### Component 3: gex_key_strike_stability

```
gex_key_strike_stability = 
    1 - min(
          1,
          abs(current_gamma_wall - prior_gamma_wall)
          / max(Item5_expected_move_points, 10)
        )

Then multiply by GEX confidence:
  gex_key_strike_stability *= gex_confidence

If GEX stale or failed:
  gex_key_strike_stability = 0.30
  data_quality_flag = 'gex_calculation_failed'
```

### Component 4: news_event_calm

```
news_event_calm = 
    1 - max(
          surprise_detector_severity,
          governor_novelty_score,
          item11_unscheduled_event_score
        )

If Item 11 event window active, cap:
  FOMC release window: news_event_calm <= 0.10
  CPI/NFP open reset:  news_event_calm <= 0.40
  OpEx late window:    news_event_calm <= 0.60
```

### Component 5: cross_asset_coherence

Use SPY / QQQ / IWM (or SPX / NDX / RUT if available).

```
cross_asset_coherence = 
    1 - normalized_dispersion(returns_15m across SPY, QQQ, IWM)

High coherence: all risk indices moving same direction with similar magnitude
Low coherence: SPX flat, QQQ ripping, IWM selling off
```

### Component 6: flow_price_coherence

From Item 8.

```
flow_price_coherence = 
    1 - min(1, abs(flow_price_divergence_5m) / 3)
```

### Stability-to-Allocation Mapping

```
stability >= 0.80:
  stability_multiplier = 1.00

0.65–0.80:
  stability_multiplier = 0.75

0.50–0.65:
  stability_multiplier = 0.50

0.35–0.50:
  stability_multiplier = 0.25

<0.35:
  stability_multiplier = 0.00 for new neutral short-gamma
  stability_multiplier = 0.25 max for defined-risk directional/convex only
```

**Important:** Low stability does not automatically mean "buy vol." It means "do NOT allocate normal risk."

---

## 3. Stability-Component Circuit Breakers

Severe single-component readings can be averaged away by other components. Circuit breakers prevent this.

```
if gex_confidence < 0.30:
    regime_stability_score = min(score, 0.50)
    flag = 'gex_unreliable'

if news_event_calm < 0.20:
    regime_stability_score = min(score, 0.40)
    flag = 'event_active'

if vol_state_persistence < 0.20:
    regime_stability_score = min(score, 0.35)
    flag = 'vol_shock'

if regime_consistency < 0.40:
    regime_stability_score = min(score, 0.45)
    flag = 'regime_unstable'

if data_quality_critical_failure = true:
    regime_stability_score = min(score, 0.40)
    flag = 'data_quality_unreliable'
```

### Critical Data Quality Failures

```
SPX stale
VIX stale
option chain stale
OPRA unavailable when OPRA-dependent decision is proposed
GEX failed for GEX-dependent strategy
```

### Circuit Breaker Authority

Circuit breakers do NOT automatically force a halt. They reduce allocation authority. Constitutional gates and Item 11 still decide hard blocks.

---

## 4. Phase Ladder Interaction (Multiplicative Nested Constraints)

```
effective_daily_budget = 
    phase_session_ceiling
    × stability_multiplier
    × performance_multiplier

Then apply event caps:
  effective_daily_budget = 
      min(effective_daily_budget, item11_event_budget_cap)
```

The phase ladder remains the long-term maturity ceiling. Item 12 is the short-term allocator inside that ceiling.

### Phase Ladder Non-Monotonic Issue

**Item 12 should NOT fix the broken Phase 2.** The phase ladder needs a separate correction before Day 40.

Proposed phase ladder fix (separate from Item 12):

```
Phase 1: core 0.50%, satellite 0.25%
Phase 2: core 0.75%, satellite 0.375%
Phase 3: core 1.00%, satellite 0.50%
Phase 4: manual expansion only
```

If Phase 1 is paper-only stress testing, rename it so it is not interpreted as live capacity. Do not let Item 12 hide the inversion.

---

## 5. Recent Performance Multiplier (Cap-Based, Not Multiplicative)

```
performance_multiplier = min(
    sharpe_cap,
    drawdown_cap,
    loss_streak_cap,
    calibration_cap,
    execution_quality_cap
)
```

Using min() prevents over-penalization. Worst component sets the cap; bad signals don't compound.

### Sharpe / Recent R Cap

```
if rolling_5d_R < 0:
    sharpe_cap = 0.85

if rolling_10d_sharpe < 0:
    sharpe_cap = 0.75

if rolling_20d_sharpe < 0:
    sharpe_cap = 0.50
```

### Drawdown Cap

```
drawdown_from_peak < 2%:    drawdown_cap = 1.00
2%–3%:                       drawdown_cap = 0.85
3%–5%:                       drawdown_cap = 0.75
5%–8%:                       drawdown_cap = 0.50
>8%:                         drawdown_cap = 0.25 + operator review required
```

### Loss Streak Cap

Existing streak halt remains constitutional.

```
loss_streak = 0 or 1: cap = 1.00
loss_streak = 2:      cap = 0.50
loss_streak >= existing halt threshold: cap = 0.00
```

### Calibration Drift Cap

```
minor drift:
    calibration_cap = 0.75

major drift:
    calibration_cap = 0.50

authority degraded to advisory:
    calibration_cap = 0.25 or 0.00 for affected strategy classes
```

Item 12 respects Item 4's promotion records for affected items.

---

## 6. Intraday Dynamics

### Cadence

```
pre-market: initial budget
09:35 ET: post-open reset
then every 30 minutes
candidate event: recompute ONLY if stability changed by >= 0.10
Item 11 transition: binding recompute
hard trigger: immediate recompute
```

### Hard Triggers

```
drawdown > 0.50%
loss streak change
daily halt / streak halt
data-quality failure
vol shock
unscheduled event playbook fires
```

### Hysteresis

```
if abs(new_stability_score - prior_stability_score) < 0.10:
    do not change budget
```

### Asymmetric Update Rule

```
Budget MAY decrease immediately.
Budget MAY increase only back toward the pre-market maximum.
Budget NEVER exceeds pre-market maximum intraday.
```

### Increase Allowed When

```
FOMC/CPI temporary event cap expires
regime stabilizes
no loss incurred
data quality restored
```

### Increase NOT Allowed When

```
intraday loss > 0.5R
Governor/adversarial high-risk conflict
calibration drift
loss streak active
```

### Expected Cadence

```
10–15 allocation snapshots per session
```

This is reviewable and auditable.

---

## 7. Concurrent Position Composition (Conviction-Weighted)

### Candidate Score

```
candidate_score = 
    0.35 * meta_p_eff
  + 0.25 * normalized_ev_per_margin
  + 0.20 * governor_confidence
  + 0.10 * item5_confidence
  + 0.10 * flow_confirmation_score
  - correlation_penalty
  - event_penalty
```

### Allocation Algorithm

```
1. Sort candidates by candidate_score (descending)
2. Try highest candidate at its allowed per-trade cap
3. If does not fit remaining budget, reduce to next valid size tier
4. Reject lower-ranked candidates if budget exhausted
5. Enforce strategy-class caps and max concurrent position cap
```

### Example

```
budget = 0.60R

A: iron_condor, p_eff 0.75, normal size 1.0R
B: put_credit_spread, p_eff 0.55, normal size 0.5R

Result:
A reduced to 0.50R if all other caps allow
B rejected or held for later

Do NOT take both at tiny sizes just to "participate."
```

### Item 4 Calibration Discipline

Hand-set V0.4 weights are starting points. Pre-V0.4 lock requires:

```
Latin-hypercube / coordinate search via Item 4

Search ranges:
  meta_p_eff:              0.20–0.45
  normalized_ev_per_margin:0.15–0.35
  governor_confidence:     0.10–0.30
  item5_confidence:        0.05–0.20
  flow_confirmation:       0.05–0.20

Constraints:
  Positive weights nonnegative, sum to 1.0
  Penalty terms calibrated separately
```

### Sensitivity Gate

```
Changing any major weight by ±0.10
must NOT flip >15% of candidate rankings.

If sensitivity gate fails:
  Item 12 remains advisory or uses coarse bucket ranking only.
```

This mirrors Item 1's discipline.

---

## 8. Reserve / Dry Powder Policy

### Base Reserve

```
base_reserve = 20% of effective_daily_budget
deployable_budget = 80% of effective_daily_budget
```

### Reserve Release Conditions

Reserve can be partially released only when ALL conditions met:

```
regime_stability_score >= 0.80
top_candidate_score >= 0.75
data_quality_ok = true
no active Item 11 high-risk window
no intraday loss > 0.25R
no calibration degradation
```

### Reserve Release Amount

```
reserve_release_allowed = up to 50% of reserve
```

### Reserve NEVER Released When

```
loss streak >= 2
drawdown_from_peak > 3%
major calibration drift
event window active
```

### V0.5+ Calibration

```
Item 4 tests reserve = 10%, 20%, 30%

Primary metric:
  loss_avoided - false_underallocation_cost

Secondary:
  Sharpe, max drawdown, capital utilization, missed A+ trades
```

### Critical Interlock

```
T0-7 floor does NOT override Item 12 no-budget.
```

If the budget is too small to support one valid defined-risk trade, the system skips. The fix is better calibration, not forcing trades through a floor. Minimum contract logic CANNOT become a backdoor around budget control.

---

## 9. Halt Logic Composition

Constitutional gates override Item 12.

```
if daily_halt_active:
    effective_daily_budget = 0

if streak_halt_active:
    effective_daily_budget = 0

if time_stop / no-new-entry window active:
    new_trade_budget = 0
    exit/risk management continues

if graduation/phase gate fails:
    production_budget = 0
```

Item 12 composes only when trading is otherwise allowed.

---

## 10. Operator Override Mechanism

### Override Types

```
override_type enum:
  cap_at_X         (operator caps at lower budget)
  extend_to_Y      (operator increases above algorithm output)
  halt_for_today   (operator full halt)
  release_reserve  (operator forces reserve release)
  restore_normal   (cancel previous override)
```

### Required Fields

```
override_type
override_reason TEXT (required, audit trail)
override_timestamp TIMESTAMPTZ
override_user TEXT
override_expires_at TIMESTAMPTZ (auto-revert)
override_recorded_for_attribution BOOLEAN (default true)
```

### Constraints

```
cap_at_X:
  always allowed if more conservative

halt_for_today:
  always allowed

extend_to_Y:
  CANNOT exceed phase_session_ceiling
  CANNOT bypass Item 11 event cap
  CANNOT bypass constitutional halt
  CANNOT bypass strategy-class caps unless operator records 
    SEPARATE reason

release_reserve:
  CANNOT bypass constitutional halt
  CANNOT bypass Item 11 block
  CANNOT exceed phase ceiling

restore_normal:
  Removes active operator override
  Does NOT restore budget above algorithmic current budget
```

### Audit

```
All overrides → capital_allocation_snapshots
Item 10 attribution captures:
  operator_override_flag
  override_type
  override_reason
  pre_override_budget
  post_override_budget
  outcome_after_override

Weekly operator review identifies override patterns.
```

---

## 11. Schema: capital_allocation_snapshots

```sql
CREATE TABLE capital_allocation_snapshots (
  allocation_id UUID PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  session_date DATE NOT NULL,
  
  -- Phase ladder context
  phase INTEGER NOT NULL,
  phase_core_pct NUMERIC NOT NULL,
  phase_satellite_pct NUMERIC NOT NULL,
  phase_session_ceiling_pct NUMERIC NOT NULL,
  
  -- Stability inputs
  regime_stability_score NUMERIC NOT NULL,
  regime_stability_components JSONB NOT NULL,
  stability_multiplier NUMERIC NOT NULL,
  circuit_breaker_flags TEXT[] NOT NULL DEFAULT '{}',
  
  -- Performance inputs
  performance_multiplier NUMERIC NOT NULL,
  performance_components JSONB NOT NULL,
  
  -- Event context
  item11_event_cap NUMERIC NULL,
  event_context JSONB,
  
  -- Budget outputs
  effective_daily_budget_pct NUMERIC NOT NULL,
  deployable_budget_pct NUMERIC NOT NULL,
  reserve_pct NUMERIC NOT NULL,
  remaining_budget_pct NUMERIC NOT NULL,
  
  -- Concentration controls
  strategy_class_caps JSONB NOT NULL,
  max_concurrent_positions INTEGER NOT NULL,
  
  -- Current state
  open_risk_pct NUMERIC NOT NULL,
  proposed_risk_pct NUMERIC NULL,
  allocation_decision TEXT NOT NULL,
  reason_codes TEXT[] NOT NULL DEFAULT '{}',
  
  -- Operator override
  operator_override_flag BOOLEAN NOT NULL DEFAULT false,
  override_type TEXT NULL,
  override_reason TEXT NULL,
  override_user TEXT NULL,
  
  -- Data quality
  data_quality_flags TEXT[] NOT NULL DEFAULT '{}',
  calibration_version TEXT NOT NULL,
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_alloc_session_date ON capital_allocation_snapshots(session_date);
CREATE INDEX idx_alloc_timestamp ON capital_allocation_snapshots(timestamp);
```

### Per-Trade Linkage

Every trade decision stores:
```
allocation_id (links to capital_allocation_snapshots)
remaining_budget_before
remaining_budget_after
```

Item 10 attribution captures these for outcome analysis.

---

## 12. Empirical Validation via Item 4

### Baselines

```
Baseline A: existing phase ladder only

Candidate B: phase ladder + Item 12 dynamic allocation

Optional:
  Candidate C: phase ladder + stability only
  Candidate D: phase ladder + stability + performance feedback
  Candidate E: full Item 12 with reserve and strategy caps
```

### Metrics

```
Sharpe
Sortino
max drawdown
worst day
daily halt frequency
profit factor
P&L per unit risk deployed
capital utilization
missed-profit from underallocation
loss avoided from de-risking
trade retention
strategy concentration
```

### Promotion Gates

#### Reduced Authority

```
minimum 120 clean sessions
minimum 100 closed trades
2 walk-forward folds
max drawdown not worse
worst day not worse
P&L per unit risk improves >= 5%
trade retention >= 60%
```

#### Production Authority

```
minimum 180 clean sessions
OR 6+ months with 3 walk-forward folds

Sharpe improves >= 0.15
OR max drawdown improves >= 10%

total P&L not worse by more than 2R
worst day not worse
daily halt frequency not worse
capital efficiency improves
false underallocation cost <= 40% of loss avoided
```

### Failure Mode

```
If validation fails:
  Item 12 advisory only
  Dashboard shows recommended budget
  Actual system uses phase ladder only
```

---

## 13. V0.4 Ship Scope

### Required for V0.4

```
1. CREATE TABLE capital_allocation_snapshots
2. backend/capital_allocator.py (main orchestrator)
3. backend/regime_stability_engine.py (6-component score + circuit breakers)
4. backend/performance_multiplier_engine.py (cap-based)
5. backend/concurrent_position_optimizer.py (conviction-weighted)
6. backend/reserve_policy.py (20% base + release conditions)
7. backend/operator_override_handler.py (audit-tracked)
8. Item 4 calibration runs for candidate scoring weights
9. Item 4 validation runs for promotion gates
10. Operator dashboard for budget visualization
```

### V0.4 Defers

```
- Learned monotonic allocation model
- Continuous Kelly optimizer
- Strategy covariance optimizer
- Cross-index allocation
- RL capital allocator
- Intraday re-leveraging above pre-market cap
- Automatic phase ladder modification
```

### Never Build

```
- Item 12 forcing trades through min budget (T0-7 backdoor)
- Item 12 bypassing Item 11 event caps
- Item 12 bypassing constitutional halts
- Auto-recovery to pre-loss budget within session
- Operator override that bypasses constitutional halts
```

---

## 14. Failure Mode Analysis

### Failure Mode 1: False Stability Before Regime Break

```
Symptom: market looks stable, then breaks
Mitigation:
  intraday decrease allowed immediately
  Items 1, 11 can still block
  reserve policy prevents full deployment
  short-gamma class cap limits damage
```

### Failure Mode 2: Underallocating Best Days

```
Symptom: Item 12 reduces risk on days that become profitable
Mitigation:
  track false_underallocation_cost
  require loss_avoided > false_underallocation_cost
  reserve can release only on A+ confirmation
  V0.4 calibration tunes thresholds
```

### Failure Mode 3: Procyclical De-Risking After Normal Variance

```
Symptom: reduce allocation after few losses, miss recovery
Mitigation:
  performance caps use rolling windows (not single trades 
    except hard halt)
  authority recovers after clean sessions
  drawdown bands are gradual (2%/3%/5%/8%)
```

### Failure Mode 4: Overfitting Stability Formula

```
Symptom: 6 components and many thresholds can overfit
Mitigation:
  V0.4 hand-coded priors with sensible ranges
  few thresholds
  Item 4 walk-forward validation
  no learned allocator until V0.5
```

---

## 15. Expected ROI Contribution

### Mature V0.4 Contribution

```
+2% to +5% annual full-account ROI
```

### Bull Case

```
+5% to +8%
```

### Mechanism

```
fewer oversized days in unstable regimes
less correlated same-day exposure
better preservation after drawdowns
more capital available for high-quality sessions
```

### Negative Case

```
underallocates best trend/event days
overreacts to short-term bad luck
duplicates upstream filters without adding portfolio-level value
```

The empirical validation gate is the test for whether positive case dominates negative case.

---

## 16. Final Architectural Statement

**Item 12 makes the system trade LESS when the market state is unstable or recent calibration is poor, and let it use NORMAL budget only when the environment is stable and the opportunity set is genuinely high quality.**

It NEVER:
- Creates permission to trade
- Increases risk beyond phase ladder
- Allocates around Item 11 event blocks
- Bypasses constitutional halts
- Forces trades through T0-7 floor

It ALWAYS:
- Composes through final arbiter min()
- Preserves operator override capability with audit trail
- Logs allocation decisions for Item 10 attribution
- Defers binding authority to Item 4 empirical validation

The architectural keystone is the dual cap interaction:

```
Phase ladder = long-term maturity ceiling (months/quarters)
Item 12 = short-term opportunity allocator within ceiling (daily)
Item 11 = event-day playbook restrictions (hours)
Items 1, 6, 7 = per-trade admissibility and sizing (minutes)

Constitutional halts override everything.
```

Each operates at its appropriate timescale. Item 12's portfolio-level discipline complements per-trade signal quality from Items 1, 5, 6, 8 — defensive value, not offensive alpha.

---

*Spec produced through GPT-5.5 Pro Round 2 + Items 1-11 dependencies + Claude verification + GPT verification accept on 2026-04-26. Locked after one full audit round plus verification. Portfolio-level constraint layer for V0.4.*
