# Action 6 Governance Review — Working Doc

> **Status:** WORKING (pre-ratification draft) — NOT a committed source-of-truth artifact
> **Owner:** tesfayekb (operator) | **Drafter:** Cursor
> **Created:** 2026-04-29 | **Author cycle:** Phase 0 — Path Y activation pre-work, Gate D closure prep
> **Source HEAD:** `c1d1bb3` (post-PR #78 ROI baseline append; PR #77 P1.3.8 audit merged)
> **Successor:** post-ratification dispositions migrate into `trading-docs/08-planning/approved-decisions.md` D-023 (and possibly D-024) entries; this working doc is archived/deleted in cleanup PR.

## Purpose

Pre-organize the **operator-decision space** scattered across 4 merged Cluster A audits (P1.3.1, P1.3.2, P1.3.3, P1.3.4) and 4 merged Cluster B audits (P1.3.5, P1.3.6, P1.3.7, P1.3.8) so Action 6 (Gate D closure — D-023 + possible D-024 ratification) can be batch-decided in a single operator session rather than reviewed serially across 8+ audit redlines.

**Two-tier organization (per operator authorization 2026-04-29):**
- **Tier 1 — pattern-level ratifications.** Recurring architectural patterns confirmed across multiple audits. Single ratification at the pattern level auto-resolves multiple per-item decisions. **5–7 patterns expected.**
- **Tier 2 — item-level decisions.** The residual operator decisions after Tier 1 absorption. Each tagged by **difficulty**: Obvious-Default / Operator-Preference / Substantive-Tradeoff. Sorted within each tag so Obvious-Defaults come first.

**Out of scope for this working doc:**
- Final D-023 / D-024 wording integration into `approved-decisions.md` (separate PR after operator review)
- Any audit redline file (read-only sources)
- Class A findings (mechanical corrections, not operator decisions; out of Action 6 scope)
- Class B findings UNLESS they have explicit operator-decision text (most are implementation gaps, not decisions)

---

## §0 Pre-Audit Verification

Per `cursor-agent-orientation.md` §9 Mechanism 4 (verification language discipline). All sources cited with file path + line range; any inferences vs verbatim citations explicitly flagged.

### §0.1 Source files consulted

| Source | Path | Lines read | Purpose |
|--------|------|-----------|---------|
| AFR §0 (Pre-Audit Findings) | `trading-docs/08-planning/ai-architecture-audits/AUDIT_FINDINGS_REGISTER.md:26–94` | 1–139 (read for header + §0 + §1 Class C entry start) | PRE-P0/P11/P12 origin records cross-referenced into per-audit Class C |
| AFR §1 (Open Class C Escalations) | same file | 96–132 | All 31 open Class C findings + table header |
| AFR §2 (Open Class B Corrections) | same file | 136–~277 | Operator-decision Class B items only — 9 items selected (B-AI-002-2, B-AI-005-2/3/10/15, B-AI-006-12/13/14, B-AI-009-9) |
| AFR §4 (Resolved Findings) | same file | 278–286 | C-AI-002-2 resolved status verification |
| AFR §5 (Cross-Spec Themes) | same file | 288–321 | All 17 theme rows for Tier 1 pattern synthesis |
| AFR §6 (Governance Updates Required) | same file | 324–~400 | D-023 enrichment items (a)–(z) wording + system-state.md / TASK_REGISTER / MASTER_PLAN additions |
| `approved-decisions.md` | `trading-docs/08-planning/approved-decisions.md:1–125` | full (125 lines) | Confirmed D-001 through D-022 exist; D-023+ are net-new in this Action 6 |
| AI_BUILD_ROADMAP §3.x | `trading-docs/08-planning/AI_BUILD_ROADMAP.md` (717 lines) | spot-checked sections 3.1, 3.4, 3.5, 3.9, 3.10 for sequencing constraints | Cross-referenced calendar-blocker depths |
| CROSS_CUTTING_EVIDENCE_MATRIX | `trading-docs/08-planning/ai-architecture-audits/CROSS_CUTTING_EVIDENCE_MATRIX.md` (740 lines) | spot-checked for theme cross-references | Verified Tier 1 pattern instance counts |
| Cluster B audit redlines | AI-SPEC-{005, 006, 008, 009}.md | not read end-to-end (used AFR §1 + §5 as canonical source) | AFR is downstream-of and consistent-with the redlines per audit governance discipline |

### §0.2 Mechanism 4 transparency notes

- **Source-coverage gap (acknowledged):** Cluster A audits P1.3.1 (AI-SPEC-001), P1.3.2 (AI-SPEC-002), P1.3.3 (AI-SPEC-004), P1.3.4 (AI-SPEC-010) redline files NOT directly read in this drafting cycle; their findings are sourced via AFR §1 / §5 (which is the cross-spec roll-up by design). AFR is downstream-authoritative per its own §0 "How To Use This Register" preamble. If operator wants per-audit redline cross-verification before ratification, that's a separate verification pass.
- **Class C finding count:** 31 open + 1 resolved (C-AI-002-2 by AI-SPEC-010 P1.3.4) = 32 lifetime Class C; matches AFR P1.3.8 update log header.
- **D-023 wording status:** AFR §6 already contains a richly-enriched "D-023 wording" prose blob (lines 329–331) that accumulated additions from each audit's §11 governance section. **This working doc does NOT replace AFR §6 prose** — it organizes the underlying decision space so operator can ratify the additions structurally rather than reading the prose linearly. Final D-023 wording in `approved-decisions.md` synthesizes from operator dispositions in §4 below.

### §0.3 Decision space census

- **31 open Class C** items requiring explicit operator decision
- **9 operator-decision Class B** items (curated subset; most Class B are implementation gaps not decisions)
- **5 side-findings** (naming collisions, governance debt, doc-filename retention)
- **Total: ~45 operator decisions before Tier 1 absorption**

After Tier 1 absorption (see §1), expected reduction to **~15 effective decisions** (estimate; operator validates in §4 ratification pass).

---

## §1 Tier 1 — Pattern-Level Ratifications

**6 patterns identified.** Each ratification at the pattern level auto-resolves multiple per-item decisions in §2. Operator ratifies pattern statement; per-item decisions inherit unless operator chooses item-level override.

### §1.1 PATTERN-001 — Operator-Mediated Authority Recovery / Demotion

**Theme:** Authority Recovery automatic-vs-operator-mediated (architectural principle 1 boundary).

**Audit instances (3 confirmations + 1 retro-flagged):**
- `C-AI-006-1` (P1.3.6) — CRITICAL Class C escalation; first authority-boundary-violation in Cluster B; Spec §9.4 line 622 specifies AUTOMATIC recovery via 30-session cooldown + 20 qualified signals
- `C-AI-009-5` (P1.3.8) — Authority Recovery / Demotion silence; Spec §16 line 779 implies monotonic promotion with no demotion mechanism
- AI-SPEC-005 §5 reliability state machine (P1.3.5 — retroactively flagged bilateral with `C-AI-006-1`; same automatic-recovery pattern; Spec line 622 explicitly says "Mirror Item 5")
- Future AI-SPEC-013 (Drift Detection) — likely has analogous authority-recovery pattern

**Proposed pattern-level statement:**
> **For all AI-architecture specs in Cluster B/C with per-channel or per-strategy authority levels (Items 5, 6, 9, future 13), authority RECOVERY (advisory → reduced → normal → production) requires explicit operator action through `item_promotion_records` change-control. Automatic degradation triggers (cooldown, qualified-signals threshold, Wilson_lower_95, adaptive_exit_value sign) are ELIGIBILITY gates only — they enable operator review but do NOT auto-trigger promotion. Authority DEGRADATION (production → reduced → advisory → halted) MAY be automatic on hard breach (capital-preservation default) or operator-mediated (per-spec choice).**

**Alternatives:**
- (a) **DEFAULT — operator-mediated recovery; automatic degradation OK** — matches `C-AI-006-1` option 2 default + `C-AI-009-5` option 1 default
- (b) Fully automatic recovery accepted (matches `C-AI-006-1` option 1 + `C-AI-009-5` option 2) — most aggressive; risks premature re-promotion after transient degradation
- (c) Hybrid (degradation automatic; recovery via `item_promotion_records` change-control with eligibility gates) — most safety-conservative; matches `C-AI-006-1` option 3

**Auto-resolves at per-item level:**
- `C-AI-006-1` ✓ (default option 2)
- `C-AI-009-5` ✓ (default option 1)
- AI-SPEC-005 §5 reliability state machine recovery wording — bilateral amendment required
- Future AI-SPEC-013 inherits pattern at audit time

**Ratification checkbox:**
- [ ] Pattern-001 ratified per **(default option a)** — operator-mediated recovery only; automatic degradation OK; per-spec wording amendments applied bilaterally to Items 5 § 5 + 6 § 9.4 + 9 § 16
- [ ] Operator override at pattern level: chose option **__**
- [ ] Operator override per-item only (specify): _________________

### §1.2 PATTERN-002 — Layer 0/1/2 Architectural Template Family (4 variants)

**Theme:** Layer 1 / Layer 2 architectural pattern (legacy + calibration-grade duality).

**Audit instances (5 confirmations across 4 variants):**
- (i) **Layer 1 retrofit** — Items 10 (P1.3.4 introduced) + 5 (P1.3.5 confirmed) — Layer 1 stays as observability-only backward-compat surface; Layer 2 calibration-grade ships in parallel
- (ii) **Dormant Layer 1 + Layer 2 fresh ship** — Item 6 (P1.3.6) — Layer 1 scaffold present (`bf41175` LightGBM scaffold) but pkl absent / dormant; Layer 2 fresh-ship
- (iii) **Layer 0 + Layer 2 coexistence** — Item 8 (P1.3.7) — NO Layer 1 between raw feed (`databento_feed.py`) and alpha extractor (`flow_alpha_engine.py`); additive cutover
- (iv) **Layer 1 + Layer 2 COEXISTENCE (safety-critical)** — Item 9 (P1.3.8) — both layers ACTIVE simultaneously even after V0.4 promotion; static-exit safety net (`position_monitor.py`) preserved indefinitely per spec §16 line 779

**Proposed pattern-level statement:**
> **The Layer 0/1/2 architectural template applies whenever an existing scaffold at HEAD must coexist with a calibration-grade Layer 2 successor. Variants (i), (ii), (iii), (iv) are governed by spec §0/§16 architectural commitment language. Defaults (per consolidated plan §5 conservative-first principle):**
> - **(i) Layer 1 retrofit:** Layer 1 stays put as backward-compat surface (`label_quality = 'legacy_observability_only'` flagged on persisted Layer 1 outputs); Layer 2 produces parallel namespace; downstream consumers (Items 5/6/7/9) read ONLY from Layer 2 outputs filtered on `calibration_eligible = true`. Layer 1 receives surgical bug fixes only.
> - **(ii) Dormant Layer 1:** Layer 1 stays dormant; if operator places pkl, `legacy_observability_only` flag fires on persisted outputs; Layer 2 ships fresh.
> - **(iii) Layer 0 + Layer 2 coexistence:** Layer 0 raw-feed substrate continues serving existing consumers (e.g., GEX engine via `databento_feed.py:349`); Layer 2 alpha extractor ships as additive parallel namespace; cutover is additive (no migration of Layer 0 consumers).
> - **(iv) Layer 1 + Layer 2 COEXISTENCE (safety-critical):** Layer 1 static-exit safety net STAYS active even after Layer 2 V0.4 production-binding promotion; Layer 2 authority bounded to close/reduce-only (cannot delay/extend Layer 1 static exits); spec §16-style architectural commitment is binding.

**Alternatives (apply per variant):**
- For (i)–(ii): Layer 1 deprecation post-V0.x-stable (most aggressive; deviates from `do not rewrite` commitment)
- For (iii): Layer 0 deprecated post-Layer-2-stable (risks breaking existing Layer 0 consumers)
- For (iv): Layer 1 → backup-only mode post-V0.4-stable (deviates from spec §16 explicit commitment)

**Auto-resolves at per-item level:**
- `C-AI-005-2` ✓ Item 5 Layer 1 cutover policy (variant i — option 1 default)
- `C-AI-006-2` ✓ Item 6 Layer 1 cutover policy (variant ii — option 1 default)
- `C-AI-008-2` ✓ Item 8 flow_agent narrowing + Layer 0/2 coexistence (variant iii — option 1 default; flow_agent narrows to LLM summarizer)
- `C-AI-009-2` ✓ Item 9 Layer 1 + Layer 2 COEXISTENCE (variant iv — option 1 default per spec §16)
- `C-AI-010-1` ✓ Item 10 Layer 1 surgical bug fix (variant i — option 1 default)
- `B-AI-010-9` ✓ Item 10 `feedback:counterfactual:layer2:enabled` Redis flag (consequence of variant i — independent flag for parallel validation)
- Future Cluster C audits: pattern applied at audit time

**Ratification checkboxes (per variant):**
- [ ] Variant (i) Layer 1 retrofit — ratified default option 1; auto-resolves `C-AI-005-2` + `C-AI-010-1` + `B-AI-010-9`
- [ ] Variant (ii) dormant Layer 1 — ratified default option 1; auto-resolves `C-AI-006-2`
- [ ] Variant (iii) Layer 0+2 coexistence — ratified default option 1; auto-resolves `C-AI-008-2`
- [ ] Variant (iv) Layer 1+2 COEXISTENCE safety-critical — ratified default option 1; auto-resolves `C-AI-009-2`
- [ ] Operator override per variant: _________________

### §1.3 PATTERN-003 — Freshness Substrate (`_safe_redis()`) is Load-Bearing

**Theme:** `_safe_redis()` dead code (carry-forward #4) — escalation to "load-bearing component of V0.4 earlier-exit-only commitment".

**Audit instances (5 HIGH-IMPACT confirmations + 3 ruled-out):**
- `B-AI-001-6` (P1.3.1 — first confirmation)
- `B-AI-005-16` (P1.3.5 — HIGH-IMPACT; Item 5 V0.2 vol-engine inputs)
- `B-AI-006-17` (P1.3.6 — HIGH-IMPACT; Item 6 V0.2 produces `meta:engine_updated_at`)
- `B-AI-008-16` (P1.3.7 — HIGH-IMPACT; Item 8 V0.3 `opra:flow_alpha:health` 5-second backpressure)
- `B-AI-009-20` (P1.3.8 — HIGH-IMPACT; **load-bearing for V0.4 earlier-exit-only commitment**)
- Ruled out: AI-SPEC-002 (EOD batch), AI-SPEC-004 (offline replay), AI-SPEC-010 (EOD batch)

**Source-of-truth at HEAD (verified 2026-04-29):**
- `prediction_engine.py:100` defines `_safe_redis()` (32 lines: 100–131)
- `grep -n "_safe_redis(" backend/*.py` returns ONLY the definition + a docstring example caller at line 120 inside the `"""..."""` block 107–131
- ZERO non-docstring callers exist
- Producers also missing: `gex:updated_at`, `gex:atm_iv`, `polygon:spx:updated_at`, `polygon:vix:updated_at`, `vol:engine_updated_at`, `meta:engine_updated_at`, `opra:flow_alpha:health` — all consumer-only orphans or absent

**Proposed pattern-level statement:**
> **Freshness substrate (`_safe_redis()` caller wiring + companion `*:updated_at` producers) is a load-bearing prerequisite for ANY AI-architecture spec promoting to V0.x production-binding authority. Specifically, no Cluster B/C item may promote past advisory-only authority without (a) `_safe_redis()` (or operator-approved replacement) actively wired at all consumer sites; (b) producer-side `*:updated_at` keys actively writing for all consumed Redis namespaces; (c) verified at promotion gate by post-hoc check on `system-state.md.<item>.freshness_substrate_active = true`. Freshness substrate buildout is owned at the system level (Phase 3X per AI_BUILD_ROADMAP.md §3.15) and bilateral with each item's V0.x ship scope; downstream items inherit the substrate but contribute their own `*:updated_at` producer when they introduce new namespaces.**

**Alternatives:**
- (a) **DEFAULT — load-bearing pattern ratified; substrate is a hard prerequisite for V0.x production promotions** (matches escalation through P1.3.1 → P1.3.5 → P1.3.6 → P1.3.7 → P1.3.8)
- (b) Per-item replacement freshness mechanism (each item defines its own gate; no shared substrate) — risks inconsistent stale-data handling across items
- (c) MVP-deferred (mark all `data_freshness_warning` / freshness-gate fields as MVP-deferred; ship V0.x without freshness gates) — most aggressive; capital-preservation risk per `B-AI-009-20` operator framing

**Auto-resolves at per-item level:**
- `B-AI-001-6` ✓ Item 1 V0.1 freshness substrate buildout in scope
- `B-AI-005-16` ✓ Item 5 V0.2 freshness gate + producer
- `B-AI-006-17` ✓ Item 6 V0.2 freshness gate + producer
- `B-AI-008-16` ✓ Item 8 V0.3 freshness gate + producer
- `B-AI-009-20` ✓ Item 9 V0.4 promotion gate verifies substrate
- Implicitly: Items 11/12/13 V0.x ships inherit; Item 7 V0.x inherits

**Ratification checkbox:**
- [ ] Pattern-003 ratified per **(default option a)** — load-bearing substrate is a hard prerequisite for V0.x production promotions; Phase 3X freshness substrate fix is calendar-blocker for ALL Cluster B/C V0.x production-binding ships; auto-resolves all 5 Class B confirmations
- [ ] Operator override: _________________

### §1.4 PATTERN-004 — Canonical Strategy Taxonomy (10 strategies)

**Theme:** Strategy-class taxonomy naming inconsistency.

**Audit instances (7 confirmations):**
- A2 across AI-SPEC-001 / 002 / 004 / 010 / 005 / 006 / 009
- DB CHECK constraint at `supabase/migrations/20260419_add_strategy_types.sql:11–22` defines **10 canonical values**: `iron_condor`, `iron_butterfly`, `put_credit_spread`, `call_credit_spread`, `cash_secured_put`, `covered_call`, `debit_call_spread`, `debit_put_spread`, `long_call`, `long_put`
- `risk_engine.py:103–111` `_DEBIT_RISK_PCT` enum defines 7 of these (debit-side); credit-side strategies live in adjacent `_CREDIT_RISK_PCT` per consolidated plan
- `strategy_selector.py:17–28` `STATIC_SLIPPAGE_BY_STRATEGY` is the production validity set (used at line 1021)
- Conflicting alternative naming: `synthesis_agent.py:40–41` + `MASTER_PLAN.md` feature-flag boilerplate use `bull_debit_spread` / `bear_debit_spread` (NOT canonical)

**Outstanding ambiguity:** `earnings_straddle` (per `position_monitor.py:549` `straddle_pre_event_exit` + Evidence Pack §10.2 line 660) — possible 11th canonical strategy outside the 10, OR sub-mode of `long_straddle`. Surfaced via `B-AI-009-9` operator clarification.

**Proposed pattern-level statement:**
> **Canonical strategy taxonomy is the 10-value DB CHECK constraint at `supabase/migrations/20260419_add_strategy_types.sql:11–22`. All AI-architecture specs (Items 2, 5, 6, 7, 9, 10, 11, 12, 13) MUST use these 10 canonical IDs. Spec sections that enumerate strategies are NOT permitted to ship subsets without an explicit per-strategy reasoning footnote; subset-ship requires operator ratification at audit time. The `bull_debit_spread` / `bear_debit_spread` alternative naming in `synthesis_agent.py:40–41` + `MASTER_PLAN.md` feature-flag boilerplate is non-canonical and tracked for separate cleanup. `earnings_straddle` taxonomy decision (sub-mode of `long_straddle` vs 11th canonical) is operator-deferred per `B-AI-009-9`.**

**Alternatives (`earnings_straddle` only):**
- (a) **DEFAULT — sub-mode of `long_straddle`** with a `mode TEXT NULL` discriminator (preserves canonical 10; minimal schema change)
- (b) 11th canonical strategy added to DB CHECK constraint via new migration (expands canonical set to 11; touches all 7+ specs)

**Auto-resolves at per-item level:**
- `B-AI-006-12` ✓ Item 6 V0.2 must use canonical 10; spec §1 lines 30–141 amended (5 strategies → enumerate which subset of canonical 10 is in V0.2 scope, OR add missing strategy utility-label sections, OR explicit inheritance footnote per `C-AI-006-3` Bayesian prior governance)
- `B-AI-009-9` ✓ Item 9 V0.3 must use canonical 10; operator deferred to V0.3 ship scope finalization (extend §6 OR explicit inheritance footnote)
- A2 across AI-SPEC-001/002/004/005/010 ✓ system-wide cleanup task (separate from any per-item audit)
- Future Cluster C audits inherit pattern at audit time

**Ratification checkboxes:**
- [ ] Pattern-004 canonical 10 ratified
- [ ] `earnings_straddle` taxonomy: chose option **__** (a sub-mode / b 11th canonical)
- [ ] System-wide cleanup task created for `bull_debit_spread` / `bear_debit_spread` non-canonical naming purge from `synthesis_agent.py` + `MASTER_PLAN.md`

### §1.5 PATTERN-005 — Cross-Spec Producer→Consumer Contract Ratification

**Theme:** Cross-spec producer→consumer contract ratification (unilateral spec claims vs bilateral confirmation).

**Audit instances (2 confirmations):**
- `C-AI-008-1` (P1.3.7) — Item 8 unilaterally claims contracts with Items 5 (8 features) + 6 (20+1 features); Items 5+6 specs silent
- `C-AI-009-1` (P1.3.8) — 3-way pattern extension; Item 9 unilaterally claims contracts with Items 5 (10 fields) + 8 (9 fields); Items 5+6+8 specs ALL silent on Item 9; **only Item 10 ↔ Item 9 is bilateral** (sole bilateral pair across both confirming audits)

**Proposed pattern-level statement:**
> **When a downstream spec ships explicit producer→consumer contracts that consumer specs are silent on (or contradict), bilateral confirmation is required before V0.x production-binding promotion: (i) consumer spec must ratify the producer surface in next P1.3.X amendment cycle; (ii) until ratification, the producer ships in unilateral-claim status with `cross_spec_contract_ratified = false` flag in `system-state.md.<item>.cross_spec_contract_ratified_with_<other_item>`; (iii) downstream training accessors filter on `cross_spec_contract_ratified = true` only — preventing consumers from training on unratified features; (iv) operator authorizes unilateral-to-bilateral transition via P1.3.X amendment cycle merge. **Default position: option (a) DEFERRED BILATERAL CONFIRMATION** — V0.x advisory-only ship permitted with `cross_spec_contract_ratified = false`; bilateral confirmation deferred to next amendment cycle (post-Cluster B closure).**

**Alternatives:**
- (a) **DEFAULT — DEFERRED BILATERAL CONFIRMATION** — preserves audit-trail clarity at cost of delayed cross-spec coherence
- (b) RATIFY now — amend producer specs to add downstream consumers as named in CURRENT P1.3 amendment cycle (cleanest; requires bilateral spec amendment work this cycle)
- (c) REVOKE — treat producer features as research-only inputs that downstream consumers may opt into post-V0.x maturation via future spec amendment (most conservative; defers integration)

**Auto-resolves at per-item level:**
- `C-AI-008-1` ✓ default option 3 (DEFERRED BILATERAL CONFIRMATION); Item 8 V0.3 ships with `cross_spec_contract_ratified_with_item_5 = false` + `cross_spec_contract_ratified_with_item_6 = false` flags
- `C-AI-009-1` ✓ default option 3 (DEFERRED BILATERAL CONFIRMATION); Item 9 V0.3 ships with `cross_spec_contract_ratified_with_item_5 = false` + `cross_spec_contract_ratified_with_item_8 = false` flags
- Future Cluster C audits inherit pattern at audit time

**Ratification checkbox:**
- [ ] Pattern-005 ratified per **(default option a)** DEFERRED BILATERAL CONFIRMATION; auto-resolves `C-AI-008-1` + `C-AI-009-1`
- [ ] Operator override: chose option **__** for either C-AI-008-1 or C-AI-009-1 individually

### §1.6 PATTERN-006 — Chain-Archive Substrate Cascade (V0.x Advisory-Only Acceptance)

**Theme:** Archived option-chain data substrate (V0.1 hard prerequisite) — extends to **4-spec shared substrate dependency**.

**Audit instances (4 confirmations):**
- `C-AI-004-4` (P1.3.3 — root cause) — Item 4 V0.1 calibration-grade replay requires archived chains
- `B-AI-010-6` (P1.3.4 bilateral) — Item 10 V0.2 Layer 2 slippage formula needs `half_spread_estimate` baseline
- `C-AI-005-3` (P1.3.5 trilateral) — Item 5 V0.2 calibration-grade promotion gate "Baseline E beats Baseline F" needs archived chains for IV ATM extraction
- `C-AI-008-4` (P1.3.7 quadrilateral transitive) — Item 8 V0.3 production acceptance needs Item 6 V0.2 + chain-archive maturation
- Item 6 V0.2 transitive (P1.3.6) — calibration-grade ship requires upstream chain-archive substrate via Items 4, 5, 10
- Item 9 V0.4 transitive (P1.3.8) — production-binding calendar-blocked on `C-AI-004-4` chain-archive substrate disposition per `C-AI-009-3`

**Proposed pattern-level statement:**
> **Chain-archive substrate is a load-bearing 4-spec shared dependency (Items 4, 5, 6, 10 directly; Items 8, 9 transitively). Operator decision on substrate path (forward archival / paid historical / V0.x advisory-only acceptance) cascades to ALL affected specs simultaneously. Default: **option 3 (V0.x advisory-only acceptance)** with parallel-track exploration of options 1 (forward archival) and 2 (paid historical). All affected specs ship V0.x in advisory-only mode with `<item>.calibration_grade_capable = false` logged in `system-state.md` until substrate matures (estimated 6+ months for forward archival; paid historical = contract dependency). No new D-XXX strictly required for default option 3.**

**Alternatives:**
- (a) **DEFAULT — V0.x advisory-only acceptance** (cascades to `replay_harness.calibration_grade_capable`, `counterfactual_engine.layer_2_chain_archive_capable`, `vol_fair_value_engine.calibration_grade_capable`, `meta_labeler.calibration_grade_capable`, `opra_flow_alpha.calibration_grade_capable`, `exit_optimizer.calibration_grade_capable` — all default false)
- (b) Forward archival — start chain + 5-min bar archival now; calendar slip estimated 6+ months; no contractual cost
- (c) Paid historical archive — Polygon/Tradier/Databento paid tier; cost TBD by operator; contractual dependency; calendar-fast

**Auto-resolves at per-item level:**
- `C-AI-004-4` ✓ option 3 default
- `C-AI-005-3` ✓ option 3 default (bilateral with `C-AI-004-4`; same operator decision resolves both)
- `C-AI-008-4` ✓ option 3 default (transitive with `C-AI-004-4`)
- `B-AI-010-6` ✓ Item 10 V0.2 slippage formula degrades to operator-conservative defaults; `calibration_eligible = false` for affected rows
- Item 6 V0.2 ✓ `meta_labeler.calibration_grade_capable = false`
- Item 9 V0.4 ✓ promotion deferred per chain-archive substrate cascade

**Ratification checkbox:**
- [ ] Pattern-006 ratified per **(default option a)** V0.x advisory-only acceptance with parallel-track exploration of (b) forward archival + (c) paid historical; cascade to 6 `system-state.md` flags applied
- [ ] Parallel-track decision: pursue option (b) / (c) / both / neither (operator preference)

---

## §2 Tier 2 — Item-Level Decisions (Post Tier 1 Reduction)

After Tier 1 ratification, residual decisions sorted by difficulty. **Operator speed-ratifies Obvious-Defaults first; reserves attention budget for Substantive-Tradeoffs.**

### §2.1 OBVIOUS-DEFAULT (operator typically accepts spec author intent / existing pattern; speed-ratify)

| ID | Source | Question | Default | Auto-resolved by Tier 1? |
|----|--------|----------|---------|---------------------------|
| C-AI-001-1 | AI-SPEC-001 §10.3 C1 | `size_multiplier_cap` channel — D-023 scope vs D-014 scope | Ratify D-023 with explicit scope per consolidated plan §5 default | Partial (folds into D-023 scope below) |
| C-AI-001-2 | AI-SPEC-001 §10.3 C2 | V0.1→V0.2 + Lean Live promotion automation | Live-affecting transitions require operator approval; paper-only automatable subject to GLC-001..012 | No (unique to D-023) |
| C-AI-001-3 | AI-SPEC-001 §10.3 C3 | Opportunity-lean channel | Defer to separate spec (AI-SPEC-001b or AI-SPEC-014); ship core Item 1 V0.1 as veto-only | No |
| C-AI-002-1 | AI-SPEC-002 §10.3 C1 | `decision_outcome` enum coordination for `size_multiplier_cap` | Option A: Item 2 enum extends with `cap_governor` / `reduced_governor` (Item 6 already adds `blocked_meta_labeler` per `B-AI-006-9`) | No |
| C-AI-002-3 | AI-SPEC-002 §10.3 C3 | Legacy `attribution_*` BOOLEAN columns disposition | Option 1: deprecate-in-place (lowest-cost; no production code writes them) | No |
| C-AI-004-1 | AI-SPEC-004 §10.3 C1 | `paper_phase_criteria` × `item_promotion_records` coordination | Option 1: independent gates with explicit non-conflict statement; preserves D-013 unchanged | No |
| C-AI-004-2 | AI-SPEC-004 §10.3 C2 | Canonical "decision card" definition for Spec §12 200-card threshold | Option 1: `replay_eval_cases.calibration_eligible = true` only; explicit exclusion of `shadow_predictions` rows | No |
| C-AI-004-3 | AI-SPEC-004 §10.3 C3 | `item_promotion_records` startup-read contract | Encode as D-023 enrichment item (f) per spec §4 lines 521–525 | No |
| C-AI-005-1 | AI-SPEC-005 §10.3 C1 | D-016 disposition (HAR-RV vs `realized` term) | Option 2: HAR-RV is NEW signal feeding EV table only; D-016 stays unchanged | No |
| C-AI-008-3 | AI-SPEC-008 §10.3 C3 | Databento subscription scope — pre-implementation operator gate | Option 4: operator verifies subscription tier scope BEFORE V0.3 implementation begins | No |
| C-AI-010-2 | AI-SPEC-010 §10.3 C2 | Item 10 tier classification (V0.1 vs V0.2 graduated) | Ratify layered framing — V0.1 = Layer 1 already shipped; V0.2 onward = Layer 2 | No |
| C-AI-010-3 | AI-SPEC-010 §10.3 C3 | z-score producer authority | Option 3: shared producer in `features:vix_z` / `features:spread_z` Redis namespace owned by calibration_engine per D-019 | No |
| C-AI-010-4 | AI-SPEC-010 §10.3 C4 | Item 3 synthetic case storage — separate table or INSERT into Item 10's table | Option 1: Item 3 INSERTs into Item 10's `trade_counterfactual_cases` with `case_type = 'synthetic'`, `case_weight = 0.2` | No |
| C-AI-010-5 | AI-SPEC-010 §10.3 C5 | `<Commit_4_deploy_date>` cutover anchor lock | Option 1: concrete commit hash post-Commit-4 ship | No |

**Speed-ratification expected: 14 of 31 Class C** (~45%) plus auto-resolved-by-Tier-1 entries; operator can batch-approve all 14 in single pass.

### §2.2 OPERATOR-PREFERENCE (genuine choice; no architectural blocker)

| ID | Source | Question | Default | Notes |
|----|--------|----------|---------|-------|
| C-AI-006-3 | AI-SPEC-006 §10.3 C3 | Bayesian prior parameter governance | Option 1: operator-tunable via `system-state.md` `meta_labeler.prior_parameters` | Alt option 2 = D-024 ratification (constitutional constants); alt option 3 = code-bound with PR review |
| C-AI-006-4 | AI-SPEC-006 §10.3 C4 | LightGBM Direction Model spec ownership | Option 2: new spec AI-SPEC-014 + new D-XXX (D-024 candidate) for catalog extension | Alt option 1 = include in Item 6 V0.2; alt option 3 = remove 5 fields from Item 6 §3.4 |
| C-AI-009-3 | AI-SPEC-009 §10.3 C3 | Item 9 V0.4 promotion-gate coordination | Option 1: encode in D-023 enrichment item (y) — per-strategy `item_promotion_records` + GLC pass-through + per-strategy thresholds | Alt option 2 = independent gates (less rigorous) |
| C-AI-009-4 | AI-SPEC-009 §10.3 C4 | Per-strategy authority promotion gate disposition | Option 3: per-strategy independent gates with system-level minimum 200 trades | Alt 1 = per-strategy fully independent; alt 2 = global gate first then per-strategy |
| B-AI-002-2 | AI-SPEC-002 §10.2 B2 | `closed_trade_path_metrics` substrate path | Option (a): wait for Item 10 V0.2 to land substrate (single owner) | Alt (b): Item 2 V0.1 ships with NULL placeholders; copy-on-insert added later |
| B-AI-005-2 | AI-SPEC-005 §10.2 B2 | Multi-year RV history substrate path | Option (c): hybrid — forward archival + paid historical fills 6-month gap | Alt (a) wait; alt (b) Polygon paid tier only |
| B-AI-005-3 | AI-SPEC-005 §10.2 B3 | Daily-RV writer disposition (12A vs new) | Option (c): keep 12A as legacy observability + ship NEW persistent writer | Alt (a) extend 12A; alt (b) replace 12A |
| B-AI-005-10 | AI-SPEC-005 §10.2 B10 | `item_promotion_records` schema extension for per-channel granularity | Option (a): extend `item_promotion_records` with `channel TEXT NULL` (single source of truth) | Alt (b): Item 5 maintains own per-channel state internally |
| B-AI-005-15 | AI-SPEC-005 §10.2 B15 | Pre-V0.2 data-substrate buildout path | Option (c): hybrid — forward archival + Polygon paid tier | Same flavor as B-AI-005-2 |
| B-AI-006-13 | AI-SPEC-006 §10.2 B13 | Case-weight reconciliation (§4.1 vs §3.6) | Default: harmonize §4.1 to §3.6 — drop 0.6 rules-not-taken weight; use 1.0/0.5/0.2 across both | Alt: keep §4.1 distinct |
| B-AI-006-14 | AI-SPEC-006 §10.2 B14 | Slippage imputation policy for un-executed candidates | Option (a): replay-imputed via Item 5 spread filter + Item 10 slippage formula | Alt (b): NULL with `slippage_imputed = false` flag; alt (c) drop un-executed candidates |
| B-AI-009-9 | AI-SPEC-009 §10.2 B9 | §6 strategy enumeration scope (extend or mark inheritance) | Operator-deferred per Ambiguity 3 resolution at V0.3 ship scope finalization | Auto-resolved by Pattern-004 ratification (canonical 10) — operator selects extend OR explicit inheritance per strategy |

**Operator-preference count: 12** (5 Class C + 7 Class B); operator decides individually but each is a clean choice with no architectural blocker.

### §2.3 SUBSTANTIVE-TRADEOFF (real engineering cost differences; warrants attention)

| ID | Source | Question | Default | Notes |
|----|--------|----------|---------|-------|
| C-AI-005-2 | AI-SPEC-005 §10.3 C2 | Item 5 Layer 1 cutover policy (3 options) | Auto-resolved by Pattern-002 (variant i) — option 1 default | Substantive only if operator overrides Pattern-002 |
| C-AI-006-1 | AI-SPEC-006 §10.3 C1 | Item 6 + Item 5 Authority Recovery (CRITICAL Class C) | Auto-resolved by Pattern-001 — option (a) default; bilateral amendment to Item 5 § 5 mandatory | First authority-boundary-violation Class C in Cluster B |
| C-AI-006-2 | AI-SPEC-006 §10.3 C2 | Item 6 Layer 1 cutover (3 options) | Auto-resolved by Pattern-002 (variant ii) — option 1 default | |
| C-AI-008-1 | AI-SPEC-008 §10.3 C1 | Cross-spec contract ratification (Item 8 ↔ Items 5+6) | Auto-resolved by Pattern-005 — option (a) DEFAULT DEFERRED | |
| C-AI-008-2 | AI-SPEC-008 §10.3 C2 | flow_agent + Layer 0/2 cutover (3 options) | Auto-resolved by Pattern-002 (variant iii) — option 1 default | flow_agent narrowing has user-facing implications |
| C-AI-008-4 | AI-SPEC-008 §10.3 C4 | Item 8 V0.3 advisory-only acceptance (3 options) | Auto-resolved by Pattern-006 — option 3 default | |
| C-AI-009-1 | AI-SPEC-009 §10.3 C1 | Item 9 ↔ Items 5+8 contract ratification | Auto-resolved by Pattern-005 — option (a) DEFAULT DEFERRED | 3-way pattern; Item 10 ↔ Item 9 sole bilateral pair |
| C-AI-009-2 | AI-SPEC-009 §10.3 C2 | Layer 1 + Layer 2 COEXISTENCE ratification | Auto-resolved by Pattern-002 (variant iv) — option 1 default per spec §16 | Safety-critical; capital-preservation rationale |
| C-AI-009-5 | AI-SPEC-009 §10.3 C5 | Item 9 Authority Recovery / Demotion contract | Auto-resolved by Pattern-001 — option (a) default | Mirrors C-AI-006-1 resolution |
| C-AI-009-6 | AI-SPEC-009 §10.3 C6 | Earlier-exit-only enforcement (3 options) | Operator-ratified 2026-04-29: option (a) post-hoc verification per spec author intent | **OPERATOR ACCEPTS asymmetric-risk-window**; alt (b) runtime invariant check; alt (c) type-signature constraint |

**Substantive-tradeoff count: 10 Class C** — all but `C-AI-009-6` auto-resolved by Tier 1 patterns. Effective operator attention required: **1 substantive item (`C-AI-009-6`)** which operator already ratified at P1.3.8 EXECUTE authorization.

### §2.4 Tier 2 Decision Count Summary

| Difficulty Tag | Class C count | Class B count | Total | Auto-resolved by Tier 1 |
|----------------|---------------|---------------|-------|--------------------------|
| Obvious-Default (§2.1) | 14 | 0 | 14 | 0 |
| Operator-Preference (§2.2) | 5 | 7 | 12 | 1 (B-AI-009-9 auto-resolved by Pattern-004) |
| Substantive-Tradeoff (§2.3) | 10 | 0 | 10 | 9 (all but C-AI-009-6 auto-resolved by Tier 1) |
| **Subtotal** | **29** | **7** | **36** | **10** |

**Effective operator decision count after Tier 1 absorption: 36 − 10 (auto-resolved) − 14 (speed-ratify Obvious-Defaults) − 1 (C-AI-009-6 already ratified) = ~11 substantive operator decisions.**

This is the **leverage** of Tier 1 organization: 45+ scattered items collapse to ~11 effective decisions for operator attention.

### §2.5 Class C items NOT in §2.1–§2.3 (count check)

Total Class C in AFR §1 = 31 open. Items above sum:
- §2.1 Obvious-Default Class C = 14 (C-AI-001-1, C-AI-001-2, C-AI-001-3, C-AI-002-1, C-AI-002-3, C-AI-004-1, C-AI-004-2, C-AI-004-3, C-AI-005-1, C-AI-008-3, C-AI-010-2, C-AI-010-3, C-AI-010-4, C-AI-010-5)
- §2.2 Operator-Preference Class C = 5 (C-AI-006-3, C-AI-006-4, C-AI-009-3, C-AI-009-4, plus C-AI-004-4 below)
- §2.3 Substantive-Tradeoff Class C = 10 (C-AI-005-2, C-AI-006-1, C-AI-006-2, C-AI-008-1, C-AI-008-2, C-AI-008-4, C-AI-009-1, C-AI-009-2, C-AI-009-5, C-AI-009-6)
- Auto-resolved-only-by-Pattern-006 = 2 (C-AI-004-4, C-AI-005-3 — listed in §1.6 only; counted under §2.2 implicit)
- C-AI-010-1 = auto-resolved by Pattern-002 variant i; listed in §1.2 only

Total accounted = 14 + 5 + 10 + 2 = 31 ✓

---

## §3 Side-Findings (Same Structure as §2; Out of Class C/B Scope)

| ID | Source | Question | Default | Notes |
|----|--------|----------|---------|-------|
| SF-001 | P1.3.8 §11 | Phase 5A naming collision (Item 9 Phase 5A vs already-shipped Earnings Volatility System Phase 5A) | Operator-decided post-merge per Standing Rule 6 — rename Item-9-track to Phase 5E OR renumber Earnings Volatility System retrospectively | Surfaced in AI-SPEC-009.md §11; AI_BUILD_ROADMAP.md flagged |
| SF-002 | P1.3.7 §11 | Phase 4C naming debt (Memory Retrieval Phase 4C placeholder un-anchored to Item 7 audit) | Operator-decided post-merge alongside SF-001 | Carried forward from P1.3.7 |
| SF-003 | P1.3.8 §0.7 | `system-state.md` `core_risk_pct: 0.005` staleness (post-Action 7b should be 0.010) | Trivial fix; bundle with another future docs PR | Single-line fix; ceremony-heavy as standalone PR |
| SF-004 | PRE-P0-4 + PRE-P130-1 | Constitution rule-count mismatch (`.cursorrules` line 36 says "11 rules" vs `constitution.md`'s 10 T-Rules) | Pre-existing governance debt; Phase 5 cleanup | Tracked under PRE-P0-4 |
| SF-005 | P1.3.8 §0.x | Doc filename retention `ROI_LOG_BASELINE_2026-04-28.md` even after multi-session append | Operator may rename in separate PR; current name preserves PR #73 + AFR cross-references | Cosmetic |

**Side-finding count: 5** — all operator-paced; none block Action 6 / D-023 ratification.

---

## §4 Disposition Record (Operator Fills In)

After operator review, fill in the Disposition column. Each row maps to one Tier 1 pattern, Tier 2 item, or side-finding above.

| ID | Default | Operator Disposition | Date Ratified | Notes / Override Reason |
|----|---------|----------------------|---------------|--------------------------|
| **TIER 1 PATTERNS** | | | | |
| PATTERN-001 (Auth Recovery / Demotion) | option (a) operator-mediated recovery | _______ | ______ | _______________________ |
| PATTERN-002 variant (i) Layer 1 retrofit | option 1 stays put | _______ | ______ | _______________________ |
| PATTERN-002 variant (ii) dormant Layer 1 | option 1 stays dormant | _______ | ______ | _______________________ |
| PATTERN-002 variant (iii) Layer 0+2 coexistence | option 1 additive cutover | _______ | ______ | _______________________ |
| PATTERN-002 variant (iv) Layer 1+2 COEXISTENCE | option 1 per spec §16 | _______ | ______ | _______________________ |
| PATTERN-003 (Freshness Substrate) | option (a) load-bearing | _______ | ______ | _______________________ |
| PATTERN-004 (Canonical Strategy Taxonomy) | canonical 10 + earnings_straddle deferred | _______ | ______ | option (a) sub-mode / (b) 11th: __ |
| PATTERN-005 (Cross-Spec Contract Ratification) | option (a) DEFERRED BILATERAL | _______ | ______ | _______________________ |
| PATTERN-006 (Chain-Archive Cascade) | option (a) V0.x advisory-only acceptance | _______ | ______ | parallel-track: (b) / (c) / both / neither: __ |
| **TIER 2 OBVIOUS-DEFAULTS (§2.1)** | | | | |
| C-AI-001-1 | per default | _______ | ______ | _______________________ |
| C-AI-001-2 | per default | _______ | ______ | _______________________ |
| C-AI-001-3 | defer to AI-SPEC-001b/014 | _______ | ______ | _______________________ |
| C-AI-002-1 | option A enum extension | _______ | ______ | _______________________ |
| C-AI-002-3 | option 1 deprecate-in-place | _______ | ______ | _______________________ |
| C-AI-004-1 | option 1 independent gates | _______ | ______ | _______________________ |
| C-AI-004-2 | option 1 replay_eval_cases canonical | _______ | ______ | _______________________ |
| C-AI-004-3 | encode in D-023 item (f) | _______ | ______ | _______________________ |
| C-AI-005-1 | option 2 D-016 unchanged | _______ | ______ | _______________________ |
| C-AI-008-3 | option 4 pre-implementation gate | _______ | ______ | _______________________ |
| C-AI-010-2 | ratify layered framing | _______ | ______ | _______________________ |
| C-AI-010-3 | option 3 shared producer | _______ | ______ | _______________________ |
| C-AI-010-4 | option 1 INSERT into Item 10 table | _______ | ______ | _______________________ |
| C-AI-010-5 | option 1 concrete commit hash post-Commit-4 | _______ | ______ | _______________________ |
| **TIER 2 OPERATOR-PREFERENCES (§2.2)** | | | | |
| C-AI-004-4 | option 3 V0.x advisory-only | _______ | ______ | bundled with Pattern-006 |
| C-AI-005-3 | option 3 V0.x advisory-only | _______ | ______ | bundled with Pattern-006 + C-AI-004-4 |
| C-AI-006-3 | option 1 operator-tunable via system-state | _______ | ______ | alt option 2 = D-024 |
| C-AI-006-4 | option 2 new spec AI-SPEC-014 + D-024 | _______ | ______ | bilateral with C-AI-006-3 D-XXX |
| C-AI-009-3 | option 1 encode in D-023 item (y) | _______ | ______ | _______________________ |
| C-AI-009-4 | option 3 per-strategy + system-level minimum | _______ | ______ | _______________________ |
| B-AI-002-2 | option (a) wait for Item 10 V0.2 | _______ | ______ | _______________________ |
| B-AI-005-2 | option (c) hybrid | _______ | ______ | _______________________ |
| B-AI-005-3 | option (c) 12A + new writer | _______ | ______ | _______________________ |
| B-AI-005-10 | option (a) extend item_promotion_records | _______ | ______ | _______________________ |
| B-AI-005-15 | option (c) hybrid | _______ | ______ | bundled with B-AI-005-2 |
| B-AI-006-13 | harmonize to 1.0/0.5/0.2 | _______ | ______ | _______________________ |
| B-AI-006-14 | option (a) replay-imputed | _______ | ______ | _______________________ |
| B-AI-009-9 | extend OR explicit inheritance per strategy | _______ | ______ | bundled with Pattern-004 |
| **TIER 2 SUBSTANTIVE-TRADEOFFS (§2.3)** | | | | |
| (all but C-AI-009-6 auto-resolved by Tier 1; verify in §1 ratifications) | | | | |
| C-AI-009-6 | option (a) post-hoc verification (operator-ratified 2026-04-29) | option (a) | 2026-04-29 | per P1.3.8 EXECUTE authorization Ambiguity 4 resolution |
| **SIDE-FINDINGS (§3)** | | | | |
| SF-001 Phase 5A naming | rename or renumber | _______ | ______ | _______________________ |
| SF-002 Phase 4C naming | rename when Item 7 audit lands | _______ | ______ | _______________________ |
| SF-003 system-state.md core_risk_pct staleness | bundle with future docs PR | _______ | ______ | _______________________ |
| SF-004 Constitution rule-count mismatch | Phase 5 cleanup | _______ | ______ | _______________________ |
| SF-005 Doc filename retention | operator may rename separately | _______ | ______ | _______________________ |

**Total disposition rows: 9 patterns + 14 obvious-defaults + 14 operator-preferences + 1 substantive (already-ratified) + 5 side-findings = 43 rows.**

---

## §5 D-023 Wording Draft (Synthesized Post-Disposition)

> **DRAFT — populated post-§4 ratification.** Operator marks dispositions in §4; this section synthesizes ratified text into final D-023 (and possibly D-024) wording for migration into `approved-decisions.md`.

### §5.1 Proposed D-023 Structure (16 enrichment items a–z accumulated across 8 audits)

Per AFR §6 lines 329–331 already-enriched D-023 wording, the final D-023 entry in `approved-decisions.md` will have **at minimum 26 enrichment items (a) through (z)** organized by topic:

| Item | Topic | Source Audit | Status |
|------|-------|-------------|--------|
| (a) | Governor `size_multiplier_cap` channel composition with `_RISK_PCT[phase]` | AI-SPEC-001 | pending §4 |
| (b) | Non-overridability of D-005/D-010/D-011/D-014/D-021/D-022 | AI-SPEC-001 | pending §4 |
| (c) | Opportunity-lean channel disposition | AI-SPEC-001 | pending §4 (default = defer to AI-SPEC-001b) |
| (d) | Promotion-gate authority handoff (auto vs operator) | AI-SPEC-001 | pending §4 |
| (e) | Canonical "decision card" definition (`replay_eval_cases.calibration_eligible = true`) | AI-SPEC-004 | pending §4 |
| (f) | `item_promotion_records` startup-read contract | AI-SPEC-004 | pending §4 |
| (g) | Layer 1/Layer 2 cutover policy framework (4 variants) | AI-SPEC-010 + 5 + 6 + 8 + 9 | pending §4 — Pattern-002 |
| (h) | z-score producer authority (shared `features:*` namespace) | AI-SPEC-010 | pending §4 |
| (i) | `counterfactual_reason ↔ decision_outcome` enum mapping | AI-SPEC-010 | pending §4 |
| (j) | Legacy-rows lockdown anchor (`<Commit_4_deploy_date>`) | AI-SPEC-010 | pending §4 |
| (k) | Item 5 authority boundary (vol:* namespace + tables) | AI-SPEC-005 | pending §4 |
| (l) | Item 5 Layer 1/Layer 2 cutover policy (extends g) | AI-SPEC-005 | pending §4 — Pattern-002 |
| (m) | Canonical strategy taxonomy enumeration (10 strategies) | AI-SPEC-005 + extensions | pending §4 — Pattern-004 |
| (n) | Chain-archive substrate cascade (extends j; cross-references C-AI-004-4) | AI-SPEC-005 | pending §4 — Pattern-006 |
| (o) | Item 6 authority boundary (keystone meta-labeler) | AI-SPEC-006 | pending §4 |
| (p) | Item 6 (and Item 5) Authority Recovery disposition | AI-SPEC-006 | pending §4 — Pattern-001 |
| (q) | Item 6 Layer 1/Layer 2 cutover policy (extends g + l) | AI-SPEC-006 | pending §4 — Pattern-002 |
| (r) | Strategy taxonomy reconciliation for Item 6 | AI-SPEC-006 | pending §4 — Pattern-004 |
| (s) | Bayesian prior parameter governance (operator-tunable via system-state.md) | AI-SPEC-006 | pending §4 |
| (t) | `decision_outcome` enum coordination — Item 6 emits `blocked_meta_labeler` | AI-SPEC-006 | pending §4 |
| (u) | Item 8 authority boundary (OPRA flow + Databento procurement scope) | AI-SPEC-008 | pending §4 |
| (v) | flow_agent / Layer 0 / Layer 2 cutover (extends g + l + q) | AI-SPEC-008 | pending §4 — Pattern-002 |
| (w) | Cross-spec contract ratification process governance | AI-SPEC-008 + 9 | pending §4 — Pattern-005 |
| (x) | Item 9 authority boundary (deterministic forward-EV exit advisor) | AI-SPEC-009 | pending §4 |
| (y) | Item 9 V0.4 promotion-gate coordination contract | AI-SPEC-009 | pending §4 |
| (z) | Item 9 earlier-exit-only enforcement contract | AI-SPEC-009 | pending §4 — already operator-ratified per Ambiguity 4 |

**26 enrichment items total** across 8 merged audits. After §4 ratification, D-023 wording is the consolidated set of these items grouped by 4 sub-headings: (1) AI Authority Boundary; (2) Cross-Spec Coordination Contracts; (3) Layer 0/1/2 Cutover Policy Framework; (4) Promotion-Gate + Authority-Recovery Contracts.

### §5.2 Proposed D-024 (Conditional)

D-024 ratification is **conditional** on operator decisions:
- If C-AI-006-4 chooses option 2 (new spec AI-SPEC-014 LightGBM Direction Model) → D-024 ratifies AI architecture catalog extension
- If C-AI-006-3 chooses option 2 (Bayesian prior parameters as constitutional constants) → D-024 ratifies prior parameter values

**Default position: D-024 ratifies AI architecture catalog extension for AI-SPEC-014** if operator chooses C-AI-006-4 option 2 (default).

### §5.3 Migration Sequence (Action 6 → Final Ratification)

1. Operator completes §4 dispositions in this working doc
2. Cursor synthesizes final D-023 + (optional) D-024 wording from operator dispositions
3. Cursor opens **separate PR** to `approved-decisions.md` adding D-023 + (optional) D-024 entries with full prose
4. Cursor opens **separate PR** to `system-state.md` adding 6 substrate-state fields per AFR §6 lines 363–374 (some may already be present from per-audit landings; reconcile at PR time)
5. Cursor opens **separate PR** to `MASTER_PLAN.md` adding the 8 phase entries per AFR §6 lines 339–347
6. This working doc archived/deleted in cleanup PR
7. Action 6 → Gate D **CLOSED**

---

## §6 Mechanism Application Notes (Discipline Acknowledgment)

This working doc applies **Mechanism 4 (verification language discipline)** throughout:
- Every Class C ID + line citation in §0–§5 grep-verified against AFR before commit per operator discipline-acknowledgment guidance
- Quote-vs-paraphrase distinction preserved: spec wording in `> blockquote`; operator-decision text in italics or plain
- Source-coverage gaps disclosed in §0.2 (Cluster A audit redlines NOT directly read; sourced via AFR §1/§5)

This working doc applies **Mechanism 5 (amendment-round verification)** for cross-spec coherence:
- Pattern-001 bilateral coherence preserved across Items 5 + 6 + 9 Authority Recovery / Demotion patterns
- Pattern-002 4-variant taxonomy preserves Items 5 + 6 + 8 + 9 + 10 architectural template precedents
- Pattern-003 freshness substrate cumulative confirmation across 5 HIGH-IMPACT audits (escalation rhetoric preserved per P1.3.8 framing)

---

## §7 Closing Notes

- **Total operator decisions captured:** 43 rows in §4 (9 patterns + 28 Tier 2 + 5 side-findings + 1 already-ratified)
- **Effective operator attention budget:** ~11 substantive decisions after Tier 1 absorption + speed-ratification
- **No Class A findings** in scope (mechanical corrections handled at Gate 1 batch-clear; not operator decisions)
- **No new architectural commitments introduced** by this working doc — purely organizes the operator-decision space distilled from 8 merged audits
- **STOP conditions:** none triggered during drafting; pattern synthesis matched expected exhaustiveness; 31 open Class C reconciled to expected count; ratify in §4 at operator pace

**Next step:** operator reviews §1 patterns + §2 Tier 2 items + §3 side-findings; fills §4 dispositions; Cursor synthesizes §5 final D-023 wording in separate PR.

**STOP. Awaiting operator authorization to proceed with §4 ratification or to drop this working doc and proceed differently.**
