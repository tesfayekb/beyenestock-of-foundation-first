# Item 6: Meta-Labeling — Should We Take This Trade At All? — LOCKED SPECIFICATION

**Status:** 🔒 LOCKED
**Locked:** 2026-04-25
**Tier:** V0.2 (Alpha Generation)
**Sources:** GPT-5.5 Pro Round 1 + Claude refinements + GPT verification round
**Expected ROI contribution at maturity (months 7-12):** +3% to +7% annual full-account ROI
**Architectural role:** The keystone — sits between Item 5's strategy_ev_table and the AI Risk Governor, deciding which proposed trades actually get taken.

---

## Architectural Commitment

The meta-labeler is a **Bayesian-shrunk, sample-efficient, calibration-first filter**. It rejects weak rules-proposed trades and reduces size on uncertain proposals. It does NOT generate alpha, override the AI Risk Governor, increase risk beyond rules/Governor caps, or bypass constitutional risk gates.

**Critical sizing rule:**
```
final_size = min(
  constitutional_cap,
  rules_cap,
  governor_cap,
  meta_labeler_cap
)
```

If any component says 0, the trade is skipped. Caps compose by minimum, never by averaging or voting.

---

## 1. Training Target — Strategy-Specific Utility

The meta-labeler answers: **P(realized_strategy_utility > 0 | proposed trade)**

NOT: P(trade makes any profit) — too coarse, allows tiny-profit trades that consumed clean setups.

### Common Terms
```
net_pnl = realized P&L after slippage and fees
max_risk = max possible loss / margin-at-risk
R = net_pnl / max_risk
MAE_R = max adverse excursion / max_risk
```

### Iron Condor (16/8) Utility

```
credit_capture = net_pnl / entry_credit
hurdle = max(0.03, 0.25 * entry_credit / max_risk)

put_side_proximity_t =
  if S_t >= K_short_put: 0
  else min(1, (K_short_put - S_t) / put_wing_width)

call_side_proximity_t =
  if S_t <= K_short_call: 0
  else min(1, (S_t - K_short_call) / call_wing_width)

proximity_t = max(put_side_proximity_t, call_side_proximity_t)

max_loss_zone_peak = max(proximity_t over trade life)
max_loss_zone_twap = average(proximity_t over trade life)

U_IC =
    R
  - hurdle
  - 0.15 * short_strike_breach_flag
  - 0.10 * max(0, MAE_R - 0.35)
  - 0.12 * max_loss_zone_peak^2
  - 0.08 * max_loss_zone_twap^2

y_take = 1 if U_IC > 0 else 0
```

The peak + twap penalty combination distinguishes brief scares from sustained pressure. A trade that hit proximity 0.8 for one minute is different from one that lived at 0.5 for 4 hours.

### Iron Butterfly Utility (Stricter — Iran-Day Protection)

```
credit_capture = net_pnl / entry_credit
hurdle = max(0.04, 0.30 * entry_credit / max_risk)

U_IB =
    R
  - hurdle
  - 0.20 * finish_outside_breakeven_flag
  - 0.20 * wing_stress_flag
  - 0.15 * max(0, MAE_R - 0.30)
  - 0.20 * event_day_short_gamma_flag

y_take = 1 if U_IB > 0 else 0
```

The `event_day_short_gamma_flag` directly encodes the Iran-day failure protection. An IB on a geopolitical-shock day where short-gamma was dangerous gets labeled bad regardless of whether it happened to make money.

### Put Credit Spread (16/8) Utility

```
credit_capture = net_pnl / entry_credit
hurdle = max(0.03, 0.25 * entry_credit / max_risk)

U_PCS =
    R
  - hurdle
  - 0.20 * short_put_breach_flag
  - 0.20 * downside_acceleration_flag
  - 0.10 * max(0, MAE_R - 0.35)

y_take = 1 if U_PCS > 0 else 0
```

Distinguishes "puts were rich and cushion held" from "we survived by luck."

### Long Straddle Utility

```
hurdle = 0.08

U_STRADDLE =
    R
  - hurdle
  - 0.15 * no_catalyst_theta_bleed_flag
  - 0.10 * max(0, time_decay_loss_rate - expected_rate)

y_take = 1 if U_STRADDLE > 0 else 0
```

Higher hurdle reflects need for convexity. Repeated small wins do not offset frequent theta bleed.

### Debit Call Spread Utility

```
hurdle = 0.06

U_DCS =
    R
  - hurdle
  - 0.15 * failed_direction_flag
  - 0.10 * stall_after_entry_flag
  - 0.10 * max(0, MAE_R - 0.40)

y_take = 1 if U_DCS > 0 else 0
```

Direction alone insufficient. Move must be large and fast enough to overcome debit decay.

### Storage

For all strategies, store both:
- `y_take` (binary label for model training)
- `quality_score` (clipped continuous U for diagnostics and reports)

---

## 2. Model Class — Three-Part Hybrid

**Critical decision:** Do NOT use pure LightGBM as production authority in V0.2. With 50-100 trades it overfits.

### Production Probability

```
p_take = w_prior * p_prior + w_model * p_logistic + w_memory * p_memory
```

### Sample-Size-Dependent Weights

```
if n_train < 150:
    w_prior  = 0.55
    w_model  = 0.20
    w_memory = 0.25

if 150 <= n_train < 300:
    w_prior  = 0.40
    w_model  = 0.35
    w_memory = 0.25

if n_train >= 300:
    w_prior  = 0.25
    w_model  = 0.50
    w_memory = 0.25
```

Memory weight stays constant at 0.25 across all stages — analogs always contribute meaningful context.

### Bayesian Prior (Hierarchical with Smooth Pooling)

```
Level 0: global (alpha=1, beta=1, weak)
Level 1: per-strategy
Level 2: strategy × regime
Level 3: strategy × regime × time_bucket
Level 4: strategy × regime × time_bucket × event_bucket
```

Smooth partial pooling formula:
```
p_level = (wins_level + k * p_parent) / (n_level + k)
where k = 20 (effective prior strength)
```

Approximate effective parent weight by sample size:
- n=5 → ~80% parent
- n=20 → ~50% parent
- n=80 → ~20% parent

Smooth transitions, no discontinuities at threshold boundaries.

**Initialization:** Before clean replay data exists, use `global prior = Beta(1,1)`. After clean replay/paper data accumulates (post-Commit-4), initialize from observed utility labels. Pre-Commit-4 contaminated trade P&L remains EXCLUDED.

### Logistic Scorecard

Regularized logistic regression. NOT neural networks.

```
penalty = L2
C = 0.25 to 1.0
class_weight = balanced (only if severe imbalance)
max features = 30-50
no high-cardinality raw identifiers
```

Why: fast, interpretable, stable, easy to recalibrate, sample-efficient.

### LightGBM (Future Authority Only)

Can run shadow-only initially. Production authority requires 300+ labeled candidate examples, preferably 500+.

If/when used:
```
num_leaves: 7-15
max_depth: 2-3
learning_rate: 0.03-0.05
n_estimators: 50-150
min_data_in_leaf: 20-40
lambda_l1: 0.1
lambda_l2: 1.0-5.0
feature_fraction: 0.7
bagging_fraction: 0.7
```

---

## 3. Feature Engineering

### From Item 5 EV Table (Vol Fair-Value Engine)

```
ev_per_margin
ev_dollars
pop
p_max_loss
cvar_5
iv_rv_ratio
rv_forecast_move
implied_move
skew_z
smile_asymmetry_score (meta-labeler feature only, NOT decision signal)
smile_width_score
tail_width_score
engine_confidence
authority_level
estimated_slippage
slippage_to_ev_ratio
breakeven_distance_points
breakeven_distance_vs_forecast_move
```

### Most Important Derived Features

```
vol_edge = log(iv_move / rv_forecast_move)
edge_after_slippage = ev_dollars - estimated_slippage
ev_to_cvar = ev_dollars / abs(cvar_5)
breakeven_to_forecast = breakeven_distance / rv_forecast_move
```

### From Rules Engine

```
rules_regime
rules_confidence
strategy_selected_by_rules
strategy_allowed_by_map
distance_from_regime_boundary
```

### From LightGBM Direction Model

```
p_bull
p_bear
direction_confidence
direction_edge = p_bull - p_bear
strategy_direction_alignment
```

Strategy-specific alignment:
- debit_call_spread alignment = p_bull - p_bear
- put_credit_spread alignment = p_bull - p_bear (penalized by downside tail risk)
- iron_condor alignment = -abs(p_bull - p_bear)

### From AI Risk Governor (Structured Fields ONLY)

```
event_class
novelty_score
uncertainty_score
signal_conflict_score
data_freshness_warning
short_gamma_block_flag
allowed_strategy_class_flag
governor_size_cap
review_required
```

Do NOT use raw LLM rationale text as a model feature.

### From Memory Retrieval (Top 20 Analogs)

```
n_similar_cases
similarity_weighted_win_rate
similarity_weighted_avg_utility
similarity_weighted_p25_utility
same_strategy_case_count
same_event_case_count
same_regime_case_count
similar_case_tail_loss_rate
analog_disagreement_score
most_recent_similar_case_age
```

Case weights for memory features:
- actual: 1.0
- counterfactual: 0.5
- synthetic: 0.2

### Explicitly Excluded

- raw headlines
- raw LLM prose
- raw option chain rows
- future realized volatility
- post-entry P&L
- date identifiers
- trade ID
- unadjusted account balance
- uncalibrated LLM confidence text

---

## 4. Training Data Strategy (Small-Sample Problem)

### 1. Train on Candidate Decisions, Not Just Executed Trades

Every rules-proposed trade becomes a labeled candidate if replay can reconstruct entry, exit, slippage, outcome.

Data weights:
```
actual executed trade        = 1.0
rules-proposed but not taken,
  replay-labeled             = 0.6
counterfactual candidate     = 0.4
synthetic perturbation       = 0.1 (research only, NOT production)
```

### 2. Hierarchical Pooling

Do NOT train separate models per strategy initially.

Use one pooled model with:
- strategy_type one-hot
- strategy × regime interactions
- strategy × vol_edge interactions
- strategy × governor_uncertainty interactions

This lets IC/IB/PCS share information while preserving strategy differences.

### 3. Conservative Default

```
if strategy_n_qualified_examples < 30:
    max meta_size_cap = 0.25 for that strategy
    cannot enable new trades
    can only reduce or skip

if strategy_n_qualified_examples < 15:
    advisory only for that strategy
```

### 4. Prior-First Probability

Early V0.2 behaves like a calibrated scorecard with learning, not a confident ML oracle. **This is the central design choice.**

---

## 5. Confidence Calibration

### Method (V0.2)

Bayesian bucket calibration + bootstrap confidence bands.

NOT isotonic regression initially — overfits at small sample sizes.

### Calibration Buckets

Raw score binned into:
```
0.00-0.40
0.40-0.55
0.55-0.65
0.65-0.75
0.75-1.00
```

For each bin, maintain Beta posterior:
```
p_calibrated = (alpha + successes) / (alpha + beta + n)
```

Use posterior credible interval as confidence band.

### Future (300-500 Samples)

After sample size grows beyond 300-500, test Platt scaling. Use isotonic regression only after walk-forward validation shows it improves calibration.

### Monitoring

Track:
- Brier score
- Expected Calibration Error (ECE)
- Calibration by strategy
- Calibration by event class
- Calibration by score bucket
- Top-score realized utility

A score of 0.80 means: 80% estimated probability that U_strategy > 0. NOT merely 80% chance of any positive P&L.

---

## 6. Interaction Protocol

### Deterministic Arbiter Rule

```
final_size = min(
    constitutional_cap,
    rules_cap,
    governor_cap,
    meta_cap
)
```

Constitutional gates always dominate. Existing hard gates remain non-overridable.

### Three Canonical Cases

**Case 1: Meta-labeler 0.8 (high take), Governor veto.**
Result: skip trade.
Why: Governor handles novel event risk and admissibility. Meta-labeler is trained on historical analogs and can be confidently wrong out-of-distribution.
Log as: `high_meta_vs_governor_veto_disagreement`

**Case 2: Meta-labeler 0.3 (low take), rules engine proposes, Governor no objection.**
Result: skip (or 0.25x only if meta authority is reduced).
In production authority mode: skip.
Why: Rules engine proposes. Meta-labeler decides whether this specific proposal is worth taking.

**Case 3: Meta-labeler 0.6 (moderate), Governor caps at 0.5x, rules proposes full size.**
Result: `final = min(meta_cap, 0.5, 1.0)`
If meta 0.6 → meta_cap = 0.25, final is 0.25.
If meta 0.6 → meta_cap = 0.5, final is 0.5.

NO averaging. NO voting. Caps compose by minimum.

---

## 7. Size Translation

Use **lower confidence bound**, not point estimate.

```
p_hat = calibrated probability
p_low = lower bound of 80% confidence interval
ci_width = p_high - p_low

p_eff = p_low - drift_penalty - data_quality_penalty
```

V0.2 mapping:

| p_eff | Meta size cap |
|---|---|
| < 0.50 | 0 |
| 0.50-0.58 | 0.25 |
| 0.58-0.68 | 0.5 |
| ≥ 0.68 | 1.0 (only if extra conditions pass) |

Extra conditions for 1.0 sizing:
```
p_hat >= 0.75
ci_width <= 0.20
strategy_sample_count >= 30
calibration_ok = true
governor_uncertainty_score < 0.50
event_class = ordinary OR confirmed_post_event
data_quality_ok = true
```

Otherwise: cap at 0.5.

**Early V0.2:** cap meta-labeler at 0.5 max until calibration is proven.

---

## 8. Time-Bucket-Aware Priors

### Locked Time Buckets

```
open:         09:35-10:30
late_morning: 10:30-12:00
midday:       12:00-13:30
late:         13:30-14:30
exit_only:    after 14:30
```

The `exit_only` bucket does NOT enable new entries (constitutional time stops). Used for exit/marking/calibration only.

### Per-Bucket Priors with Cross-Bucket Sparse Pooling

```
Time buckets have separate priors
Authority degradation is per time bucket
But sparse time buckets still shrink to strategy-level parent
```

Practical sample-size caps:
```
if n_time_bucket < 20:
    cap meta_size at 0.25 for that bucket

if n_time_bucket < 10:
    advisory only for that bucket
```

If late-day calibration drifts but morning calibration is stable, degrade authority for late-day trades only — not all trades.

---

## 9. Drift Detection

### Four Drift Types

**1. Outcome Drift**
```
rolling_30_brier
rolling_50_brier
rolling_expected_calibration_error
top_bucket_realized_utility
```

Trigger warning if:
- Brier worsens >20% vs prior window
- ECE > 0.12
- Top score bucket has negative cumulative utility

**2. Calibration Drift**
```
predicted 0.70-0.80 bucket realizes below 0.55
for two rolling windows
```

Trigger: recalibrate buckets, reduce authority one step.

**3. Feature Drift (PSI)**
```
iv_rv_ratio distribution shift
skew_z distribution shift
governor_uncertainty distribution shift
strategy mix shift
time-of-day mix shift
```

Trigger: PSI > 0.25 on core features.

**4. Disagreement Drift**
```
meta_take_governor_veto_count
meta_skip_rules_take_count
meta_high_confidence_losses
```

### Authority Degradation (Statistically Rigorous)

For high-confidence bucket (p_take > 0.70):

```
window = rolling 30 qualified trades with p_take > 0.70
observed_loss_rate = losses / n
expected_loss_rate = mean(1 - p_take_i)
```

Trigger degradation only if:
```
Wilson_lower_95(observed_loss_rate, n) > max(1.5 * expected_loss_rate, expected_loss_rate + 0.10)
```

The `+0.10` absolute floor prevents overreacting at low expected loss rates.

### Degradation Scope

Apply degradation by scope first, escalating:
```
strategy × time_bucket first
global only if multiple buckets fail
```

So late-day IC degradation does NOT automatically punish morning PCS trades.

### Recovery

Mirror Item 5: minimum 30-session cooldown, then one-step recovery (advisory → reduced → normal) after demonstrated recalibration over 20 qualified signals.

---

## 10. Replay Validation

### Minimum Sample Sizes

| Authority Level | Required |
|---|---|
| Advisory mode | 50 labeled actual trades or candidates |
| Reduced authority | 100 actual/counterfactual labeled candidates AND ≥20 actual executed trades |
| Production skip/reduce | 200+ labeled candidates, 50+ actual trades, ≥20 in each enabled strategy |
| Full 1.0 sizing authority | 300-500 labeled candidates, 100+ actual trades, strategy-specific calibration passes |

### Validation Method

Walk-forward, NOT random split.

```
Train: weeks 1-6
Validate: week 7

Train: weeks 1-7
Validate: week 8

Train: weeks 1-8
Validate: week 9
```

### Required Promotion Gates

Meta-labeler can promote only if:
- Brier score beats hierarchical-prior baseline by ≥5%
- Expected Calibration Error ≤ 0.12
- Top probability bucket has positive cumulative utility
- Bottom probability bucket underperforms top bucket
- Max drawdown does not worsen
- Worst day does not worsen
- Trade retention ≥ 50%

NOT required: high AUC. AUC is secondary. Calibration and realized utility matter more.

### Day 1 V0.2 Authority

```
advisory or reduced authority only
can skip/reduce clear low-quality setups
cannot increase size
cannot enable long-vol live
cannot override Governor veto
```

---

## 11. Expected ROI Trajectory

| Period | Live Contribution | Authority |
|---|---|---|
| Months 1-3 | 0% (paper-only) | advisory / calibration |
| Months 4-6 | +1% to +3% | skip/reduce only |
| Months 7-12 | +3% to +7% | mature if validation passes |

### ROI Mechanism

Months 4-6 contribution from:
- Skipping weak IC/IB/PCS proposals
- Reducing size on uncertain proposals
- Avoiding trades where EV after slippage is poor

Months 7-12 upper range requires:
- Stable calibration
- Clear top/bottom bucket separation
- Positive strategy-specific utility
- No excessive false skips

### Underperformance Risks

Could underperform if:
- Labels are noisy
- Sample size remains too small
- Slippage estimates are wrong
- Governor already captures most bad trades (redundancy)
- Regime shifts faster than calibration
- Meta-labeler blocks too many ordinary profitable trades

---

## 12. Iran-Day Walkthrough

Rules engine proposes:
```
strategy: iron_butterfly
regime: pin_range
```

Features show:
```
event_class: geopolitical_shock
governor_uncertainty: high
signal_conflict: high
short_gamma_block_flag: true
event_day_short_gamma_flag (IB-specific): true
memory analogs: poor short-gamma outcomes
```

Meta-labeler likely outputs:
```
p_take: 0.15-0.30
confidence: medium
meta_size_cap: 0
reason_codes:
  - event_short_gamma_conflict
  - high_uncertainty
  - weak_pin_quality
  - poor_analog_outcomes
```

Even if the meta-labeler mistakenly outputs 0.80, the Governor veto still skips the trade. Belt-and-suspenders architecture: either system catching the failure is sufficient.

---

## 13. V0.2 Build Scope

**Build:**
- Strategy-specific utility label calculator
- Hierarchical Bayesian prior with smooth pooling
- Regularized logistic scorecard
- Memory analog evidence blender
- Bayesian bucket calibration with bootstrap CIs
- Time-bucket-aware prior structure
- Wilson-interval-based drift detection
- Authority degradation per strategy × time bucket
- Replay validation harness with walk-forward
- Iran-day-style canonical test cases

**Do not build in V0.2:**
- LightGBM as production authority (shadow only)
- Neural network meta-labeler
- Isotonic calibration
- Trade-generation logic
- Direct Governor override capability
- Sizing expansion above rules/Governor caps

---

## 14. Final Architectural Statement

The meta-labeler's job is **not to discover new alpha first**. Its job is to **reject weak rule-proposed trades with calibrated humility**. Once enough clean labeled data accumulates, it can become a stronger allocator. Until then, it behaves as a conservative, auditable filter.

The architectural keystone holds:
- AI controls admissibility and size ceilings, not trade execution
- Rules engine is the safety floor
- Constitutional gates are non-overridable
- Caps compose by minimum, never by averaging

---

*Spec produced through GPT-5.5 Pro + Claude collaboration over 2026-04-25. Locked after two rounds of iteration plus verification round. No code changes during specification.*
