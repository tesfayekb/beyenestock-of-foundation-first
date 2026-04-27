# Item 2: Strategy-Aware Attribution Schema — LOCKED SPECIFICATION

**Status:** 🔒 LOCKED
**Locked:** 2026-04-26
**Tier:** V0.1 Foundation (4-6 weeks)
**Architectural Role:** The label-quality substrate. Items 6 and 10 cannot produce calibration-grade training data without this.
**Sources:** Round 2 GPT-5.5 Pro design + Items 6/10 integration audit + Claude verification + GPT verification accept

---

## Architectural Commitment

**Item 2 is a label-quality layer.** Its purpose is to produce calibration-grade strategy-specific outcome labels so Items 5, 6, 7, 9, and 10 learn from correct strategy-specific outcomes instead of generic P&L.

**Do not let Item 2 become an observability vanity table.** A missed enum value, mutable path metric, or approximate-width row accidentally entering Item 6 training can do more ROI damage than having no attribution row at all.

---

## 1. Four-Table Architecture

```
trading_positions          → execution ledger only (existing)
trade_counterfactual_cases → case ledger: actual / counterfactual / synthetic (Item 10)
strategy_attribution       → strategy-aware outcome decomposition (NEW, this spec)
strategy_utility_labels    → Item 6 derived training labels (NEW, derived)
```

`trading_positions` remains the execution ledger — what was actually opened, what was closed, what the broker reported. Don't overload it with attribution.

`strategy_attribution` is a new table linked by `position_id` (when a trade exists) or `case_id` (when blocked). It's the authoritative source for strategy-aware outcome data.

`strategy_utility_labels` is derived from `strategy_attribution` via the EOD attribution engine. It's what Item 6's meta-labeler trains on.

---

## 2. strategy_attribution Schema

### Core Identity Fields

```sql
id UUID PRIMARY KEY
case_id UUID REFERENCES trade_counterfactual_cases(id)
position_id UUID NULL REFERENCES trading_positions(position_id)
decision_id UUID NULL REFERENCES ai_governor_decisions(decision_id)
meta_labeler_decision_id UUID NULL  -- references future Item 6 table
adversarial_decision_id UUID NULL   -- references future Item 7 table
candidate_id UUID NULL
```

### Decision and Case Type

```sql
decision_outcome TEXT NOT NULL CHECK (decision_outcome IN (
  'opened_traded',
  'blocked_governor',
  'blocked_meta_labeler',
  'blocked_adversarial',
  'skipped_rules',
  'blocked_constitutional',
  'halted_blocked_cycle',
  'synthetic_case'
))

case_type TEXT NOT NULL CHECK (case_type IN (
  'actual',
  'counterfactual',
  'synthetic'
))
```

**Critical mapping:**
- `opened_traded` → case_type = `actual`
- `blocked_*` → case_type = `counterfactual` (decision was actual, trade outcome is inferred)
- `synthetic_case` → case_type = `synthetic`

### Strategy Identity

```sql
strategy_hint TEXT NOT NULL  -- captured at decision time, not entry time
strategy_type TEXT NOT NULL CHECK (strategy_type IN (
  'iron_condor',
  'iron_butterfly',
  'put_credit_spread',
  'call_credit_spread',
  'debit_call_spread',
  'debit_put_spread',
  'long_call',
  'long_put',
  'long_straddle',
  'calendar_spread'
))

strategy_class TEXT NOT NULL CHECK (strategy_class IN (
  'neutral_short_gamma',
  'single_side_credit',
  'directional_debit',
  'long_vol_convex',
  'calendar'
))

strategy_structure JSONB NOT NULL  -- legs, strikes, quantities

structure_quality TEXT NOT NULL CHECK (structure_quality IN (
  'full',
  'approximate_width',
  'insufficient'
))
```

### Calibration Status (Critical Filter Fields)

```sql
simulation_status TEXT NOT NULL CHECK (simulation_status IN (
  'calibration_grade',
  'approximate_width',
  'insufficient_strategy_context',
  'legacy_observability_only'
))

calibration_eligible BOOLEAN NOT NULL DEFAULT false
attribution_schema_version INTEGER NOT NULL
label_version INTEGER NOT NULL
```

### Time and Market State

```sql
entry_at TIMESTAMPTZ NOT NULL
exit_at TIMESTAMPTZ NULL  -- NULL for blocked decisions
time_bucket TEXT NOT NULL CHECK (time_bucket IN (
  'open',
  'late_morning',
  'midday',
  'late',
  'exit_only'
))

entry_spx NUMERIC NOT NULL
exit_spx NUMERIC NULL
entry_vix NUMERIC NULL
exit_vix NUMERIC NULL
```

### Pricing and P&L

```sql
entry_credit NUMERIC NULL
entry_debit NUMERIC NULL
exit_mark NUMERIC NULL
gross_pnl NUMERIC NULL
slippage_estimate NUMERIC NULL
net_pnl_after_slippage NUMERIC NULL
max_risk NUMERIC NULL
realized_R NUMERIC NULL
```

### Path Metrics (Copied From closed_trade_path_metrics)

```sql
mae_R NUMERIC NULL
mfe_R NUMERIC NULL
pnl_path_vol NUMERIC NULL
peak_unrealized_pnl NUMERIC NULL
peak_unrealized_pnl_at TIMESTAMPTZ NULL
trough_unrealized_pnl NUMERIC NULL
trough_unrealized_pnl_at TIMESTAMPTZ NULL
profit_velocity NUMERIC NULL
max_loss_zone_proximity_peak NUMERIC NULL
max_loss_zone_proximity_twap NUMERIC NULL
```

These are COPIED from `closed_trade_path_metrics` at attribution time. Once copied, they are IMMUTABLE.

### Item 5 Integration (Volatility Fair-Value)

```sql
expected_move_dollars NUMERIC NULL
realized_move_dollars NUMERIC NULL
realized_vs_expected_ratio NUMERIC NULL
item5_snapshot_id UUID NULL
item8_snapshot_id UUID NULL  -- Item 8 OPRA flow snapshot
```

### Outcome Classification

```sql
outcome_mode TEXT NULL  -- per-strategy enum, see Section 4
failure_mode TEXT NULL  -- nullable compatibility field
exit_quality TEXT NULL
attribution_status TEXT NOT NULL CHECK (attribution_status IN (
  'pending',
  'complete',
  'partial',
  'failed'
))
```

### Strategy-Specific Metrics

```sql
strategy_metrics JSONB NOT NULL DEFAULT '{}'
```

Per-strategy fields stored here (see Section 3). GIN index for query performance.

### Data Quality and Contamination

```sql
data_quality_flags TEXT[] NOT NULL DEFAULT '{}',
CHECK (
  data_quality_flags <@ ARRAY[
    'intraday_vix_stale',
    'intraday_spx_stale',
    'options_chain_stale_at_entry',
    'options_chain_stale_at_exit',
    'greeks_unreliable',
    'slippage_high_uncertainty',
    'mark_to_market_failed',
    'opra_feed_disconnected_during_trade',
    'gex_calculation_failed',
    'quote_width_excessive',
    'path_metrics_incomplete'
  ]::TEXT[]
)

contamination_reason TEXT NULL,
CHECK (
  contamination_reason IS NULL OR contamination_reason IN (
    'pre_commit_4_pricing_pipeline',
    'pre_commit_2_gex_corruption',
    'pre_commit_3_pcs_credit_inversion',
    'manual_override_recorded',
    'data_feed_outage',
    'test_data',
    'unknown_legacy',
    'placeholder_pricing_used',
    'approximate_width_used'
  )
)
```

### Critical Database-Level Rule

```
TRIGGER: contamination_reason IS NOT NULL 
         → calibration_eligible MUST be false
```

Enforce via trigger or application accessor with database constraint backup. Even if developer bypasses application code, contaminated rows cannot be marked calibration_eligible.

### Superseding Rows (Audit History)

```sql
supersedes_attribution_id UUID NULL REFERENCES strategy_attribution(id)
is_current BOOLEAN NOT NULL DEFAULT true
```

When a material correction is needed:
1. Insert NEW row with corrected values
2. Set new row's `supersedes_attribution_id` = old row's id
3. Set old row's `is_current` = false
4. Old row preserved for audit; new row used for training

### Timestamps

```sql
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

---

## 3. Strategy-Specific Metrics (strategy_metrics JSONB)

All point/distance fields stored as **points**, not dollars. Multiply by index multiplier (SPX=100, XSP=10) at query time if dollar values needed.

### Iron Condor

```json
{
  "profit_zone_held": boolean,
  "breach_side": "none|put_side|call_side|both",
  "max_excursion_outside_zone_points": numeric,
  "short_gamma_stress_flag": boolean,
  "short_gamma_stress_twap": numeric,
  "credit_realized": numeric,
  "theta_capture_pct": numeric,
  "exit_quality": "string",
  "max_loss_zone_proximity_peak": numeric,
  "max_loss_zone_proximity_twap": numeric,
  "short_put_touch_count": integer,
  "short_call_touch_count": integer
}
```

**Definitions:**
```
profit_zone_held = all sampled SPX prices stayed between short_put and short_call

breach_side = put_side if any sample < short_put
              call_side if any sample > short_call
              both if both occurred
              none if zone held

max_excursion_outside_zone_points = max(
  short_put - min_spx_during_trade,
  max_spx_during_trade - short_call,
  0
)

theta_capture_pct = (entry_credit - exit_debit) / entry_credit
```

### Iron Butterfly

```json
{
  "body_strike": numeric,
  "pin_accuracy_distance_points": numeric,
  "pin_accuracy_time_weighted_points": numeric,
  "max_distance_from_body_points": numeric,
  "wing_stress_flag": boolean,
  "wing_stress_proximity_peak": numeric,
  "wing_stress_proximity_twap": numeric,
  "gamma_stress_score": numeric,
  "realized_move_points": numeric,
  "expected_move_points": numeric,
  "realized_vs_expected_ratio": numeric,
  "finish_outside_breakeven_flag": boolean
}
```

**Definitions:**
```
pin_accuracy_distance_points = abs(exit_spx - body_strike)

pin_accuracy_time_weighted_points = Σ abs(spx_t - body_strike) * dt / total_dt

realized_move_points = max(abs(spx_t - entry_spx)) during trade

expected_move_points = Item 5 expected move from entry to planned close

gamma_stress_score = composite proxy:
  time_weighted_distance_outside_breakeven 
  + wing_proximity_penalty 
  + realized_vs_expected_ratio_penalty
```

True `gamma_loss_dollars` requires reliable Greeks decomposition. Deferred to V0.2 with `gamma_stress_score` as V0.1 proxy.

### Put Credit Spread

```json
{
  "short_strike_breached": boolean,
  "downside_cushion_held_points": numeric,
  "closest_approach_to_short_strike_points": numeric,
  "adverse_move_speed_points_per_hour": numeric,
  "credit_adequate_flag": boolean,
  "vol_expansion_during_trade": numeric,
  "short_put_delta_peak": numeric,
  "downside_acceleration_flag": boolean
}
```

**Definitions:**
```
closest_approach_to_short_strike_points = min(spx_t - short_put_strike)
  positive = cushion held
  negative = breach

adverse_move_speed_points_per_hour = max rolling 5-minute downside move 
                                     annualized to hourly pace

credit_adequate_flag = entry_credit >= Item5 fair_credit_required
                       OR Item5 EV_after_slippage > 0

vol_expansion_during_trade = max(vix_t) / entry_vix - 1
```

### Call Credit Spread

Mirror of PCS for upside:
```json
{
  "short_strike_breached": boolean,
  "upside_cushion_held_points": numeric,
  "closest_approach_to_short_strike_points": numeric,
  "adverse_move_speed_points_per_hour": numeric,
  "credit_adequate_flag": boolean,
  "vol_expansion_during_trade": numeric,
  "short_call_delta_peak": numeric,
  "upside_acceleration_flag": boolean
}
```

```
closest_approach_to_short_strike_points = min(short_call_strike - spx_t)
```

### Debit Call Spread

```json
{
  "direction_correct": boolean,
  "magnitude_past_breakeven_points": numeric,
  "time_to_peak_minutes": integer,
  "time_to_peak_pct": numeric,
  "peak_capture_pct": numeric,
  "peak_capture_status": "valid|insufficient_mfe_for_ratio|unavailable_path_metrics",
  "theta_drag_estimate": numeric,
  "iv_change_estimate": numeric,
  "failed_direction_flag": boolean,
  "stall_after_entry_flag": boolean
}
```

**Definitions:**
```
direction_correct = max_spx_during_trade > entry_spx

magnitude_past_breakeven_points = max(0, max_spx_during_trade - breakeven)

peak_capture_pct = realized_pnl / mfe_pnl IF mfe_pnl >= max($20, 0.10R)
                   ELSE NULL

peak_capture_status:
  'valid' if mfe_pnl >= threshold
  'insufficient_mfe_for_ratio' if mfe_pnl < threshold
  'unavailable_path_metrics' if path data missing
```

`theta_drag_estimate` and `iv_change_estimate` are V0.2 (require reliable Greeks). V0.1 stores NULL.

### Debit Put Spread

Mirror:
```
direction_correct = min_spx_during_trade < entry_spx
magnitude_past_breakeven_points = max(0, breakeven - min_spx_during_trade)
```

### Long Call / Long Put

```json
{
  "direction_correct": boolean,
  "magnitude_points": numeric,
  "time_to_peak_minutes": integer,
  "peak_capture_pct": numeric,
  "peak_capture_status": "valid|insufficient_mfe_for_ratio|unavailable_path_metrics",
  "premium_decay_dollars": numeric,
  "extrinsic_decay_dollars": numeric,
  "exit_discipline": "peak_capture|half_capture|decay_loss|forced_close|manual_exit"
}
```

```
magnitude_points = call: max_spx - entry_spx
                   put: entry_spx - min_spx

extrinsic_decay_dollars = entry_extrinsic - exit_extrinsic
```

### Long Straddle

```json
{
  "realized_move_points": numeric,
  "implied_move_points": numeric,
  "realized_to_implied_ratio": numeric,
  "vol_expansion_flag": boolean,
  "entry_iv_richness_z": numeric,
  "exit_timing_quality": numeric,
  "peak_capture_pct": numeric,
  "peak_capture_status": "valid|insufficient_mfe_for_ratio|unavailable_path_metrics",
  "theta_bleed_flag": boolean,
  "move_after_exit_flag": boolean
}
```

```
realized_move_points = max(abs(spx_t - entry_spx)) during trade

implied_move_points = Item5 expected_move_to_close (preferred)
                      0.85 * entry_straddle_debit (fallback)

exit_timing_quality = realized_pnl / max(mfe_pnl, ε)
```

### Calendar Spread

```json
{
  "calendar_strike": numeric,
  "spot_proximity_to_strike_avg_points": numeric,
  "spot_proximity_to_strike_min_points": numeric,
  "term_structure_change": numeric,
  "front_iv_change_pct": numeric,
  "back_iv_change_pct": numeric,
  "pin_behavior_flag": "pinned|drifted|broke_away|unknown",
  "front_leg_decay_capture": numeric,
  "back_leg_mark_change": numeric
}
```

```
spot_proximity_to_strike_avg_points = Σ abs(spx_t - calendar_strike) * dt / total_dt

term_structure_change = front_iv_change_pct - back_iv_change_pct
```

---

## 4. outcome_mode Taxonomy (Per Strategy)

### Iron Condor

```
profit_target_hit
theta_decay_capture
direction_breach_put
direction_breach_call
range_breach_two_sided
vol_expansion_loss
late_gamma_loss
forced_close_1430
forced_close_halt
pricing_slippage_loss
operator_manual_exit
halt_day_blocked_cycle
unknown
```

### Iron Butterfly

```
pin_profit
theta_pin_capture
body_drift_loss
wing_stress_loss
trend_break_put
trend_break_call
event_short_gamma_loss
realized_move_exceeded_expected
forced_close_1430
forced_close_halt
pricing_slippage_loss
unknown
```

### Put Credit Spread

```
credit_capture
downside_cushion_held
downside_breach
downside_acceleration_loss
vol_skew_expansion_loss
insufficient_credit
forced_close_1430
forced_close_halt
pricing_slippage_loss
unknown
```

### Call Credit Spread

```
credit_capture
upside_cushion_held
upside_breach
upside_acceleration_loss
vol_skew_expansion_loss
insufficient_credit
forced_close_1430
forced_close_halt
pricing_slippage_loss
unknown
```

### Debit Call Spread / Debit Put Spread

```
directional_followthrough
direction_right_magnitude_short
direction_wrong
move_too_late
theta_decay_loss
iv_crush_loss
profit_target_hit
forced_close_1430
forced_close_halt
unknown
```

### Long Call / Long Put

```
directional_followthrough
direction_right_magnitude_short
direction_wrong
premium_decay_loss
iv_crush_loss
peak_capture
late_exit_giveback
forced_close_1430
forced_close_halt
unknown
```

### Long Straddle

```
realized_move_capture
vol_expansion_win
no_move_theta_decay
move_after_exit
iv_crush_loss
early_exit_missed_move
forced_close_1430
forced_close_halt
unknown
```

### Calendar Spread

```
pin_capture
term_structure_win
spot_drift_loss
front_iv_crush
back_iv_loss
term_structure_inversion_loss
broken_pin
forced_close_1430
forced_close_halt
unknown
```

### Blocked / Skipped Decisions (Universal)

```
useful_block_loss_avoided
costly_block_profit_missed
neutral_block
insufficient_context
halt_day_blocked_cycle
unknown_counterfactual
```

---

## 5. Decision_id Linkage Constraints

```
blocked_governor:
  decision_id REQUIRED (non-null)
  
blocked_meta_labeler:
  decision_id required if Governor was consulted
  meta_labeler_decision_id REQUIRED
  
blocked_adversarial:
  decision_id REQUIRED
  adversarial_decision_id REQUIRED
  
opened_traded:
  decision_id required if Governor was consulted
  nullable only for legacy rows or rules-only trades
  
skipped_rules:
  decision_id may be null (rules engine never consulted AI)
  
blocked_constitutional:
  decision_id may be null (constitutional gate fired before Governor)
  
synthetic_case:
  decision_id may be null
  
schema_version < governor_deployed:
  decision_id may be null (legacy)
```

This linkage enables Items 6 and 7 to learn relationships between Governor decision components (novelty_score, uncertainty_score, evidence_grade, retrieval_quality_score) and outcome_mode.

---

## 6. EOD Attribution Engine

### Job Specification

```
File: backend/eod_attribution_engine.py
Schedule: 16:35 ET (5 minutes after market close, allows late marks 
          and broker sync to settle)
Idempotent: safe to re-run on same day
Process date parameter: required (ISO date)
```

### Process Flow

**Phase 1: Opened/closed positions**
```
1. SELECT positions where exit_at on process_date AND no strategy_attribution
2. For each position:
   a. Fetch path metrics from closed_trade_path_metrics
   b. Fetch Item 5 snapshot
   c. Fetch Item 8 snapshot if present
   d. Compute strategy-specific metrics (per Section 3)
   e. Classify outcome_mode (per Section 4)
   f. INSERT INTO strategy_attribution
   g. If calibration_eligible: derive strategy_utility_labels row
   h. SET attribution_status = 'complete' or 'partial'
```

**Phase 2: Blocked decisions**
```
1. SELECT trade_counterfactual_cases for process_date with no attribution
2. For each blocked case:
   a. Require strategy_hint and strategy_structure (else skip)
   b. Compute counterfactual after-slippage outcome (Item 10 engine)
   c. Compute counterfactual outcome_mode
   d. INSERT INTO strategy_attribution with:
      - position_id = NULL
      - case_id = trade_counterfactual_cases.id
      - case_type = 'counterfactual'
      - decision_outcome = 'blocked_X'
      - exit fields populated from counterfactual computation
```

**Phase 3: Synthetic cases (weekly only, not daily)**
```
1. Run weekly Sunday EOD
2. INSERT case_type = 'synthetic' rows
3. calibration_eligible = false unless explicitly promoted via 
   research validation
```

### Idempotency Keys

```sql
UNIQUE(position_id) WHERE position_id IS NOT NULL
UNIQUE(case_id, label_version) WHERE position_id IS NULL
```

This allows label_version to bump (e.g., utility formula changes in V0.2) without duplicating actual trade rows.

### Failure Handling

```
Row failure:
  attribution_status = 'failed'
  error_reason captured in error_log JSONB field
  Operator alert
  Retry next run
  Never silently drop
```

---

## 7. Path Metrics Immutability

### Copy-On-Insert Rule

When EOD attribution runs:
```sql
INSERT INTO strategy_attribution (mae_R, mfe_R, peak_unrealized_pnl, ...)
VALUES (
  SELECT mae_R, mfe_R, peak_unrealized_pnl, ...
  FROM closed_trade_path_metrics
  WHERE position_id = X
)
```

Once inserted, strategy_attribution row is IMMUTABLE.

### Definition Changes (V0.2+)

If path metric definitions change:
```
1. NEW strategy_attribution rows use new computation
2. OLD rows keep original values
3. attribution_schema_version distinguishes them
4. Meta-labeler training queries filter by current schema_version 
   by default
```

### Material Corrections

If a row needs correction (e.g., bug discovered in computation):
```
1. INSERT new row with corrected values
2. Set new_row.supersedes_attribution_id = old_row.id
3. Set old_row.is_current = false
4. Training queries filter is_current = true
5. Old row preserved for audit
```

**Never UPDATE strategy_attribution rows after attribution_status = 'complete'.**

---

## 8. strategy_utility_labels Schema (Derived)

```sql
CREATE TABLE strategy_utility_labels (
  id UUID PRIMARY KEY,
  attribution_id UUID NOT NULL REFERENCES strategy_attribution(id),
  case_id UUID NOT NULL,
  position_id UUID NULL,
  strategy_type TEXT NOT NULL,
  utility_score NUMERIC NOT NULL,
  y_take BOOLEAN NOT NULL,
  label_version INTEGER NOT NULL,
  label_formula_version INTEGER NOT NULL,
  calibration_eligible BOOLEAN NOT NULL,
  reason_codes TEXT[],
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Item 6 Training Accessor

```sql
SELECT * FROM strategy_utility_labels
WHERE calibration_eligible = true
  AND label_version = (SELECT current_label_version FROM ai_governor_versions)
  AND utility_score IS NOT NULL
```

This filter MUST be enforced by Item 6's training accessor, not left to query-writer memory.

---

## 9. Index Strategy

```sql
PRIMARY KEY: id

UNIQUE PARTIAL:
  UNIQUE(position_id) WHERE position_id IS NOT NULL
  UNIQUE(case_id, label_version) WHERE position_id IS NULL

INDEXES:
  case_id
  decision_id
  position_id
  (strategy_type, entry_at DESC)
  (decision_outcome, entry_at DESC)
  (calibration_eligible, strategy_type, entry_at DESC)
  (outcome_mode, strategy_type)
  attribution_schema_version
  (time_bucket, strategy_type)
  is_current
  
GIN INDEX:
  strategy_metrics
  data_quality_flags
```

---

## 10. Computation Timing Reference

### Entry-Time Fields (populate at decision/entry)

```
strategy_hint (decision time, NOT entry time)
strategy_type
strategy_structure
decision_outcome
entry_spx
entry_vix
entry_credit / entry_debit
max_risk
time_bucket
item5_snapshot_id
item8_snapshot_id (if available)
expected_move_dollars
calibration_eligible (initial value)
attribution_schema_version
data_quality_flags (entry-time subset)
```

### Intraday Fields (position monitor)

Cadence: normal 60s, stress 15-30s

```
mae_R, mfe_R
peak_unrealized_pnl, trough_unrealized_pnl
pnl_path_vol
short strike touches
breakeven breaches
max loss zone proximity
pin distance over time
adverse velocity
spot proximity to calendar strike
```

Storage: compact path metrics + optional minute-level samples (~150-300 bytes per minute = 45-90 KB per 5-hour trade). Don't store tick-level paths.

### Close-Time Fields

```
exit_spx, exit_vix
exit_mark
gross_pnl, slippage_estimate
net_pnl_after_slippage
realized_R
exit_quality
theta_capture_pct (IC)
peak_capture_pct (debit/long strategies)
```

### Post-Close Fields (EOD attribution)

```
realized_move
realized_vs_expected_ratio
outcome_mode
failure_mode
strategy_utility_labels row creation
counterfactual usefulness classification (for blocked decisions)
attribution_status
```

### Backfill Rules

**Pre-Commit-4 contaminated rows:**
```
simulation_status = 'legacy_observability_only'
calibration_eligible = false
contamination_reason = 'pre_commit_4_pricing_pipeline'
```

**Can backfill (for diagnostics only):**
```
SPX path metrics
Rough MAE/MFE for operator review
```

**Cannot backfill as calibration-grade:**
```
entry credit/debit (pricing pipeline was wrong)
slippage-adjusted utility labels
strategy EV correctness
pricing-sensitive attribution
```

---

## 11. ROI Priority

### Highest ROI / Required for V0.1

These are load-bearing for learning velocity:
```
1. strategy_hint captured at decision time
2. full strategy_structure
3. net_pnl_after_slippage
4. MAE/MFE
5. breach/profit-zone flags
6. realized_vs_expected_ratio
7. calibration_eligible enforcement
8. outcome_mode
```

Ship these first.

### Medium ROI / V0.2 Acceptable

```
time-weighted pin accuracy
max loss zone proximity TWAP
adverse velocity
spot proximity TWAP
peak capture
path volatility
```

### Nice-to-Have / V0.2+ Optional

```
true gamma_loss_dollars
theta_drag_dollars
iv_change_dollars
full Greek decomposition
```

**Strong opinion: NULL is better than fake precision.** Store these only when data quality is good; otherwise NULL.

---

## 12. Integration With Other Items

### Item 5 (Volatility Fair-Value)

Provides:
- expected_move_dollars (entry-time snapshot)
- credit_adequate_flag computation input
- entry_iv_richness_z computation input

### Item 6 (Meta-Labeler)

Reads from strategy_utility_labels (derived from strategy_attribution).

Required fields:
```
utility_score
y_take
strategy_type
time_bucket
outcome_mode
net_pnl_after_slippage
realized_R
mae_R, mfe_R
breach flags
credit capture
realized_vs_expected_ratio
calibration_eligible
```

### Item 7 (Adversarial Review)

Reads adversarial_decision_id linkage to strategy_attribution.outcome_mode for evaluating adversarial value.

### Item 9 (Exit Optimizer)

Reads path metrics from strategy_attribution for forward-EV training.

### Item 10 (Counterfactual P&L)

Provides:
- counterfactual outcome computation for blocked decisions
- three-tier degradation classification (calibration_grade / approximate_width / insufficient_strategy_context)
- strategy_hint capture at decision time

---

## 13. New Future Strategies (Extensibility)

The hybrid schema extends to new strategies via:
```
strategy_type (add enum value)
strategy_class (assign to existing class)
strategy_structure JSONB (legs/strikes)
strategy_metrics JSONB (per-strategy fields)
outcome_mode taxonomy (extend per-strategy enum)
```

No table redesign required for:
```
broken-wing butterfly
ratio spreads
jade lizards
vertical rolls
```

---

## 14. Edge Cases

### Partial Fills

```
strategy_structure.legs[]:
  strike, right, qty, side, fill_price, fill_time

partial_fill_flag BOOLEAN
leg_mismatch_flag BOOLEAN
fill_quality_score NUMERIC
```

### Leg-By-Leg Early Exits

```
position_lifecycle = 'single_close' | 'partial_close' | 'legged_exit'

V0.1 marking:
  attribution_status = 'partial'
  calibration_eligible = false
  
V0.2 may add full legged-exit attribution support.
```

### Forced Closes and Halts

```
forced_1430_close_applied BOOLEAN
halt_exit_applied BOOLEAN
constitutional_exit_reason TEXT
```

Constitutional exits remain non-overridable (Item 1 rule).

---

## 15. V0.1 Ship Scope

### Required for V0.1

```
1. CREATE TABLE strategy_attribution (full schema)
2. CREATE TABLE strategy_utility_labels (derived schema)
3. Enum CHECK constraints on data_quality_flags and contamination_reason
4. Trigger enforcing contamination_reason → calibration_eligible = false
5. backend/eod_attribution_engine.py (16:35 ET schedule)
6. Strategy-specific metric computation per Section 3
7. outcome_mode classification logic per Section 4
8. Idempotency keys
9. Path metrics copy-on-insert
10. Integration with closed_trade_path_metrics
```

### V0.2 Defers

```
- True Greek P&L decomposition (gamma_loss_dollars, theta_drag_dollars)
- Legged-exit full attribution
- Cross-index extensibility (NDX, RUT, XSP)
- Material correction superseding-row workflow (UI)
```

### Never Build

```
- One table per strategy (creates migration overhead)
- Free-form data_quality_flags (invites inconsistency)
- Mutable strategy_attribution rows (corrupts audit history)
- Untyped outcome_mode (loses categorical learning signal)
```

---

## 16. Final Architectural Statement

**Item 2 protects the training layer from ambiguity.** A missed enum, mutable path metric, or approximate-width row accidentally entering Item 6 training does more ROI damage than having no attribution row at all.

The four-table architecture (trading_positions / trade_counterfactual_cases / strategy_attribution / strategy_utility_labels) separates execution from attribution from learning labels. Each layer has one job. Each layer's failures are contained.

The `calibration_eligible` filter is the single most important safety property. Enforced structurally (database trigger + application accessor + meta-labeler training accessor), it prevents contaminated, partial, or low-quality rows from corrupting the learning loop.

**The learning system will improve faster from correct simple labels than from unreliable sophisticated labels.**

---

*Spec produced through Round 2 GPT-5.5 Pro design + Items 6/10 integration audit + Claude verification + GPT verification accept on 2026-04-26. Locked after one full audit round plus verification. Substrate for Items 6, 7, 9, 10.*
