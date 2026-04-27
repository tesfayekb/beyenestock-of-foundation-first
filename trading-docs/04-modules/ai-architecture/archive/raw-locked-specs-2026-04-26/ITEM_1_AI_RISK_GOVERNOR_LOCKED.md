# Item 1: AI Risk Governor with Capped Opportunity Lean — LOCKED SPECIFICATION

**Status:** 🔒 LOCKED
**Locked:** 2026-04-25
**Tier:** V0.1 Foundation (4-6 weeks)
**Architectural Role:** The system's anchor. Controls trade admissibility and size ceilings, never trade execution.
**Sources:** Round 2 GPT-5.5 Pro design + Items 5-10 integration audit + Claude verification + GPT verification accept

---

## Architectural Commitment

**The Governor never becomes a strategy selector or execution brain.** It handles uncertainty, event risk, admissibility, and capped lean permission. ROI comes from avoiding invalid short-gamma exposure under novel conditions, not from picking better trades.

Items 5/6/8/9 provide measurable edge. Item 10 makes the learning loop calibration-grade. Item 1 supplies restraint.

---

## 1. Final Decision Stack

```
Rules + Constitutional Gates
        ↓
Item 5 Vol Fair-Value (deterministic features)
        ↓
Item 8 OPRA Flow Summary (deterministic features)
        ↓
Market State Card (refactored synthesis_agent)
        ↓
Supabase pgvector case retrieval
        ↓
AI Risk Governor (LLM, structured JSON output)
        ↓
Item 6 Meta-Labeler (downstream filter)
        ↓
Preliminary Arbiter
        ↓
Item 7 Adversarial Review (only if trigger fires)
        ↓
Final Arbiter
        ↓
Execution
        ↓
Item 10 Attribution (calibration memory)
```

### Composition Rule (Final Arbiter)

```
final_size = min(
    constitutional_cap,    # -3% halt, time stops, etc.
    rules_cap,             # rules engine size
    governor_cap,          # AI Risk Governor cap
    meta_labeler_cap,      # Item 6 utility-aware p_take
    adversarial_cap_if_present  # Item 7 challenge result
)
```

Each layer can only reduce, never increase. This is the constitutional safety property.

---

## 2. Item Integration

| Item | Position | What It Provides / Consumes |
|------|----------|----------------------------|
| Item 5 (Vol Fair-Value) | Upstream | Provides iv_rv_ratio, strategy_ev_table, short_gamma_ev_warning, vol_engine_confidence, skew_z, surface_risk_flags |
| Item 6 (Meta-Labeler) | Downstream | Applies utility-aware p_take filter on Governor's "proceed" decisions; can reduce size, never increase |
| Item 7 (Adversarial Review) | Selective | Sequential after Meta-Labeler IF trigger fires (5-20% of trades); routine trades skip |
| Item 8 (OPRA Flow) | Upstream | Provides 20 deterministic flow features as compact summary to Governor; full features go to Meta-Labeler |
| Item 9 (Exit Optimizer) | Parallel | Independent — handles open positions only, doesn't affect entry permission |
| Item 10 (Counterfactual) | Downstream | Logs all Governor decisions as actual/counterfactual cases; provides retrieval cases via pgvector |

### Item 7 Latency Behavior

```
Routine trade:
  Governor → Meta → Arbiter → Execution
  (no adversarial latency)

Triggered trade (5-20% target rate):
  Governor → Meta → Preliminary Arbiter
  → Adversarial Review (p95 < 5 sec, hard timeout 6 sec)
  → Final Arbiter
```

### Item 7 Timeout Fallback

```
Ordinary non-short-gamma: proceed after reprice, possibly reduced one tier
Event / late-day / short-gamma: reduce one tier or skip
```

---

## 3. JSON Schema (Split: LLM Output vs Decision Record)

### A. GovernorLLMOutput

What the LLM is allowed to produce. Validated strictly.

```json
{
  "schema_version": "1.0",
  "event_class": "geopolitical_downside | macro_dovish | macro_hawkish | event_pre | event_post | normal | unknown",
  "event_subtype": "string | null",
  "event_direction": "bullish | bearish | two_sided | none",
  "evidence_grade": "none | weak | medium | strong",
  
  "novelty_score": 0.0-1.0,
  "uncertainty_score": 0.0-1.0,
  "signal_conflict_score": 0.0-1.0,
  "data_freshness_warning": true/false,
  "data_freshness_flags": ["string"],
  
  "allowed_strategy_classes": ["enum"],
  "blocked_strategy_classes": ["enum"],
  "block_reasons": ["string"],
  
  "size_multiplier_cap": 0 | 0.25 | 0.5 | 1.0,
  
  "opportunity_lean_allowed": true/false,
  "opportunity_lean_direction": "bullish | bearish | two_sided | none",
  "opportunity_lean_strategy_classes": ["enum"],
  "lean_requires_confirmation": true/false,
  
  "review_required": true/false,
  "rationale_short": "string, max 600 chars",
  "supporting_case_ids": ["string"]
}
```

**Critical:** risk_score is NOT in LLM output. The LLM provides components; deterministic code computes final risk_score. This prevents the LLM from grading itself.

### B. GovernorDecisionRecord

System-appended metadata, persisted to Supabase.

```json
{
  "decision_id": "uuid",
  "candidate_id": "uuid | null",
  "session_id": "uuid",
  "timestamp_decision_created": "timestamptz",
  "timestamp_decision_received": "timestamptz",
  
  "prompt_version_id": "string",
  "prompt_hash": "string",
  "model_version": "string",
  "llm_model_used": "gpt-5.4 | gpt-5.4-nano | gpt-5.5 | other",
  "model_snapshot": "string | null",
  "temperature": "float",
  "schema_version": "string",
  
  "market_state_card_hash": "string",
  "feature_hash": "string",
  "retrieval_query_hash": "string",
  "retrieved_case_ids": ["string"],
  "retrieval_quality_score": 0.0-1.0,
  
  "input_token_count": "int",
  "output_token_count": "int",
  "estimated_cost_usd": "numeric",
  "latency_ms": "int",
  
  "parse_status": "success | malformed_json | timeout | unavailable",
  "validation_status": "valid | logical_conflict | schema_invalid",
  "fallback_used": "boolean",
  "fallback_reason": "string | null",
  
  "governor_size_cap": 0 | 0.25 | 0.5 | 1.0,
  "computed_risk_score": 0.0-1.0,
  "final_arbiter_size_before_adversarial": "float | null",
  
  "raw_output_json": "jsonb",
  "validated_output_json": "jsonb",
  
  "item5_snapshot_id": "uuid | null",
  "item6_meta_labeler_id": "uuid | null",
  "item7_adversarial_id": "uuid | null",
  "item10_case_id": "uuid | null"
}
```

---

## 4. Action Types

```
block — full no-trade
reduce — size cap < 1.0x
proceed — normal trade allowed (subject to downstream filters)
capped opportunity lean — defined-risk convex structure
  V0.1: ≤ 0.25x (paper only)
  V0.2: ≤ 0.5x (graduated to live, see graduation criteria)
```

---

## 5. Opportunity Lean Constraints

```
Defined-risk only
No naked short optionality
No increase to net short gamma
Requires market confirmation (unless extremely high reliability event 
  source like FOMC/CPI)
V0.1 paper-only at ≤ 0.25x
V0.2 may go live at ≤ 0.5x ONLY if separate graduation criteria pass
```

---

## 6. Risk Score (Deterministic Code, Not LLM Output)

### V0.1 Initial Formula

```
risk_score = 
    0.30 * calibrated_event_uncertainty
  + 0.25 * signal_conflict
  + 0.20 * novelty
  + 0.15 * data_freshness_penalty
  + 0.10 * recent_strategy_drift
```

Components extracted from LLM output. Final risk_score computed by deterministic code.

### V0.1 Replay Calibration

The Round 2 weights ship as initial prior. V0.1 must replay-calibrate before binding.

**Replay Test:**
```
1. Rebuild point-in-time Market State Cards
2. Run frozen Governor prompt
3. Compute risk_score with candidate weight sets (Latin-hypercube search)
4. Apply size map
5. Compare rules-only vs Governor-size-capped outcomes
```

**Objective Function:**
```
J = veto_value_R
  + 0.50 * log(maxDD_baseline / maxDD_candidate)
  + 0.25 * log(profit_factor_candidate / profit_factor_baseline)
  - 0.50 * false_veto_cost_R
  - 1.00 * max(0, worst_day_candidate / worst_day_baseline - 1)
```

**Sensitivity Rule:**
```
If changing any major weight by ±0.10 flips >15% of decisions,
treat the formula as unstable and use more conservative thresholds.
```

V0.1 advisory uses Round 2 thresholds. V0.2 binding uses replay-calibrated weights.

---

## 7. Size Mapping

```
risk_score >= 0.75 → size_cap = 0 (block)
0.60 <= risk_score < 0.75 → size_cap = 0.25
0.45 <= risk_score < 0.60 → size_cap = 0.50
risk_score < 0.45 → size_cap = 1.0 (only if calibration healthy)
```

---

## 8. Deterministic Fallback Rules (Locked)

### Rule 1: Logical Conflict (Lean With High Risk)

```
if novelty_score >= 0.80
   AND uncertainty_score >= 0.70
   AND opportunity_lean_allowed = true:
       validation_status = "logical_conflict"
       opportunity_lean_allowed = false
       governor_size_cap = 0
       fallback_reason = "high_novelty_high_uncertainty_lean_conflict"
```

### Rule 2: High Risk Without Lean

```
elif novelty_score >= 0.80 AND uncertainty_score >= 0.70:
       opportunity_lean_allowed = false
       governor_size_cap = 0.25
       review_required = true
```

### Rule 3: Single High-Risk Dimension

```
elif novelty_score >= 0.80 OR uncertainty_score >= 0.70:
       opportunity_lean_allowed = false
       governor_size_cap = 0.50
```

### Rule 4: Iran-Day Encoding

```
if strategy_class == "neutral_short_gamma" AND novelty_score >= 0.80:
       governor_size_cap = 0
```

This rule encodes the Iran-day failure mode directly. Even when uncertainty is moderate, high-novelty + neutral short-gamma blocks unconditionally.

---

## 9. LLM Confidence vs ML Confidence Reconciliation

**Do not average raw confidences.** They are not the same unit.

### LightGBM Confidence

Calibrated with rolling isotonic or Platt scaling. Track degradation by regime.

### LLM Output

Ignore raw "I am 70% confident." Extract structured outputs:
- event_class
- evidence_grade
- novelty
- directional implication
- uncertainty
- data-staleness warning

LLM buckets calibrated from replay history.

### Deterministic Arbiter Combination

```
if ML and LLM agree:
    allow normal strategy map subject to risk gates

if ML confident but LLM flags high novelty/event risk:
    reduce size or block short gamma

if LLM directional but evidence weak:
    no lean; treat as uncertainty

if LLM directional + evidence high + price confirms:
    allow capped convex lean
```

**Example resolution:**
```
ML: 0.65 bull
LLM: 0.40 bear

→ Do NOT average to 0.525 bull.

→ If LLM evidence weak: ML primary, size may be reduced
→ If LLM evidence high-quality and novel: block neutral short-gamma 
  and short calls
→ Do not open bearish exposure unless price confirms
```

---

## 10. Constitutional Gates (Non-Overridable)

The Governor cannot override:

```
-3% daily halt (D-005)
2:30 PM time stop (D-010)
3:45 PM hard close (D-011)
Streak halt
Phase sizing tiers
Graduation rules (paper_phase_criteria GLC-001 through GLC-012)
```

These are encoded in the rules engine. The Governor sees the post-gate result and operates within those bounds.

---

## 11. Failure Mode Specification

| Failure | Fallback Behavior |
|---------|-------------------|
| LLM unavailable | No new short-gamma. No lean. Non-short-gamma capped at 0.25 if rules clean |
| LLM timeout | Same as unavailable |
| Malformed JSON | Reject output. Fallback mode |
| Schema validation fail | Reject output. Fallback mode |
| Logical conflict | Reject output. Fallback mode |
| High novelty + high uncertainty + lean | Lean disabled. Cap 0.25 OR block per Rule 1 |
| pgvector retrieval fail | Run Governor with retrieval_quality=0, +0.15 uncertainty penalty, no lean |
| No analogs returned | Same as retrieval weak. Don't auto-block |
| Market State Card fails | No Governor call. Fallback mode |
| Cost limit reached | Disable LLM entries. No short-gamma. No lean. Exits continue |
| Unsupported strategy class returned | Strip unsupported. If empty, block |
| Data freshness fail | Block new short-gamma. No lean |

### Fallback Mode Definition

```
Deterministic exits continue
Constitutional gates continue
No opportunity lean
Neutral short-gamma blocked
Single-side defined-risk trades max 0.25x only if rules + data quality clean
```

**Critical:** Do NOT fail open into normal rules-only short gamma. That reintroduces the Iran-day failure mode.

---

## 12. Promotion Gates

### V0.1 Advisory → V0.2 Paper-Binding

Required to graduate Governor from advisory to binding paper decisions for short-gamma vetoes:

```
Statistical:
  ≥ 200 replay/advisory decision cards
  ≥ 20 paper sessions
  ≥ 30 Governor veto/reduce actions
  
Effect Size:
  veto_value_after_slippage ≥ +2R cumulative
  Wilson_lower_95(useful_veto_rate) ≥ 0.40
  false_veto_cost ≤ 45% of avoided_loss
  catastrophic_loss_capture_rate ≥ 60%
  
Operational:
  JSON parse success ≥ 99.5%
  logical validation pass ≥ 99.0%
  p95 routine latency ≤ 6 sec
  prompt frozen ≥ 10 trading days
  
Safety Floor:
  no single block in prior 10 sessions cost > 0.50R
  block_rate among eligible short-gamma ≤ 35%
    (unless veto_value improves by ≥ +4R, which justifies higher rate)
```

### V0.2 Paper → Small Live Auto-Veto

```
Statistical:
  ≥ 60 paper sessions
  ≥ 50 Governor veto/reduce actions
  
Effect Size:
  veto_value_after_slippage ≥ +3R cumulative
  false_veto_cost ≤ 40% of avoided_loss
  catastrophic_loss_capture_rate ≥ 70%
  
Operational:
  no unresolved schema/fallback incidents in last 15 sessions
  prompt frozen ≥ 20 trading days
```

**Opportunity lean is excluded from live authority at this stage.** Lean follows separate graduation (Section 13).

---

## 13. Opportunity Lean Graduation (Separate Track)

### Paper → Live 0.25x

```
Statistical:
  ≥ 60 paper lean candidates
  ≥ 30 executed paper lean trades
  ≥ 30 paper sessions

Effect Size:
  cumulative lean P&L after slippage > 0
  profit factor ≥ 1.15
  max lean drawdown ≤ 2R
  no single lean day worse than -0.50% account
  directional thesis correct ≥ 55% for directional debit spreads
  realized move / implied move favorable for long-vol leans
  no strategy bucket with negative cumulative R if n ≥ 10
```

### Live 0.25x → 0.5x

```
Additional ≥ 60 lean trades
cumulative live/paper utility ≥ +2R
profit factor ≥ 1.25
max drawdown not worse than no-lean baseline
no unresolved operator override incident
```

### Benchmarking Requirement

Lean must be benchmarked against:
1. No-lean baseline
2. Governor-veto-only baseline
3. Rules-only baseline

Prevents the lean channel from looking good only because the rest of the system improved.

---

## 14. Versioning and Rollback

### Git-Tracked Artifacts

```
prompt template
schema definition
validator rules
risk-score config
fallback config
```

### Supabase Table: ai_governor_versions

```sql
CREATE TABLE ai_governor_versions (
  version_id TEXT PRIMARY KEY,
  prompt_hash TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  model_id TEXT NOT NULL,
  model_snapshot TEXT,
  risk_score_config JSONB,
  status TEXT CHECK (status IN ('draft','challenger','champion','retired','rollback')),
  created_at TIMESTAMPTZ DEFAULT now(),
  promoted_at TIMESTAMPTZ,
  retired_at TIMESTAMPTZ,
  promotion_metrics JSONB,
  rollback_reason TEXT
);
```

### Versioning Rules

```
1. No mutable aliases in production if a snapshot is available
2. Every prompt change starts as challenger
3. Champion prompt frozen ≥ 10 trading days
4. Rollback is immediate if validation failure or veto value 
   deterioration appears
5. Do not average champion/challenger decisions. 
   Challenger is shadow only.
```

### Champion/Challenger Promotion Criteria

```
≥ 100 shadow decisions
no parse degradation
latency not worse by >20%
veto_value not worse than champion
block rate not >1.5x champion (unless veto value improves)
```

### Champion/Challenger Architecture

**Asynchronous (locked):**

```
Champion runs synchronously and controls live/paper decision:
  Market State Card → Champion Governor → decision

Challenger runs asynchronously after champion ships:
  captured Market State Card 
  + same retrieval bundle
  + same candidate
  → challenger output (after champion decision recorded)
```

**Requirement:** Challenger must use the exact captured `feature_hash` and `market_state_card_hash`. Same point-in-time evaluation.

**Challenger output uses:**
- Shadow comparison
- Prompt/model evaluation
- Disagreement analytics
- Future promotion

---

## 15. Decision Caching

**Cache Key:**
```
feature_hash + candidate_strategy_class + prompt_version 
+ model_version + retrieval_bundle_hash
```

**TTL by Regime:**
```
Ordinary regime: 3 minutes
Event / high novelty / high uncertainty: NO CACHE
Late day after 13:30: NO CACHE
Open position stress: NO CACHE
```

**Cache Conditions (ALL required):**
```
retrieval_quality_score ≥ 0.70
governor_uncertainty_score < 0.50
data_freshness_warning = false
no active event trigger
no OPRA/vol/price regime change since cached decision
```

**Reuse Validation:**
```
current_feature_hash == cached_feature_hash (exact match required)
```

If feature hash changed, no reuse.

**Expected Benefit:** 10-20% cost reduction (not the 30% commonly cited). Staleness risk matters more than AI cost.

---

## 16. Retrieval Quality Score

### Formula

```
retrieval_quality_score = 
    0.40 * top_k_similarity
  + 0.30 * actual_case_share
  + 0.15 * time_decay_factor
  + 0.15 * schema_quality_factor
```

### Component Definitions

```
top_k_similarity = 
  average cosine similarity of top 12 retrieved cases

actual_case_share = 
  count(case_type = 'actual') / 12

time_decay_factor = 
  exp(-avg_days_old / 90)

schema_quality_factor:
  1.00 = current schema + calibration_eligible = true
  0.70 = prior schema but calibration_eligible = true
  0.40 = approximate / non-training-eligible but useful for observability
  0.00 = pre-Commit-4 contaminated OR legacy_observability_only
```

**Critical:** schema_quality_factor = 0.00 for contaminated rows. This structurally enforces Item 10's commitment that contaminated data must not contribute to retrieval-based calibration.

### Retrieval Penalties

```
score > 0.70:    no penalty
0.50-0.70:       uncertainty += 0.05
0.30-0.50:       uncertainty += 0.15, opportunity_lean_allowed = false
< 0.30:          retrieval_insufficient = true
                 block neutral short-gamma
                 cap other defined-risk trades at 0.25
                 require clean deterministic signals
```

---

## 17. Disagreement Bands and Alerts

### V0.1/V0.2 Bands (Initial — Wider Tolerance)

```
Rules disagreement:
  Healthy: 5%-30%
  < 5% for 5 sessions → alert: Governor adding little incremental value
  > 30% for 5 sessions → alert: possible over-veto or regime mismatch

LightGBM disagreement:
  Healthy: 10%-35%
  < 10% for 5 sessions → alert: not detecting semantic novelty
  > 35% for 5 sessions → alert: fighting calibrated ML too often

Meta-labeler disagreement:
  Healthy: 5%-25%
  < 5% for 5 sessions → alert: final filter not adding value
  > 25% for 5 sessions → alert: poorly calibrated together
```

### V0.3 Bands (Mature — Tighter)

```
Rules: 5%-25%
LightGBM: 10%-30%
Meta: 5%-20%
```

**Critical:** Disagreement alerts trigger review and calibration checks. They do NOT change live decisions directly. Authority degradation requires explicit operator action.

---

## 18. Observability Dashboard (V0.1 Minimum)

```
Governor status: active / degraded / fallback
Current prompt_version and model
Decisions today: proceed / reduce / block / lean / fallback
Short-gamma blocks today
Opportunity lean suggestions today
LLM latency p50 / p95 / max
LLM cost today and month-to-date
Token usage today
JSON parse failure rate
Logical validation failure rate
Fallback count and reason
Retrieval quality average
Rules disagreement rate
LightGBM disagreement rate
Meta-labeler disagreement rate
Veto value rolling 30 decisions
False veto cost rolling 30 decisions
Catastrophic-loss capture count
Data freshness warnings
Operator overrides
```

### Loud Alert Trigger

```
Governor degraded + short-gamma candidate proposed
```

This must be a loud alert, not a passive dashboard value.

---

## 19. Validator Layer

Every LLM output passes:

```
Schema validation (JSON shape, field types, required fields)
Enum validation (event_class, strategy_classes, etc.)
Logical consistency validation (lean+high-uncertainty conflict, etc.)
Strategy support validation (only supported strategy classes)
Risk cap validation (size_multiplier_cap in valid set)
```

**Invalid output is never "interpreted." It is rejected.**

This is the same principle as Item 10's `calibration_eligible` filter: structural enforcement, not convention.

---

## 20. Decision Cadence

### V0.1

```
Pre-market Governor card (once before session)
Entry-time Governor call (only when candidate exists)
Event-triggered Governor refresh (when regime/news/vol/flow changes)
NO tick-level LLM calls
```

### Trigger Definitions

Event-triggered refresh fires when:
- VIX moves ≥ 1.5 std intraday
- Major news headline detected (high-priority calendar event)
- Rules engine regime flip
- OPRA flow regime change (Item 8)
- Open position under stress

---

## 21. Cost Circuit Breaker

```
Monthly budget approaching (80%):
  Disable opportunity lean
  Continue routine and escalation

Monthly budget breached (100%):
  Disable escalation (GPT-5.5)
  Continue routine if remaining budget
  Alert operator

Monthly budget exhausted:
  Disable LLM entries entirely
  Maintain deterministic exits
  Alert operator (loud)
```

Budget breach must NOT silently disable logging.

---

## 22. Human Override Logging

Every operator override creates an attribution case:

```
override_reason
operator_action
pre_override_recommendation
post_override_outcome
timestamp
session_id
linked_decision_id
```

Overrides feed Item 10's case memory as `case_type = 'override'`.

---

## 23. Strategy-Class Taxonomy

Locked enums:

```
neutral_short_gamma: iron_condor, iron_butterfly
single_side_credit: put_credit_spread, call_credit_spread
directional_debit: debit_call_spread, debit_put_spread
long_vol_convex: long_straddle, long_strangle
calendar: calendar_spread
no_trade
```

Governor controls classes, not exact strikes.

---

## 24. Market State Card Contract

V0.1 includes only:

```
Rules regime / confidence
LightGBM p_bull / p_bear / confidence
Item 5 EV summary
Item 8 flow summary (when available)
Macro / event calendar
News / event brief
Data freshness table
Open risk state
Retrieved analog summaries
```

**Maximum size: 6-10k tokens.** No raw chains, no raw OPRA, no raw headlines dump.

The Market State Card is a refactored synthesis_agent that produces structured input. The 8 specialist agents continue feeding Redis briefs that the Card consumes and summarizes.

---

## 25. Model Selection

### V0.1 Production Stack

```
Routine pre-market / main Governor: GPT-5.4
Fast intraday triage: GPT-5.4 nano
High-novelty escalation: GPT-5.5 (when available in API account)
Weekly blind audit / challenger: Claude Opus 4.7 or Sonnet-class 
  (NOT live path)
Embeddings: text-embedding-3-small (unless eval says otherwise)
```

### Cost Estimate (Routine Day)

```
Pre-market governor (GPT-5.4): ~$0.07
Intraday triage 6 calls (GPT-5.4 nano): ~$0.01
EOD attribution (GPT-5.4): ~$0.06
Embeddings: ~$0.0002

Routine total: ~$0.14/day
Annual: ~$35 for 252 sessions
```

### Cost Estimate (With Escalation)

```
GPT-5.5 event arbitration: ~$0.215/event
50 event days/year: ~$11
Weekly Claude audit: ~$0.225/week
52 weeks: ~$12

All-in annual: < $300 with safety margin
```

**Cost is not the constraint. Bad risk decisions are the constraint.**

### Latency Targets

```
pgvector retrieval: sub-second
GPT-5.4 nano triage: 0.5-2 seconds
GPT-5.4 synthesis: 3-10 seconds
GPT-5.5 escalation: 8-25 seconds
```

---

## 26. Operator Intervention Curve

| Period | Operator Role |
|--------|---------------|
| Week 1 | Review every AI output |
| Week 2 | Review replay results and threshold proposals |
| Weeks 3-4 | Review every veto, every lean suggestion, all errors |
| Weeks 5-6 | Paper binding veto; daily review |
| Month 3 | Daily review of A/B ledgers |
| Month 4 | Review exception days + weekly calibration |
| Month 5 | Promotion rehearsal; review drift and failover |
| Month 6+ | Weekly review only if gates clean; exception alerts immediately |

### Reduction Criteria

Do NOT reduce intervention because the calendar says so. Reduce only when:

```
Data is clean
Veto value is positive
False veto cost is bounded
Strategy attribution is stable
Drawdown is lower than rules-only baseline
No unexplained losses
```

### Return-to-High-Intervention Triggers

```
Daily halt triggers
Two unexplained losses within 20 trading days
Prompt/model/threshold version changes
Data freshness fails
Veto value turns negative
Synthetic/replay calibration diverges from live paper results
```

---

## 27. Final Architectural Statement

**The single most important decision: AI controls admissibility and size ceilings, not trade execution.**

That dominates ROI because:
- Largest avoidable losses come from regime-misclassified 0DTE days, not from clever strike selection
- A system preventing short-gamma exposure when semantic reality invalidates stale quantitative signals improves rolling Sharpe by reducing drawdown
- That is more valuable than letting an LLM chase marginal upside

### What This Architecture Might Be Wrong About

The dangerous assumption is that semantic event-risk detection has enough precision to improve Sharpe AFTER false veto costs.

If the AI overreacts to headlines and blocks too many profitable ordinary premium-selling days, it reduces expectancy.

V0.1 must prove the ratio:

```
expected drawdown avoided / opportunity cost of false vetoes  >  1.0
```

If not, demote the AI to attribution and anomaly detection only.

---

## 28. V0.1 Ship Scope (4-6 Weeks)

```
1. Supabase schema for AI decisions, attribution, replay, thresholds, 
   pgvector memory
2. Market State Card generator (refactored synthesis_agent)
3. AI Governor structured JSON output
4. Validator layer
5. Deterministic arbiter enforcing allowed strategy classes and size caps
6. Replay harness for threshold calibration
7. Strategy-aware attribution
8. Counterfactual ledgers
9. Synthetic opportunity records
10. Paper-only binding veto for neutral short-gamma strategies
11. Weekly calibration report
```

### V0.1 Excluded

```
Live AI-controlled trading
Exact strike selection by LLM
LLM order routing
Self-modifying prompts
Online RL
Fine-tuned LLM
Autonomous live opportunity lean
```

### V0.2 (4-6 weeks after V0.1)

```
Learned monotonic size-policy model
Prompt/model tournament
Live AI veto after graduation criteria
Paper-to-live graduated opportunity lean
Automated weekly calibration drift reports
Model-family blind audit
```

### Never Build

```
LLM as primary trader
LLM choosing exact strikes
LLM increasing risk limits
Multi-agent debate committee for live decisions
RL capital allocator for 0DTE execution
```

---

*Spec produced through Round 2 GPT-5.5 Pro design + Items 5-10 integration audit + Claude verification + GPT verification accept over 2026-04-25. Locked after one full audit round plus verification. Architectural anchor for Items 2-4 (Tier 1 Foundation) and Items 5-10 (Tier 2/3 V0.2-V0.4).*
