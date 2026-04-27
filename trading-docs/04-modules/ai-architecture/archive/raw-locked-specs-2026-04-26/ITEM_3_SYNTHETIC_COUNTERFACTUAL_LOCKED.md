# Item 3: Synthetic Counterfactual Case Generation — LOCKED SPECIFICATION

**Status:** 🔒 LOCKED
**Locked:** 2026-04-26
**Tier:** V0.1 Foundation (4-6 weeks)
**Architectural Role:** Memory-coverage and selection-bias mitigation layer. NOT a training-label generator.
**Sources:** Cursor selection-bias surfacing + GPT Round 2 integration + Item 2 schema lock + Claude verification + GPT verification accept

---

## Architectural Commitment

**Synthetic cases are for retrieval coverage, not training truth.**

The system's case memory naturally accumulates records of contexts the system decided to engage with — actual trades and explicit blocked decisions. It does NOT accumulate records of contexts the system silently ignored. Over time, this creates selection bias: the LLM retrieves only "seen decision contexts," not the broader distribution of market states.

Item 3 fixes this by adding **coverage cases**:

```
actual cases:         what really happened
counterfactual cases: what would have happened under a precise alternate action
synthetic cases:      what market state existed but was not decision-sampled
```

**Critical commitment:** Synthetic cases remain `calibration_eligible = false` in V0.1 and V0.2. They are NEVER training data. They exist only to provide retrieval coverage and remind the Governor what the system ignored.

If a synthetic case becomes training-grade, it must be **reclassified** as a counterfactual replay case (with `case_type='counterfactual'` and full Item 10 three-tier degradation evaluation), not promoted while remaining synthetic.

---

## 1. Taxonomy of Cases

### A. Scheduled No-Trade Snapshots — V0.1 Scope

The most important V0.1 synthetic case category.

**Fixed Timestamps (5 per trading day):**
```
09:35 ET — post-open reality check; overnight thesis meets cash market
10:30 ET — first-hour trend/range character usually clearer
12:30 ET — midday theta/range/pin context
14:00 ET — late-day gamma and event continuation risk
15:00 ET — exit-only / late volatility context, not entry permission
```

These are **fixed base timestamps**, not adaptive. Adaptive timestamps would create selection bias of their own (events that happen often would be over-sampled).

**Optional Event Snapshots (V0.2+):**
```
FOMC/CPI/NFP release + 5 min
FOMC/CPI/NFP release + 30 min
large SPX move trigger
major news shock trigger
```

V0.1 ships only the five fixed timestamps. Event-driven snapshots are V0.2 research.

### B. Counterfactual Decision Variants — V0.1 Partial Scope

These are **counterfactual** cases (case_type='counterfactual'), NOT synthetic. Item 3 generates them; Item 10 evaluates them.

**Variant 1 — Actual trade opened, what if blocked? — V0.1 SCOPE**

Known outcome:
```
counterfactual_action = no_trade
counterfactual_pnl = 0
opportunity_cost = actual net_pnl_after_slippage
case_type = counterfactual
weight = 0.5
calibration_eligible = true (if actual outcome is calibration-grade)
```

This is the most useful counterfactual category. Actual P&L is known, no estimation required.

**Variant 2 — Trade blocked, what if allowed? — V0.1 SCOPE (conditional)**

Known only if:
```
strategy_hint exists
strategy_structure exists  
entry chain/marks available
exit policy known
market path available
slippage model available
```

If all available → Item 10 replay produces calibration-grade outcome. If structure missing → `simulation_status = insufficient_strategy_context`, `calibration_eligible = false`. If approximate width → `simulation_status = approximate_width`, `calibration_eligible = false`. (Follows locked Item 10 three-tier degradation.)

**Variant 3 — Alternative strategy — V0.1 SCOPE (strict)**

V0.1 rule:
```
Generate only if deterministic strategy selector can produce 
exact structure from same timestamp chain.
```

If exact structure unavailable, store only:
```
alternative_considered = true
outcome_status = unknown_context_only
```

NEVER estimate training P&L from vibes or analogs.

**Variant 4 — AI opposite decision — V0.1 SCOPE (conditional)**

```
Governor allowed → synthetic "Governor would have blocked"
Governor blocked → counterfactual "Governor would have allowed"
```

Only the "allowed" branch can have replayed P&L if precise strategy exists. The "blocked/no-trade" branch has known P&L = 0, opportunity_cost = actual/estimated trade result.

### C. Near-Miss Replay Cases — DEFERRED

V0.2+ research only. Logic like "similar-but-not-identical day would have proposed PCS instead of IC" is too easy to overfit. V0.1 already has sufficient coverage from blocked decisions, scheduled snapshots, and exact-alternative variants.

### D. Adversarial Examples — DEFERRED to V0.2/V0.3 research

Do NOT insert fabricated cases ("Iran day but bullish") into production memory in V0.1. Useful for stress tests, NOT retrieval memory.

V0.2+ storage:
```
replay_stress_tests
adversarial_eval_cases
```

NEVER:
```
production ai_case_memory
```

False event cases pollute the Governor's prior.

---

## 2. Generation Logic

### Scheduled Snapshots: Daily Capture, Weekly Insertion

Reconciles two requirements:
- Capture point-in-time market state (live, real-time)
- Item 2 spec: synthetic cases generated weekly Sunday EOD

**Live Capture Table:** `synthetic_snapshot_staging`

**At Each Fixed Timestamp:**

```
1. Run live-capture data quality validation (Section 3)
2. If validation passes:
   - Build compact point-in-time market snapshot
   - Run rules engine in shadow mode (no execution)
   - If AI deployed: run Governor/meta in shadow mode
   - Store feature_hash and market_state_card_hash
   - Mark retrieval_candidate = true (pending weekly validation)
3. If validation fails:
   - Capture compact snapshot with data_quality_flags
   - Mark retrieval_eligible_pending = false
   - Mark diagnostic_only = true
```

**Sunday EOD Generation:**

```
1. Load all weekly snapshots from synthetic_snapshot_staging
2. Apply duplicate suppression (Section 4)
3. Validate data quality (Section 5)
4. Attach realized market outcome:
   - realized_move_to_close
   - realized_vol_to_close
   - trend/range/event realized label
   - breached key strikes
5. INSERT INTO strategy_attribution:
   case_type = 'synthetic'
   decision_outcome = 'synthetic_case'
   calibration_eligible = false
   strategy_metrics JSONB stores snapshot details
6. position_id = NULL
   exit_at = NULL
   net_pnl_after_slippage = NULL
   outcome_mode = 'synthetic_market_context'
```

NO fake trade label. Synthetic cases capture market context, not trade outcomes.

### Counterfactual Variants: EOD Generation, Not Intraday

For every actual or blocked decision:

```
1. Load decision record from ai_governor_decisions
2. Load strategy_hint and strategy_structure
3. Check if exact replay is possible (Item 10 three-tier degradation)
4. If exact replay possible:
   - Simulate under static exit policy using realized path
   - Apply strategy-specific slippage
   - Store after-slippage result
   - simulation_status = 'calibration_grade'
   - calibration_eligible = (true if actual was calibration-grade)
5. Else:
   - Store unknown or approximate status
   - simulation_status = 'insufficient_strategy_context' or 'approximate_width'
   - calibration_eligible = false
6. INSERT INTO trade_counterfactual_cases
7. INSERT INTO strategy_attribution if attribution-grade or observability useful
```

**Outcome Status Enum:**
```
known_replay              → calibration_grade
approximate_replay        → approximate_width
unknown_context_only      → insufficient_strategy_context
analog_estimate_research  → V0.2+ research only, not training
```

Only `known_replay` is training-grade. Analog-based estimates are NEVER training labels.

---

## 3. Live-Capture Validation

At each scheduled snapshot timestamp, run data freshness checks:

```
polygon_vix_age_seconds < 60
tradier_chain_age_seconds < 30
gex_engine_confidence > 0.50
spx_realtime_age_seconds < 10
redis_required_briefs_present = true
market_state_card_build_success = true
```

**If ALL pass:**
```
capture full snapshot
retrieval_eligible_pending = true
diagnostic_only = false
```

**If ANY fail:**
```
capture compact snapshot
populate data_quality_flags (per Item 2 locked enum)
retrieval_eligible_pending = false
diagnostic_only = true
calibration_eligible = false
```

**Allowed data_quality_flags** (from Item 2 lock, reused):
```
intraday_vix_stale
intraday_spx_stale
options_chain_stale_at_entry
greeks_unreliable
slippage_high_uncertainty
mark_to_market_failed
opra_feed_disconnected_during_trade
gex_calculation_failed
quote_width_excessive
path_metrics_incomplete
```

**Weekly Generator Rule:**
```
Only retrieval_eligible_pending = true rows can become 
retrieval_enabled = true.
```

Diagnostic-only rows remain useful for operator review but never enter production retrieval memory.

---

## 4. Duplicate Suppression

**Default Window:** ±2 minutes

If real decision exists within ±2 minutes of snapshot timestamp:
```
do not insert scheduled synthetic snapshot as retrieval-enabled
attach scheduled_snapshot_reference to the real decision
```

**High-Volatility Tightening:**
```
if VIX > 25 OR abs(SPX 5-minute return) > 0.40%:
    duplicate window = ±1 minute
```

**Rationale:** A real decision has richer attribution than a synthetic context snapshot. But we should not discard the captured snapshot entirely — preserve it as a reference for auditing.

The 0.40% threshold (not 0.50%) is correct for SPX 0DTE. At SPX 7100, 0.40% = ~28 points, which can move iron condor positions through breakeven zones.

---

## 5. Quality Validation

### Data Quality

Reject from retrieval if:
```
SPX stale
VIX stale
options chain stale
Market State Card failed
feature_hash missing
critical data freshness warning
```

Store as diagnostics only. Never delete.

### Plausibility

For observed snapshots, extreme markets are allowed because they actually happened.

For generated variants, require:
```
SPX move assumption within observed historical distribution
no fabricated macro/event label
no strategy outside allowed strategy map
no impossible timestamp
no post-close data leakage
```

### Strategy-Regime Consistency

Reject alternative strategy variants if:
```
strategy not in regime strategy map
strategy disabled by constitutional gate
strategy requires data not available at timestamp
defined-risk structure cannot be built from chain
```

### Event Accuracy (Hard Rule)

```
Do not create CPI/FOMC/geopolitical event labels unless event 
source confirms it.
```

Synthetic events are stress tests, NOT production memory.

### Drop vs Flag Decisions

```
invalid/generated impossible case → drop
real snapshot with data gaps → store diagnostics, retrieval_enabled = false
approximate structure → store observability, calibration_eligible = false
valid synthetic snapshot → retrieval_enabled = true, calibration_eligible = false
```

---

## 6. Weighting

### Locked Weights (V0.1)

```
actual = 1.0
counterfactual = 0.5
synthetic = 0.2
operator_override = 0.3 (overlay, not separate type)
```

**These are not magic truth weights. They express evidence reliability:**
```
actual:           real fill, real path, real P&L
counterfactual:   real market path, modeled fill/exit/slippage
synthetic:        real market state, no precise trade outcome
operator_override: real expert judgment, subjective context
```

**Objective:**
```
reduce retrieval selection bias
without letting non-executed/non-real cases overpower actual history
```

**Effects:**
```
- retrieval ranking
- memory summary statistics  
- case analog features
```

**Restriction:**
```
Weights NEVER let synthetic rows enter Item 6 training by default.
```

### V0.2 Sensitivity Test

Before V0.2 promotion, replay-test:

```
A: 1.0 / 0.3 / 0.1
B: 1.0 / 0.5 / 0.2  ← V0.1 starting choice
C: 1.0 / 0.7 / 0.3
```

Score by:
- Governor veto value
- false veto cost
- retrieval coverage improvement
- meta-labeler calibration
- no increase in worst-day loss

---

## 7. Retrieval Impact

### Locked Retrieval Rule

```
retrieved_analogs:
  top 12 analogs maximum
  max synthetic = 3
  max counterfactual = 4
  max operator_override = 2
  actual target = 7 when available
```

### Retrieval Fill Logic

```
1. Pull actual cases first
2. Add counterfactual cases if useful
3. Add operator_override cases if relevant
4. Add synthetic cases last
5. If not enough actuals exist, return fewer than 12 rather 
   than overfill with synthetic
```

### Sparse-Strategy Coverage Notes

For new strategies with very few actuals:

```
if actual_similar_count < 5
AND retrieval_quality_score < 0.50:
    normal top-12 still max synthetic = 3 (UNCHANGED)
    additionally attach up to 2 synthetic_coverage_notes
    retrieval_quality_low = true
    Governor uncertainty += 0.05
```

**Coverage notes are context appendices, not full analogs.**

```
retrieved_analogs:
  max 12, max 3 synthetic, max 4 counterfactual, max 2 operator_override

coverage_notes:
  max 2 synthetic, low weight, clearly labeled as "context only"
```

This avoids overfilling the analog set with fake evidence while still surfacing coverage gaps. Scarce actuals produce uncertainty acknowledgment, not synthetic confidence.

### Storage Cost

```
5 snapshots/day × 252 trading days = 1,260 synthetic rows/year
plus counterfactual variants (estimated few thousand/year)
plus operator overrides (variable)
```

pgvector handles this trivially. Store compact embedded summaries, not raw snapshots.

### Retrieval Scoring

```
case_retrieval_score = 
    cosine_similarity 
  * case_weight 
  * schema_quality_factor 
  * recency_factor
```

**Schema_quality_factor** uses Item 1 locked formula:
```
1.00 = current schema + calibration_eligible = true
0.70 = prior schema but calibration_eligible = true
0.40 = approximate / non-training-eligible but useful
0.00 = pre-Commit-4 contaminated
```

Synthetic cases (`calibration_eligible = false`) get schema_quality_factor = 0.40 max. They will rarely dominate top analog lists.

---

## 8. Operator Override Overlay

**Critical architectural decision:** operator_override is NOT a fifth case_type. It's an overlay on existing case_types (actual / counterfactual / synthetic).

**Reasoning:** Items 2 and 10 locked the core evidence taxonomy as three values. Adding a fourth would break API surface and calibration_eligible enforcement. Operator overrides apply orthogonally to evidence type.

### Overlay Fields

```sql
operator_override_flag BOOLEAN NOT NULL DEFAULT false
operator_action TEXT NULL CHECK (operator_action IN (
  'skip_session',
  'skip_trade',
  'reduce_size',
  'override_block',
  'manual_halt',
  'force_exit',
  'resume_after_halt'
))
operator_reason TEXT NULL
operator_confidence TEXT NULL
operator_timestamp TIMESTAMPTZ NULL
operator_user TEXT NULL
operator_case_weight NUMERIC NOT NULL DEFAULT 0.3
```

### Application Examples

```
actual + operator_override:
  operator manually reduced size, trade still opened
  case_type = 'actual', operator_override_flag = true
  
counterfactual + operator_override:
  operator manually skipped a trade that system wanted
  case_type = 'counterfactual', operator_override_flag = true
  
synthetic + operator_override:
  operator skipped entire session
  case_type = 'synthetic', operator_override_flag = true
```

### Eligibility

```
calibration_eligible = false (subjective, not training-grade)
retrieval_eligible = true (operator wisdom is valuable context)
```

### Quality Filter

If operator notes are emotionally subjective or vague:
```
retrieval_enabled = false
diagnostic_only = true
```

**Acceptable operator reasons:**
```
"Manual halt due to unscheduled geopolitical headline; data feeds lagging."

"Reduced size because bid/ask widened beyond normal despite valid model signal."
```

**Not suitable for retrieval:**
```
"Did not feel good."
"Busy today."
```

---

## 9. Promotion Criteria

### Synthetic → Training NEVER (V0.1, V0.2)

**Locked rule:** Synthetic cases do not enter Item 6 training in V0.1 or V0.2.

### Retrieval Promotion (Synthetic → Retrieval-Enabled)

A synthetic case becomes retrieval-enabled if A/B replay shows:

```
retrieval coverage improves
Governor veto value does not worsen
false veto cost does not worsen
LLM rationales do not over-anchor on synthetic analogs
synthetic share in top-12 stays within cap (≤ 3)
```

### Training Promotion (Synthetic → Counterfactual Reclassification)

Only allowed if the case is **reclassified**:
```
synthetic → counterfactual
```

Possible only when exact structure and realized replay become available later.

After reclassification, must satisfy:
```
simulation_status = 'calibration_grade'
calibration_eligible = true
after-slippage P&L exists
strategy utility label exists
no contamination_reason
```

**Operator approval required** for any rule that promotes synthetic-origin cases into training.

### Demotion

```
if synthetic retrieval worsens veto value, calibration, or false-veto cost:
    retrieval_enabled = false
    keep row for audit (never delete)
```

---

## 10. Replay Harness Separation

**Critical rule:** Replay harness cases must NEVER be production synthetic cases.

### Separate Storage

```sql
replay_eval_runs
replay_eval_cases
```

Or at minimum:
```
source = 'replay_harness'
retrieval_enabled = false
calibration_eligible = false
environment = 'research'
```

### Production Retrieval Filter

```
WHERE environment = 'production'
  AND retrieval_enabled = true
```

The replay harness can generate synthetic-like reconstructions, but those are evaluation artifacts. They must NEVER appear in live Governor memory.

This is critical because replay can contain many reconstructed alternatives, which would swamp true production memory if mixed.

---

## 11. Selection-Bias Quantification

### Definition

```
selection_bias = distribution(memory_cases) ≠ distribution(market_states_seen_by_system)
```

Across major buckets:
```
time_bucket
rules_regime
event_class
volatility_bucket
trend/range realized outcome
strategy_eligibility
data_quality_state
```

### Detection Test

Build two distributions:
```
A = all scheduled market snapshots (the "ground truth" sample)
B = actual + counterfactual + retrieval-enabled memory cases
```

Measure:
```
Jensen-Shannon divergence (A, B)
bucket coverage ratio per major bucket
underrepresented bucket count
propensity score: P(case_in_memory | market_features)
```

### Warning Thresholds

`selection_bias_warning` fires if ANY:
```
JS divergence > 0.10
major bucket coverage < 60%
propensity model AUC > 0.65
```

### Action on Warning (V0.1)

```
warning only — not action
weekly review required
synthetic coverage continues
no direct trading authority change
```

If persists for 4+ weeks:
```
increase synthetic coverage monitoring
review rules proposal thresholds
review whether no-trade states are underrepresented
```

### Validation That Synthetic Cases Reduce Bias

Compare retrieval with and without synthetic cases:

```
retrieval_coverage_JS
bucket coverage ratio
Governor veto value
false veto cost
catastrophic-loss capture
meta-labeler calibration
LLM rationale quality
```

**Synthetic mechanism passes if:**
```
coverage JS improves by ≥ 25%
AND veto value does not worsen
AND false veto cost does not increase by > 10%
AND synthetic cases do not exceed retrieval caps
```

**Expected magnitude:**
```
direct ROI: small, maybe +0.5% to +2%
learning velocity / calibration value: meaningful
```

**Honest framing:** Item 3 is NOT a primary alpha engine. It prevents memory overfitting.

### Drop Criteria

Disable synthetic retrieval if:
```
Governor veto value worsens over replay
false veto cost increases materially
LLM overuses synthetic analogs in rationale
retrieval quality falls
synthetic cases appear in top analogs too often
meta-labeler calibration worsens
```

When dropped:
```
keep capture running
retrieval_enabled = false
preserve rows for audit (never delete)
```

---

## 12. Schema Extensions to strategy_attribution

These fields are added to Item 2's locked strategy_attribution table:

### Synthetic Snapshot Fields

```sql
-- For case_type = 'synthetic' rows
shadow_strategy_hint TEXT NULL
shadow_strategy_structure JSONB NULL  
shadow_reject_reason TEXT NULL
realized_move_to_close NUMERIC NULL
realized_vol_to_close NUMERIC NULL
realized_outcome_label TEXT NULL CHECK (
  realized_outcome_label IN ('trend_up', 'trend_down', 'range', 'event', NULL)
)
breached_key_strikes BOOLEAN NULL
```

### Operator Override Overlay Fields

```sql
operator_override_flag BOOLEAN NOT NULL DEFAULT false
operator_action TEXT NULL  -- enum per Section 8
operator_reason TEXT NULL
operator_confidence TEXT NULL
operator_timestamp TIMESTAMPTZ NULL
operator_user TEXT NULL
operator_case_weight NUMERIC NOT NULL DEFAULT 0.3
```

### Coverage Note Fields

```sql
coverage_note BOOLEAN NOT NULL DEFAULT false
coverage_note_reason TEXT NULL
```

### Live-Capture Staging Reference

```sql
staging_capture_id UUID NULL  -- links to synthetic_snapshot_staging
scheduled_snapshot_reference UUID NULL  -- for actual decisions that absorb a snapshot
```

---

## 13. New Table: synthetic_snapshot_staging

```sql
CREATE TABLE synthetic_snapshot_staging (
  id UUID PRIMARY KEY,
  capture_timestamp TIMESTAMPTZ NOT NULL,
  scheduled_time TEXT NOT NULL CHECK (scheduled_time IN (
    '09:35', '10:30', '12:30', '14:00', '15:00'
  )),
  
  -- Market state at capture
  spx_price NUMERIC NOT NULL,
  vix_value NUMERIC NULL,
  spx_5min_return NUMERIC NULL,
  
  -- Item integration snapshot pointers
  item5_snapshot_id UUID NULL
  item8_snapshot_id UUID NULL
  market_state_card_hash TEXT NOT NULL,
  feature_hash TEXT NOT NULL,
  
  -- Shadow rules engine output
  would_rules_propose_trade BOOLEAN NOT NULL,
  shadow_strategy_hint TEXT NULL,
  shadow_strategy_structure JSONB NULL,
  shadow_reject_reason TEXT NULL,
  
  -- Validation status
  retrieval_eligible_pending BOOLEAN NOT NULL DEFAULT false,
  diagnostic_only BOOLEAN NOT NULL DEFAULT true,
  data_quality_flags TEXT[] NOT NULL DEFAULT '{}',
  
  -- Status tracking
  inserted_to_strategy_attribution BOOLEAN NOT NULL DEFAULT false,
  attribution_id UUID NULL REFERENCES strategy_attribution(id),
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Weekly Sunday EOD generator reads from this table, applies validation, and inserts into `strategy_attribution`.

---

## 14. ROI Priority and Honest Expectations

### What Item 3 Does

```
Prevents memory overfitting
Reduces selection bias
Captures operator wisdom for retrieval
Provides coverage notes for sparse strategies
Surfaces market states the system ignored
```

### What Item 3 Does NOT Do

```
Generate alpha (it's not an alpha engine)
Train the meta-labeler (synthetic cases are NEVER training data)
Replace counterfactual ledgers (those are Item 10)
Replace replay harness (that's Item 4)
```

### Expected ROI Impact

```
Direct ROI: +0.5% to +2% annually (modest)
Learning velocity: meaningful (better calibration over time)
Failure-mode reduction: prevents silent bias accumulation
```

**Strong opinion:** Item 3 is the kind of infrastructure that doesn't show up in P&L attribution but prevents the system from quietly degrading over months. It's insurance, not alpha.

---

## 15. V0.1 Ship Scope

### Required for V0.1

```
1. CREATE TABLE synthetic_snapshot_staging
2. ALTER TABLE strategy_attribution: add synthetic + operator override + 
   coverage note fields
3. backend/synthetic_snapshot_capture.py (intraday capture at 5 timestamps)
4. backend/synthetic_snapshot_validator.py (live-capture validation)
5. backend/eod_synthetic_generator.py (Sunday EOD batch insertion)
6. backend/counterfactual_variant_generator.py (Item 10 integration)
7. backend/operator_override_capture.py (operator action recording)
8. Selection-bias monitoring queries
9. Retrieval logic with sparse-strategy coverage notes
10. replay_eval_cases separation enforcement
```

### V0.2 Defers

```
- Event-driven snapshot capture (FOMC/CPI/NFP +5min, +30min)
- Adaptive timestamp shifting (V0.2 research only)
- Variant 4 (AI opposite decision counterfactuals)
- Weight calibration empirical sensitivity test
- Adversarial example generation (research only, NEVER production)
```

### Never Build

```
- Adversarial cases in production memory
- Synthetic training data path
- Vibes-based alternative strategy estimation
- Adaptive timestamps based on event detection
- Synthetic case_type as fifth evidence type (use overlay instead)
```

---

## 16. Final Architectural Statement

**Synthetic cases preserve coverage. Actual cases teach truth. Counterfactual cases estimate missed outcomes. Operator overrides preserve expert context.**

The danger is contamination: if synthetic cases enter training or dominate retrieval, they create confidence without evidence. The architectural commitment — `calibration_eligible = false` enforced structurally, retrieval caps preventing dominance, separate storage from replay harness — prevents this entire failure class.

Item 3's value is not alpha. Its value is preventing the meta-labeler from training on a biased subset of market states, and preventing the Governor from retrieving only "seen decision contexts" when novel situations arise.

**This is insurance against silent degradation, not a profit engine.**

---

*Spec produced through Cursor selection-bias surfacing + GPT Round 2 + Item 2 schema lock + Claude verification + GPT verification accept on 2026-04-26. Locked after one full audit round plus verification. Coverage layer for Items 1, 6, 7.*
