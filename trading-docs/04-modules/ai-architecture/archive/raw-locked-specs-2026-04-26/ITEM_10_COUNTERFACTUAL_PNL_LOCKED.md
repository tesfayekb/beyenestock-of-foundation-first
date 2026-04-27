# Item 10: Counterfactual P&L Attribution — LOCKED SPECIFICATION

**Status:** 🔒 LOCKED
**Locked:** 2026-04-25
**Tier:** V0.2 immediate / V0.2 strategy-specific / V0.3 adversarial / V0.4 exit (graduated)
**Sources:** Existing 12E implementation (commit 2400e98, shipped 2026-04-20) + GPT-5.5 Pro audit Round 1 + Claude verification + GPT verification accept
**Expected ROI contribution at maturity:** +6% to +15% indirect (multiplier on Items 5-9)
**Architectural role:** Calibration-grade attribution data feeding Items 5-9. Existing engine becomes legacy observability layer.

---

## Architectural Commitment

**Do not rewrite the current counterfactual_engine.py.** It works (9 passing tests) and serves real observability value. Instead, split into two layers:

```
Layer 1: Legacy Counterfactual Reporter (existing engine)
  - Basic no-trade P&L observability
  - Weekly missed-opportunity summaries
  - Operator dashboards
  - Health reporting
  - Output: legacy_observability_only, calibration_eligible = false

Layer 2: Calibration-Grade Attribution Engine (new)
  - Strategy-specific structures
  - Strategy-aware utility labels
  - Path-dependent metrics
  - actual/counterfactual/synthetic case typing
  - After-slippage P&L (training-grade)
  - Output: calibration_eligible = true (when conditions met)
```

**Critical principle:** Wrong labels are worse than missing labels. If the system learns from approximate widths, missing strategy context, or no-slippage counterfactuals, Items 5-9 will look smarter in replay than they are in live trading.

---

## 1. What Already Exists (DO NOT REWRITE)

### Shipped 2026-04-20 (Commit 2400e98)

```
backend/counterfactual_engine.py (349 lines, 9 tests)
  _fetch_spx_price_after_signal() → Polygon I:SPX 1-min at t+30
  _simulate_pnl()                  → 3 branches (short-gamma/long-gamma/generic)
  label_counterfactual_outcomes()  → EOD batch labeler
  generate_weekly_summary()        → Sunday report (gates >= 30 sessions)
  run_counterfactual_job()         → scheduler entry

Migration: 20260421_add_counterfactual_pnl.sql
  trading_prediction_outputs.counterfactual_pnl
  trading_prediction_outputs.counterfactual_strategy
  trading_prediction_outputs.counterfactual_simulated_at

Schedule:
  Daily 16:25 ET Mon-Fri (label no_trade rows)
  Weekly 18:30 ET Sunday (top-3 missed opportunities, gated >= 30 sessions)
```

### Architectural Properties (Preserve These)

- Pure observability (zero reads into trading-decision path)
- Fail-open at every layer (per-row try/except)
- Deterministic (no LLM)
- 30-session warmup gate on weekly reports

---

## 2. Three-Tier Spread Width Degradation

The hardcoded 5pt spread width is the most dangerous current behavior. Replacement uses explicit degradation tiers.

### Tier 1: Calibration-Grade

```
Conditions:
  strategy_hint exists
  AND strategy_structure exists (with actual strikes)

Behavior:
  Use actual strikes / width / credit / debit from strategy_structure
  Compute exact payoff from market path

Metadata:
  simulation_status = "calibration_grade"
  calibration_eligible = true
  width_source = "actual_strategy_structure"
  simulation_confidence = "high"
```

### Tier 2: Approximate

```
Conditions:
  strategy_hint exists
  BUT strategy_structure missing

Behavior:
  Use VIX_SPREAD_WIDTH_TABLE defaults for the strategy
  Note table version used

Metadata:
  simulation_status = "approximate_width"
  calibration_eligible = false
  width_source = "vix_default_table"
  width_table_version = <current version>
  simulation_confidence = "medium"
```

### Tier 3: Insufficient Context

```
Conditions:
  strategy_hint completely unavailable

Behavior:
  counterfactual_pnl = NULL
  Skip simulation entirely

Metadata:
  simulation_status = "insufficient_strategy_context"
  calibration_eligible = false
  width_source = "none"
  simulation_confidence = "none"
```

### Versioned Width Table

```
width_table_version
vix_bucket
strategy_type
time_bucket
default_short_delta
default_long_delta
default_width
```

When the table gets calibrated from real trade data, version increments. Historical Tier 2 rows know which approximation was used, enabling reproduction.

---

## 3. Strategy_hint Capture (CRITICAL)

**The most important single fix.** Without strategy_hint capture, every downstream calibration consumer learns from systematically wrong labels.

### Schema Addition

```sql
ALTER TABLE trading_prediction_outputs ADD COLUMN
  strategy_hint TEXT,
  strategy_structure JSONB,
  candidate_source TEXT;
```

### Capture Timing

Capture at **decision time, before no-trade filtering removes context**. The rules engine often computes a candidate strategy even when the final decision is no-trade. That candidate is what the counterfactual would have executed.

### strategy_structure Format

```json
{
  "strategy_type": "iron_condor",
  "short_put": 6970,
  "long_put": 6940,
  "short_call": 7040,
  "long_call": 7070,
  "entry_credit": 4.25,
  "width": 30,
  "dte": 0
}
```

### Replace Default-to-iron_condor Behavior

```
Current (DANGEROUS):
  if strategy_hint missing:
    default_strategy = "iron_condor"
    simulate using iron_condor logic

New:
  if strategy_hint missing:
    counterfactual_pnl = NULL
    simulation_status = "insufficient_strategy_context"
```

**Rationale:** Better to have NULL labels than systematically wrong labels.

---

## 4. New Tables

### trade_counterfactual_cases

Dedicated table for case-typed counterfactuals (replaces extending trading_prediction_outputs further):

```sql
CREATE TABLE trade_counterfactual_cases (
  id BIGSERIAL PRIMARY KEY,
  source_decision_id BIGINT REFERENCES trading_prediction_outputs(id),
  case_type TEXT,           -- actual | counterfactual | synthetic
  case_weight NUMERIC,      -- 1.0 | 0.5 | 0.2
  decision_timestamp TIMESTAMPTZ,
  strategy_type TEXT,
  strategy_structure JSONB,
  entry_snapshot JSONB,     -- market state at decision
  exit_policy_version TEXT,
  counterfactual_reason TEXT,  -- no_trade | governor_block | meta_skip |
                                -- adversarial_block | halt_block | alternative_strategy
  simulated_pnl_gross NUMERIC(10,2),         -- AUDIT ONLY
  estimated_slippage NUMERIC(10,2),
  counterfactual_pnl_after_slippage NUMERIC(10,2),  -- TRAINING-GRADE
  realized_R NUMERIC,
  max_risk NUMERIC,
  mae_R NUMERIC,
  mfe_R NUMERIC,
  simulation_status TEXT,
  simulation_confidence TEXT,
  width_table_version TEXT,
  label_version INTEGER,
  calibration_eligible BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### strategy_utility_labels

Item 6-specific labels, separate from raw P&L:

```sql
CREATE TABLE strategy_utility_labels (
  id BIGSERIAL PRIMARY KEY,
  case_id BIGINT REFERENCES trade_counterfactual_cases(id),
  strategy_type TEXT,
  utility_score NUMERIC,
  y_take BOOLEAN,
  
  -- Common metrics
  credit_capture NUMERIC,
  mae_R NUMERIC,
  mfe_R NUMERIC,
  
  -- Iron condor specific
  breach_flag BOOLEAN,
  max_loss_zone_proximity_peak NUMERIC,
  max_loss_zone_proximity_twap NUMERIC,
  
  -- Iron butterfly specific
  finish_outside_breakeven_flag BOOLEAN,
  wing_stress_flag BOOLEAN,
  event_day_short_gamma_flag BOOLEAN,
  
  -- PCS specific
  short_put_breach_flag BOOLEAN,
  downside_acceleration_flag BOOLEAN,
  
  -- Long straddle specific
  realized_vs_implied_move_ratio NUMERIC,
  theta_bleed_flag BOOLEAN,
  
  -- Debit spreads specific
  failed_direction_flag BOOLEAN,
  stall_after_entry_flag BOOLEAN,
  
  label_version INTEGER,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### closed_trade_path_metrics

Path-dependent metrics on executed trades (for Item 9 future use):

```sql
CREATE TABLE closed_trade_path_metrics (
  position_id BIGINT PRIMARY KEY REFERENCES trading_positions(id),
  peak_unrealized_pnl NUMERIC(10,2),
  peak_unrealized_pnl_at TIMESTAMPTZ,
  trough_unrealized_pnl NUMERIC(10,2),
  trough_unrealized_pnl_at TIMESTAMPTZ,
  mae_R_path NUMERIC,
  mfe_R_path NUMERIC,
  pnl_path_vol NUMERIC,
  profit_velocity NUMERIC,
  max_loss_zone_proximity_peak NUMERIC,
  max_loss_zone_proximity_twap NUMERIC,
  short_strike_touch_count INTEGER,
  breakeven_breach_count INTEGER,
  forced_1430_close_applied BOOLEAN,
  path_metrics_available BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### Optional: position_path_samples (only if needed)

```sql
CREATE TABLE position_path_samples (
  position_id BIGINT REFERENCES trading_positions(id),
  timestamp TIMESTAMPTZ,
  mark_pnl NUMERIC,
  pnl_R NUMERIC,
  spot NUMERIC,
  nearest_short_strike_distance NUMERIC,
  delta_snapshot JSONB
);
```

**Do NOT store tick-level paths.** Minute-level is enough for calibration and maintainable.

### Path Sampling Cadence

```
Normal: every 60 seconds
Stress: every 15-30 seconds (vol spike, short strike approach, large P&L move)
```

---

## 5. Slippage Modeling

### Two-Field Separation

```
simulated_pnl_gross               (AUDIT ONLY — never used for training)
counterfactual_pnl_after_slippage (TRAINING-GRADE — used by Items 5-9)
```

### Slippage Formula

```
estimated_slippage =
  base_strategy_slippage
  * time_multiplier
  * vol_multiplier
  * spread_multiplier
  * size_multiplier

Cap: estimated_slippage <= 3.0 * normal_strategy_slippage
```

### Component Definitions

**base_strategy_slippage:**
```
iron_condor        = 4 legs × half_spread_estimate
iron_butterfly     = 4 legs × half_spread_estimate
put_credit_spread  = 2 legs × half_spread_estimate
call_credit_spread = 2 legs × half_spread_estimate
long_straddle      = 2 legs × half_spread_estimate
debit_call_spread  = 2 legs × half_spread_estimate
```

**time_multiplier:**
```
Before 11:00 ET:    1.00
11:00-13:30 ET:     1.15
13:30-14:30 ET:     1.35
After 14:30 / forced close: 1.75
```

**vol_multiplier:**
```
1.0 + 0.25 * max(0, vix_z)
```

**spread_multiplier:**
```
1.0 + 0.30 * max(0, spread_z)
```

**size_multiplier:**
```
1.0 + 0.10 * max(0, contracts - 1)
```

### Training Rule

```
Items 5-9 utility labels use counterfactual_pnl_after_slippage
simulated_pnl_gross is audit-only
```

This prevents the meta-labeler failure mode where it learns to LOVE skipped trades that "would have made money on paper" but would have lost after costs.

---

## 6. API-Level Calibration_eligible Enforcement

**Filtering must be structural, not convention.**

### Required Function Signatures

```
get_meta_labeler_training_data():
  ALWAYS filters: calibration_eligible = true
  No way to disable except diagnostic_opt_in (explicit, noisy, logged)

get_vol_engine_replay_cases():
  Excludes legacy_observability_only by default
  Diagnostic mode requires diagnostic_opt_in = true

get_adversarial_block_outcomes():
  Excludes approximate_width AND legacy rows by default
  
get_exit_optimizer_training_paths():
  Requires calibration_eligible = true
  AND path_metrics_available = true
```

### Diagnostic Access

```
include_legacy = true
  - Must be explicit
  - Must log to audit table
  - Generates warning in monitoring
  - Used only for one-off diagnostic queries
```

### Old Rows Lockdown

```sql
UPDATE trade_counterfactual_cases
SET 
  label_quality = 'legacy_observability_only',
  calibration_eligible = false
WHERE created_at < <Commit_4_deploy_date>;
```

**Rationale:** Pre-Commit-4 contaminated data must never be used for training. The constraint must be in code, not documentation.

---

## 7. Halt-Day Blocked-Cycle Labeling

**Gap 2 fix:** When daily -3% halt fires, blocked cycles short-circuit before producing trading_prediction_outputs rows.

### New Capture Logic

```
On halt activation:
  Continue rules-engine candidate computation (without execution)
  Create row in trade_counterfactual_cases:
    case_type = "counterfactual"
    counterfactual_reason = "halt_block"
    strategy_hint = <whatever rules engine would have selected>
    strategy_structure = <if available>
    simulation_status = "pending_eod_label"
    
On EOD job:
  Label these rows with realized counterfactual P&L
```

**Rationale:** Without halt-day labeling, the engine cannot measure whether constitutional halts protect capital or block opportunity. This data is needed to validate the -3% halt threshold and the eventual adaptive halt threshold (Phase C from 12F).

---

## 8. Adversarial Review Attribution (V0.3)

For Item 7 calibration:

```
adversarial_trigger_id
adversarial_action: proceed | reduce | block | block_alert
adversarial_strength: 0.0-1.0
adversarial_cap: 0.0-1.0
final_operator_action
useful_block_flag (counterfactual outcome shows trade would have lost)
costly_block_flag (counterfactual outcome shows trade would have won)
latency_slippage_cost
adversarial_value (computed from useful/costly/value/latency components)
```

This data feeds Item 7's Wilson lower bound on useful_block_rate calculation.

---

## 9. Item 5 Vol Engine Validation

For Item 5's Baseline E vs F replay test:

```
Capture per decision:
  item5_predicted_ev (from strategy_ev_table)
  realized_counterfactual_utility (after slippage)
  prediction_error = realized - predicted
  vol_engine_authority_at_decision
  reliability_score_at_decision
```

**Critical:** The counterfactual labeler does NOT use Item 5's distribution machinery to compute outcomes. It uses realized market path. Item 5's distribution is what's being VALIDATED, not what's being used to validate.

---

## 10. Synthetic Case Generation

For Item 6's selection-bias mitigation:

### Real-World-Grounded Synthesis (NOT Random Perturbation)

```
Synthetic case generation procedure:
1. Identify historically-realized adverse events from past months
   (Iran days, Fed surprises, geopolitical shocks)
2. Replay those adverse contexts against current strategy logic
3. Produce labels of "what would happen if this adverse context 
   occurred today with current rules engine state"
4. Tag as case_type = "synthetic", weight = 0.2
```

**NOT recommended:** random perturbation within +/- 1 std of feature means. This produces synthetic cases without real-world grounding and risks teaching the model artifacts.

### Retrieval Rule (per Item 6 spec)

```
Top 12 analogs maximum
At least 7 actual cases when available
Maximum 3 synthetic cases
Synthetic cases inform reasoning but never count as live performance evidence
```

---

## 11. Migration Sequencing

### V0.2 Immediate (Ship Now — Low Risk)

```
1. Fix frontend health status write (Gap 4)
   counterfactual_engine.py adds write_health_status() calls
   
2. Fix Activation page builtStatus (Gap 5)
   useActivationStatus.ts: Counterfactual Tracking → 'live'
   
3. Add strategy_hint and strategy_structure capture
   ALTER TABLE migrations
   prediction_engine writes these at decision time
   
4. Stop defaulting missing strategy to iron_condor
   _simulate_pnl returns NULL with insufficient_strategy_context status
   
5. Add simulation_status / simulation_confidence / label_version
   ALTER TABLE migrations
   
6. Add halt-day blocked-cycle row creation
   risk_engine creates counterfactual rows on halt
   
7. Start path-dependent metrics capture on executed trades
   position_monitor writes closed_trade_path_metrics
   
8. Lock old rows: label_quality = legacy_observability_only
```

These are data integrity fixes. Ship before Items 5-9 begin training.

### V0.2 With Items 5/6 (Strategy-Specific)

```
9.  Strategy-specific simulators (replace generic _simulate_pnl)
10. trade_counterfactual_cases table
11. strategy_utility_labels table
12. counterfactual_pnl_after_slippage with full slippage model
13. Three-tier degradation logic
14. Realized-vs-predicted EV attribution (for Item 5)
15. API enforcement of calibration_eligible filtering
```

Ships when Items 5 and 6 are being built and need the data.

### V0.3 With Items 7/8 (Adversarial + OPRA)

```
16. Adversarial useful/costly block accounting
17. OPRA feature snapshot attached to counterfactual cases
18. Full-stack Baseline E vs F attribution hooks
19. Synthetic case generation (real-world-grounded)
```

Ships when Items 7 and 8 reach advisory mode.

### V0.4 With Item 9 (Exit Optimizer)

```
20. Static-vs-adaptive exit replay
21. Adaptive exit slippage model integration
22. Strategy-specific exit optimizer promotion metrics
23. Path-metrics consumption (data already capturing from V0.2)
```

Ships when Item 9 reaches V0.4 production gate.

---

## 12. Architectural Conflicts (Resolved)

### No Conflict

The current engine is deterministic, observability-only, and respects constitutional gates. These properties align with locked Items 5-9 architecture and are PRESERVED in the dual-layer split.

### Strategy Granularity (Resolved by Tier 1 simulators)

Current: short-gamma / long-gamma / generic (3 buckets)
Locked: strategy-specific simulators per Items 5-9 requirements

### Path Dependence (Resolved by capture starting now)

Current: t+30 SPX point-in-time only
Locked: full path metrics captured during V0.2, used by Item 9 in V0.4

### EV Validation (Resolved by Item 5 attribution)

Current: rough simulated P&L
Locked: predicted vs realized EV attribution per strategy

### Case Types (Resolved by trade_counterfactual_cases table)

Current: only no-trade rows
Locked: actual / counterfactual / synthetic with weights 1.0 / 0.5 / 0.2

---

## 13. Frontend And Health Fixes (Ship Immediately)

### Gap 4 Fix: Health Status Writes

```python
# In counterfactual_engine.py — add to all top-level functions

from health import write_health_status

def label_counterfactual_outcomes(redis_client):
    try:
        # ... existing logic ...
        write_health_status("counterfactual_engine", "ok", details={
            "rows_labeled": n,
            "calibration_eligible_count": k,
            "approximate_count": j,
            "null_count": m
        })
        return result
    except Exception as exc:
        write_health_status("counterfactual_engine", "error", 
                            last_error_message=str(exc))
        raise
```

### Gap 5 Fix: Activation Page

```typescript
// In useActivationStatus.ts

{
  name: "Counterfactual Tracking",
  builtStatus: 'live',  // was 'not_built'
  shippedDate: '2026-04-20',
  shippedCommit: '2400e98',
  description: 'Daily P&L attribution for no-trade signals'
}
```

These ship immediately, separate from larger upgrade. Low risk, fast validation, immediate operator value.

---

## 14. ROI Impact Ranking

### Highest ROI (Critical — Ship in V0.2 Immediate)

1. **strategy_hint + strategy_structure capture** (~+1% to +3% indirect)
   Without it, every downstream calibration is wrong.
   
2. **Stop defaulting to iron_condor** (~+1% to +2% indirect)
   Prevents systematic mislabeling.
   
3. **Three-tier spread width degradation** (~+1% to +3% indirect)
   Prevents short-gamma counterfactual bias.
   
4. **Halt-day blocked-cycle labeling** (~+1% to +2%)
   Validates whether halts protect or block.

### High ROI (Strategy-Specific — V0.2 With Items 5/6)

5. **Strategy-specific utility labels** (~+2% to +5% indirect)
   Item 6's training depends entirely on this.
   
6. **counterfactual_pnl_after_slippage** (~+1% to +3% indirect)
   Prevents inflated missed-opportunity learning.
   
7. **trade_counterfactual_cases table** (~+1% to +3% indirect)
   Enables actual/counterfactual/synthetic typing.
   
8. **API enforcement of calibration_eligible** (structural — prevents future contamination)

### Medium ROI (V0.3 With Items 7/8)

9. **Adversarial block attribution** (~+0.5% to +2%)
   Validates Item 7's blocks.
   
10. **Synthetic case generation** (~+1% to +2%)
    Reduces selection bias in meta-labeler.

### Later ROI (V0.4 With Item 9)

11. **Exit optimizer static-vs-adaptive ledger** (~+2% to +5% if Item 9 validates)
    Path metrics already capturing from V0.2 ensures data is available.

### Cosmetic (Ship Immediately)

12. **Frontend health + Activation page** (~0% direct)
    But improves operator trust and monitoring.

### Total Indirect ROI Contribution

Counterfactual P&L attribution multiplies the ROI of Items 5-9 by enabling correct calibration. Without it, those items would underperform by:
- Item 5: incorrect EV calibration → reduced engine value
- Item 6: wrong utility labels → meta-labeler trains on noise
- Item 7: false useful_block rates → premature deprecation OR over-trust
- Item 9: invalid path data → exit optimizer can't validate

Cumulative indirect ROI: **+6% to +15% beyond what Items 5-9 would achieve with current engine outputs.**

---

## 15. Final Architectural Statement

**The most important Item 10 fix is data eligibility enforcement.** Wrong labels are worse than missing labels. If the system learns from approximate widths, missing strategy context, or no-slippage counterfactuals, Items 5-9 will look smarter in replay than they are in live trading.

The architecture splits cleanly:
- **Legacy Counterfactual Reporter:** keeps doing what it does well (operator observability)
- **Calibration-Grade Attribution Engine:** serves Items 5-9 with correct strategy-aware after-slippage labels

The architectural commitments hold:
- AI controls admissibility and size ceilings, not trade execution
- Constitutional gates remain non-overridable
- Counterfactual engine is observability-only
- Caps compose by minimum (in trading flow, unaffected by Item 10)
- Calibration_eligible filtering is structural, not conventional

**Single most important rule:** Items 5-9 utility labels use `counterfactual_pnl_after_slippage`. Never `simulated_pnl_gross`. The naming convention enforces this.

---

*Spec produced through audit of existing 12E (commit 2400e98) + GPT-5.5 Pro Round 1 audit + Claude verification + GPT verification accept over 2026-04-25. Locked after one full round plus verification. No code changes during specification.*
