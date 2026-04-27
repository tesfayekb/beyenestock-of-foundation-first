# Item 4: Pre-V0.1 Replay Harness for Threshold Calibration — LOCKED SPECIFICATION

**Status:** 🔒 LOCKED
**Locked:** 2026-04-26
**Tier:** V0.1 Foundation (4-6 weeks)
**Architectural Role:** The promotion court. Calibration authority for Items 1, 5, 6. Research-only — never contaminates production.
**Sources:** Round 2 GPT-5.5 Pro design + Items 1/2/3/5/6 dependencies + Claude verification + GPT verification accept

---

## Architectural Commitment

**Item 4 is the promotion court. No replay reconstruction, no promotion.**

If the harness cannot reconstruct point-in-time pricing, model state, paths, and slippage cleanly, Items 1, 5, and 6 may still log or advise, but they do NOT get binding authority.

The replay harness is research-only infrastructure. It must NEVER:
- Enter production case memory
- Generate synthetic cases for live retrieval
- Influence live trading logic
- Become a generic backtester

It IS the empirical authority for promoting items from advisory to binding. Without rigorous validation, hand-set thresholds become the de facto policy — and hand-set thresholds will be wrong.

---

## 1. Reconstruction Logic

### Data Sources (Priority Order)

```
Supabase:
  trading_sessions
  trading_positions
  trading_prediction_outputs
  strategy_attribution
  trade_counterfactual_cases
  ai_governor_decisions
  model/version tables
  archived market snapshots if available

Polygon:
  SPX / I:SPX historical 1-min bars
  VIX historical
  news/events only if published_at <= replay timestamp

Tradier:
  archived option chains / marks / greeks if stored
  if no historical chain archive exists, chain-dependent 
  replay is NOT calibration-grade

Databento:
  historical OPRA replay
  GEX / flow reconstruction
  OPRA-derived features once Item 8 exists

Redis archives:
  only if Redis briefs were durably copied to Supabase
  raw Redis TTL state is NOT replay-safe
```

### Hard Rule: No Theoretical Pricing

```
No archived chain = no calibration-grade option pricing replay.
```

Do NOT reconstruct past option chains from today's chain or theoretical models and call it calibration-grade. If the chain isn't archived, reconstruction status is `quote_incomplete`, calibration_eligible = false.

### Commit 1 Correction — IC/IB target_credit

For each replay timestamp T:
```
1. Load historical option chain as of T.
2. Re-run corrected strike selector logic.
3. Build chain index: (strike, right) → (bid, ask, mid, quote_age, spread_pct)
4. Select IC/IB legs.
5. Compute:

iron_condor_credit = (short_put_mid - long_put_mid) 
                   + (short_call_mid - long_call_mid)

iron_butterfly_credit = (short_put_mid + short_call_mid) 
                      - (long_put_mid + long_call_mid)
```

If any required leg is missing:
```
reconstruction_status = quote_incomplete
calibration_eligible = false
```

NO placeholder fallback.

### Commit 2 Correction — Databento LTRIM / GEX

Do NOT use corrupted historical Redis GEX values.

Recompute GEX from raw historical Databento / chain data:
```
1. Load OPRA / chain snapshot available at T.
2. Apply corrected bounded-list / aggregation logic.
3. Recompute dealer gamma, net GEX, gamma wall, flip zone.
4. Store gex_reconstructed = true.
```

If raw OPRA or chain data unavailable:
```
gex_reconstructed = false
data_quality_flags += ['gex_calculation_failed']
case may be usable for non-GEX diagnostics
NOT calibration-grade for Governor/vol thresholds
```

### Commit 3 Correction — PCS/CCS spread credit

```
put_credit_spread_credit = short_put_mid - long_put_mid
call_credit_spread_credit = short_call_mid - long_call_mid
```

NEVER use short-leg mid alone. If long leg missing:
```
pricing_unavailable
NOT calibration-grade
```

### Commit 4 Correction — Re-mark + Slippage

```
entry_mark = historical chain mid at T
exit_mark = historical chain mid at simulated exit time
gross_pnl = strategy payoff from actual SPX path
estimated_slippage = strategy/time/VIX/spread/size model
net_pnl_after_slippage = gross_pnl - estimated_slippage
```

Rows with legacy NULL slippage are NOT used directly. Slippage must be replay-estimated.

### Impossible Reconstruction

Exclude from calibration if:
```
missing SPX bars
missing option chain at entry
missing required legs
missing exit mark
stale quote beyond tolerance
unknown strategy_structure
GEX required but unreconstructable
event/news source unavailable for event-sensitive test
```

Store as:
```
replay_status = diagnostic_only
calibration_eligible = false
```

**Wrong reconstruction is worse than exclusion.**

---

## 2. Calibration Order

Calibration must be ordered. Do not tune everything jointly.

### Step 0 — Reconstruction Validation (BINARY GATE)

Before tuning anything, reconstruction must pass four tests.

#### Test A: Pricing Reconstruction

For at least 100 sampled actual closed trades:
```
reconstructed_entry_credit/debit  vs  Commit-4-corrected re-marked value
```

PASS:
```
95% within $0.10
AND no systematic bias > $0.05
```

FAIL:
```
> 5% deviate by more than $0.10
OR bias > $0.05
```

#### Test B: SPX Path Reconstruction

For at least 50 sessions:
```
reconstructed 5-min SPX path  vs  Polygon-confirmed bars
```

PASS:
```
99% of bars match within 1 tick / rounding tolerance
```

#### Test C: VIX Reconstruction

For at least 50 sessions where archived VIX exists:
```
correlation > 0.99
max deviation < 0.50 VIX points
```

If archived VIX does not exist:
```
use Polygon historical VIX
mark archived_comparison_unavailable
do NOT fail solely for missing Redis archive
```

#### Test D: Slippage Estimation

For post-Commit-4 closed trades:
```
estimated_slippage  vs  actual / corrected slippage
```

PASS:
```
median absolute error < $0.10
absolute bias < $0.05
```

### Step 0 Failure Behavior

```
If ANY validation fails:
  no downstream calibration runs
  run marked failed
  operator must fix data/reconstruction before retry
```

Without explicit pass criteria, "reconstruction validation" becomes operator judgment. With them, binary test.

### Step 1 — Item 5 Vol Fair-Value

Calibrate first because Item 5 features feed Items 6 and 1.

Calibrate:
```
HAR-RV vs EWMA fallback
Student-t df by time bucket
option-strip / ATM fallback confidence
strategy EV table thresholds
late-day authority degradation
```

Do NOT calibrate long-vol authority until enough examples exist.

### Step 2 — Item 1 Governor Risk Score

Use frozen Governor outputs, NOT repeated LLM calls per parameter sample.

Calibrate:
```
risk_score component weights (5 components)
size_cap thresholds: 0.45 / 0.60 / 0.75
retrieval-quality penalties
short-gamma block thresholds
opportunity-lean disable thresholds
```

Search method: Latin-hypercube / coordinate search, NOT brute-force grids.

### Step 3 — Item 6 Meta-Labeler

Only after Items 5 and 1 features exist.

Calibrate:
```
Bayesian/logistic/memory blend weights
utility hurdle thresholds
hierarchical pooling k (test 10, 20, 40)
p_eff size mapping
calibration bins
```

Do NOT overfit k.

### Step 4 — Promotion Gates

**Promotion gates are evaluated, not optimized.**

Examples:
```
veto_value
useful_veto_rate
false_veto_cost
block_rate
worst-day impact
parse success
latency
```

These are pass/fail gates. Do NOT tune to pass them.

---

## 3. LightGBM Model State Policy (LOCKED PRECEDENCE)

```
1. Logged historical model artifact available
   → use it
   → calibration_grade eligible

2. Logged live predictions available
   → use logged p_bull / p_bear / confidence as source of truth
   → calibration_grade eligible for replay of historical decisions

3. Artifact missing, but exact training data + hyperparameters logged
   → reconstruct model
   → calibration_grade ONLY if prediction correlation > 0.95
      against logged outputs from same period

4. No artifact, no logged predictions, no exact training data
   → diagnostic only
   → NOT calibration_grade
```

### V0.1 Implication

```
If LightGBM state is not calibration-grade:
  Item 1 calibration paths that depend on ML confidence are BLOCKED
  Non-ML-only diagnostics may still run
  Binding Governor authority should not promote
```

Going forward, daily model artifacts AND prediction outputs must be versioned. Otherwise replay cannot faithfully reconstruct what the system knew at time T.

---

## 4. Infrastructure

### Tables

#### `replay_eval_runs`

Run-level metadata.

```sql
CREATE TABLE replay_eval_runs (
  run_id UUID PRIMARY KEY,
  run_type TEXT NOT NULL CHECK (run_type IN (
    'governor_threshold',
    'vol_engine',
    'meta_labeler',
    'full_stack',
    'prompt_challenger'
  )),
  environment TEXT NOT NULL DEFAULT 'research' 
    CHECK (environment = 'research'),
  code_version TEXT NOT NULL,
  data_version TEXT NOT NULL,
  config_version TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ NULL,
  status TEXT NOT NULL CHECK (status IN (
    'running', 'completed', 'failed', 'aborted'
  )),
  train_start DATE NOT NULL,
  train_end DATE NOT NULL,
  validation_start DATE NOT NULL,
  validation_end DATE NOT NULL,
  holdout_start DATE NOT NULL,
  holdout_end DATE NOT NULL,
  parameters_json JSONB,
  metrics_json JSONB,
  step0_validation_pass BOOLEAN NULL,
  step0_validation_details JSONB,
  failure_reason TEXT,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### `replay_eval_cases`

One row per reconstructed decision/snapshot/candidate.

```sql
CREATE TABLE replay_eval_cases (
  case_id UUID PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES replay_eval_runs(run_id),
  replay_timestamp TIMESTAMPTZ NOT NULL,
  as_of_timestamp TIMESTAMPTZ NOT NULL,
  source_decision_id UUID NULL,
  
  strategy_type TEXT,
  strategy_structure JSONB,
  
  market_state_card JSONB,
  feature_hash TEXT NOT NULL,
  
  governor_output JSONB,
  item5_snapshot JSONB,
  item6_output JSONB,
  
  baseline_action JSONB,
  candidate_action JSONB,
  realized_outcome JSONB,
  
  net_pnl_after_slippage NUMERIC,
  realized_R NUMERIC,
  max_drawdown_contribution NUMERIC,
  
  reconstruction_status TEXT CHECK (reconstruction_status IN (
    'calibration_grade',
    'approximate',
    'quote_incomplete',
    'gex_calculation_failed',
    'pricing_unavailable',
    'diagnostic_only'
  )),
  calibration_eligible BOOLEAN NOT NULL DEFAULT false,
  leakage_check_pass BOOLEAN NOT NULL DEFAULT false,
  data_quality_flags TEXT[] NOT NULL DEFAULT '{}',
  
  -- Prevents replay cases from leaking to production
  environment TEXT NOT NULL DEFAULT 'research' 
    CHECK (environment = 'research'),
  retrieval_enabled BOOLEAN NOT NULL DEFAULT false,
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Critical constraint:** environment defaults to 'research' and CANNOT be 'production'. retrieval_enabled defaults to false. This is structural enforcement that replay cases cannot enter production memory.

#### `replay_eval_results`

Calibrated parameter outputs.

```sql
CREATE TABLE replay_eval_results (
  result_id UUID PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES replay_eval_runs(run_id),
  item TEXT NOT NULL CHECK (item IN (
    'governor_v1', 'vol_engine_v1', 'meta_labeler_v1'
  )),
  parameter_set JSONB NOT NULL,
  train_metrics JSONB,
  validation_metrics JSONB,
  holdout_metrics JSONB,
  promoted BOOLEAN NOT NULL DEFAULT false,
  promotion_recommendation TEXT,
  reason TEXT,
  promotion_id UUID NULL,  -- links to item_promotion_records if promoted
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### `item_promotion_records`

The authority table. Items 1, 5, 6 read this at startup.

```sql
CREATE TABLE item_promotion_records (
  promotion_id UUID PRIMARY KEY,
  item_id TEXT NOT NULL,
  authority_level TEXT NOT NULL CHECK (authority_level IN (
    'production',
    'reduced',
    'advisory',
    'diagnostic_only',
    'disabled'
  )),
  authority_scope TEXT NOT NULL,
  thresholds JSONB NOT NULL,
  validation_metrics JSONB NOT NULL,
  failed_gates TEXT[] NOT NULL DEFAULT '{}',
  next_recalibration_due DATE NOT NULL,
  prompt_version_at_promotion TEXT NULL,
  model_version_at_promotion TEXT NULL,
  data_version_at_promotion TEXT NOT NULL,
  replay_run_id UUID NOT NULL REFERENCES replay_eval_runs(run_id),
  promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NULL,
  is_current BOOLEAN NOT NULL DEFAULT true,
  
  -- Constraint: production requires no failed gates
  CHECK (
    authority_level != 'production' 
    OR cardinality(failed_gates) = 0
  )
);

CREATE UNIQUE INDEX uq_promotion_current 
  ON item_promotion_records(item_id, authority_scope) 
  WHERE is_current = true;
```

Authority scopes per item:

```
governor_v1:
  short_gamma_veto
  all_strategy_veto
  capped_lean_paper

vol_engine_v1:
  short_gamma_filter
  strategy_ev_table
  long_vol_authority
  advisory

meta_labeler_v1:
  skip_reduce_production
  reduce_only
  advisory
```

**Startup behavior:**
```
Items 1, 5, 6 read item_promotion_records at startup.
If no current record exists for an item/scope:
  default to advisory or disabled, NEVER production.
```

This prevents items from inventing their own promotion status.

### Files

```
backend/replay_harness.py
  main orchestrator

backend/replay_data_reconstructor.py
  point-in-time data builder

backend/replay_feature_builder.py
  corrected feature transforms

backend/replay_decision_stack.py
  runs rules / Item5 / Governor / Item6 adapters

backend/replay_threshold_optimizer.py
  Latin-hypercube and coordinate search

backend/replay_leakage_guard.py
  timestamp-boundary validation

backend/replay_validator.py
  promotion gate evaluator

backend/replay_reporter.py
  summary report for operator
```

### Storage Estimate

```
1,500–5,000 replay cases per run
20–50 KB per compact case
≈ 75–250 MB per run

12 major runs/year ≈ 1–3 GB/year
```

Acceptable for Supabase if raw option chains are NOT stored inside replay_eval_cases.

Store: compact snapshots + hashes
Do NOT store: raw full chains, raw OPRA ticks, repeated LLM prompts

### Compute Estimate

**Critical principle:**
```
LLM Governor output is generated ONCE per decision card per prompt version.
Threshold search reuses stored structured outputs.
```

Do NOT call the LLM inside every Latin-hypercube sample.

```
decision cards: 200–1,000
LLM calls: 200–1,000 (once per prompt)
threshold samples: 100–300 (no-LLM offline samples)
wall clock: 1–4 hours per cycle
```

Item 5 Monte Carlo:
```
5,000 scenarios during search
10,000 scenarios for final validation
fixed random seed
vectorized simulation
```

---

## 5. Leakage Prevention

This is the most important part of Item 4.

### Timestamp Boundary

At decision time T, ALLOWED:
```
bars with close_time <= T
option quotes timestamp <= T
news where published_at <= T
calendar events known before T
model versions available at T
case memory with available_at <= T
```

FORBIDDEN:
```
future bars
future option marks
EOD P&L
post-close attribution
future Governor decisions
future synthetic cases
future corrected labels
news discovered after T
```

### Enforced Separation

Use two namespaces:

```
decision_inputs       → readable by decision stack ONLY
evaluation_outcomes   → readable by evaluator (decision_inputs + future realized path)
```

The decision stack code path can ONLY query decision_inputs. The evaluator can read both.

Without this separation, leakage happens by accident — code that should only read decision-time data accidentally reads outcome data because both are in the same query path.

### Retrieval Leakage

Every memory case has:
```
case_timestamp        (when did the trade/snapshot occur)
case_available_at     (when did this case become available for retrieval)
environment
retrieval_enabled
```

Replay retrieval query MUST use:
```sql
WHERE environment = 'production'
  AND retrieval_enabled = true
  AND case_available_at <= :as_of_timestamp
```

**Critical:** Use `case_available_at`, NOT `case_timestamp`. A trade from 9:35 AM might not have outcome attribution until 4:30 PM EOD attribution job. Using case_timestamp would leak attribution data.

### Rolling Features

All rolling features must assert:
```
max_source_timestamp <= T
```

**Required test:**
```
Add unit test with future sentinel row:
  Insert row with timestamp T+1.
  Recompute rolling feature for time T.
  ASSERT feature value unchanged.

If rolling feature changes after future sentinel insertion:
  feature builder FAILS unit test
```

### LightGBM Model State

Per Section 3 precedence. If reconstruction is required, must pass correlation > 0.95 against logged outputs.

For V0.1, every result must disclose:
```
model_state_source: 'logged_artifact' | 'logged_predictions' | 'reconstructed' | 'unavailable'
```

Going forward: log model artifacts daily.

---

## 6. Walk-Forward Methodology

Use rolling window, NOT expanding window.

**Reason:** 0DTE market structure drifts. Expanding windows over-weight stale regimes.

### Preferred Split

```
calibration window: 60 trading sessions
validation window: 20 sessions
holdout window: 20 sessions
step size: 10 sessions
```

### Graduated Authority by Sample Size

Based on **clean calibration-grade sessions** only:

```
N >= 90 sessions:
  full production eligibility
  60/20/20 split
  3+ walk-forward folds preferred

70–89 sessions:
  reduced production eligibility
  50/20/20 split
  2 folds minimum
  max authority = reduced / capped

50–69 sessions:
  advisory-only
  operator opt-in required
  NO binding authority

30–49 sessions:
  diagnostic-only
  no thresholds promoted

< 30 sessions:
  do NOT run calibration
```

**Critical:** "Full production eligibility" does NOT mean automatic production. The item still must pass its own promotion gates. Item 4 is the promotion court, not a rubber stamp.

### Walk-Forward Loop

```
for each fold:
  1. Fit/calibrate on calibration window
  2. Select parameters using validation window
  3. Score ONCE on holdout
  4. Store fold metrics
```

### Holdout Protection

Holdout data CANNOT enter:
```
feature scaling
case retrieval memory
synthetic coverage
threshold tuning
model retraining
```

Final promotion requires consistency across folds, NOT one lucky holdout.

---

## 7. Item 5 Baseline E vs F Specification

### Baseline E (Item 5 enabled)

```
full stack with Item 5 Vol Fair-Value Engine enabled
all Item 5 outputs fed to Items 1, 6 normally
```

### Baseline F (Item 5 neutralized)

Neutral default values:
```
iv_rv_ratio = 1.0
skew_z = 0.0
smile_asymmetry_score = 0.0
smile_width_score = 0.0
tail_width_score = 0.0
strategy_ev_table = neutral_equal_ev
vol_engine_confidence = 0.0
short_gamma_ev_warning = false
long_vol_edge_flag = false
late_day_vol_authority = neutral
```

Both Governor and Meta-Labeler receive these neutral values.

### Promotion Rule

```
E must beat F (NOT merely E beats rules-only)
```

Without F as baseline, Item 5's promotion could pass by stacking with rules-engine alpha that exists independently of the vol engine. E vs F isolates Item 5's marginal contribution.

---

## 8. Validation Criteria Per Item

### Item 1 Governor

**Minimum sample:**
```
200 decision cards
30 veto/reduce actions
20 trading sessions
```

**Promotion to paper-binding short-gamma veto:**
```
veto_value_after_slippage >= +2R cumulative
Wilson_lower_95(useful_veto_rate) >= 0.40
false_veto_cost <= 45% of avoided_loss
catastrophic_loss_capture_rate >= 60%
worst_day not worse than baseline
max_drawdown not worse than baseline
block_rate <= 35% (unless veto_value >= +4R)
```

**Operational gates:**
```
JSON parse success >= 99.5%
logical validation pass >= 99.0%
p95 routine latency <= 6 seconds
prompt frozen >= 10 trading days
```

**Sensitivity:**
```
±0.10 major weight change flips <= 15% decisions
```

If sensitivity fails: use more conservative thresholds OR keep advisory.

### Item 5 Vol Fair-Value

**Forecast gates:**
```
HAR-RV QLIKE >= 5% better than EWMA
OR fallback to EWMA
```

**EV gates:**
```
top EV bucket realized utility > bottom EV bucket
top-bottom gap positive in at least 70% of folds
no worsening of worst-day loss
Baseline E beats Baseline F
```

**Long-vol authority** (separate gate):
```
30+ clean long-vol candidates
positive expectancy after slippage
profit factor > 1.15
no theta-bleed cluster beyond threshold
```

If not met: Vol Engine ships as short-gamma risk filter / advisory only.

### Item 6 Meta-Labeler

**Minimum for advisory:**
```
50 labeled candidates
```

**Reduced authority:**
```
100 labeled candidates
20 actual executed trades
```

**Production skip/reduce:**
```
200 labeled candidates
50 actual trades
20 examples per enabled major strategy bucket
```

**Validation gates:**
```
Brier score beats hierarchical prior by >= 5%
ECE <= 0.12
top probability bucket positive cumulative utility
bottom bucket underperforms top bucket
max drawdown not worse
worst day not worse
trade retention >= 50%
```

**Confidence calibration:**
```
observed success rate falls within bootstrap 95% CI 
for major score buckets
```

If calibration fails: advisory only.

---

## 9. Strategy Sample Size Tiers

Use pooled calibration first.

### Strategy Groups

```
neutral_short_gamma:
  iron_condor, iron_butterfly

single_side_credit:
  put_credit_spread, call_credit_spread

directional_debit:
  debit_call_spread, debit_put_spread, long_call, long_put

long_vol_convex:
  long_straddle

calendar:
  calendar_spread
```

### Per-Strategy Authority

```
N < 15:
  diagnostic only

15 <= N < 30:
  advisory only

30 <= N < 40:
  pooled strategy-class calibration
  max size 0.25

40 <= N < 80:
  strategy-specific reduced authority
  max size 0.5

N >= 80:
  eligible for strategy-specific full calibration
```

**For rare strategies (calendar, long_straddle):**
```
do not ship unvalidated thresholds
paper/advisory only
```

Conservative defaults are acceptable. Fake calibration is not.

---

## 10. Pre-V0.1 vs Ongoing

### Pre-V0.1 Scope (Must Ship Before V0.1)

```
reconstructor
leakage guard
Item 5 replay validation
Item 1 risk-score threshold replay
Item 6 advisory calibration check
promotion report
item_promotion_records seeded
```

### Pre-V0.1 Exit Criteria

```
all replay cases tagged eligible / ineligible
no leakage test failures
reconstruction coverage report complete
Step 0 validation passed
Governor thresholds selected or marked advisory-only
Vol Engine authority level selected
Meta-labeler authority level selected
item_promotion_records populated for all items
```

### Failure Mode

```
If the replay harness cannot produce calibration-grade evidence:
  V0.1 ships advisory only
  All items default to authority_level = 'advisory' or 'disabled'
```

### Ongoing Schedule

**Weekly:**
```
drift report
veto value
false veto cost
calibration plots
reconstruction health
```

**Monthly:**
```
threshold recalibration candidate
champion/challenger prompt evaluation
Item 5 forecast-error review
```

**On Trigger:**
```
after model/prompt change
after data pipeline change
after 2 unexplained losses in 20 sessions
after veto value turns negative
after feature drift alert
```

### Prompt Versioning

```
challenger runs on captured historical cards
champion remains live
promotion only if challenger beats champion on replay + paper shadow
```

NO prompt goes live directly from intuition.

---

## 11. ROI Priority

### Most Load-Bearing Calibrations

```
1. Corrected pricing / slippage reconstruction
2. Governor short-gamma veto thresholds
3. Vol Engine short-gamma risk filter
4. Meta-labeler skip/reduce calibration
```

### Nice-to-Have

```
long-vol lean calibration
strategy-specific rare-strategy thresholds
fine-grained utility hurdle tuning
```

**Rule:** Do NOT delay V0.1 for rare-strategy calibration.

---

## 12. Conflict Resolutions

### Item 3 Conflict

Replay cases must NOT enter production synthetic memory.
```
Resolution: replay_eval_cases only
            environment = 'research' (CHECK constraint)
            retrieval_enabled = false (default)
```

### Item 2 / Item 10 Conflict

Legacy and approximate rows must NOT train models.
```
Resolution: training accessors require calibration_eligible = true
            simulation_status = calibration_grade
```

### Item 1 Conflict

LLM outputs are expensive if run inside every search.
```
Resolution: freeze outputs once per decision card per prompt version
            optimize deterministic thresholds offline
```

### Item 6 Conflict

Small-sample meta-labeler cannot be over-promoted.
```
Resolution: authority depends on sample size
            calibration failure = advisory only
```

---

## 13. V0.1 Ship Scope

### Required for V0.1

```
1. CREATE TABLE replay_eval_runs
2. CREATE TABLE replay_eval_cases (with environment CHECK constraint)
3. CREATE TABLE replay_eval_results
4. CREATE TABLE item_promotion_records (with current-record unique index)
5. backend/replay_harness.py main orchestrator
6. backend/replay_data_reconstructor.py with Commit 1-4 corrections
7. backend/replay_feature_builder.py with rolling-feature sentinel tests
8. backend/replay_decision_stack.py with frozen LLM output policy
9. backend/replay_threshold_optimizer.py (Latin-hypercube)
10. backend/replay_leakage_guard.py with dual-namespace enforcement
11. backend/replay_validator.py with Step 0 + per-item gate logic
12. backend/replay_reporter.py
13. Step 0 validation tests (4 binary checks)
14. Walk-forward implementation (rolling window)
```

### V0.2 Defers

```
- Adversarial replay scenarios (research only)
- Cross-asset feature replay (NDX/RUT)
- Operator UI for replay run review
- Automated weekly drift report dashboards
```

### Never Build

```
- Replay cases entering production memory (CHECK constraint enforced)
- Theoretical option chain reconstruction (no archived chain = no calibration)
- LLM calls inside parameter search loop (cost runaway)
- Expanding-window walk-forward (stale regime over-weighting)
```

---

## 14. Final Architectural Statement

**No replay reconstruction, no promotion.**

If the harness cannot reconstruct point-in-time pricing, model state, paths, and slippage cleanly, Items 1, 5, and 6 may still log or advise — but they do NOT get binding authority.

The replay harness is the empirical authority for promoting items from advisory to binding. Without it, hand-set thresholds become de facto policy. With it, every threshold has a defensible empirical basis.

**Item 4's value is preventing items from shipping with hand-tuned thresholds that nobody can defend empirically.** It is the difference between "this looks reasonable" and "this beats baseline by N% with Wilson lower bound > X across N folds."

The promotion-court framing is the architectural keystone: Item 4 doesn't make items work better, it forces items to prove they work before getting authority. Items that can't prove value in replay without leakage do not get binding authority. They may still ship as logging or advisory, but not as live decision-makers.

---

*Spec produced through Round 2 GPT-5.5 Pro design + Items 1/2/3/5/6 dependencies + Claude verification + GPT verification accept on 2026-04-26. Locked after one full audit round plus verification. Promotion court for Items 1, 5, 6.*
