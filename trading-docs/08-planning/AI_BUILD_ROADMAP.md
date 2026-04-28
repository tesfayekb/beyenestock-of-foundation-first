# MarketMuse — AI Build Roadmap v1.7
**Owner:** tesfayekb
**Drafted:** 2026-04-28 (ET)
**Revised:** 2026-04-28 — v1.4 → v1.5 applies 7 items previously raised but unfixed: **CR-1** (CRITICAL silent drop — §3.4 phantom "sub-item 14D.6" reference; VIX spread width recalibration baseline genuinely missing from §3.4 enumeration; added as new Stage 1 sub-item 10 with full renumbering of Stage 2 sub-items 10-12 → 11-13 and Stage 3 sub-items 13-15 → 14-16; §3.4 header sub-item count 15 → 16) + **H-1** (§6 source citation history v1.0 → v1.1 → v1.2 narrative line extended to capture v1.3/v1.4/v1.5 inheritance) + **H-2** (§8 Coverage check intro v1.2 restated post Cursor v1.1 H-C → v1.5 inherits v1.2 restatement post Cursor v1.4 review) + **H-3** (§8 footnote "Cursor v1.2 verification" → "Cursor v1.5 verification") + **M-1** (§3.4 header "15 build sub-items" → "16 build sub-items (Stages 1-3) + Stage 4 sub-items owned by Item 9 per registry §138 — see AI-SPEC-009 build commitment in §3.10") + **M-2** (§4 Item 10 footnote "see §3.4 for full 4-stage table" → "see §3.4 for full 4-stage breakdown" — §3.4 is prose enumeration not a table) + **N-1** (v1.4 header carryover typo "subsequent v1.4" → "subsequent v1.5"). **Honest acknowledgment of v1.4 framing error:** v1.4 header asserted "No items deferred from this draft" while 6 items from Cursor's prior v1.3 review were in fact unfixed; that claim was structurally false; v1.5 corrects by applying all 7 items per operator standing rule (fix-now over defer-to-later) and acknowledging the v1.4 mistake explicitly.
**Patch v1.5 → v1.6 applies Cursor combined-round O-2 (2 sites — Master Plan version reference now stale at v2.0.1 because Master Plan advanced v2.0.1 → v2.0.2 in same combined round; status line + footer hardcoded references updated to v2.0.2) + O-2-derived forward-pointer roll-forward (1 site, NOT in Cursor's O-2 enumeration but identified by operator per same H-1 next-version anchor pattern Cursor approved at DP v1.3 → v1.4 + DP v1.5 → v1.6: line 6 "subsequent v1.6" became self-referential when this document moved v1.5 → v1.6, so rolled to "subsequent v1.7" — same logic as M-1 finding 3rd site Cursor missed). 3 sites total. Per operator standing rule (fix-now over defer-to-later) applied symmetrically to all combined-round items.
**Patch v1.6 → v1.7 applies converged-state cleanup from second combined verification round (Cursor identified 7 bounded residuals across the trio after the v1.6 O-2 cleanup advanced this doc + DP but didn't propagate companion-version references back to Master Plan; same recursion problem the O-2 cleanup itself was meant to fix, only polarity flipped). 6 physical sites in this document covering Cursor's 4 logical fixes: (i) cross-doc version updates: status line + footer references "Master Plan v2.0.2 + DP v1.7" → "Master Plan v2.0.3 + DP v1.8" (2 sites); (ii) O-2-derived forward-pointer roll-forward: "subsequent v1.7" → "subsequent v1.8" per next-version anchor pattern (1 site); (iii) H-1/H-2/H-3 carryover residuals from prior cycle that O-2 cleanup missed: §6 source-citation history "v1.3/v1.4/v1.5 inherit" → "v1.3/v1.4/v1.5/v1.6/v1.7 inherit" (1 site) + §8 Coverage check intro "v1.5 inherits v1.2 restatement post Cursor v1.4 review" → "v1.5/v1.6/v1.7 inherit v1.2 restatement post Cursor v1.4/v1.5 reviews" (1 site) + §8 final footnote "Cursor v1.5 verification" → "Cursor v1.7 verification" (1 site). Per operator standing rule (fix-now over defer-to-later) applied symmetrically including derived items per Cursor's "DO NOT INTRODUCE FURTHER REGRESSION" instruction. Build Roadmap settles at v1.7; trio commit-ready as Master Plan v2.0.3 + Build Roadmap v1.7 + DP v1.8.
**Status:** **DRAFT v1.7** — Phase 2 Document 1; all v1.2 deferred cosmetic items fixed in v1.3 + cross-reference patched in v1.4 + 7 substantive items from Cursor v1.3 review applied in v1.5 + 3 O-2 cleanup items applied in v1.6 + 6 converged-state cleanup items applied in v1.7 per operator standing rule. Commit-ready as part of Phase 2 deliverable trio (Master Plan v2.0.3 + this v1.7 + Audit Disposition Plan v1.8).
**No items deferred from this draft.** Per operator standing rule "fix-now over defer-to-later" because thread/agent handoffs are silent-drop surfaces that annotation alone cannot fully prevent. If post-commit verification surfaces new items, they will be fixed in a subsequent v1.8 produced before commit.
**Source register:** `trading-docs/04-modules/ai-architecture/archive/raw-locked-specs-2026-04-26/AI_ARCHITECTURE_IMPROVEMENT_REGISTRY.md`
**Authority:** This document governs **what** AI architecture components get built and **in what order**. The Master ROI Plan governs **when** activation events happen (Gates A-F, Action 9). Audit Disposition Plan governs **operator decisions** that change build sequencing. For any conflict, the source register wins.

---

## ⚠️ §0 — READ-ME-FIRST

This document is one of three β-lite governance documents for MarketMuse. **DO NOT READ THIS DOCUMENT IN ISOLATION.** See `MASTER_ROI_PLAN.md` §0 pointer table for full context.

**Authority hierarchy:**
- This document specifies build commitments and tier sequencing
- `MASTER_ROI_PLAN.md` specifies activation gates and operational sequencing
- `AUDIT_DISPOSITION_PLAN.md` specifies operator decisions that may change this document's defaults

**Class C dependency footnote pattern:** Build phases that depend on a Class C audit decision use Class-C-ID-as-anchor citations (e.g., `[C-AI-004-4]`) — NOT numbered footnotes — so the citation survives row reordering and is unambiguous across §§0/2/3. This makes this document revisable rather than re-draftable when audit dispositions land.

**Class C dependency map (load-bearing):**
| Class C item | Default position assumed in this document | If operator vetoes default → reshape impact |
|---|---|---|
| **[C-AI-004-4]** chain archive substrate | option 3: V0.1-advisory-only acceptance | Phase 3C / 3D / 3E (Items 4 + 5 + 10 V0.2) reshape; calibration-grade timeline +6 months |
| **[C-AI-005-1]** D-016 disposition (HAR-RV vs realized) | option 2: HAR-RV new advisory signal, D-016 unchanged | Phase 3E (Item 5 V0.2 calibration-grade) reshape minimal — HAR-RV is additive to D-016, not replacement |
| **[C-AI-005-2]** Item 5 Layer 1 cutover | option 1: Layer 1 stays as legacy observability | Phase 3E reshape minimal — Layer 1 dormant, Layer 2 ships fresh |
| **[C-AI-006-1]** authority recovery | option 2: operator-mediated only | Phase 4A (Item 5) + Phase 4B (Item 6) V0.2 promotion semantics tighten; no automated re-promotion |
| **[C-AI-006-2]** Item 6 Layer 1 (12K bf41175) cutover | option 1: dormant_legacy_observability | Phase 4B reshape minimal — Layer 1 dormant, Layer 2 ships fresh |
| **[C-AI-006-3]** Bayesian prior parameter governance | option 1: operator-tunable via system-state.md | Phase 4B reshape minimal; first promotion-gate review revisits |
| **[C-AI-006-4]** LightGBM Direction Model ownership | option 2: new spec AI-SPEC-016 (renumbered from earlier AI-SPEC-014 to avoid collision with deferred Item 14) | Phase 3G exists (new audit P1.3.9 + new build phase); if option 1, Item 6 V0.2 absorbs sub-scope; if option 3, Item 6 V0.2 ships without 5 LightGBM features |
| **[C-AI-010-1]** Layer 1 §0/§3 contradiction | option 1: surgical Layer 1 NULL-return fix authorized | Phase 3D-i reshape minimal |
| **[C-AI-010-5]** cutover anchor lock | option 1: concrete commit hash post-Commit-4 | Phase 3D ships immediately after Commit 4 verifies; bilateral with Master ROI Plan Action 7 |

If any Class C decision lands differently than its default, the corresponding phase in this document gets a patch, not a re-draft.

---

## 1 — Where the Build Stands Today (2026-04-28)

### 1.1 What's already shipped from the 13 specs
| Item | Spec | What's in production at HEAD `fc6b077` | Source verification |
|---|---|---|---|
| Item 10 Layer 1 | AI-SPEC-010 | Counterfactual Engine (Section 12E) — observability-only, marked `legacy_observability_only`, calibration-ineligible per spec §0 | Shipped at commit `2400e98` 2026-04-20; verified in Cursor inventory §3.A |
| Item 6 Layer 1 (dormant) | AI-SPEC-006 | 12K LightGBM meta-label scoring scaffold — `train_meta_label_model()` at `model_retraining.py:722` + inference at `execution_engine.py:328-399` + `model:meta_label:enabled` Redis flag (default ON, fail-open) | Shipped at commit `bf41175`; `meta_label_v1.pkl` absent at HEAD = pass-through |
| Phase 2A AI synthesis layer | (no locked spec — predates the 13) | `synthesis_agent.py` 628 LOC, dual Anthropic/OpenAI provider, JSON schema, Redis-flag-gated `agents:ai_synthesis:enabled` (default OFF) | Verified in Cursor v1.0 inventory; activation governed by Master ROI Plan Gates A-F |

**That's it.** 1 of 13 components shipped (Layer 1 only); 1 of 13 has a dormant Layer 1 scaffold; 11 of 13 have **no production code**. This is the gap v2.0.1 spine flagged and this roadmap addresses.

### 1.2 What's audited but not built
6 of 13 audits complete (P1.3.1-P1.3.6). Audits produce specifications; **they do not build the components**. The audit redlines are at `trading-docs/08-planning/ai-architecture-audits/AI-SPEC-{001,002,004,005,006,010}.md`.

### 1.3 Operational items (data improvements + infrastructure) that bundle into build phases
Per `trading-docs/08-planning/TASK_REGISTER.md` §11 (Profit Maximization Roadmap, Data Improvements subsection — formerly cited as HANDOFF_3 §15 in v1.0/v1.1; re-sourced to in-workspace canonical TASK_REGISTER.md per Cursor v1.1 H-A and Master ROI Plan §0 pointer table):
- 15A real-time news headlines in prediction context
- 15B options flow signals (Databento OPRA — already paid subscription, currently underutilized)
- 15C VIX full term structure (9D/3M/6M)
- 15D cross-asset signals (HYG, TLT, DXY)
- 15E retail sentiment indicators
- 17C Phase A LightGBM training (after 90 labeled sessions)

These items map into specific build phases below — they are NOT silent drops; each has a phase home. **Specific mapping for §15A-E in §6 below; for §16A-C and §17A-C in §7 below.** §15D and §15E are deferred per Master ROI Plan §6 out-of-scope; §16A and §17A-B are owned by Master ROI Plan Actions 7b / 11 / 12 respectively (not this roadmap).

---

## 2 — Build Phases Ladder

The registry's tier-based sequencing maps to phase numbers as follows. Phase numbering preserves Master Plan §"Phase 3A/3B/3C..." pre-staging convention (audit register §6 governance updates). **Tier tags reflect the registry's locked tier assignment; phase ordering reflects calendar dependency. A Tier-1 phase that ships calendar-after a Tier-2 phase is still a Tier-1 build commitment** (registry says when it ships, not just calendar order). This was corrected from v1.0 — Cursor v1.0 review C-1 caught Item 3 silently demoted Tier-1 → Tier-4 because dependency-chain logic overrode registry tier.

| Phase | Builds | Tier (registry) | Calendar window | Dependencies |
|---|---|---|---|---|
| **Phase 3A** | Item 1 V0.1 (AI Risk Governor — advisory only) | Tier 1 | 4-6 weeks post-Commit-4 | Commit 4 verified |
| **Phase 3B** | Item 2 V0.1 (Strategy-Aware Attribution schema) | Tier 1 | Parallel with 3A | Commit 4 verified |
| **Phase 3X** | Freshness substrate fix (`_safe_redis()` + `gex:updated_at` producer + per-feature drift scaffolding) | Tier 1 | Parallel with 3A; bilateral with Item 1 §3.1 sub-item 3 | Commit 4 verified; bilateral with G-41 from spine §7 |
| **Phase 3C** | Item 4 V0.1 (Replay Harness) | Tier 1 | After 3A + 3B | Chain archive substrate [C-AI-004-4] |
| **Phase 3D** | Item 10 Layer 2 V0.2-immediate ONLY (data integrity fixes — `strategy_hint` capture, three-tier logic, halt-day labeling, frontend fixes, path metrics start) | Tier 1 substrate (Tier 2 spec graduation deferred to bilateral phases per spec §11 migration sequencing) | After Phase 3C | Commit 4 verified [C-AI-010-5] |
| **Phase 3F** | Item 3 V0.1 (Synthetic Counterfactual generation — Scheduled No-Trade Snapshots + 4 Counterfactual Variants for retrieval-coverage / selection-bias mitigation) | **Tier 1** per registry §16-26 + spec line 5 (4-6 weeks). Corrects v1.0 C-1 silent demotion. | After Phase 3D (consumes Item 10 V0.2-immediate scaffolding for `trade_counterfactual_cases` INSERT path) | Phase 3D + Phase 3B Item 2 schema; ownership [C-AI-010-4] |
| **Phase 3E** | Item 5 V0.x (Volatility Fair-Value Engine) | Tier 2 | 4-6 weeks post-V0.1 stable | Phases 3A-D + chain archive [C-AI-004-4] |
| **Phase 3G** | Item 16 V0.x — AI-SPEC-016 LightGBM Direction Model (renamed from AI-SPEC-014 per Cursor v1.0 H-1 to avoid collision with deferred Item 14 Tournament Engine) | Tier 3 (new spec, contingent) | Parallel with 4B; ships before Phase 4B Item 6 V0.2 promotion gate | [C-AI-006-4] → option 2 |
| **Phase 4A** | Item 7 V0.x (Adversarial Pre-Trade Review) | Tier 2 (insurance, not core) | After Phase 3E | Phase 3E V0.2 stable |
| **Phase 4B** | Item 6 V0.2 (Meta-Labeler Layer 2 — Bayesian three-part hybrid). **Bilateral bundles Item 10 V0.2-with-Items-5/6 sub-stage** (strategy-specific simulators, utility labels, after-slippage P&L) per spec §11 migration | Tier 2 | After Phase 3E | Phase 3E + 4A; bilateral Phase 3G |
| **Phase 4C** | Item 8 V0.x (OPRA Flow Alpha). **Bilateral bundles Item 10 V0.3-with-Items-7/8 sub-stage** (adversarial attribution, OPRA snapshots, synthetic case integration) per spec §11 migration | Tier 3 | After Phase 4B | Phase 4B V0.2 stable |
| **Phase 5A** | Item 9 V0.3 advisory → V0.4 production (Exit Optimizer). **Bilateral bundles Item 10 V0.4-with-Item-9 sub-stage** (static-vs-adaptive ledger, exit slippage integration) per spec §11 migration | Tier 3 | After Phase 4B | Phase 4B + Phase 3E |
| **Phase 5B** | Item 13 V0.x (Drift Detection — full Item 13 build per locked spec) | **Tier 4** per registry §75 + spec line 5 | **6-12 months after V0.3 stable** per registry §66. Corrects v1.0 C-2 silent acceleration to Day-60-post-V0.1. P1.3.10 audit cadence (in Master ROI Plan §1.3) is independent of build calendar — audit can happen first-post-V0.1 even if build ships years later. | Phase 4B + 6-12 months V0.3 real data; consumes Phase 3X substrate |
| **Phase 5C** | Item 11 V0.x (Event-Day Playbooks) | Tier 4 | After Phase 5B | Phase 5B drift detection operational |
| **Phase 5D** | Item 12 V0.x (Dynamic Capital Allocation) | Tier 4 | After Phase 5C | Phase 5C + audit register PRE-P12-2 sequencing constraint resolved (Action 7b ladder fix per Master ROI Plan) |
| (Deferred) | Item 14 Tournament + Item 15 Cross-Index | Tier 5 | Likely never | Single-developer maintainability constraint |

**Class C dependencies cited by ID anchor `[C-AI-XXX-N]` per §0; not numbered footnotes.** A future agent looking up `[C-AI-004-4]` finds the canonical resolution in §0 dependency map and `AUDIT_DISPOSITION_PLAN.md`. Numbered footnote scheme dropped from v1.0 per Cursor v1.0 review C-3 — numbered footnotes broke under section-local re-numbering (§2 footnote ² meant [C-AI-010-5] while §0 footnote ² meant [C-AI-006-1]).

---

## 3 — Per-Spec V0.1/V0.2 Build Commitments

Each section below specifies what gets built, in what scope, with what sub-items. Sub-item counts and time estimates come from audit register §6 governance updates per audit redline.

### 3.1 — Item 1 (AI-SPEC-001) AI Risk Governor V0.1 advisory build (Phase 3A)
**Audit:** P1.3.1 complete (PR #60)
**Spec:** `trading-docs/04-modules/ai-architecture/archive/raw-locked-specs-2026-04-26/ITEM_1_AI_RISK_GOVERNOR_LOCKED.md`
**Build commitment:** 11 build sub-items per audit register §6 line 285 + AI-SPEC-001.md §28
**Estimated work:** 4-6 weeks
**ROI vector:** Tier 1 — gates entire AI authority chain
**Critical architectural commitment:** AI controls admissibility and size ceilings, NOT trade execution (registry principle 1). V0.1 is advisory-only (veto + size_multiplier_cap channels)

**V0.1 build sub-items (high-level):**
1. Decision-Card surface (new table)
2. `decision_outcome` enum coordination with AI-SPEC-002 (Item 2)
3. `_safe_redis()` substrate fix (per PRE-P12-1; bilateral with G-41 freshness substrate)
4. D-023 ratification reflection in code (per `AUDIT_DISPOSITION_PLAN.md` enrichment items)
5. Card schema + freeze-version policy (per [C-AI-001-2])
6. Decision-card counting definition (≥200 promotion gate per [C-AI-001-3])
7. Startup-read contract: default 'advisory' or 'disabled', NEVER 'production' (per [C-AI-004-3])
8. Veto channel implementation
9. size_multiplier_cap channel (deferred per [C-AI-001-1]; V0.2 candidate)
10. Opportunity-lean channel scope (per [C-AI-001-3])
11. Tests + replay harness integration (Phase 3C dependency)

**V0.2 promotion gates (per AI-SPEC-001.md §12; bilateral with G-67):**
- ≥200 replay/advisory decision cards
- ≥30 actions
- Wilson lower-95 ≥ 0.40
- Parse rate ≥99.5%
- Prompt frozen ≥10 days

**Class C dependencies:** [C-AI-001-1], [C-AI-001-2], [C-AI-001-3], [C-AI-004-3] (folded into D-023)

---

### 3.2 — Item 2 (AI-SPEC-002) Strategy-Aware Attribution V0.1 (Phase 3B)
**Audit:** P1.3.2 complete (PR #62)
**Spec:** `ITEM_2_STRATEGY_AWARE_ATTRIBUTION_LOCKED.md`
**Build commitment:** 8 sub-items per audit register §6 line 286 + AI-SPEC-002.md §15
**Estimated work:** 3-4 weeks (parallel with Phase 3A)
**ROI vector:** Tier 1 — substrate for Items 5/6/7/9 calibration

**V0.1 build sub-items:**
1. New `strategy_attribution` table
2. New `strategy_utility_labels` table
3. `decision_outcome` enum coordination with Item 1 (FK cascade)
4. Legacy `attribution_*` BOOLEAN columns disposition (per [C-AI-002-3]) — default option = retire post-Item-2 V0.1
5. Pre-Item-2 closed positions cutover policy (per B-AI-002-6) — training contamination handling
6. Per-strategy utility label semantics (canonical 8 strategies, NOT Item 6's 5-strategy subset per B-AI-006-12)
7. Migration scripts
8. Tests + Item 1 Decision-Card integration

**V0.2 promotion gates:** None spec'd directly — Item 2 ships once V0.1 is complete; promotion is "ready for Items 5/6/7/9 to consume"

**Class C dependencies:** [C-AI-002-1], [C-AI-002-3] (folded into D-023)

---

### 3.3 — Item 4 (AI-SPEC-004) Replay Harness V0.1 (Phase 3C)
**Audit:** P1.3.3 complete (PR #63)
**Spec:** `ITEM_4_REPLAY_HARNESS_LOCKED.md`
**Build commitment:** 14 build sub-items per audit register §6 line 287 + AI-SPEC-004.md §13
**Estimated work:** Variable — depends on chain archive decision ([C-AI-004-4])
**ROI vector:** Tier 1 — gates V0.2 promotion of EVERY other AI item

**V0.1 build sub-items (assumes [C-AI-004-4] → option 3 default):**
1. New `replay_eval_cases` table
2. New `item_promotion_records` table
3. 4 migrations
4. 8 `replay_*.py` files
5. Step-0 validation infrastructure
6. Walk-forward validation
7. Chain-archive substrate (Polygon paid OR forward archival OR V0.1-advisory-only acceptance — per [C-AI-004-4])
8. News/event `published_at` TIMESTAMPTZ extension (per B-AI-004-6) — leakage risk for Spec §5 timestamp boundary
9. LightGBM artifact-log substrate (per B-AI-004-10) — affects Item 6 V0.2 reproducibility
10. Polygon historical 1-min fetch capability (per B-AI-004-4) — may require Polygon paid tier
11. `backend/scripts/backtest_gex_zg.py` deprecation (per B-AI-004-2) — Spec §1 hard rule violation
12. Promotion-court infrastructure
13. Deterministic random seeds + reproducibility testing
14. Tests + Item 1 Decision-Card integration

**V0.2 promotion gates:** None — Item 4 ships when V0.1 is complete; subsequent items use Item 4 as their promotion infrastructure

**Class C dependencies:** [C-AI-004-1], [C-AI-004-2], [C-AI-004-3], **[C-AI-004-4]** (CRITICAL — folded into D-023)

---

### 3.4 — Item 10 Layer 2 (AI-SPEC-010) Counterfactual P&L canonical (Phase 3D V0.2-immediate; bilateral 4B/4C/5A for V0.2-strategy / V0.3 / V0.4)
**Audit:** P1.3.4 complete (PR #64)
**Layer 1:** Already shipped at commit `2400e98` 2026-04-20 (observability-only, calibration-ineligible)
**Spec:** `ITEM_10_COUNTERFACTUAL_PNL_LOCKED.md`
**Build commitment:** 16 build sub-items (Stages 1-3) + Stage 4 sub-items owned by Item 9 per registry §138 — see AI-SPEC-009 build commitment in §3.10. Per audit register §6 lines 288 + 297 + AI-SPEC-010.md §11. **(M-1 fix:** v1.4 said "15 build sub-items" without Stage 4 ownership clarification; v1.5 explicit per Cursor v1.4 review.)
**Estimated work:** 4-6 weeks across all 4 migration stages (registry §138 4-stage sequence)
**ROI vector:** Tier 1 substrate / Tier 2 strategy-specific / Tier 3 adversarial / Tier 4 exit per spec migration sequencing (corrects v1.0 C-4 — single-phase collapse lost spec §11 sequencing intent)

**4-stage migration per spec §11 (corrects v1.0 C-4):**

**Stage 1 — Phase 3D V0.2-immediate (Tier 1 substrate, ships standalone after Phase 3C):**
1. New `trade_counterfactual_cases` table (canonical Layer 2 schema)
2. `strategy_hint` capture at decision time (load-bearing per spec §3.2 — "wrong labels are worse than missing labels")
3. Three-tier degradation: `calibration_grade` / `approximate_width` / `insufficient_strategy_context`
4. `calibration_eligible` filter — STRUCTURAL in API functions, not convention
5. Halt-day labeling (Item 10 V0.1 surgical fix per [C-AI-010-1])
6. Path metrics start
7. Frontend fixes (legacy `legacy_observability_only` cutover)
8. Cutover anchor lock per [C-AI-010-5] — bilateral with Master ROI Plan Action 7
9. Item 3 vs Item 10 INSERT ownership per [C-AI-010-4] (Item 3 INSERTs into Item 10 table — bilateral with Phase 3F Item 3 V0.1)
10. **VIX spread width recalibration baseline (per B-AI-010-8 versioned width table; bilateral with TASK_REGISTER §11 16B / G-55 — runs after 20 trades validate IC/IB target_credit fix sequence post-Commit-4)** — added per Cursor v1.4 review CR-1; closes phantom "sub-item 14D.6" reference from §7 16B row that had no enumerated home in §3.4 prior to v1.5

**Stage 2 — Phase 4B-bilateral V0.2-with-Items-5/6 (Tier 2 strategy-specific, ships with Item 6 V0.2):**
11. Strategy-specific simulators (8 canonical strategies — bilateral with Item 6 §3.8 sub-item 7 strategy taxonomy correction)
12. Per-strategy utility labels (consumes Item 2 schema from Phase 3B)
13. After-slippage P&L computation (`counterfactual_pnl_after_slippage` training-grade)

**Stage 3 — Phase 4A-bilateral + 4C-bilateral V0.3-with-Items-7/8 (Tier 3, ships with Items 7 + 8):**
14. Adversarial attribution (bilateral with Item 7 Phase 4A `adversarial_value` field)
15. OPRA snapshots integration (bilateral with Item 8 Phase 4C deterministic features)
16. Synthetic case integration end-to-end (bilateral with Item 3 Phase 3F V0.1 `case_type='counterfactual'` reclassification path)

**Stage 4 — Phase 5A-bilateral V0.4-with-Item-9 (Tier 4, ships with Item 9 V0.4):**
- (Sub-items deferred to Item 9 spec §3 — static-vs-adaptive ledger + exit slippage integration; not enumerated here as separate Item 10 sub-items because they're owned by Item 9 build commitment per registry §138 Stage 4)

**`simulated_pnl_gross` audit-only path** is naming-convention enforcement applied across all 4 stages — not a separate sub-item.

**Slippage formula** (adjusts by strategy/time/vol/spread/size with 3.0x cap) is applied in Stage 2 (after-slippage P&L) and Stage 4 (exit slippage). z-score producer authority for slippage formula per [C-AI-010-3] — shared `features:*` namespace owned by `calibration_engine` per D-019.

**V0.2 promotion gates (per G-70):**
- Chain-archive sufficiency (bilateral with [C-AI-004-4])
- Commit-4 cutover anchor active

**Class C dependencies:** [C-AI-010-1], [C-AI-010-2], [C-AI-010-3], [C-AI-010-4], **[C-AI-010-5]** (CRITICAL anchor — folded into D-023)

---

### 3.5 — Item 5 (AI-SPEC-005) Volatility Fair-Value Engine V0.x (Phase 3E)
**Audit:** P1.3.5 complete (PR #65)
**Spec:** `ITEM_5_VOLATILITY_FAIR_VALUE_ENGINE_LOCKED.md`
**Build commitment:** 18 build sub-items per audit register §6 line 291 + AI-SPEC-005.md §11
**Estimated work:** 8-12 weeks advisory + 6+ months calibration-grade [C-AI-004-4]
**ROI vector:** Tier 2 — feeds EV table to Items 1/6/9; LARGEST Tier 2 contributor per registry

**V0.x build sub-items (high-level):**
1. New engine module (HAR-RV)
2. New `vol_fair_value_snapshots` table
3. `vol:*` Redis namespace
4. Reliability-score state machine
5. `rv_forecast_final` field
6. Multi-year SPX 5-min bar history substrate (per B-AI-005-2) — calibration prerequisite
7. Pre-V0.2 substrate minimums per B-AI-005-15 (30-60 / 90 / 60 / 100 / 100 / 30 sessions)
8. `polygon:spx:overnight_gap` consumer-only orphan resolution (per B-AI-005-4)
9. `fc64840` cutover anchor for daily-RV history (per B-AI-005-17, verified 2026-04-20)
10. D-016 disposition (HAR-RV vs realized term per [C-AI-005-1])
11. Layer 1 cutover policy (per [C-AI-005-2]) — default option 1 = Layer 1 stays as backward-compat
12. Authority recovery semantics (per [C-AI-006-1])
13. Item 4 chain-archive bilateral dependency (per [C-AI-005-3] + [C-AI-004-4])
14. Surface features (full vol-surface ingestion)
15. Calibration loop (HAR-RV training)
16. Production-vs-advisory state machine
17. Tests + Item 4 replay harness integration
18. Frontend visualization

**V0.x promotion gates (per G-68 + AI-SPEC-005.md §7):**
- **V0.2 paper-binding:** Baseline E beats Baseline F on Item 4 replay
- **V0.2 calibration-grade:** chain-archive sufficiency

**Class C dependencies:** [C-AI-005-1], [C-AI-005-2], [C-AI-005-3] (folded into D-023; defaults per §0 dependency map)

---

### 3.6 — Item 16 (AI-SPEC-016) LightGBM Direction Model V0.x (Phase 3G — CONTINGENT)
**Renamed in v1.1:** Was Item 14 / AI-SPEC-014 / Phase 3F in v1.0. Renamed per Cursor v1.0 H-1 to avoid collision with registry's deferred Item 14 (Strategy Tournament Engine, Tier 5). Phase letter shifted from 3F to 3G to make room for Item 3 V0.1 at Phase 3F (corrects v1.0 C-1).
**Trigger:** ONLY if [C-AI-006-4] → option 2 (default position) — adds new spec to architecture catalog
**Audit:** P1.3.9 contingent — see `MASTER_ROI_PLAN.md` Action 4b
**Spec:** Does not exist yet — Phase 3G includes spec authoring as a precondition
**Build commitment:** Variable; depends on which 5 LightGBM fields Item 6 §3.4 references (`p_bull`, `p_bear`, `direction_confidence`, `direction_edge`, `strategy_direction_alignment`)
**Estimated work:** 3-5 weeks (spec + build)
**ROI vector:** Tier 3 — feeds Item 6 advisory `w_logistic` channel

**V0.x build sub-items (preliminary, pending audit P1.3.9):**
1. Spec authoring (P1.3.9 redline) — produces canonical `AI-SPEC-016.md`
2. New module: `backend/lightgbm_direction_model.py`
3. Training pipeline (extends 12H Phase A scaffold at `prediction_engine.py:71-89, 512-599`)
4. Model artifact: `backend/models/direction_lgbm_v1.pkl` (currently absent)
5. Inference path in prediction_engine
6. 5 output fields exposed to Item 6 (`p_bull`, `p_bear`, `direction_confidence`, `direction_edge`, `strategy_direction_alignment`)
7. Tests
8. Bilateral coordination with Item 6 V0.2 build (Phase 4B)

**V0.x promotion gates:** TBD per audit P1.3.9

**Class C dependencies:** **[C-AI-006-4]** (CRITICAL — gates whether this phase exists at all)

---

### 3.7 — Item 7 (AI-SPEC-007) Adversarial Pre-Trade Review V0.x (Phase 4A)
**Audit:** Pending P1.3.x (registry §6 line 290 — bilateral with B-AI-006-6 calendar-blocker)
**Spec:** `ITEM_7_ADVERSARIAL_REVIEW_LOCKED.md` (583 lines)
**Build commitment:** TBD per audit; insurance not core ROI
**Estimated work:** 3-4 weeks V0.x advisory; V0.3 production cap if calibration passes
**ROI vector:** Tier 2 (insurance) — 0% months 1-3, 0% to +1% months 4-6, +1% to +3% months 7-12 per registry

**Critical architectural commitment from registry:** Item 7 is INSURANCE, not core ROI infrastructure. Selective trigger conditions (target 5-20% of trades). V0.2 advisory only, V0.3 production cap if calibration passes. **Deprecation possible if calibration shows negative value.**

**V0.x build sub-items (preliminary, pending audit):**
1. Adversarial agent module
2. Cross-vendor model selection (registry: Claude proposed, GPT refined)
3. Selective high-conviction kill-switch logic
4. V0.2 advisory authority only
5. V0.3 production-blocking authority gate: 30+ blocks accumulated, positive `adversarial_value`, response stability passes, latency thresholds met
6. Bilateral with Item 6 V0.2 (Phase 4B)
7. Tests

**V0.x promotion gates:** Per registry — 30+ blocks + positive adversarial_value + stability + latency

---

### 3.8 — Item 6 (AI-SPEC-006) Meta-Labeler Layer 2 V0.2 (Phase 4B)
**Audit:** P1.3.6 complete (PR #67)
**Layer 1:** Dormant scaffold (12K bf41175) — see §1.1 above
**Spec:** `ITEM_6_META_LABELER_LOCKED.md`
**Build commitment:** 17 build sub-items per audit register §6 line 289 + AI-SPEC-006.md §13
**Estimated work:** 6-10 weeks advisory + 6+ months production
**ROI vector:** Tier 2 — KEYSTONE admissibility decision-maker; strongest Brier/utility uplift in registry projections

**Critical architectural commitment:** Layer 1 (12K LightGBM scaffold) stays as `dormant_legacy_observability` per default [C-AI-006-2]. Layer 2 ships fresh as canonical Bayesian three-part hybrid.

**V0.2 build sub-items (high-level):**
1. New module: `backend/meta_labeler_engine.py` (or absorb LightGBM Direction Model per [C-AI-006-4] option 1)
2. Bayesian three-part hybrid: prior + logistic + memory
3. Hardcoded prior parameters (alpha=1, beta=1, k=20, w_prior=0.55/0.40/0.25 per spec §2)
4. Operator-tunable governance for prior parameters per [C-AI-006-3]
5. Memory retrieval substrate (bilateral with Item 7 build via B-AI-006-6)
6. Logistic regression training (consumes Item 16 LightGBM features if Phase 3G ships, else Item 6 fallback)
7. Strategy taxonomy: canonical 8 strategies (NOT 5-strategy subset per B-AI-006-12) — bilateral with Item 2 V0.1
8. Authority recovery semantics per [C-AI-006-1]
9. Layer 1 cutover (default option 1: dormant; per [C-AI-006-2])
10. Champion-challenger infrastructure (existing `run_meta_label_champion_challenger` at `model_retraining.py:984+` repurposable)
11. 5 LightGBM Direction Model fields integration per [C-AI-006-4]
12. Item 5 vol-surface input integration (Phase 3E dependency)
13. Item 7 adversarial review integration (Phase 4A dependency)
14. After-slippage P&L training data from Item 10 Layer 2 (Phase 3D dependency)
15. Decision-Card surface to Item 1 (Phase 3A dependency)
16. Tests + replay harness integration
17. Drift hooks for Item 13 (Phase 5B forward dependency)

**V0.2 promotion gates (per G-69 + AI-SPEC-006.md §10 lines 654-662):**
- Brier ≥5% improvement
- ECE ≤0.12
- Top-bucket positive utility
- 7-criteria gate (full enumeration in spec)

**Class C dependencies:** [C-AI-006-1], [C-AI-006-2], [C-AI-006-3], **[C-AI-006-4]** (all folded into D-023)

---

### 3.9 — Item 8 (AI-SPEC-008) OPRA Flow Alpha V0.x (Phase 4C)
**Audit:** P1.3.7 next per Master ROI Plan Action 3
**Spec:** `ITEM_8_OPRA_FLOW_ALPHA_LOCKED.md` (585 lines)
**Build commitment:** TBD per audit P1.3.7
**Estimated work:** 4-6 weeks V0.x
**ROI vector:** Tier 3 — LARGEST Tier 3 opportunity per registry given paid Databento subscription is currently underutilized

**Critical architectural commitment from registry:** OPRA features are DETERMINISTIC and feed Items 5/6/Governor as STRUCTURED INPUTS. **The LLM never reads raw OPRA data.** Item 6 with OPRA features must beat Item 6 without OPRA features on calibration, realized utility, and drawdown — otherwise OPRA stays research-only.

**V0.x build sub-items (preliminary, pending audit):**
1. Flow alpha engine module (deterministic)
2. 20-feature spec implementation
3. Lee-Ready aggressor signing
4. `flow_persistence` formula
5. 0DTE-specific validation
6. Production safeguards
7. Storage discipline: Redis live state with TTL + LTRIM (matching Commit 2 fix pattern)
8. Supabase durable bars only — never raw ticks
9. **Marginal-value gate at meta-labeler level** (production test): does Item 6 + OPRA beat Item 6 alone?
10. Successor-replace today's `flow_agent.py` (currently brief generator; Item 8 is alpha extractor)
11. Cutover policy from current flow_agent.py (operator decision pending audit)
12. Bundle with TASK_REGISTER.md §11 (formerly HANDOFF_3 §15B options flow signals — Databento) — same paid subscription, same alpha layer

**Bundles legacy HANDOFF_3 items (now in TASK_REGISTER.md §11 per H-A re-citation):**
- 15B Options flow signals (block trades, sweeps) from Databento — this IS Item 8

**V0.x promotion gates:** Marginal-value gate at meta-labeler (per registry critical production test)

**Expected ROI per registry:** 0% months 1-3 (collect/replay), +0% to +2% months 4-6 (advisory), +4% to +8% base / +8% to +12% bull months 7-12 (production if validated)

---

### 3.10 — Item 9 (AI-SPEC-009) Exit Optimizer V0.3 advisory → V0.4 production (Phase 5A)
**Audit:** P1.3.8 next per Master ROI Plan Action 4
**Spec:** `ITEM_9_EXIT_OPTIMIZER_LOCKED.md` (783 lines)
**Build commitment:** TBD per audit P1.3.8
**Estimated work:** 4-6 weeks V0.3 advisory; +4-6 weeks V0.4 production if validated
**ROI vector:** Tier 3 — bilateral with Item 6 V0.2 + Item 5 V0.x

**Critical architectural commitment from registry:** Exit optimizer ADVISES in V0.3, EARNS limited authority in V0.4 strategy-by-strategy. **Static exits remain the execution backbone.** Adaptive exits can ONLY cause earlier exits, never later. Constitutional gates absolute. **A bad entry filter skips one trade; a bad exit optimizer can damage every open trade.**

**V0.3 advisory build sub-items (preliminary, pending audit):**
1. Continuous EV evaluator (reuses Item 5 machinery)
2. Trajectory features: giveback, path_vol, profit_velocity (multiplicative on uncertainty, NOT raw EV)
3. 14:30 close interaction (mandatory close embedded in every simulation as forced terminal exit)
4. Adaptive exit slippage formula (1.0 + vol stress + time pressure + spread widening + stress flag, capped at 3x)
5. EV_hold path slippage simulation (no apples-to-oranges comparison)
6. Static-vs-adaptive ledger (Item 10 V0.4 integration)
7. V0.3 advisory authority (recommendations only)
8. Replaces today's rule-based `position_monitor.py` exit logic

**V0.4 production build sub-items (after V0.3 calibration):**
1. Strategy-by-strategy production authority earning
2. "Earlier exit only" constraint enforcement
3. Bilateral with Item 6 V0.2 (Phase 4B): meta-labeler can override exit optimizer

**V0.x promotion gates:** Per registry (V0.4 promotion: per-strategy validation; "earlier-exit-only" verified)

**Expected ROI per registry:** 0% months 1-3, 0% to +1% months 4-6 (V0.3), +2% to +5% base / +5% to +7% bull months 7-12 (V0.4)

---

### 3.11 — Item 13 (AI-SPEC-013) Drift Detection V0.x (Phase 5B — Tier 4, 6-12 months post-V0.3)
**Audit:** P1.3.10 first post-V0.1 audit per Master ROI Plan §1.3 commitment
**Calendar correction (v1.1 vs v1.0):** v1.0 incorrectly wrote "Day 60 post-V0.1 activation" — Cursor v1.0 review C-2 caught this as silent acceleration. Registry §66 + spec line 5 lock Item 13 at **Tier 4, 6-12 months after V0.3 stable**. Build calendar honors registry. The Tier-1 substrate work (`_safe_redis()` + `gex:updated_at`) that v1.0 conflated into Phase 5B is split out to **Phase 3X** (§3.15 below) — that work IS Day-1-foundational and ships parallel with Phase 3A.
**Spec:** `ITEM_13_DRIFT_DETECTION_LOCKED.md` (1136 lines)
**Build commitment:** TBD per audit P1.3.10
**Estimated work:** 6-8 weeks once V0.3 + 6-12 months real data exists
**ROI vector:** Tier 4 — prevents silent degradation rather than producing new alpha

**Audit-vs-build separation (CRITICAL clarification per Cursor C-2):** The P1.3.10 audit produces the Item 13 redline (timing per Master ROI Plan §1.3 — first audit post-V0.1, no later than Day 60 post-activation). The Item 13 BUILD ships years later when Phase 4B has matured and 6-12 months of V0.3 data exists. Audits and builds run on independent calendars. Operator can audit early to lock spec; build cannot ship before substrate exists.

**Critical architectural commitment from registry:** Tier 4 maturation — by this stage you have 6-12 months of real data; focus shifts from "more alpha" to "make existing alpha more reliable across regime shifts." Drift can auto-demote but NEVER auto-promote.

**V0.x build sub-items (preliminary, pending audit P1.3.10):**
1. Per-feature drift detection (consumes Phase 3X scaffolding)
2. Auto-demotion logic for Items 5/6/7/9 (NOT auto-promotion)
3. Operator-override drift authority
4. Dependency graph for cross-spec demotion cascades
5. Material auto-promotion explicitly DISABLED
6. Drift-triggered audit cadence integration

**V0.x promotion gates:** TBD per audit P1.3.10

**Bundles legacy HANDOFF_3 items (now in TASK_REGISTER.md §11 per H-A re-citation):**
- 17C Phase A LightGBM training pipeline gated on 90 sessions — Phase 5B retraining substrate uses this

---

### 3.12 — Item 11 (AI-SPEC-011) Event-Day Playbooks V0.x (Phase 5C)
**Spec:** `ITEM_11_EVENT_DAY_PLAYBOOKS_LOCKED.md` (874 lines)
**Audit:** Pending (Cluster C)
**Build commitment:** TBD per audit
**Estimated work:** 6-10 weeks
**ROI vector:** Tier 4

**Architectural framing from registry:** Pre-defined playbooks per event class with microstructure timing rules — what to do, what to avoid, when to act, when to wait. **The system's worst losses come from event days handled poorly (Iran day, Fed surprises, etc.).**

**V0.x build sub-items (preliminary, pending audit):**
1. Per-event policies (FOMC, CPI, NFP, geopolitical, earnings clusters)
2. IV-crush schedules
3. Liquidity gates per event class
4. Microstructure timing rules
5. Replaces today's 2-branch hardcoded if/elif at `prediction_engine.py:195-251`

---

### 3.13 — Item 12 (AI-SPEC-012) Dynamic Capital Allocation V0.x (Phase 5D)
**Spec:** `ITEM_12_DYNAMIC_CAPITAL_ALLOCATION_LOCKED.md` (972 lines)
**Audit:** Pending (Cluster C)
**Build commitment:** TBD per audit
**Estimated work:** 6-10 weeks
**ROI vector:** Tier 4 — bilateral with `_RISK_PCT` ladder fix (Master ROI Plan Action 7b / PRE-P11-3 / Gate F)

**Sequencing constraint (CRITICAL):** Per audit register PRE-P12-2: AI-SPEC-001 → AI-SPEC-013 → AI-SPEC-012 (risk_engine.py module-level merge order). Master ROI Plan Action 7b satisfies the prerequisite by landing the ladder fix before Phase 5D begins.

**V0.x build sub-items (preliminary, pending audit):**
1. Replaces `capital_manager.get_deployed_capital()` static-key reading at `backend/main.py:13`
2. Regime-conditioned allocation
3. Regime-stability check (cooldown logic)
4. Bilateral with `capital:deployment_pct` and `capital:leverage_multiplier` operator-tunable scaling levers (per Master ROI Plan §1.4)

---

### 3.14 — Item 3 (AI-SPEC-003) Synthetic Counterfactual generation V0.1 (Phase 3F — Tier 1)
**Tier correction (v1.1 vs v1.0):** v1.0 placed Item 3 in Phase 5E (Tier 4) with rationale "INSERTs into Item 10 table → ship gated on Phase 3D Item 10 Layer 2 stable." That dependency is real but was misapplied — Cursor v1.0 review C-1 caught this as silent re-tiering of a locked Tier 1 spec. Per registry §16-26 Item 3 is Tier 1; per `ITEM_3_SYNTHETIC_COUNTERFACTUAL_LOCKED.md` line 5: **"Tier: V0.1 Foundation (4-6 weeks)"**. The dependency on Phase 3D justifies calendar ordering (Item 3 ships AFTER Phase 3D), not tier demotion.
**Spec:** `ITEM_3_SYNTHETIC_COUNTERFACTUAL_LOCKED.md` (932 lines)
**Audit:** Pending (will be P1.3.x; cluster-A by registry tier despite session-cluster-C in audit-batch terminology — see §0 note re tier-vs-cluster)
**Build commitment:** TBD per audit; aligned to registry Tier 1 V0.1 Foundation
**Estimated work:** 4-6 weeks per spec
**ROI vector:** Tier 1 — memory-coverage and selection-bias mitigation layer (NOT a training-label generator per spec architectural commitment)

**Architectural commitment from spec line 13:** "Synthetic cases are for retrieval coverage, not training truth." Synthetic cases remain `calibration_eligible = false` in V0.1 AND V0.2. They are NEVER training data. They exist only to provide retrieval coverage and remind the Governor what the system ignored. If a synthetic case becomes training-grade, it must be **reclassified** as a counterfactual replay case (with `case_type='counterfactual'` and full Item 10 three-tier degradation evaluation), not promoted while remaining synthetic.

**V0.1 build sub-items (preliminary, pending audit):**
1. Scheduled No-Trade Snapshots (when system silently ignored a market state)
2. 4 Counterfactual Variants per snapshot (covers what the system would have done under alternate parameters)
3. INSERT into Item 10's `trade_counterfactual_cases` table per [C-AI-010-4] default option 1
4. `case_type='synthetic'` tagging with `calibration_eligible=false` invariant
5. Reclassification path to `case_type='counterfactual'` with full Item 10 three-tier degradation
6. Memory retrieval integration for Item 1 Card builder
7. Selection-bias metrics surface
8. Tests + Item 4 replay harness integration

**V0.1 promotion gates:** None — Item 3 V0.1 ships when sub-items complete; subsequent V0.2 promotion is "synthetic case retrieval coverage validated by Item 1 Card builder consumption metrics"

**Class C dependencies:** [C-AI-010-4] (folded into D-023 — Item 3 INSERT ownership default option 1)

**Calendar ordering:** Phase 3F ships AFTER Phase 3D (consumes Item 10 V0.2-immediate scaffolding). Can ship in parallel with Phase 3E Item 5 V0.x once Phase 3D V0.2-immediate is stable. Tier-1 build commitment satisfied within 4-6 weeks of Phase 3D Stage-1 completion.

---

### 3.15 — Phase 3X Freshness Substrate Fix (Tier 1 — bilateral with Item 1 Phase 3A)
**Source of this section:** v1.0 placed `_safe_redis()` substrate fix + `gex:updated_at` producer inside Phase 5B Item 13 sub-items 2-3. Cursor v1.0 review C-2 caught this as conflation of Tier-4 drift detection build with a Tier-1 safety-critical substrate fix. They are different work items with different tier commitments. Splitting out per Cursor recommendation.
**Tier:** Tier 1 substrate (NOT a 13-spec build; foundational fix)
**Audit register provenance:** PRE-P12-1 + B-AI-001-6 + B-AI-005-16 + B-AI-006-17 (3-audit cross-spec confirmed safety-critical per spine §7 G-41)
**Build commitment:** Substrate fix only — distinct from Item 13 (Phase 5B) which CONSUMES this substrate years later
**Estimated work:** ~1 week (substrate fix); Item 1 Phase 3A's sub-item 3 already accounts for the work — Phase 3X is the explicit rollup
**ROI vector:** Capital-safety substrate (Item 6 admissibility authority depends on freshness gates per architectural principle)

**V0.x build sub-items:**
1. `_safe_redis()` dead code at `prediction_engine.py:100` — wire callers OR remove with explicit note
2. `gex:updated_at` Redis key producer — currently no writer; one of Items 1/4/5 must own it (default: Item 1 Phase 3A scope per §3.1 sub-item 3)
3. Per-feature drift scaffolding (NOT drift detection itself — that's Item 13 / Phase 5B)
4. Freshness staleness alerts feeding Master ROI Plan Action 11 (Resend SMTP migration)
5. Tests asserting `gex:updated_at` is monotonically advancing during market hours
6. Documentation in `system-state.md` of freshness substrate as Day-1-foundational

**Calendar:** Parallel with Phase 3A — substrate must exist before Item 1 V0.1 advisory cards can rely on freshness gates.

**Bilateral references:**
- Item 1 Phase 3A §3.1 sub-item 3 (`_safe_redis()` substrate fix appears as sub-item there too — Phase 3X is the rollup view)
- Item 13 Phase 5B (consumes this substrate years later)
- Spine §7 G-41 (cross-references this section for safety-critical substrate handling)

---

## 4 — V0.1 → V0.2 Promotion Gates Summary

Aggregated from sections 3.1-3.15. This section is the consolidated promotion-gate ladder a future operator/agent uses to assess "is the AI architecture ready for V0.2?"

| Item | V0.1 promotion (Phase 3A-D) | V0.2 promotion |
|---|---|---|
| Item 1 (Risk Governor) | All 11 sub-items + advisory cards flowing | ≥200 cards, ≥30 actions, Wilson-95 ≥0.40, parse rate ≥99.5%, prompt frozen ≥10 days |
| Item 2 (Strategy Attribution) | Schema + FK cascade + decision_outcome enum live | Items 5/6/7/9 consuming attribution successfully |
| **Phase 3X (Freshness Substrate)** | `_safe_redis()` wired + `gex:updated_at` producer + per-feature drift scaffolding | N/A — substrate, not a promotable spec; CONSUMED by Item 13 V0.x at Phase 5B (years later, post-V0.3) |
| Item 4 (Replay Harness) | Chain-archive substrate + replay_eval_cases populated | Promotion court ratified; ≥1 promotion completed via Item 4 |
| Item 10 Layer 2 (Stage 1, Phase 3D V0.2-immediate) | strategy_hint capture live + three-tier degradation + calibration_eligible structural filter | Chain-archive sufficiency + Commit-4 cutover anchor active *(footnote: Stage 1 only; Stages 2/3/4 bundle into Items 5/6 / Items 7/8 / Item 9 promotion gates per spec §11 migration — see §3.4 for full 4-stage breakdown)* |
| Item 3 (Synthetic Counterfactual, V0.1) | Scheduled No-Trade Snapshots + 4 Counterfactual Variants live; INSERT path into Item 10 `trade_counterfactual_cases` working; `case_type='synthetic'` `calibration_eligible=false` invariant enforced | Synthetic case retrieval coverage validated by Item 1 Card builder consumption metrics |
| Item 5 (Vol Fair-Value) | HAR-RV advisory shipping rv_forecast_final | Baseline E beats Baseline F on Item 4 replay |
| Item 6 (Meta-Labeler L2) | Bayesian three-part hybrid live + advisory cards | Brier ≥5%, ECE ≤0.12, top-bucket positive utility, 7-criteria gate |
| Item 7 (Adversarial) | Advisory authority + 5-20% trigger rate | 30+ blocks, positive adversarial_value, stability + latency thresholds |
| Item 8 (OPRA Flow Alpha) | Deterministic features feeding Items 5/6/Governor | Item 6 + OPRA beats Item 6 alone (marginal-value gate) |
| Item 9 (Exit Optimizer) | V0.3 advisory only | V0.4 production: per-strategy validation; "earlier-exit-only" verified |
| Item 13 (Drift Detection) | **N/A — Item 13 has no V0.1; ships post-V0.3 per registry §66 (Tier 4, 6-12 months after V0.3 stable). Substrate work `_safe_redis()` + `gex:updated_at` is split out to Phase 3X above (Cursor v1.1 R-3 corrected v1.0/v1.1 conflation).** | Auto-demotion validated; auto-promotion still DISABLED |
| Item 11 (Event Playbooks) | Per-event policies live; advisory mode | Per-event class validated calibration |
| Item 12 (Dynamic Cap) | regime-stability check + cooldown live | Per-regime allocation validated |

---

## 5 — Per-Tier ROI Trajectory (from registry)

| Tier | Items | Calendar | Annual full-account ROI | Mechanism (registry-attributed) |
|---|---|---|---|---|
| Clean baseline | Rules + ML, post-Commit-4 | Now | 8-15% | Pre-AI rules engine performance |
| **+ Tier 1 (V0.1)** | Items 1, 2, 3, 4, 10 Layer 2 | Q3 2026 | **15-25%** | Loss avoidance on regime-misclassified days; **Sharpe improvement primarily through drawdown reduction, not gross return increase** (registry §29). Item 3 V0.1 is memory-coverage / selection-bias mitigation per spec — its V0.1 ROI contribution is indirect (improves Item 1 Card retrieval coverage) and not separately enumerated in registry per-tier numbers. |
| **+ Tier 2 (V0.2)** | Items 5, 6, 7 | Q4 2026 | **22-32%** | Move from loss-avoidance to positive-expectancy strategy selection; vol fair-value is largest single contributor; meta-labeling highest leverage given existing rules-engine accuracy gaps (registry §45) |
| **+ Tier 3 (V0.3)** | Items 8, 9 + Item 16 contingent | Q1-Q2 2027 | **30-40%** | OPRA flow alpha is the largest opportunity given paid Databento subscription is currently underutilized (registry §61) |
| **+ Tier 4 (V0.4)** | Items 11, 12, 13 | Q3-Q4 2027 | **35-45%** | Better capital efficiency and event-day handling; **drift detection prevents silent degradation rather than producing new alpha** (registry §77). Item 3 was incorrectly listed in this row in v1.0/v1.1 — Cursor v1.1 R-1 caught the silent re-tiering in this table specifically (after §3.14 was corrected). Item 3 is Tier 1 per registry. |
| + Tier 5 (selective) | Items 14, 15 (deferred) | 2028+ | 40-50% (best case) | Mature edge stacking |

**Important caveats from registry (load-bearing — do not drop in any future revision):**
- Each tier requires the prior to be stable. Skipping tiers compounds risk.
- ROI estimates assume **successful build AND successful empirical validation**. Real outcomes may be lower if specific edges fail to materialize in live trading.
- 50%+ sustained returns require either capacity-limited strategies or genuine alpha that outpaces market adaptation. Both are hard.
- Compounding matters more than headline ROI. **35% sustained for 5 years turns $100k into $448k.**
- Tier 1 ROI uplift is **primarily** drawdown reduction, not gross-return increase. A reader skimming the table without this caveat will overestimate Tier 1 alpha generation. (Cursor v1.0 review M-2 corrected v1.0 dropping this qualifying language.)

---

## 6 — Data Improvements Mapping (sourced from `trading-docs/08-planning/TASK_REGISTER.md` §11)

**Source citation history (v1.0 → v1.1 → v1.2; v1.3/v1.4/v1.5/v1.6/v1.7 inherit v1.2 source-citation discipline):** v1.0 cited "HANDOFF_3 §15" without verifying file location — Cursor v1.0 review H-3 caught it. v1.1 cited `/mnt/project/HANDOFF_3_PENDING_TASKS_AND_AI_PLAN.md` claiming verification, but Cursor v1.1 review H-A correctly identified that path as Claude's sandbox environment, NOT the operator's workspace (`/Users/.../beyenestock-of-foundation-first/`). A future agent in the workspace following that citation would hit a missing file. v1.2 corrects this by re-sourcing from `trading-docs/08-planning/TASK_REGISTER.md`, which IS in workspace and IS the canonical line-item source per `MASTER_ROI_PLAN.md` §0 pointer table. v1.3 applied 4 cosmetic items previously deferred. v1.4 was a metadata-only patch for cross-references. v1.5 closes the structural CR-1 silent drop on B-AI-010-8 / G-55 / 16B (VIX spread width recalibration sub-item) per Cursor v1.4 review. v1.6 + v1.7 are bounded cross-doc-version-cleanup cycles only; no source-citation discipline changes.

**The §15A-E line items below trace to TASK_REGISTER.md §11 Profit Maximization Roadmap** (Phase A "Data Improvements" subsection — not directly numbered §15A-E in TASK_REGISTER, but the same line items are present there). Operator may also keep a personal HANDOFF_3 copy in their external sandbox; if so, it's authoritative for the operator but not citable for in-workspace agents.

Every data-improvement item is mapped to a build phase. None are silent drops.

| Item (legacy HANDOFF_3 numbering preserved for cross-reference) | Description | Build phase | Status |
|---|---|---|---|
| **15A** | Real-time news headlines in prediction context | Phase 4B (Item 6 V0.2 — feature input) + Phase 5C (Item 11 — event detection) | Bundles into Phase 4B + 5C |
| **15B** | Options flow signals (block trades, sweeps) from Databento | Phase 4C (Item 8 OPRA Flow Alpha) | IS Item 8 — primary build target |
| **15C** | VIX full term structure (9D/3M/6M) | Phase 3E (Item 5 V0.x — surface features sub-item 14) | Bundles into Phase 3E |
| **15D** | Cross-asset signals (HYG, TLT, DXY) | Out-of-scope V0.1; **deferred to V0.2+** | Per Master ROI Plan §6 out-of-scope |
| **15E** | Retail sentiment indicators (Reddit/Twitter) | Out-of-scope V0.1; **deferred to V2+** per `deferred-work-register.md` | Per Master ROI Plan §6 out-of-scope |

---

## 7 — Other Operational Items Mapping (TASK_REGISTER.md §11 — formerly HANDOFF_3 §16/§17)

| Item (legacy HANDOFF_3 numbering preserved for cross-reference) | Description | Phase / Action |
|---|---|---|
| 16A | Phase ladder fix | Master ROI Plan Action 7b (Gate F) — NOT in this roadmap |
| 16B | VIX spread width recalibration (after 20 trades) | Bundles into Item 10 Layer 2 V0.2 §3.4 Stage 1 sub-item 10 (per B-AI-010-8 versioned width table; runs after 20 trades validate IC/IB target_credit fix sequence post-Commit-4) — Phase 3D. **Citation corrected per Cursor v1.4 review CR-1: v1.0-v1.4 had stale "sub-item 14D.6" reference (carryover from v1.0's pre-collapse 14A/14B/14C/14D numbering scheme); v1.5 added the missing sub-item to §3.4 Stage 1 and updated this citation.** |
| 16C | OCO bracket orders pre-real-capital | Master ROI Plan Action 10 — NOT in this roadmap |
| 17A | Resend SMTP migration | Master ROI Plan Action 11 — NOT in this roadmap |
| 17B | Edge Function deploy for Learning Dashboard | Master ROI Plan Action 12 — NOT in this roadmap |
| 17C | Phase A LightGBM training (after 90 sessions) | Phase 5B (Item 13) sub-item — retraining substrate |

---

## 8 — Findings Tracking (G-N IDs delegated to this document)

| ID | Finding | Source | Resolution path | Status |
|---|---|---|---|---|
| G-1 | AI-SPEC-001 Risk Governor V0.1 advisory build commitment | Cursor gap scan §3.A | Phase 3A | [ ] |
| G-2 | AI-SPEC-002 Strategy Attribution V0.1 build commitment | Cursor gap scan §3.A | Phase 3B | [ ] |
| G-3 | AI-SPEC-003 Synthetic Counterfactual V0.1 build commitment (corrected v1.0 V0.4 / Phase 5E silent re-tiering — Cursor v1.1 R-2) | Cursor gap scan §3.A | Phase 3F | [ ] |
| G-4 | AI-SPEC-004 Replay Harness V0.1 build commitment | Cursor gap scan §3.A | Phase 3C | [ ] |
| G-5 | AI-SPEC-005 Vol Fair-Value V0.x build commitment | Cursor gap scan §3.A | Phase 3E | [ ] |
| G-6 | AI-SPEC-006 Meta-Labeler V0.2 build commitment | Cursor gap scan §3.A | Phase 4B | [ ] |
| G-7 | AI-SPEC-007 Adversarial Review V0.x build commitment | Cursor gap scan §3.A | Phase 4A | [ ] |
| G-8 | AI-SPEC-008 OPRA Flow Alpha V0.x build commitment | Cursor gap scan §3.A | Phase 4C | [ ] |
| G-9 | AI-SPEC-009 Exit Optimizer V0.x build commitment | Cursor gap scan §3.A | Phase 5A | [ ] |
| G-10 | AI-SPEC-010 Layer 2 Counterfactual P&L V0.2 build commitment | Cursor gap scan §3.A | Phase 3D | [ ] |
| G-11 | AI-SPEC-011 Event-Day Playbooks V0.x build commitment | Cursor gap scan §3.A | Phase 5C | [ ] |
| G-12 | AI-SPEC-012 Dynamic Capital Allocation V0.x build commitment | Cursor gap scan §3.A | Phase 5D | [ ] |
| G-13 | AI-SPEC-013 Drift Detection V0.x build commitment (Tier 4, 6-12 months post-V0.3 — corrected v1.0 C-2 silent acceleration) | Cursor gap scan §3.A | Phase 5B | [ ] |
| G-14 | CONTINGENT AI-SPEC-016 LightGBM Direction Model (renamed from AI-SPEC-014 per Cursor v1.0 H-1; G-14 ID retained per Cursor v1.1 H-B since it's the same gap-scan finding under a renamed spec) | Cursor gap scan §3.A | Phase 3G (contingent on [C-AI-006-4] → option 2) | [ ] |
| G-15 | Tiered ROI trajectory commitment | Cursor gap scan §3.A | §5 of this document | [x] |
| G-16 | Cluster A → B → C ship order with cross-tier sequencing | Cursor gap scan §3.A | §2 phases ladder of this document | [x] |
| G-49 | 15A real-time news ingestion | Cursor gap scan §3.C | §6 — bundles Phase 4B + 5C | [ ] |
| G-50 | 15B options flow archival | Cursor gap scan §3.C | §6 — IS Phase 4C Item 8 | [ ] |
| G-51 | 15C VIX term structure full curve | Cursor gap scan §3.C | §6 — bundles Phase 3E | [ ] |
| G-55 | 16B VIX spread width recalibration | Cursor gap scan §3.C | §7 — bundles Phase 3D Item 10 Layer 2 | [ ] |
| G-59 | 17C Phase A LightGBM training pipeline | Cursor gap scan §3.C | §7 — bundles Phase 5B Item 13 | [ ] |
| G-67 | AI-SPEC-001 V0.2 paper-binding gates | Cursor gap scan §3.E | §3.1 — V0.2 promotion gates | [ ] |
| G-68 | AI-SPEC-005 V0.2 promotion: Baseline E vs Baseline F | Cursor gap scan §3.E | §3.5 — V0.x promotion gates | [ ] |
| G-69 | AI-SPEC-006 V0.2 promotion: Brier/ECE/utility/7-criteria | Cursor gap scan §3.E | §3.8 — V0.2 promotion gates | [ ] |
| G-70 | AI-SPEC-010 Layer 2 V0.2 promotion: chain-archive + cutover anchor | Cursor gap scan §3.E | §3.4 — V0.2 promotion gates | [ ] |
| G-71 | Item 4 V0.2 / Item 7 V0.2 promotion gate placeholder — Cursor v1.0 H-2 caught numbering gap (G-67/68/69/70/[71 missing]/72/73). Item 4 V0.2 gate = "Item 4 ships when V0.1 complete; replay harness IS the promotion infrastructure." Item 7 V0.x V0.3-production-promotion gate = 30+ blocks accumulated, positive `adversarial_value`, response stability passes, latency thresholds met (per registry §186 + spec §3) | Cursor v1.0 H-2 numbering-gap fix | §4 promotion-gate ladder rows for Items 4 + 7 | [x] |
| G-72 | Per-channel authority recovery ([C-AI-006-1] cascading Items 5+6) | Cursor gap scan §3.E | §0 dependency map + §3.5 sub-item 12 + §3.8 sub-item 8 | [ ] |
| G-73 | item_promotion_records startup-read contract (advisory NOT production) | Cursor gap scan §3.E | §3.1 sub-item 7 | [ ] |
| G-93 | polygon:spx:overnight_gap consumer-only orphan | Cursor gap scan §3.H | §3.5 sub-item 8 | [ ] |
| G-98 | backend/scripts/backtest_gex_zg.py deprecation | Cursor gap scan §3.H | §3.3 sub-item 11 | [ ] |
| G-99 | backend/models/meta_label_v1.pkl absent dormant_legacy_observability state | Cursor gap scan §3.H | §3.8 sub-item 9 (default [C-AI-006-2] option 1) | [ ] |
| G-100 | Bayesian prior parameter governance | Cursor gap scan §3.H | §3.8 sub-item 4 + §0 dependency map [C-AI-006-3] | [ ] |
| G-101 | Item 6 5-strategy enum is strict subset of canonical 8 | Cursor gap scan §3.H | §3.8 sub-item 7 — strategy taxonomy fix | [ ] |
| G-102 | fc64840 cutover anchor for daily-RV history | Cursor gap scan §3.H | §3.5 sub-item 9 | [ ] |
| G-103 | bf41175 Layer 1 meta-label scaffold cutover | Cursor gap scan §3.H | §3.8 sub-item 9 (default [C-AI-006-2] option 1) | [ ] |
| G-104 | Champion-challenger infrastructure repurposable | Cursor gap scan §3.H | §3.8 sub-item 10 | [ ] |

**Coverage check (v1.5/v1.6/v1.7 inherit v1.2 restatement post Cursor v1.4/v1.5 reviews; v1.6 + v1.7 are bounded cross-doc-version-cleanup cycles only — no §8 register changes):** All G-N IDs that Cursor gap scan §3.A delegated to this document are present (G-1 through G-16 contiguous; G-14 holds AI-SPEC-016 LightGBM per H-1 + H-B; G-49/50/51/55/59 for data improvements; G-67 through G-73 for V0.2 promotion gates including G-71 placeholder per Cursor v1.0 H-2; G-93/98/99/100/101/102/103/104 for substrate items). All `polygon:*` orphans + Layer-1 cutover items mapped. Cross-table consistency verified post-Cursor-v1.1: §3 prose ↔ §4 promotion table ↔ §5 ROI table ↔ §8 register all show Item 3 V0.1 / Phase 3F / Tier 1 (R-1 + R-2 fixes); Item 13 Tier 4 / 6-12-months-post-V0.3 / no V0.1 (R-3 fix); Phase 3X freshness substrate as standalone Tier-1 substrate work distinct from Item 13 build (R-3 fix). **CR-1 phantom citation closed in v1.5:** §7 16B row + §3.4 Stage 1 sub-item 10 now correctly enumerated (G-55 cross-reference verified). **No silent drops detected post v1.5 cross-table sweep; v1.6 + v1.7 cleanup cycles introduced no §8 changes.** *(If Cursor v1.7 verification finds residual silent drops, this coverage check needs further restatement.)*

---

## 9 — Out of Scope with Explicit Handling

These items are NOT in this roadmap's scope but are explicitly tracked elsewhere or deferred with rationale:

- **TASK_REGISTER.md §11 cross-asset signals (HYG, TLT, DXY) — formerly HANDOFF_3 §15D** — V0.2+ deferral; potential Phase 4B feature additions in V0.3 expansion
- **TASK_REGISTER.md §11 retail sentiment — formerly HANDOFF_3 §15E** — V2+ deferral per `deferred-work-register.md`
- **Tier 5 Item 14 Tournament Engine** — DEFERRED (registry §Tier 5)
- **Tier 5 Item 15 Cross-Index Diversification (NDX/RUT)** — DEFERRED (registry §Tier 5; single-developer maintainability)
- **Phase 2A `synthesis_agent.py` succession plan** — D-024 in `MASTER_ROI_PLAN.md` resolves; this roadmap does NOT model Phase 2A's relationship to Items 1/6
- **Operator decisions enumerated in `AUDIT_DISPOSITION_PLAN.md`** — out of scope here; this roadmap depends on those decisions but does not duplicate their content (Class C dependencies tracked via `[C-AI-XXX-N]` ID anchors per §0 dependency map)
- **Pre-AI fix track Commits 4-10** — Master ROI Plan §1.2 + Action 10; not in this roadmap

---

## 10 — Maintenance Protocol

This document is sourced from `AI_ARCHITECTURE_IMPROVEMENT_REGISTRY.md`. Updates flow:

1. Registry update (new spec locked, tier change, item rejected/deferred) → this document patched in same session
2. Audit register Class C decision lands → corresponding [C-AI-XXX-N] dependency entry in §0 dependency map updated; affected phase patched if needed
3. Build phase complete → status checkbox tick + verification note + ROI tracking entry
4. V0.1/V0.2 promotion gate met → table in §4 updated with date

**This document does NOT auto-generate from the registry — but every entry MUST trace to a registry tier or audit register row.** New items NOT in registry must be added to registry first, then mirrored here.

---

*End of AI Build Roadmap v1.7 — DRAFT commit-ready as part of Phase 2 deliverable trio (Master Plan v2.0.3 + this v1.7 + Audit Disposition Plan v1.8). All v1.2 deferred cosmetic items fixed in v1.3; v1.3→v1.4 patched stale cross-reference; v1.4→v1.5 closes the CR-1 silent drop (B-AI-010-8 / G-55 / 16B VIX spread width recalibration) plus 6 other items from Cursor v1.4 review; v1.5→v1.6 applies Cursor combined-round O-2 (Master Plan v2.0.1 → v2.0.2 reference update at status line + footer) + O-2-derived forward-pointer roll-forward; v1.6→v1.7 applies converged-state cleanup (cross-doc version updates to Master Plan v2.0.3 + DP v1.8 + forward-pointer roll + 3 H-1/H-2/H-3 carryover residuals at §6/§8/§8 that O-2 cleanup missed) per operator standing rule (fix-now over defer-to-later applied symmetrically). Commit all 3 documents together.*
