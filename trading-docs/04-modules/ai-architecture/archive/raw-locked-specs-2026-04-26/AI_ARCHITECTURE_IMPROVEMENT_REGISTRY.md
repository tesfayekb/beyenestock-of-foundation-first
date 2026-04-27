# MarketMuse AI Architecture — Improvement Registry
## Master List of All Architectural Improvements Under Discussion

**Created:** Saturday 2026-04-25
**Purpose:** Single reference document tracking every AI architecture improvement identified across the multi-model collaboration (Cursor + Claude + GPT-5.5 Pro). Updated as items are discussed, locked, or deprioritized.

**Status legend:**
- 🔒 **LOCKED** — Specification agreed by both Claude and GPT, documented, ready for implementation
- 🟡 **IN DISCUSSION** — Currently being worked through with back-and-forth iteration
- ⏳ **PENDING** — Waiting in queue, not yet discussed
- ❄️ **DEFERRED** — Acknowledged but explicitly pushed to later milestone
- ❌ **REJECTED** — Considered and decided against

---

## Tier 1 — V0.1 Foundation
**Target ship: 4-6 weeks after Commit 4 (calibration cleanup) is verified**
**Status: ALL ITEMS LOCKED (2026-04-26)**

| # | Item | Status | Source |
|---|------|--------|--------|
| 1 | AI Risk Governor with capped Opportunity Lean | 🔒 LOCKED | GPT Round 2, Claude refined, GPT audit + verification |
| 2 | Strategy-aware attribution schema | 🔒 LOCKED | GPT audit + Claude verification + GPT lock (2026-04-26) |
| 3 | Synthetic counterfactual case generation | 🔒 LOCKED | GPT audit + Claude verification + GPT lock (2026-04-26) |
| 4 | Pre-V0.1 replay harness for threshold calibration | 🔒 LOCKED | GPT audit + Claude verification + GPT lock (2026-04-26) |

**Tier 1 represents the foundation. Loss-avoidance focus. Conservative scope. Designed to ship within 4-6 weeks once Commit 4 contamination cleanup is complete. Captures the safety floor without yet pursuing alpha generation.**

**Expected ROI contribution at full Tier 1 maturity:** Move full-account ROI from contaminated baseline to 8-15% annual through loss avoidance on regime-misclassified days. Sharpe improvement primarily through drawdown reduction, not through gross return increase.

---

## Tier 2 — V0.2 Alpha Generation
**Target ship: 4-6 weeks after V0.1 stable (estimated Q3 2026)**
**Status: Item 5 in discussion, items 6-7 pending**

| # | Item | Status | Source |
|---|------|--------|--------|
| 5 | Volatility Fair-Value Engine | 🔒 LOCKED | GPT expansion, Claude refinements, GPT verification |
| 6 | Meta-Labeling: should we take this trade at all | 🔒 LOCKED | GPT proposed, Claude refined, GPT verification |
| 7 | Adversarial pre-trade review | 🔒 LOCKED | Claude proposed, GPT refined, GPT verification accept |

**Tier 2 begins alpha generation. Each item is independent — V0.2 can ship any subset. Target: move from loss-avoidance to positive-expectancy strategy selection.**

**Expected ROI contribution at full Tier 2 maturity:** Additional +7-15% annual ROI on top of Tier 1, bringing full system to 15-30% range. Volatility fair-value is the largest single contributor; meta-labeling is the highest leverage given existing rules-engine accuracy gaps.

---

## Tier 3 — V0.3 Edge Stacking
**Target ship: 3-6 months after V0.2 stable (estimated Q4 2026 - Q1 2027)**
**Status: Pending**

| # | Item | Status | Source |
|---|------|--------|--------|
| 8 | OPRA Flow Alpha — structured features, not raw LLM consumption | 🔒 LOCKED | GPT proposed, Claude refined, GPT verification accept |
| 9 | Exit Optimizer — continuous EV evaluator | 🔒 LOCKED | GPT proposed, Claude reframed, GPT verification accept |
| 10 | Counterfactual P&L attribution at strategy-pair level | 🔒 LOCKED | Audit of existing 12E + GPT gap analysis + Claude verification |

**Tier 3 takes the alpha-generation layer and refines it with better data (OPRA flow), better exits (continuous EV), and better learning signal (counterfactual pairs). Each multiplies the value of Tier 2.**

**Expected ROI contribution at full Tier 3 maturity:** Additional +5-12% annual ROI on top of Tier 2. OPRA flow alpha is the largest opportunity given paid Databento subscription is currently underutilized.

---

## Tier 4 — V0.4 Maturation
**Target ship: 6-12 months after V0.3 stable (estimated Q2-Q3 2027)**
**Status: ALL ITEMS LOCKED (2026-04-26)**

| # | Item | Status | Source |
|---|------|--------|--------|
| 11 | Event-Day Playbooks with microstructure timing | 🔒 LOCKED | GPT audit + Claude verification + GPT lock (2026-04-26) |
| 12 | Dynamic Capital Allocation with regime-stability check | 🔒 LOCKED | GPT audit + Claude verification + GPT lock (2026-04-26) |
| 13 | Realized-vs-modeled drift detection | 🔒 LOCKED | GPT audit + Claude verification + GPT lock (2026-04-26) |

**Tier 4 is system maturation. By this stage you have 6-12 months of real data; focus shifts from "more alpha" to "make existing alpha more reliable across regime shifts."**

**Expected ROI contribution at full Tier 4 maturity:** Additional +3-8% annual ROI through better capital efficiency and event-day handling. Drift detection prevents silent degradation rather than producing new alpha.

---

## Tier 5 — V0.5+ Long-term
**Target ship: 12+ months out, possibly never**
**Status: Likely deferred**

| # | Item | Status | Source |
|---|------|--------|--------|
| 14 | Strategy Tournament Engine — research only | ❄️ DEFERRED | GPT proposed, Claude added strict constraints |
| 15 | Cross-Index Diversification — SPX → NDX/RUT | ❄️ DEFERRED | GPT proposed, Claude pushed back |

**Tier 5 is acknowledged but not on the active build path. Tournament engine is research infrastructure that's useful but not on the critical ROI path. Cross-index diversification adds three-system complexity that single-developer maintainability probably can't support sustainably.**

---

## ROI Trajectory Estimates

The cumulative ROI improvement path, from clean-baseline rules engine to fully built-out system:

| Stage | System Capability | Annual Full-Account ROI |
|-------|-------------------|------------------------|
| Clean baseline | Rules + ML, post-Commit-4 | 8-15% |
| + Tier 1 (V0.1) | + AI Risk Governor + Opportunity Lean | 15-25% |
| + Tier 2 (V0.2) | + Vol Fair-Value + Meta-Labeling | 22-32% |
| + Tier 3 (V0.3) | + OPRA Flow + Exit Optimizer | 30-40% |
| + Tier 4 (V0.4) | + Event Playbooks + Drift Detection | 35-45% |
| + Tier 5 (selective) | + Mature edge stacking | 40-50% (best case) |

**Important caveats:**
- Each tier requires the prior to be stable. Skipping tiers compounds risk.
- ROI estimates assume successful build AND successful empirical validation. Real outcomes may be lower if specific edges fail to materialize in live trading.
- 50%+ sustained returns require either capacity-limited strategies or genuine alpha that outpaces market adaptation. Both are hard.
- Compounding matters more than headline ROI. 35% sustained for 5 years turns $100k into $448k.

---

## Architectural Principles (Locked Across All Tiers)

These principles govern every improvement and cannot be violated by any individual item:

1. **AI controls admissibility and size ceilings, not trade execution.** This is the core architectural commitment from Round 2. Every tier honors it.

2. **Rules engine is the safety floor.** Constitutional invariants (-3% halt, time stops, sizing tiers, streak halt) cannot be overridden by AI at any tier.

3. **Defined-risk only for AI-influenced positions.** No naked short optionality regardless of AI conviction.

4. **Empirical validation precedes deployment.** Every new layer goes through replay harness validation before going live.

5. **Counterfactual ledgers required.** Every AI-influenced decision generates a counterfactual P&L record. No selection-bias accumulation.

6. **Strategy-aware attribution.** P&L labels must match payoff structure per strategy type. Generic "trade won/lost" insufficient.

7. **Single-developer maintainability.** Architecture must be understandable and modifiable by one person. Sophistication that requires a team is rejected.

8. **Cost is not the constraint.** Annual AI API costs are projected under $1k. Bad decisions are the constraint.

---

## Discussion Log

This section tracks each item's discussion history. Updated as items move through 🟡 IN DISCUSSION → 🔒 LOCKED.

### Item 1-4: Locked from Round 2 (2026-04-25)
See `MARKETMUSE_AI_ARCHITECTURE_v1.md` (to be produced) for full specifications.

### Item 5: Volatility Fair-Value Engine (LOCKED 2026-04-25)
**Status:** 🔒 LOCKED
**Specification:** See `ITEM_5_VOLATILITY_FAIR_VALUE_ENGINE_LOCKED.md`

**Three rounds of iteration:**
- Round 1: GPT produced initial spec (HAR-RV, two-layer IV extraction, strategy EV table)
- Round 2: Claude pushed back on 7 refinements + 2 additions; GPT accepted 5, modified 2 (Refinement 4 and Addition 2)
- Verification round: 3 clarifications on recovery, tilt suppression, skew vs smile asymmetry

**Key architectural commitment:** Vol Fair-Value Engine is a deterministic measurement system, NOT a trading brain. It outputs strategy-conditional EV table; meta-labeler and AI Risk Governor decide what to do with it.

**Expected ROI contribution:** -2% to +3% months 1-3 (calibration), +1% to +5% months 4-6 (constrained authority), +5% to +10% months 7-12 (mature).

**Critical promotion gate:** Baseline E (full stack with engine) must beat Baseline F (full stack minus engine) — proves marginal contribution within production architecture, not just isolated improvement over rules-only.

### Item 6: Meta-Labeling — Should We Take This Trade At All? (LOCKED 2026-04-25)
**Status:** 🔒 LOCKED
**Specification:** See `ITEM_6_META_LABELER_LOCKED.md`

**Two rounds of iteration plus verification:**
- Round 1: GPT produced sample-efficient three-part hybrid (Bayesian prior + regularized logistic + memory analogs)
- Round 2: Claude pushed back on 3 verifications + 1 addition (IC max-loss-zone definition, hierarchical pooling specification, drift detection rigor, time-bucket-aware priors)
- Verification round: GPT accepted all with sharper refinements (peak+twap penalty, smooth Bayesian pooling, Wilson interval with absolute floor)

**Key architectural commitment:** Meta-labeler is a calibrated skip/reduce filter, NOT a trade generator. Sample-efficient by design. Cannot override Governor or increase risk.

**Critical sizing rule:** `final_size = min(constitutional_cap, rules_cap, governor_cap, meta_cap)` — caps compose by minimum, never by averaging.

**Expected ROI contribution:** 0% months 1-3 (paper-only), +1% to +3% months 4-6 (constrained skip authority), +3% to +7% months 7-12 (mature).

**Iran-day protection encoded directly:** `event_day_short_gamma_flag` in IB utility label penalizes IB trades on geopolitical shock days regardless of P&L outcome.

### Item 7: Adversarial Pre-Trade Review (LOCKED 2026-04-25)
**Status:** 🔒 LOCKED
**Specification:** See `ITEM_7_ADVERSARIAL_REVIEW_LOCKED.md`

**One round plus verification:**
- Round 1: Claude proposed selective high-conviction kill-switch with cross-vendor model selection
- Verification round: 3 verifications + 1 structural question, all accepted with refinements

**Key architectural commitment:** Item 7 is INSURANCE, not core ROI infrastructure. Selective trigger conditions (target 5-20% of trades). V0.2 advisory only, V0.3 production cap if calibration passes.

**Critical sequencing:** Build infrastructure in V0.2 (advisory authority only). Promote to production blocking authority in V0.3 only if 30+ blocks accumulated, positive adversarial_value, response stability passes, and latency thresholds met.

**Expected ROI contribution:** 0% months 1-3, 0% to +1% months 4-6, +1% to +3% months 7-12. NOT a primary ROI engine — deprecation possible if calibration shows negative value.

**Iran-day note:** Adversarial review does NOT fire on Iran-day IB trades — they're already blocked by Governor and meta-labeler. Adversarial layer's value is in residual confirmation-bias cases, not obvious failures.

### Item 8: OPRA Flow Alpha — Structured Features (LOCKED 2026-04-25)
**Status:** 🔒 LOCKED
**Specification:** See `ITEM_8_OPRA_FLOW_ALPHA_LOCKED.md`

**One round plus verification:**
- Round 1: GPT produced 20-feature spec with deterministic flow_alpha_engine architecture
- Verification round: 3 verifications (Lee-Ready aggressor signing, flow_persistence formula, quantitative acceptance gates) + 1 addition (0DTE-specific validation), all accepted with production safeguards

**Key architectural commitment:** OPRA features are DETERMINISTIC and feed Items 5/6/Governor as structured inputs. The LLM never reads raw OPRA data. Item 6 with OPRA features must beat Item 6 without OPRA features on calibration, realized utility, and drawdown — otherwise OPRA stays research-only.

**Expected ROI contribution:** 0% months 1-3 (collect/replay), +0% to +2% months 4-6 (advisory), +4% to +8% base / +8% to +12% bull months 7-12 (production if validated).

**Critical production test:** Marginal-value gate at meta-labeler level. Item 8 doesn't get production authority by being interesting — it gets it by demonstrably improving Item 6's performance.

**Storage discipline:** Redis live state with TTL + LTRIM (matching Commit 2 fix pattern). Supabase durable bars only — never raw ticks.

### Item 9: Exit Optimizer (LOCKED 2026-04-25)
**Status:** 🔒 LOCKED
**Specification:** See `ITEM_9_EXIT_OPTIMIZER_LOCKED.md`

**One round plus verification:**
- Round 1: GPT produced deterministic forward-EV exit advisor reusing Item 5 machinery, V0.3 advisory / V0.4 production sequencing
- Verification round: 3 verifications + 1 addition + 1 structural question, all accepted with refinements

**Key architectural commitment:** Exit optimizer ADVISES in V0.3, EARNS limited authority in V0.4 strategy-by-strategy. Static exits remain the execution backbone. Adaptive exits can ONLY cause earlier exits, never later. Constitutional gates absolute.

**Critical principle:** A bad entry filter skips one trade; a bad exit optimizer can damage every open trade. Promotion to production authority must reflect this asymmetry.

**Path-dependence handling:** Trajectory features (giveback, path_vol, profit_velocity) adjust uncertainty multiplicatively, NOT raw EV. Smooth trades have tighter thresholds; volatile-trajectory trades have wider thresholds.

**14:30 close interaction:** Mandatory close embedded in every simulation as forced terminal exit. Optimizer cannot recommend impossible holds past 14:30.

**Adaptive exit slippage:** Adjustment factor 1.0 + vol stress + time pressure + spread widening + stress flag, capped at 3x. EV_hold also includes simulated path slippage. No apples-to-oranges comparison.

**Expected ROI contribution:** 0% months 1-3 (paper calibration), 0% to +1% months 4-6 (V0.3 advisory), +2% to +5% base / +5% to +7% bull months 7-12 (V0.4 if validated).

### Item 10: Counterfactual P&L Attribution (LOCKED 2026-04-25)
**Status:** 🔒 LOCKED
**Specification:** See `ITEM_10_COUNTERFACTUAL_PNL_LOCKED.md`

**Different process — audit not design:** Item 10's counterfactual engine ALREADY EXISTS, shipped as Section 12E commit 2400e98 on 2026-04-20. Operator correctly noted this and asked for audit-and-upgrade rather than design-from-scratch.

**One round plus verification:**
- Round 1: GPT audited existing engine against locked Items 5-9 needs, identified 5 known gaps + 4 architectural conflicts, recommended dual-layer split (legacy reporter vs calibration-grade engine)
- Verification round: 3 verifications + 1 addition (slippage modeling), all accepted with operational refinements

**Key architectural commitment:** DO NOT REWRITE existing engine. Split into Legacy Counterfactual Reporter (existing, observability-only) and Calibration-Grade Attribution Engine (new, strategy-aware, after-slippage). Legacy outputs marked `legacy_observability_only, calibration_eligible = false` and never used for training.

**Critical principle from spec:** Wrong labels are worse than missing labels. Pre-Commit-4 contaminated outputs and approximate-width simulations must NEVER be used for Items 5-9 calibration.

**Most important fix (per GPT):** strategy_hint capture at decision time. Without it, every downstream calibration consumer learns from systematically wrong labels. This is the load-bearing change.

**Three-tier degradation:** calibration_grade (real strikes available) / approximate_width (VIX table defaults) / insufficient_strategy_context (NULL). Explicit tiers prevent silent corruption.

**Architectural enforcement:** calibration_eligible filter must be structural in API functions, not convention. Diagnostic access requires explicit opt-in that's logged and noisy.

**Slippage model:** counterfactual_pnl_after_slippage is training-grade; simulated_pnl_gross is audit-only. Naming convention enforces correct usage. Slippage formula adjusts by strategy/time/vol/spread/size with 3.0x cap.

**Expected ROI contribution:** +6% to +15% INDIRECT (multiplier on Items 5-9). Counterfactual P&L attribution doesn't generate alpha directly; it ensures Items 5-9 calibrate correctly and don't over-promise in replay vs live.

**Migration sequencing:**
- V0.2 immediate: data integrity fixes (strategy_hint capture, three-tier logic, halt-day labeling, frontend fixes, path metrics start)
- V0.2 with Items 5/6: strategy-specific simulators, utility labels, after-slippage P&L
- V0.3 with Items 7/8: adversarial attribution, OPRA snapshots, synthetic cases
- V0.4 with Item 9: static-vs-adaptive ledger, exit slippage integration

### Item 11: Event-Day Playbooks (started 2026-04-25)
**Status:** 🟡 IN DISCUSSION

**Context:** First Tier 4 item. The system's worst losses come from event days handled poorly (Iran day, Fed surprises, etc.). Item 11 proposes pre-defined playbooks per event class with microstructure timing rules — what to do, what to avoid, when to act, when to wait.

**Pending Claude opening position and prompt for GPT.**

---

## Cross-References

This document references and is referenced by:
- `MARKETMUSE_AI_ARCHITECTURE_v1.md` — locked Round 2 architecture (Items 1-4)
- `FINAL_DEPLOY_PLAN_v2.md` — Commits 1-10 deploy sequence (data pipeline cleanup, prerequisite to V0.1)
- `OUTSTANDING_WORK_REGISTRY.md` — broader project backlog including non-AI items
- Future: `MARKETMUSE_AI_ARCHITECTURE_v2.md` — final consolidated architecture document produced after all items in this registry reach 🔒 LOCKED status

---

## How To Update This Document

When an item is discussed:
1. Move from ⏳ PENDING to 🟡 IN DISCUSSION
2. Add entry to Discussion Log with Claude's opening position and open questions
3. After GPT response and iteration: update Discussion Log with synthesized agreements
4. When agreed: move to 🔒 LOCKED, produce formal specification, move to next item

When an item is rejected or deferred:
1. Move to ❌ REJECTED or ❄️ DEFERRED
2. Document the reasoning in Discussion Log
3. Note revisit conditions if applicable

---

*Document maintained throughout the multi-model architecture session. Each update should preserve prior decisions; never silently revise locked items.*
