# Item 7: Adversarial Pre-Trade Review — LOCKED SPECIFICATION

**Status:** 🔒 LOCKED
**Locked:** 2026-04-25
**Tier:** V0.2 infrastructure / V0.3 production authority (graduated)
**Sources:** Claude opening proposal + GPT-5.5 Pro Round 1 + Claude verification round + GPT verification accept
**Expected ROI contribution at maturity (months 7-12):** +1% to +3% annual full-account ROI
**Architectural role:** Selective high-conviction kill-switch, NOT general-purpose second Governor.

---

## Architectural Commitment

Item 7 is **insurance against confirmation-bias anchoring**, not core ROI infrastructure. It fires only on high-conviction trades that survived all other filters (Items 5/6/Governor), and only when those trades match specific conditions where confirmation-bias failures are most likely.

It is NOT a general-purpose adversarial system that runs on every trade. Items 5 and 6 already provide layered rejection. Item 7 adds the last sanity check for the case where "all systems agree, but they are all anchored wrong."

**Critical sizing rule (when in production authority):**
```
final_size = min(
  constitutional_cap,
  rules_cap,
  governor_cap,
  meta_labeler_cap,
  adversarial_cap
)
```

Adversarial review can only reduce or block. It can never increase size, never override Governor, never bypass constitutional gates.

---

## 1. Trigger Conditions

### Pre-Adversarial Size Calculation

```
pre_adversarial_size = min(
  constitutional_cap,
  rules_cap,
  governor_cap,
  meta_labeler_cap
)
```

### Primary Trigger Conditions (Fire If All True)

```
pre_adversarial_size >= 0.50
AND meta_labeler_p_eff >= 0.58
AND meta_labeler_p_hat >= 0.70
AND ev_per_margin_after_slippage >= 0.12
AND data_quality_ok = true
```

### Auto-Fire Triggers (Fire If Any True)

```
governor.review_required = true but trade still allowed
governor.event_class != ordinary AND trade still allowed
first trade of day with size >= 0.50
late-day entry after 13:30 with size >= 0.25
any short-gamma trade during scheduled macro / post-event regime
strategy is iron_butterfly AND size >= 0.50
```

### Opportunity Lean Triggers (Modified — More Selective)

For opportunity lean / long-vol enable signals, fire ONLY if:

```
lean_size >= 0.50
OR pre-event lean
OR similar past leans in same regime had >2 losses in last 10
OR governor.uncertainty_score >= 0.60 but trade is still allowed
OR long-vol/lean trade is being considered for live authority
```

Do NOT auto-fire for:
- V0.1 paper-only 0.25x leans
- Ordinary post-confirmation 0.25x debit spreads
- Lean trades tagged as advisory/research only

### Do Not Fire When

```
trade already blocked by upstream layers
size cap is only 0.25 due to weak confidence (already filtered)
trade is exit/risk-management action
after 14:30 entry time-stop (no new entries anyway)
quotes stale enough that trade should be re-priced regardless
```

**Target trigger rate: 5-20% of proposed trades.** Not every trade.

---

## 2. Adversarial Prompt Structure

The prompt must be hostile to confirmation bias but not allowed to hallucinate.

### Input To Adversarial Model

```
Market State Card summary
Proposed trade structure
strategy_ev_table row from Item 5 (Vol Fair-Value Engine)
Meta-labeler score and reason codes
Governor structured fields ONLY (no rationale prose)
Top 8 memory analogs, biased toward FAILURES
Current quote/slippage snapshot
Data freshness flags
Time bucket and event bucket
```

**Critical exclusion:** The adversarial model does NOT receive the original bullish/approval rationale in prose. That creates anchoring — the entire point of adversarial review is to break anchoring.

### Prompt Skeleton

```
You are the adversarial pre-trade reviewer.

Your task is NOT to decide whether this is a good trade.
Your task is to find the strongest evidence-grounded reason 
this trade is wrong.

You may only use evidence present in the supplied context.
Do not invent news, prices, events, or analogs.
Do not list generic risks that apply to all trades.
If there is no credible evidence-grounded counterargument, 
say so.

A valid response can be:
"I do not see a credible counterargument from the supplied 
evidence."

That is not approval. It only means no adversarial objection 
was found.

Return JSON only.
Rank the strongest counterargument first.
Every concern must cite the input field or memory case that 
supports it.
```

The framing matters: adversarial call is a **prosecutor**, not a second analyst.

---

## 3. Output Schema

```json
{
  "counter_argument_strength": 0.0,
  "evidence_grade": "none | weak | medium | strong",
  "primary_concern": "string",
  "concern_type": "event_conflict | vol_mispricing | skew_tail | flow_divergence | stale_data | late_day_gamma | analog_failure | execution_slippage | none",
  "supporting_fields": ["field names"],
  "analog_failure_ids": ["case ids"],
  "recommended_action": "proceed | reduce | block | block_alert",
  "adversarial_size_cap": 1.0
}
```

### Action Thresholds

| counter_argument_strength | Action |
|---|---|
| < 0.35 | proceed |
| 0.35-0.60 | reduce one tier |
| 0.60-0.75 | reduce to 0.25 OR require review |
| 0.75-0.85 | block |
| > 0.85 | block + alert operator |

### Evidence-Based Override Rules (Critical)

```
If evidence_grade = weak:
  max action = reduce one tier (cannot block regardless of strength score)

If evidence_grade = none:
  action = proceed (regardless of strength score)
```

This prevents "scary but unsupported concern kills good trade" failure mode. A model can generate plausible-sounding counter-arguments without actual evidence; requiring evidence pinning prevents pure rhetoric from killing trades.

---

## 4. Model Selection

**Use a different model family than the AI Risk Governor.**

Reason: shared training distribution = shared blind spots. The point of adversarial review is reducing those shared blind spots through cross-vendor diversity.

### Locked Pairing

```
Governor primary: chosen main model (currently Claude Sonnet)
Adversarial review: secondary vendor/model, fast mid-tier
```

If Governor is Claude/Sonnet → Adversarial uses GPT-5 mini or GPT-5
If Governor is GPT → Adversarial uses Claude Haiku or Sonnet

### Cost Per Trigger (Reference)

For 4k input / 600 output:
```
GPT-5 mini ≈ $0.002 per trigger
GPT-5 ≈ $0.011 per trigger
Claude Haiku ≈ $0.006 per trigger
Claude Sonnet ≈ $0.021 per trigger
```

At 1,000 triggers/year: $2-21/year. Cost is not the constraint. Latency and quality matter more.

---

## 5. Latency Targets

```
p50 < 2.5 sec
p95 < 5 sec
hard timeout = 6 sec
```

### Timeout Behavior

If timeout occurs:
```
Ordinary regime, non-short-gamma, size 0.5:
  proceed after reprice

Event/late-day/short-gamma:
  reduce one tier OR skip if quote moved materially
```

**Never execute against the old quote after adversarial review.** Reprice before order submission to capture any market movement during the review.

---

## 6. Architecture Placement

### Decision Flow Sequence

```
Rules Engine → Vol Engine → Meta-Labeler → Governor → Adversarial Review → Deterministic Arbiter → Execution
```

Adversarial review is the **last pre-trade check** because its job is to challenge the entire approved stack.

### Integration With Sizing Rule

```
final_size = min(
  constitutional_cap,
  rules_cap,
  governor_cap,
  meta_labeler_cap,
  adversarial_cap
)
```

Adversarial review becomes a fifth cap. It can reduce or block. It can never increase size, never override Governor, never bypass constitutional gates.

---

## 7. Post-Trade Attribution

### Logged Fields Per Adversarial Trigger

```
trade_candidate_id
pre_adversarial_size
adversarial_size_cap
counter_argument_strength
evidence_grade
concern_type
supporting_fields
analog_failure_ids
model_version
prompt_version
latency_ms
quote_before_review
quote_after_review
final_action
operator_override_flag
```

### Counterfactual Tracking

If adversary blocks:
```
Record counterfactual outcome with:
  same entry timestamp
  same strategy
  same exit logic
  same slippage model
```

If operator overrides a block:
```
Track actual P&L
Track counterfactual no-trade
Mark as operator_override
```

If adversary proceeds and trade loses:
```
label = missed_catch
Classify whether concern was: absent, too weak, or threshold too high
```

### Core Value Metric

```
adversarial_value =
    avoided_losses_from_blocks
  - missed_profits_from_blocks
  + value_from_size_reductions
  - latency_slippage_cost
```

---

## 8. Calibration

### Outcome Bucketing

```
useful_block: blocked trade would have lost
costly_block: blocked trade would have won
useful_pass: allowed trade won
missed_catch: allowed trade lost
```

### Net-Positive Threshold

```
adversarial_value > 0 over rolling 50 triggers
AND avoided_loss / costly_block_profit > 1.5
AND latency_slippage < 10% of projected EV
AND block rate among triggers < 35%
```

### Deprecation Logic (Wilson + Value)

**Eligible only after:**
```
minimum 30 adversarial blocks
minimum 4 weeks operation
```

**Track:**
```
useful_block_rate = useful_blocks / total_blocks

adversarial_value =
    avoided_losses_from_blocks
  - missed_profits_from_blocks
  + value_from_size_reductions
  - latency_slippage_cost
```

**Deprecate to advisory-only if:**
```
Wilson_lower_95(useful_block_rate) < 0.30
AND adversarial_value < 0
```

**Immediately degrade one authority level if:**
```
adversarial_value < 0 over rolling 50 triggers
AND block_rate > 40%
```

The combined statistical + economic test prevents two failure modes:
- Pure count-based: misses that one big save justifies many small mistakes
- Pure dollar-based: too sensitive to single trade outcomes

---

## 9. Response Stability Monitoring

Cross-vendor adversarial review can produce inconsistent responses on similar inputs. Same context might produce action=block one moment and action=proceed the next, based on adversarial model variance rather than market conditions.

### Pre-Production Stability Test

Before adversarial review graduates to production authority:
```
Same input sent 5 times
temperature = 0 (or lowest available)
same schema
same model version
```

Measure:
```
action_consistency_rate
strength_std_dev
concern_type_consistency
cap_consistency
```

### Production Promotion Threshold

```
action_consistency_rate >= 80%
AND block/reduce/proceed tier consistency >= 85%
AND counter_argument_strength std_dev <= 0.15
```

If stability fails: adversarial_review = advisory_only.

### Ongoing Monitoring

Weekly variance check on similar-context groups using compact feature hash:
```
strategy_type
time_bucket
event_class
governor_uncertainty bucket
meta p_take bucket
iv_rv bucket
skew bucket
```

If action consistency drops:
```
Below 80%: reduce authority one step
Below 70%: advisory only
```

---

## 10. V0.2 vs V0.3 Sequencing

### V0.2 — Infrastructure (Advisory Only)

**Build:**
- Adversarial prompt templates
- Schema validator
- Trigger logic
- Logging table
- Counterfactual ledger hooks
- Latency tracking
- Response stability tests

**Authority:**
- Advisory only
- Can display recommended cap
- CANNOT block live/paper execution automatically
- Exception: paper mode "shadow blocking" ledgers permitted for measurement

### V0.3 — Production Authority Promotion

Promotion gates (ALL required):
```
minimum 30 blocks accumulated in V0.2
minimum 50 total triggers in V0.2
minimum 4 weeks of operation
positive adversarial_value
response stability passes thresholds
latency p95 < 5 seconds
no evidence of excessive overblocking
```

When promoted, becomes the fifth cap in the sizing minimum.

---

## 11. Failure Modes And Mitigations

| Risk | Mitigation |
|---|---|
| Hallucinated risk | Require evidence_grade and supporting_fields |
| Too aggressive (overblocking) | Block threshold starts at 0.75, not 0.60 |
| Too diplomatic | Prosecutor prompt; no approval language permitted |
| Cross-vendor inconsistency | Output is schema-only; deterministic arbiter interprets |
| Latency/slippage | Hard timeout, reprice before order submission |
| Overblocking best trades | Rolling adversarial_value and costly_block tracking |
| Generic concerns | Prompt rejects risks that apply to all 0DTE trades |

**Biggest danger: plausible overblocking, not hallucination.** A model that sounds persuasive but is wrong about specific trades is the failure mode to guard against.

---

## 12. Iran-Day Walkthrough

In the locked architecture, Iran-day butterflies are blocked by Governor and meta-labeler before reaching adversarial review:
- Governor flags geopolitical_shock
- Meta-labeler's IB utility includes event_day_short_gamma_flag penalty

So adversarial review **does not fire** on Iran-day IB trades — they don't reach the high-conviction approval threshold.

If forced to review anyway, expected output:
```json
{
  "counter_argument_strength": 0.90,
  "evidence_grade": "strong",
  "concern_type": "event_conflict",
  "primary_concern": "Neutral short-gamma IB depends on pin/range behavior, but current context shows geopolitical downside shock, bearish futures confirmation, and stale market-structure signals.",
  "supporting_fields": ["governor.event_class", "futures_overnight", "vix_freshness"],
  "recommended_action": "block_alert",
  "adversarial_size_cap": 0
}
```

The adversarial layer's value is in the case where Items 5/6/Governor approve a high-conviction trade and confirmation-bias anchoring is the residual risk. Iran day is NOT that case — it's the case where multiple layers correctly catch the failure.

---

## 13. Expected ROI Trajectory

| Period | Live Contribution | Authority |
|---|---|---|
| Months 1-3 (V0.2 infrastructure) | 0% (paper/advisory) | infrastructure build |
| Months 4-6 (V0.2 calibration) | 0% to +1% | advisory data accumulation |
| Months 7-12 (V0.3 production if promoted) | +1% to +3% | fifth-cap kill-switch |

### ROI Mechanism

Lower bound (+1%) from:
- Catching one or two high-conviction false positives per year
- Reducing size on a few fragile A+ trades

Upper bound (+3%) from:
- Blocking rare large-loss trades that survived all other filters
- Especially late-day short-gamma or post-event false confidence

### Negative Case (Deprecation Triggered)

- Blocks the best high-EV trades
- Adds latency that costs slippage
- Hallucinates concerns
- Duplicates Governor without adding new information

If calibration shows negative adversarial value: **kill it.** Do not keep it because it sounds sophisticated.

---

## 14. V0.2 Build Scope

**Build:**
- Adversarial prompt template (cross-vendor)
- JSON schema validator
- Trigger logic with all conditions
- Logging table for triggers
- Counterfactual ledger hooks
- Latency tracking
- Response stability test harness
- Compact feature hash for similar-context grouping
- Wilson interval + adversarial_value calibration
- Authority promotion / deprecation logic

**Do not build in V0.2:**
- Production blocking authority (V0.3 only)
- Adversarial review on every trade
- Multi-model ensemble adversaries
- LLM-driven prompt self-modification

---

## 15. Final Architectural Statement

Item 7 is **useful insurance against confirmation-bias anchoring**, not core ROI infrastructure. The main ROI comes from:
- Item 5 measuring volatility mispricing
- Item 6 rejecting weak proposals via Bayesian-shrunk meta-labeling
- AI Risk Governor blocking novel-event short-gamma exposure

Item 7 catches the residual case: high-conviction trades where all other filters approved, but confirmation-bias anchoring led the system to a wrong conclusion. This is rare but expensive when it happens.

Build the hooks in V0.2 because they are small and auditable. Do not let it block production trades until V0.3, after calibration proves positive adversarial_value and stable cross-vendor outputs.

The architectural commitments hold:
- AI controls admissibility and size ceilings, not trade execution
- Constitutional gates remain non-overridable
- Caps compose by minimum
- Adversarial review can reduce or block, never expand

---

*Spec produced through Claude opening + GPT-5.5 Pro Round 1 + Claude verification + GPT verification accept over 2026-04-25. Locked after one full round plus verification. No code changes during specification.*
