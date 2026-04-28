# MarketMuse — Audit Findings Disposition Plan v1.9
**Owner:** tesfayekb
**Drafted:** 2026-04-28 (ET)
**Revised:** 2026-04-28 — v1.5 → v1.6 applies 2 items from combined verification round across Master Plan v2.0.1 + Build Roadmap v1.5 + DP v1.5: **H-1** (§0 paragraph 5 "subsequent v1.5" → "subsequent v1.6" — same revision-stamp roll-forward pattern Cursor caught in v1.3 → v1.4 N-1; document IS now v1.5 so forward-pointing reference must roll to v1.6) + **N-1** (header concurrent-review note "AI Build Roadmap is undergoing Cursor verification of v1.3 in parallel" → "AI Build Roadmap settled at v1.5 (Cursor v1.4 review applied)" — historical staleness; the version-agnostic citation pattern in §0 invariant + footer handles structural concern but symmetric standing-rule application requires fix-now). **Per operator standing rule (fix-now over defer-to-later) applied symmetrically to all 5 combined-round items: 3 in companion Master Plan v2.0.1 → v2.0.2 (CR-1 + M-1 + M-2) + 2 here.** Audit-trail discipline preserved: all 16 prior fixes (v1.0 through v1.5) intact (math-corrected from inherited typo "11 prior fixes" in v1.7 acknowledgment text per v1.8 cumulative-count math correction; correct count v1.1+v1.2+v1.3+v1.4+v1.5 = 7+5+2+1+1 = 16).
**Patch v1.6 → v1.7 applies Cursor combined-round O-2 (1 site — DP status line "MASTER_ROI_PLAN.md v2.0.1" → "v2.0.2" per operator option (a) hardcode preference; companion Build Roadmap also receiving 2-site O-2 patch in same combined-round cleanup, advancing v1.5 → v1.6) + O-2-derived forward-pointer roll-forward (1 site, NOT in Cursor's O-2 enumeration but per same H-1 next-version anchor pattern Cursor approved at v1.3 → v1.4 + v1.5 → v1.6: §0 paragraph 5 "subsequent v1.7" became self-referential when document moved v1.6 → v1.7, rolled to "subsequent v1.8") + concurrent-review note refresh (Build Roadmap settled at v1.5 → settled at v1.6 since companion document advanced in same patch cycle). 3 sites total.
**Patch v1.7 → v1.8 applies converged-state cleanup from second combined verification round (Cursor flagged 7 bounded residuals across the trio after the O-2 cleanup advanced this doc + Build Roadmap but didn't propagate companion-version references back to Master Plan; same recursion pattern only polarity flipped). 4 logical fixes / 6 physical sites in this document: (i) cross-doc version updates: status line + footer references "Master Plan v2.0.2 + Build Roadmap v1.6" → "Master Plan v2.0.3 + Build Roadmap v1.7" (2 sites); (ii) O-2-derived forward-pointer roll-forward: §0 paragraph 5 "subsequent v1.8" → "subsequent v1.9" per next-version anchor pattern (1 site); (iii) concurrent-note refresh: "AI Build Roadmap settled at v1.6" → "settled at v1.7" since companion document advanced in same cleanup cycle (1 site); (iv) **cumulative-fix-count carryover with math correction** (1 logical fix at 1 site): inherited "all 11 prior fixes (v1.0 through v1.5) intact" was mathematically wrong — at v1.6 drafting, prior fixes (v1.1 through v1.5) = 7+5+2+1+1 = 16, not 11. The "11" was a typo introduced when the v1.6 patch was generated; Cursor's recommendation in this round preserved the typo by suggesting "13 prior fixes through v1.6" (which would be 11+2). v1.8 restores math correctness: at v1.8 drafting, prior fixes through v1.7 = 7+5+2+1+1+2+3 = 21. Per operator standing rule (fix-now over defer-to-later applied symmetrically) AND operator's "DO NOT INTRODUCE FURTHER REGRESSION" instruction, propagating a known-wrong number is itself a regression — v1.8 fixes the math correctly and documents the correction explicitly. Per operator standing rule applied symmetrically including derived items. DP settles at v1.8; trio commit-ready as Master Plan v2.0.3 + Build Roadmap v1.7 + DP v1.8.
**Patch v1.8 → v1.9 applies Phase 1 factual-correction cycle from external pre-deployment audit (Cursor 2026-04-28, conducted against the Action 1 v1.0 prompt and surfacing that item (m)'s prior 8-strategy canonical-list assertion was factually wrong: the migration it cited enumerates 10 values, not 8, with two of the listed values appearing in zero production code (verified via exhaustive grep — pure documentation phantoms) and four real canonical values silently omitted). 3 substantive sites in this document corrected: (i) §268 item (m) canonical-list replaced with the migration-order 10 + citation chain widened to include `strategy_selector.py:17-28` `STATIC_SLIPPAGE_BY_STRATEGY` (production validity set used at line 1021) and `risk_engine.py` line range corrected from `:105-106` to `:103-111` (full `_DEBIT_RISK_PCT` table); (ii) §273 item (r) Item 6 V0.2 build commitment corrected — ratifies the 2 long-side additions (`U_LC`, `U_LP`) ahead of D-023 and defers the 3 not-yet-covered canonical strategies (`call_credit_spread`, `debit_put_spread`, `calendar_spread`) to D-023 ratification with default-and-alternative pattern matching prior §1/§2 items; (iii) §318 B-AI-006-12 Class B findings row updated to mirror the corrected canonical-10 framing. Authoritative ground truth: `supabase/migrations/20260419_add_strategy_types.sql:11-22` (10 canonical strategy_type values; no later migration alters the constraint, verified during pre-deployment audit). Per operator standing rule (fix-now over defer-to-later) applied to the trio docs only — the phantom-value propagation in `AUDIT_FINDINGS_REGISTER.md` + `AI-SPEC-006.md` is deferred to a separate Phase-1B PR (different governance path; specs are audit source-of-record). 2-doc cleanup cycle in this round (DP v1.8 → v1.9 + Build Roadmap v1.7 → v1.8); Master ROI Plan stays at v2.0.3 (no canonical-list claim in that doc; verified). DP settles at v1.9; trio commit-ready as Master Plan v2.0.3 + Build Roadmap v1.8 + DP v1.9.
**Independent count verification (Cursor CR-1 confirmed):** Read AUDIT_FINDINGS_REGISTER.md §0 directly. Unique PRE-P findings: §0.1 PRE-P0-1..4 (4) + §0.2 PRE-P11-1..7 (7) + §0.3 PRE-P12-1..4 (4) + §0.4 PRE-P130-1 (1) + §0.5 PRE-P130B-1..2 (2) = **18 unique**. §0.6 cross-reference table re-cites 6 of these (PRE-P11-3, PRE-P11-4, PRE-P11-5, PRE-P11-6, PRE-P11-7, PRE-P12-1) for cross-section visibility — those are duplicates, not new findings. Naive `grep '^| PRE-P'` returns 24 rows because it counts §0.6 re-cites; that's the source of the v1.2 H-A miscount.
**Concurrent review note:** AI Build Roadmap settled at v1.8 (Phase 1 factual-correction cycle applied alongside this DP v1.9 patch in same simultaneous 2-doc cleanup cycle). Footer + §0 invariant below use version-agnostic citation ("AI Build Roadmap [current published version]") to avoid stale references regardless of further version churn through commit.
**Status:** **DRAFT v1.9** — Phase 2 Document 3 (companion to `MASTER_ROI_PLAN.md` v2.0.3 + `AI_BUILD_ROADMAP.md` v1.8 — DP + BR settled in Phase 1 factual-correction cycle; Master ROI Plan unchanged; trio commit-ready)
**Source register:** `trading-docs/08-planning/ai-architecture-audits/AUDIT_FINDINGS_REGISTER.md` (334 lines; **21 open Class C + 1 resolved (C-AI-002-2)** + 74 open Class B + **18 unique PRE-P findings** + §5 Cross-Spec Themes + §6 Governance Updates)
**Authority:** This document governs **operator decisions** that Master ROI Plan and AI Build Roadmap depend on. For every Class C row, this document enumerates the operator-decision options verbatim from the source register and names a default position. Default positions match the audit register's "Default position" lines. **For any conflict between this document and the source register, the source register wins.**

---

## ⚠️ §0 — READ-ME-FIRST

This document is one of three β-lite governance documents for MarketMuse. **DO NOT READ THIS DOCUMENT IN ISOLATION.** See `MASTER_ROI_PLAN.md` §0 pointer table for full context.

**Source-fidelity discipline (load-bearing per Cursor v1.2 verification approval):** Every Class C row's default position quotes the audit register verbatim using "(option N)" markers. This makes cross-doc verification grep-checkable: any reviewer can run `grep "(option 2)" trading-docs/08-planning/ai-architecture-audits/AUDIT_FINDINGS_REGISTER.md` and confirm each disposition default cites the right option from the source row.

**Authority hierarchy:**
- This document specifies **what operator decisions are pending** and **default positions**
- `MASTER_ROI_PLAN.md` specifies **when activation events happen** (Gates A-F including D-023/D-024 ratification at Action 6)
- `AI_BUILD_ROADMAP.md` specifies **what gets built and in what order** — its §0 dependency map cites this document's defaults for 9 Class C decisions affecting build sequencing

**β-lite cross-document consistency invariant:** AI Build Roadmap (current published version) §0 Class C dependency map MUST match this document's default positions. The 9 Class C items cited there are: [C-AI-004-4], [C-AI-005-1], [C-AI-005-2], [C-AI-006-1], [C-AI-006-2], [C-AI-006-3], [C-AI-006-4], [C-AI-010-1], [C-AI-010-5]. Each is enumerated in §1 of this document with the exact same default position the build roadmap assumed. The combined verification round will spot-check this consistency end-to-end. **Version-agnostic citation pattern adopted per Cursor v1.2 H-1** to handle parallel-revision drift between this document and AI Build Roadmap.

**Deferred to combined verification round (per operator standing rule: NONE deferred from this draft):** Per operator's standing rule "fix-now over defer-to-later" because thread/agent handoffs are the silent-drop surface that annotation alone cannot fully prevent. All 7 items from Cursor v1.0 review (3 critical + 2 high + 2 medium) were fixed in v1.1, NOT deferred. If the post-commit verification surfaces new items in this document, they will be fixed in a subsequent v2.0 produced before commit (NOT deferred to post-commit). This pattern differs from `AI_BUILD_ROADMAP.md` v1.2's deferral of 4 cosmetic items, because the operator rule applies prospectively — the Build Roadmap v1.2 deferrals were made before the standing rule was articulated; future cycles fix-now.

---

## 1 — 21 Open Class C Operator Decisions Enumerated (C-AI-002-2 RESOLVED per register §4 — see §1.0 below for cross-reference)

Every row below is an operator decision that the audit register flags as **open** with `**Operator decision required**` framing. Default positions cite the register verbatim. **Where a row says "Folds into D-023 wording", the resolution does NOT require a new D-XXX** — it extends D-023's scope. Where a row says "Possible new D-XXX (e.g., D-024)", a new decision record may be needed.

### 1.0 — C-AI-002-2 (RESOLVED — cross-reference only)
**Source:** AI-SPEC-002 §10.3 C2; register §4 line 234 (Resolved Findings); Update Log entry P1.3.2
**Issue:** `trade_counterfactual_cases` table-vs-column architectural divergence with Item 10 (originally raised in P1.3.2 as Class C escalation).
**Resolution:** RESOLVED per register §4 — option 1 (new table) chosen. Item 10 Layer 2 owns the canonical `trade_counterfactual_cases` table; AI-SPEC-002's role is consumer, not table-owner. **No operator decision pending.** Cross-referenced here for completeness — total Class C count was 22 (21 open + 1 resolved); Cursor v1.0 review C-2 caught the heading drift.

### 1.1 — AI-SPEC-001 AI Risk Governor (3 Class C)

#### [C-AI-001-1] Governor `size_multiplier_cap` channel scope
**Source:** AI-SPEC-001 §10.3 C1; register line 102
**Issue:** Does Governor's `size_multiplier_cap` channel (LLM-driven sizing reducer composing `min()` with `_RISK_PCT[phase]`) require new D-023, or fall inside D-014's existing "automatic regression" scope?
**Default position (verbatim from register):** "Ratify D-023 with explicit scope: LLM-driven sizing reducer; cannot increase any cap; cannot override D-005 / D-010 / D-011 / D-022; promotion to live-binding requires V0.2 graduation criteria + 90-day A/B per `system-state.md` line 8 (`live_trading: blocked_until_90day_AB_test_passes`)."
**Folds into D-023 enrichment item (a)** per §6 governance updates.
**Cited by AI Build Roadmap §3.1** sub-items 4, 9 (size_multiplier_cap channel deferred per C-AI-001-1; V0.2 candidate).

#### [C-AI-001-2] Promotion-gate authority handoff (V0.2 paper-binding + Lean Live)
**Source:** AI-SPEC-001 §10.3 C2; register line 103
**Issue:** V0.1 → V0.2 paper-binding gate AND V0.2 Lean Live 0.25x → 0.5x gate use mixed thresholds. Spec doesn't specify whether transitions are automated when criteria pass or require explicit operator approval per event.
**Default position (verbatim):** "Per T-Rule 9 + `system-state.md`: any transition that affects live capital (V0.2 → small-live veto, lean live 0.25x → 0.5x) requires explicit operator approval per event; paper-binding-only promotions can be automated subject to GLC-001..012 cleanliness. Encode this distinction in D-023 alongside C1."
**Folds into D-023 enrichment item (d).**

#### [C-AI-001-3] Opportunity-lean channel disposition
**Source:** AI-SPEC-001 §10.3 C3; register line 104
**Issue:** Opportunity-lean is the only Governor authority surface that *proposes* a trade rather than gating one (admissibility-of-a-new-strategy-class). In tension with Spec §27 ("AI controls admissibility and size ceilings, not trade execution").
**Default position (verbatim):** "Per consolidated plan §5 conservative-first principle: defer the lean channel to a separate spec (AI-SPEC-001b or AI-SPEC-014); ship core Item 1 V0.1 as veto-only. Re-introduce lean only after the core Governor passes graduation."
**Folds into D-023 enrichment item (c).** Corresponds to AI Build Roadmap §3.1 sub-item 10 (deferred from V0.1 build commitment).

---

### 1.2 — AI-SPEC-002 Strategy-Aware Attribution (2 Class C)

#### [C-AI-002-1] `decision_outcome` enum coordination with AI-SPEC-001
**Source:** AI-SPEC-002 §10.3 C1; register line 105
**Issue:** Item 2's `decision_outcome` enum is binary-coded (8 values for opened/blocked) but has no value for Governor sizing reductions (`size_multiplier_cap` channel). Without coordination, Item 1's size-cap writes will fail Item 2's CHECK constraint.
**Default position:** Operator decision between two options — register does not name a single default but provides resolution path: "(option 1) extend Item 2 enum with `cap_governor` / `reduced_governor` BEFORE Item 2 ships; (option 2) D-023 wording requires AI-SPEC-001 to write `opened_traded` for size-cap decisions and Item 1's authority is limited to size-cap-not-block. Either way, encode resolution in D-023 alongside the AI-SPEC-001 dispositions. **Folds into existing D-023 wording, not a new D-XXX.**"
**Operator action item:** Pick option 1 OR option 2 at D-023 ratification (Master ROI Plan Action 6).
**Folds into D-023 enrichment item (b).**

#### [C-AI-002-3] Legacy `attribution_*` BOOLEAN columns disposition on `trading_positions`
**Source:** AI-SPEC-002 §10.3 C3; register line 106
**Issue:** `trading_positions` has 4 dead `attribution_*` columns from baseline migration `20260416172751_*.sql:203-206`. No production code path writes them.
**Default position (verbatim):** "**Default position:** option 1 (deprecate-in-place), unless a Phase 2 audit discovers silent consumers."
**Three options summarized:** option 1 deprecate-in-place via migration comment; option 2 formally remove via DROP COLUMN; option 3 repurpose with backfill from `strategy_attribution`.
**No new D-XXX strictly required.**

---

### 1.3 — AI-SPEC-004 Replay Harness (4 Class C)

#### [C-AI-004-1] `paper_phase_criteria` vs `item_promotion_records` authority overlap
**Source:** AI-SPEC-004 §10.3 C1; register line 107
**Issue:** Spec creates per-item authority-promotion gate alongside existing `paper_phase_criteria` (12 GLC criteria per D-013, system-wide go-live gate). Coordination is silent.
**Default position (verbatim):** "**Default position (per consolidated plan §5 conservative-first principle):** option 1 (independent gates with explicit non-conflict statement; preserves D-013)."
**Three options:** option 1 independent gates; option 2 unified gate (adds GLC-013 to paper_phase_criteria, requires new D-XXX); option 3 hierarchical.
**No new D-XXX strictly required for default option 1.**

#### [C-AI-004-2] Decision-card definition for ≥200 promotion gate
**Source:** AI-SPEC-004 §10.3 C2; register line 108
**Issue:** AI-SPEC-001 §12 V0.2 paper-binding gate requires "≥200 replay/advisory decision cards" but canonical card surface is ambiguous between `replay_eval_cases.calibration_eligible = true` (Item 4 surface), `shadow_predictions` rows (existing forward A/B), or some non-existent advisory surface.
**Default position (verbatim):** "**Default position:** option 1 (rigorous; matches spec architectural intent)."
**Three options:** option 1 canonical = `replay_eval_cases.calibration_eligible = true` (excludes shadow_predictions); option 2 canonical = UNION of replay_eval_cases AND shadow_predictions (broader); option 3 two separate gates.
**Folds into D-023 enrichment item (e). No new D-XXX required.**

#### [C-AI-004-3] `item_promotion_records` startup-read contract
**Source:** AI-SPEC-004 §10.3 C3; register line 109
**Issue:** Spec mandates "Items 1, 5, 6 read item_promotion_records at startup. If no current record exists for an item/scope: default to advisory or disabled, NEVER production." But no D-XXX currently codifies the rule.
**Default position (verbatim):** "Operator decision: extend the pending D-023 wording to include a clause: 'any item subject to AI authority promotion (Items 1, 5, 6, and any future per-item-promotion-gated specs) MUST read its current authority level from `item_promotion_records` at startup; absence of a current row defaults to `advisory` (for items already paper-binding-eligible) or `disabled` (for items not yet paper-binding-eligible); items MUST NOT invent their own promotion status.'"
**Folds into D-023 enrichment item (f). No new D-XXX strictly required.**
**Cited by AI Build Roadmap §3.1 sub-item 7** (capital preservation invariant — "default to 'advisory' or 'disabled', NEVER 'production'").

#### [C-AI-004-4] Chain archive substrate as HARD V0.1 prerequisite ⚠️ CRITICAL CASCADE
**Source:** AI-SPEC-004 §10.3 C4; register line 110
**Issue:** Spec §1 lines 47-66 establishes hard architectural prerequisite: archived option-chain data. At HEAD, no chain archive exists. **Load-bearing for V0.1 calendar.**
**Default position (verbatim):** "**Default position (per consolidated plan §5 conservative-first principle):** option 3 with parallel-track exploration of options 1 and 2; operator revisits the V0.1-vs-V0.2 promotion line at end-of-V0.1."
**Three options:**
- **option 1** forward archival (months-long) — start chain-archival now; Item 4 V0.1 ships with scaffolding + Step 0 validation but produces no calibration-grade results until archive sufficient (estimated 6+ months for 90 sessions per Spec §6).
- **option 2** paid historical archive — Polygon historical-bars + Tradier (or Databento) historical chains paid tier; V0.2 can run calibration-grade replay over recent historical data. Cost: TBD; contractual dependency.
- **option 3 (default)** explicit V0.1 advisory-only acceptance — operator formally accepts Spec §10 Failure Mode; V0.1 ships per spec scaffolding (4 tables + 8 files + Step 0 validation logic + walk-forward implementation) but produces no calibration-grade results. Items 1, 5, 6 stay advisory; production-binding deferred to V0.2 calendar.
**Cascade impact:** This decision **cascades to Items 4 + 5 + 10 V0.2 timing** (cited in AI Build Roadmap §0 dependency map + Phases 3C/3D/3E). Bilateral with [C-AI-005-3].
**No new D-XXX strictly required for default option 3** — explicit operator acceptance logged in `system-state.md` `replay_harness.calibration_grade_capable = false`.
**Cited by AI Build Roadmap §0 Class C dependency map row 1 + §3.3 sub-item 7.**

---

### 1.4 — AI-SPEC-005 Volatility Fair-Value Engine (3 Class C)

#### [C-AI-005-1] D-016 disposition (HAR-RV vs realized term)
**Source:** AI-SPEC-005 §10.3 C1; register line 116
**Issue:** Spec is silent on D-016. Spec proposes HAR-RV remainder model that produces `rv_forecast_final` — the natural successor to the `realized` term in D-016's `sigma = max(realized, 0.70 × implied)` formula. **Spec must take a position on D-016 before integration.**
**Default position (verbatim):** "**Default position (per consolidated plan §5 conservative-first principle):** option 2 (HAR-RV as new signal; D-016 unchanged). Lowest-cost; preserves D-016 explicit governance; defers any D-016 amendment to a future spec or upgrade decision."
**Three options:**
- **option 1** HAR-RV REPLACES `realized` in D-016 — requires D-016 amendment with new D-XXX (e.g., D-024). Highest-impact.
- **option 2 (default)** HAR-RV is NEW signal feeding EV table only; D-016 unchanged. Lowest-impact.
- **option 3** HAR-RV outputs `rv_forecast_final` AND D-016 amends `realized` to read from HAR-RV after V0.2 graduation. Two-phase.
**Folds into D-023 enrichment items (k) [Item 5 authority boundary including "Item 5 does NOT have authority to amend D-016"] AND (l) [Item 5 Layer 1/Layer 2 cutover policy via C-AI-005-2]. No new D-XXX strictly required for default option 2.**
**Source-register inheritance note (Cursor v1.0 H-2):** Audit register line 116 cites only "(D-023 enrichment item (l))" but register §6 places the D-016 disposition wording under item (k). This is an inherited contradiction in the register itself; this disposition plan resolves by citing both items so neither path drops on cross-reference. Combined verification round may surface this for register §6 amendment.
**Resolves D-015/D-016 divergence open** per `what-is-actually-built.md` line 14 ("D-016 partially built").
**Cited by AI Build Roadmap §0 Class C dependency map row 2 + §3.5 sub-item 10.**

#### [C-AI-005-2] Item 5 Layer 1 cutover policy
**Source:** AI-SPEC-005 §10.3 C2; register line 117
**Issue:** Spec silent on what happens to existing 12A `polygon:spx:realized_vol_20d` writer at `polygon_feed.py:486` after Layer 2 ships.
**Default position (verbatim):** "**Default position (per consolidated plan §5 conservative-first principle):** option 1 (Layer 1 stays put; Layer 2 ships parallel keys)."
**Three options:**
- **option 1 (default)** Layer 1 stays put as backward-compat surface; Layer 2 produces NEW `vol:*` keys; existing consumers continue reading `polygon:spx:realized_vol_20d` indefinitely.
- **option 2** Layer 1 stays as `legacy_observability_only`; Layer 2 outputs become canonical; existing consumers migrate.
- **option 3** Layer 1 deprecated entirely; Layer 2 producer replaces 12A writer.
**Folds into D-023 enrichment item (l) — extends item (g) for Layer 1/Layer 2 cutover policy. No new D-XXX strictly required.**
**Cited by AI Build Roadmap §0 Class C dependency map row 3 + §3.5 sub-item 11.**

#### [C-AI-005-3] Item 5 V0.x advisory-only acceptance ⚠️ BILATERAL with [C-AI-004-4]
**Source:** AI-SPEC-005 §10.3 C3; register line 118
**Issue:** Item 5's V0.2 promotion gate "Baseline E must beat Baseline F" requires archived chains for IV extraction during replay calibration. **Bilateral with [C-AI-004-4]:** if operator chooses option 3 there, Item 5 V0.2 promotion is calendar-blocked.
**Default position (verbatim):** "**Default position (per consolidated plan §5 conservative-first principle):** option 3 with parallel-track exploration of options 1 and 2; operator revisits the advisory-only-vs-calibration-grade promotion line at end-of-V0.2."
**Three options:** Same option 1/2/3 as [C-AI-004-4] — same operator decision resolves both.
**No new D-XXX strictly required for option 3** — explicit operator acceptance logged in `system-state.md` `vol_fair_value_engine.calibration_grade_capable = false`.

---

### 1.5 — AI-SPEC-006 Meta-Labeler (4 Class C)

#### [C-AI-006-1] Authority Recovery automatic-vs-operator-mediated ⚠️ CRITICAL FIRST AUTHORITY-BOUNDARY CLASS C
**Source:** AI-SPEC-006 §10.3 C1; register line 119
**Issue:** Spec §9.4 line 622 specifies AUTOMATIC authority recovery (advisory → reduced → normal) via `30-session cooldown + 20 qualified signals` — verbatim "Mirror Item 5: minimum 30-session cooldown, then one-step recovery (advisory → reduced → normal) after demonstrated recalibration over 20 qualified signals." Per architectural principle 1 + T-Rule 4, authority RECOVERY (increasing AI authority) should require explicit operator action. **Bilateral with AI-SPEC-005 §5 reliability state machine** which has the SAME automatic-recovery pattern. **CRITICAL Class C escalation per Guard 1 — first authority-boundary-violation Class C in Cluster B.**
**Default position (verbatim):** "**Default position (per consolidated plan §5 conservative-first principle):** option 2 (operator-mediated recovery only); D-023 enrichment item (p). **Bilateral resolution mandatory** with AI-SPEC-005 §5 to avoid cross-spec inconsistency."
**Three options:**
- **option 1** automatic recovery accepted — operator approves Spec §9.4 line 622 as-is for both Item 5 and Item 6.
- **option 2 (default)** operator-mediated recovery only — Spec §9.4 line 622 amended to require explicit operator approval for any one-step authority recovery; cooldown + qualified-signals threshold becomes ELIGIBILITY gate, not TRIGGER. Bilateral amendment to AI-SPEC-005 §5 mandatory.
- **option 3** hybrid — degradation automatic (authority reduction always allowed); recovery requires operator-mediated approval through `item_promotion_records` change-control with 30+20 as ELIGIBILITY gate.
**Folds into D-023 enrichment item (p). No new D-XXX strictly required.**
**Cited by AI Build Roadmap §0 Class C dependency map row 4 + §3.5 sub-item 12 + §3.8 sub-item 8.**

#### [C-AI-006-2] Item 6 Layer 1 (12K bf41175) cutover
**Source:** AI-SPEC-006 §10.3 C2; register line 120
**Issue:** Spec §13 V0.2 Build Scope silent on `bf41175` Layer 1 LightGBM meta-label scaffold cutover policy. Layer 1 dormant pass-through (`backend/models/meta_label_v1.pkl` absent) but `train_meta_label_model()` + inference block + Redis flag + 9 tests are LIVE code at HEAD.
**Default position (verbatim):** "**Default position (per Cluster A precedent of Items 5 + 10):** option 1 (Layer 1 stays put as legacy observability)."
**Three options:**
- **option 1 (default)** Layer 1 stays put as legacy observability — `system-state.md` `meta_labeler.layer_1_phase = 'dormant_legacy_observability'`.
- **option 2** Layer 1 deprecated entirely — `bf41175` scoring block removed; `train_meta_label_model()` retired; champion-challenger deleted.
- **option 3** Layer 1 + Layer 2 run as champion-challenger — `run_meta_label_champion_challenger` infrastructure repurposed.
**Folds into D-023 enrichment item (q).** No new D-XXX required.
**Cited by AI Build Roadmap §0 Class C dependency map row 5 + §3.8 sub-item 9.**

#### [C-AI-006-3] Bayesian prior parameter governance
**Source:** AI-SPEC-006 §10.3 C3; register line 121
**Issue:** Spec §2 hardcodes prior parameters (`alpha=1, beta=1`, `k=20`, `w_prior` 0.55/0.40/0.25). Spec contains zero references to operator-tunable governance.
**Default position (verbatim):** "**Default position (per consolidated plan §5 conservative-first principle):** option 1 (operator-tunable via `system-state.md`); first promotion-gate review revisits the question. **No new D-XXX strictly required if default option 1 chosen** — folds into D-023 enrichment item (s)."
**Three options:**
- **option 1 (default)** prior parameters operator-tunable via `system-state.md` `meta_labeler.prior_parameters` field.
- **option 2** prior parameters operator-tunable via `approved-decisions.md` — new D-XXX (e.g., D-024) ratifies values as constitutional constants.
- **option 3** prior parameters code-bound constants until first promotion-gate review (`n_train >= 300`).
**Cited by AI Build Roadmap §0 Class C dependency map row 6 + §3.8 sub-item 4.**

#### [C-AI-006-4] LightGBM Direction Model spec ownership ⚠️ DETERMINES PHASE 3G EXISTENCE
**Source:** AI-SPEC-006 §10.3 C4; register line 122
**Issue:** Spec §3.4 lines 293-305 reads 5 fields from a "LightGBM Direction Model" producer. The producer has NO spec in the AI architecture catalog. Bilateral with `B-AI-006-4`.
**Default position (verbatim):** "**Default position (per consolidated plan §5 conservative-first principle):** option 2 (new spec AI-SPEC-014); minimizes Item 6 V0.2 scope creep but adds Cluster B audit cycle. **Possible new D-XXX (e.g., D-024) for AI architecture catalog extension** — operator decision pending; bilateral with `C-AI-006-3` D-XXX numbering choice."
**Three options:**
- **option 1** add LightGBM Direction Model as Item 6 V0.2 ship sub-scope — Item 6 V0.2 builds the direction model in same engine module.
- **option 2 (default)** add new spec — register names "AI-SPEC-014"; **AI Build Roadmap v1.2 renamed to AI-SPEC-016 per Cursor v1.0 H-1** to avoid collision with deferred Item 14 Tournament Engine. Operator decision concerns whether to extend the AI architecture catalog.
- **option 3** remove the 5 LightGBM Direction Model fields from Item 6 §3.4 — Item 6 V0.2 ships without direction-tilt features.
**Possible new D-XXX (e.g., D-024)** for AI architecture catalog extension if option 2 chosen.
**Resolves D-021 divergence** per `what-is-actually-built.md` line 16 ("HMM + LightGBM regime classifier — NOT BUILT — rule-based").
**Cited by AI Build Roadmap §0 Class C dependency map row 7 + §3.6 (Phase 3G existence gated on this decision).**

---

### 1.6 — AI-SPEC-010 Counterfactual P&L (5 Class C)

#### [C-AI-010-1] Spec §0 "do not rewrite" vs Spec §3 Layer 1 surgical fix internal contradiction
**Source:** AI-SPEC-010 §10.3 C1; register line 111
**Issue:** Spec §0 line 14 ("Do not rewrite the current `counterfactual_engine.py`") + Spec §3 lines 174-186 ("Replace Default-to-iron_condor Behavior") — internal contradiction.
**Default position (verbatim):** "**Default position (per consolidated plan §5 conservative-first principle):** option 1 (surgical bug fix to Layer 1 with documentation update). Folds into Spec §0 wording amendment in Phase 2."
**Two options:**
- **option 1 (default)** treat Spec §3 change as small surgical bug fix not a rewrite — Layer 1 modified in-place via tiny PR (`counterfactual_engine.py:213-223` hardcoded `iron_condor` fallback → NULL-return path when `strategy_hint` missing).
- **option 2** freeze Layer 1 entirely; Spec §3 fix lives ONLY in Layer 2 — higher-cost.
**Cited by AI Build Roadmap §0 Class C dependency map row 8 + §3.4 Stage 1 sub-item 5.**

#### [C-AI-010-2] Cluster/tier classification discrepancy
**Source:** AI-SPEC-010 §10.3 C2; register line 112
**Issue:** Spec §0 line 5 (Tier "V0.2 immediate / V0.2 strategy-specific / V0.3 adversarial / V0.4 exit") vs `CROSS_CUTTING_EVIDENCE_MATRIX.md` §1 line 52 (Tier "V0.1") — cluster/tier classification discrepancy.
**Default position (verbatim):** "Operator decision: ratify the layered framing — **V0.1 = Layer 1 (already shipped at commit `2400e98`); V0.2 onward = Layer 2 (proposed in this spec).** Cluster A is correct because Items 5/6/9 (Cluster B) cannot promote to binding without Item 10 V0.2 outputs; Cluster A audit is therefore complete after P1.3.4 with the understanding that 'Cluster A complete' means 'all four Cluster A specs audited' — not 'all V0.1 work done' (Layer 2 V0.2 ships in Phase 4 alongside Cluster B). Matrix §1 line 52 amended in Phase 2 to show graduated tier."
**No new D-XXX required.**

#### [C-AI-010-3] z-score producer authority
**Source:** AI-SPEC-010 §10.3 C3; register line 113
**Issue:** Spec §5 lines 363-376 (slippage formula's `vix_z` / `spread_z` z-score producer authority). Slippage formula references without defining producer.
**Default position (verbatim):** "**Default position (per consolidated plan §5 conservative-first principle):** option 3 (shared producer in stable namespace). Resolves bilateral concerns; encoded in D-023 wording alongside other cross-spec data producer ownership. **Folds into existing pending D-023 wording, not a new D-XXX.**"
**Three options:** option 1 AI-SPEC-001 owns; option 2 AI-SPEC-005 owns; option 3 (default) shared producer with explicit Redis namespace (e.g., `features:vix_z`, `features:spread_z`) owned by `calibration_engine` per D-019.
**Folds into D-023 enrichment item (h).**
**Cited by AI Build Roadmap §3.4 Stage 1 sub-item: z-score producer authority shared `features:*` namespace owned by calibration_engine per D-019.**

#### [C-AI-010-4] Item 3 vs Item 10 ownership of synthetic counterfactual cases
**Source:** AI-SPEC-010 §10.3 C4; register line 114
**Issue:** Item 10 owns the table `trade_counterfactual_cases` that stores synthetic cases. But Item 3 (AI-SPEC-003) is the canonical owner of synthetic case generation. **Unresolved:** does Item 3 INSERT into Item 10's table, or does Item 3 own a separate table?
**Default position (verbatim):** "**Default position (per consolidated plan §5 conservative-first principle):** option 1 (Item 3 INSERTs into Item 10's table). Encoded in Item 3 P1.3.X audit (Cluster C — future). **No new D-XXX required.**"
**Two options:**
- **option 1 (default)** Item 3 generates synthetic cases that INSERT into Item 10's `trade_counterfactual_cases` table with `case_type = 'synthetic'`, `case_weight = 0.2`. Single canonical table.
- **option 2** Item 3 owns separate `synthetic_counterfactual_cases` table; Items 5-9 read via UNION.
**Cited by AI Build Roadmap §3.14 (Item 3 V0.1 sub-item 3 — INSERT into Item 10 table per [C-AI-010-4] default option 1).**

#### [C-AI-010-5] `<Commit_4_deploy_date>` cutover anchor lock ⚠️ BILATERAL with Master ROI Plan Action 7
**Source:** AI-SPEC-010 §10.3 C5; register line 115
**Issue:** Lockdown migration uses `<Commit_4_deploy_date>` as cutover for legacy-observability lockdown. "Commit 4" not yet shipped at HEAD (planned for 2026-04-28 per pre-AI track addendum A1). Anchor is moving target until Commit 4 ships.
**Default position (verbatim):** "**Default position (per consolidated plan §5 conservative-first principle):** option 1 (concrete commit hash post-Commit-4 ship). Lowest-cost; preserves operator-explicit governance. **Folds into existing D-023 wording (Layer 1/Layer 2 cutover policy) — no new D-XXX strictly required.**"
**Three options:**
- **option 1 (default)** concrete commit hash — once Commit 4 ships, replace `<Commit_4_deploy_date>` with actual deploy timestamp. Layer 1 backfill runs on that date.
- **option 2** date-of-Layer-2-deployment anchor — cutover = Layer 2 first-deploy date; decouples Item 10 V0.2 from IC/IB sequence.
- **option 3** per-row classifier — evaluate each Layer 1 row at backfill time.
**Bilateral with Master ROI Plan Action 7 (Pre-AI Commit 4 ship).** Phase 3D ship date = Action 7 ship date + verification.
**Folds into D-023 enrichment item (j). No new D-XXX strictly required.**
**Cited by AI Build Roadmap §0 Class C dependency map row 9 + §3.4 Stage 1 sub-item 8.**

---

## 2 — D-023 Ratification Scope (enrichment items a-t)

D-023 is reserved per `approved-decisions.md` for "AI Authority Boundary." Master ROI Plan Action 6 ratifies it. Per audit register §6, D-023 wording covers items (a) through (t):

| Item | Source | Wording (verbatim from register §6) |
|---|---|---|
| **(a)** | AI-SPEC-001 §11 | Governor's `size_multiplier_cap` channel composing with `_RISK_PCT[phase]` |
| **(b)** | AI-SPEC-001 §11 + AI-SPEC-002 §11 addendum (`C-AI-002-1`) | Explicit non-overridability of D-005 / D-010 / D-011 / D-014 / D-021 / D-022 with reductive-only constraint; `decision_outcome` enum coordination contract — Item 1 size-cap writes use either `cap_governor`/`reduced_governor` OR `opened_traded` per option chosen |
| **(c)** | AI-SPEC-001 §11 (`C-AI-001-3`) | Opportunity-lean channel disposition (folded into D-023 OR deferred to separate spec); **default per §1.1 above: deferred to separate spec, V0.1 ships veto-only** |
| **(d)** | AI-SPEC-001 §11 (`C-AI-001-2`) | Promotion-gate authority handoff between automated criteria and operator approval; **default: any transition affecting live capital requires explicit operator approval per event** |
| **(e)** | AI-SPEC-004 §11 (`C-AI-004-2`) | Canonical "decision card" definition for Spec §12 thresholds = `replay_eval_cases.calibration_eligible = true`; explicit exclusion of `shadow_predictions` rows |
| **(f)** | AI-SPEC-004 §11 (`C-AI-004-3`) | `item_promotion_records` startup-read contract: "any item subject to AI authority promotion (Items 1, 5, 6, and any future per-item-promotion-gated specs) MUST read its current authority level from `item_promotion_records` at startup; absence of a current row defaults to `advisory` (for items already paper-binding-eligible) or `disabled` (for items not yet paper-binding-eligible); items MUST NOT invent their own promotion status." |
| **(g)** | AI-SPEC-010 §11 (`C-AI-010-1` + `C-AI-010-3` + `C-AI-010-5` + `B-AI-010-10`) | Layer 1 / Layer 2 cutover policy: "Item 10 Layer 1 (`counterfactual_engine.py`) is observability-only; Layer 2 (`counterfactual_engine_v2.py`) is calibration-grade advisory authority; downstream training consumers (Items 5/6/7/9) MUST read ONLY from Layer 2 outputs filtered on `calibration_eligible = true` + `simulation_status = 'success'`; Layer 1 surgical bug fixes (e.g., NULL-return on missing `strategy_hint`) ARE permitted under 'do not rewrite' provided they preserve the observability contract" |
| **(h)** | AI-SPEC-010 §11 (`C-AI-010-3`) | z-score producer authority assignment (`vix_z` / `spread_z` shared producer in `features:*` Redis namespace owned by `calibration_engine` per D-019) |
| **(i)** | AI-SPEC-010 §11 | `counterfactual_reason ↔ decision_outcome` enum mapping table (Item 10 owns the mapping function in Layer 2 engine) |
| **(j)** | AI-SPEC-010 §11 (`C-AI-010-5`) | Legacy-rows lockdown anchor (`<Commit_4_deploy_date>` cutover anchor for retroactive `label_quality = 'legacy_observability_only'` marking — operator-locked once Commit 4 of IC/IB sequence ships) |
| **(k)** | AI-SPEC-005 §11 | Item 5's authority boundary: authority over `vol:*` Redis namespace + `vol_fair_value_snapshots` + `strategy_ev_table` + `spx_realized_vol_history` + `vol_engine_reliability_log`; outputs measurements consumed by Items 1/6/9; **Item 5 does NOT have authority to amend D-016** |
| **(l)** | AI-SPEC-005 §11 (`C-AI-005-1` + `C-AI-005-2`) | Item 5 Layer 1 / Layer 2 cutover policy (extends item (g)): default per `C-AI-005-2` option 1 — Layer 1 stays put as backward-compat surface; Layer 2 produces parallel `vol:*` keys. **Item (l) ALSO covers `C-AI-005-1` D-016 disposition default option 2** (HAR-RV as new advisory signal; D-016 unchanged) per Cursor v1.0 H-2 — register line 116's citation of "(item (l))" for D-016 is preserved here even though item (k) above states the Item 5 authority boundary including the D-016 amendment prohibition. Both items are bilateral; operator ratification of D-023 covers both. |
| **(m)** | AI-SPEC-005 §11 + AI-SPEC-006 §11 (`B-AI-005-9` + `B-AI-006-12`) | Canonical strategy-taxonomy enumeration (extends item (i)): "Items 2 + 5 + 6 + 10 MUST use canonical 10-strategy IDs (`put_credit_spread`, `call_credit_spread`, `iron_condor`, `iron_butterfly`, `debit_put_spread`, `debit_call_spread`, `long_put`, `long_call`, `long_straddle`, `calendar_spread`) matching DB CHECK constraint `20260419_add_strategy_types.sql:11-22` and `risk_engine.py:103-111` `_DEBIT_RISK_PCT` literal + `strategy_selector.py:17-28` `STATIC_SLIPPAGE_BY_STRATEGY` (production validity set used at line 1021) — not the `bull_debit_spread` / `bear_debit_spread` alternative" |
| **(n)** | AI-SPEC-005 §11 (`C-AI-004-4` + `C-AI-005-3`) | Chain-archive substrate cascade (extends item (j)): Item 4 V0.1 + Item 5 V0.2 + Item 10 V0.2 share the same chain-archive substrate dependency; operator decision on `C-AI-004-4` cascades to all three |
| **(o)** | AI-SPEC-006 §11 | Item 6's authority boundary: keystone between Item 5's `strategy_ev_table` and AI Risk Governor; authority to BLOCK trades and REDUCE size but NO authority to FORCE/UPSIZE/override Item 1; size cap composes via `min()` only |
| **(p)** | AI-SPEC-006 §11 (`C-AI-006-1`) | Item 6 (and Item 5) Authority Recovery disposition: **default option 2 (operator-mediated recovery only)**; Spec §9.4 line 622 + AI-SPEC-005 §5 amended to require explicit operator approval for any one-step authority recovery; cooldown + qualified-signals threshold become ELIGIBILITY gates not automatic triggers; **bilateral resolution with AI-SPEC-005 mandatory** |
| **(q)** | AI-SPEC-006 §11 (`C-AI-006-2`) | Layer 1 / Layer 2 cutover policy for Item 6 (extends items (g) + (l)): default option 1 — Layer 1 stays put as legacy observability |
| **(r)** | AI-SPEC-006 §11 (`B-AI-006-12`) | Strategy taxonomy reconciliation for Item 6 (extends item (m)): Item 6 V0.2 ships utility-label calculators for the 2 long-side canonical strategies omitted from spec's existing 5 (adds `U_LC`, `U_LP`). **Deferred to D-023 ratification (Action 6, Days 5–7):** whether Item 6 V0.2 additionally ships utility-label calculators for the 3 canonical strategies not covered by spec's existing 5 + this addition (`call_credit_spread`, `debit_put_spread`, `calendar_spread`). **Default deferred-decision = ship subset whose live-emission sample size meets [C-AI-006-3] Bayesian prior thresholds at Action 6 evaluation; alternative = ship all 3 ahead of sample-size validation to maximize calibration coverage.** |
| **(s)** | AI-SPEC-006 §11 (`C-AI-006-3`) | Bayesian prior parameter governance: default option 1 — operator-tunable via `system-state.md` `meta_labeler.prior_parameters` field |
| **(t)** | AI-SPEC-006 §11 (`B-AI-006-9`) | `decision_outcome` enum coordination — Item 6 emits `blocked_meta_labeler` / `reduced_meta_labeler`; bilateral with Item 10's `counterfactual_reason = 'meta_skip'` |

**Operator action (Master ROI Plan Action 6):** Ratify D-023 with these 20 enrichment items. Each item references the source Class C / Class B finding for default rationale. Operator may veto any default position; if vetoed, the corresponding default in `AI_BUILD_ROADMAP.md` §0 dependency map gets a patch (NOT a re-draft).

---

## 3 — D-024 Candidates and Scope

D-024 is reserved per `approved-decisions.md` for "Phase 2A activation criteria + succession plan + capital tuning discipline" per `MASTER_ROI_PLAN.md` §5. Three additional D-024 candidates have surfaced from the audit register that may bundle into D-024 or get their own D-XXX number:

| Candidate | Source | Bundles with D-024 if operator opts for option 2; alternative is no new D-XXX |
|---|---|---|
| **Chain archive paid historical access** | [C-AI-004-4] option 2 | If operator chooses paid historical archive (instead of default option 3 V0.1-advisory-only acceptance), contractual dependency may warrant D-XXX ratification |
| **LightGBM Direction Model AI architecture catalog extension** | [C-AI-006-4] option 2 | New spec (audit register currently uses "AI-SPEC-014" naming per register line 122 verbatim; **AI Build Roadmap v1.2 renamed to AI-SPEC-016 per Cursor v1.0 H-1 to avoid collision with deferred Item 14 Tournament Engine**). Operator's D-XXX ratification should explicitly select naming: register's "AI-SPEC-014" or roadmap's "AI-SPEC-016". Possible new D-XXX (e.g., D-024) for catalog extension; bilateral with [C-AI-006-3] D-XXX numbering choice |
| **Bayesian prior parameter constitutional governance** | [C-AI-006-3] option 2 | If operator chooses option 2 (operator-tunable via `approved-decisions.md` instead of default `system-state.md`), new D-XXX (e.g., D-024) ratifies prior parameter values as constitutional constants |

**Operator action (Master ROI Plan Action 6 — D-024 ratification):**
- D-024 primary scope per Master ROI Plan: Phase 2A `synthesis_agent.py` activation criteria + succession plan + capital tuning discipline + abort thresholds + A/B comparison methodology
- D-024 candidate bundling: only if operator vetoes default positions for [C-AI-004-4] / [C-AI-006-3] / [C-AI-006-4]; otherwise the candidates resolve via D-023 enrichment items (n) / (s) / (no D-XXX) respectively

---

## 4 — ROI-Relevant Class B Items (20 of 74 open)

Not all 74 Class B items are ROI-blocking. The audit register flags 20 as load-bearing for V0.1 ship or V0.2 promotion (counted: B-AI-001-6/7/8, B-AI-002-2/6, B-AI-004-3/4/6/10, B-AI-005-2/15/16/17, B-AI-006-4/6/12/17, B-AI-010-3/5/8). The remaining 54 are documentation/migration items absorbed by per-spec build commitments in `AI_BUILD_ROADMAP.md`. The ROI-relevant subset:

| ID | Description | Cited in Build Roadmap | Default operator position |
|---|---|---|---|
| **B-AI-001-6** | `_safe_redis()` dead code + `gex:updated_at` no-producer freshness substrate non-functional — bundles with B-AI-005-16, B-AI-006-17 | §3.1 sub-item 3 + §3.15 (Phase 3X freshness substrate) | Approve substrate buildout in Phase 3A + Phase 3X (Tier 1 substrate) |
| **B-AI-001-7** | `_RISK_PCT` ladder non-monotonic at HEAD; D-022 enforcement split between `risk_engine.py` and `prediction_engine.py`; Governor `size_multiplier_cap` MUST NOT widen non-monotonic regression | Master ROI Plan Action 7b (Gate F PRE-P11-3 fix) | Approve fix as Master ROI Plan Action 7b before Action 9 activation |
| **B-AI-001-8** | V0.2 paper-binding gate ("≥200 cards") calendar-blocked on Item 4 V0.1 ship + ≥200 card production rate | §3.1 V0.2 promotion gate + §3.3 Item 4 V0.1 | Approve Item 4 must ship first; gate calendar-blocked accordingly |
| **B-AI-002-2** | `closed_trade_path_metrics` substrate gap — owner = Item 10 V0.2 | §3.4 Stage 2 (V0.2-with-Items-5/6) | Approve Item 10 Layer 2 owns substrate; ships in Phase 4B-bilateral |
| **B-AI-002-6** | Legacy `trading_positions` cutover policy (pre-Item-2 closed positions) — training contamination risk | §3.2 sub-item 5 | Approve cutover policy in Phase 3B — pre-Item-2 closed positions excluded from `calibration_eligible` |
| **B-AI-004-3** | Chain archive infrastructure absent — bundles into [C-AI-004-4] | §3.3 sub-item 7 | Approve as part of [C-AI-004-4] default option 3 (V0.1-advisory-only acceptance) |
| **B-AI-004-4** | Polygon historical 1-min fetch capability missing — may require Polygon paid tier | §3.3 sub-item 10 | Approve as operator contract dependency; bundles with [C-AI-004-4] option 2 if pursued |
| **B-AI-004-6** | News/event `published_at` TIMESTAMPTZ extension missing — leakage risk for Spec §5 timestamp boundary | §3.3 sub-item 8 | Approve fix in Phase 3C V0.1 sub-item |
| **B-AI-004-10** | LightGBM artifact-log substrate missing — affects Item 6 V0.2 reproducibility | §3.3 sub-item 9 | Approve substrate in Phase 3C; bundles with Item 6 V0.2 prep |
| **B-AI-005-2** | Multi-year SPX 5-min bar history substrate missing — HAR-RV training prerequisite | §3.5 sub-item 6 | Approve substrate in Phase 3E; bilateral with [C-AI-005-3] |
| **B-AI-005-15** | Pre-V0.2 substrate minimums (30-60 / 90 / 60 / 100 / 100 / 30 sessions) — `calibration_eligible` flag theme | §3.5 sub-item 7 | Approve threshold gates in Phase 3E |
| **B-AI-005-16** | `_safe_redis()` substrate gap (cross-spec confirmation with B-AI-001-6, B-AI-006-17) — 3-audit safety-critical | §3.15 Phase 3X (G-41 freshness substrate) | Approve as cross-spec substrate buildout |
| **B-AI-005-17** | `fc64840` cutover anchor for daily-RV history | §3.5 sub-item 9 | Approve anchor in Phase 3E |
| **B-AI-006-4** | LightGBM Direction Model 5 fields absent at HEAD — bilateral with [C-AI-006-4] | §3.6 (Phase 3G contingent) | Approve resolution via [C-AI-006-4] decision |
| **B-AI-006-6** | Memory retrieval substrate calendar-blocker — bilateral with Item 7 build | §3.7 + §3.8 sub-item 5 | Approve memory retrieval substrate in Phase 4A or 4B |
| **B-AI-006-12** | Item 6 5-strategy enum is strict subset of canonical 10 — taxonomy inconsistency | §3.8 sub-item 7 + D-023 enrichment item (r) | Approve canonical 10-strategy taxonomy; Item 6 V0.2 ships utility calculators for spec's existing 5 + 2 long-side additions (`U_LC`, `U_LP`); D-023 default decision per item (r) on the 3 canonical strategies not covered (`call_credit_spread`, `debit_put_spread`, `calendar_spread`) |
| **B-AI-006-17** | `_safe_redis()` substrate gap from Item 6 perspective — `meta:engine_updated_at` producer (cross-spec confirmation) | §3.15 Phase 3X (G-41 freshness substrate) | Approve as cross-spec substrate buildout (3-audit confirmed safety-critical) |
| **B-AI-010-3** | Layer 1 NULL-return surgical fix at `counterfactual_engine.py:213-223` — bilateral with [C-AI-010-1] | §3.4 Stage 1 sub-item 5 | Approve via [C-AI-010-1] default option 1 |
| **B-AI-010-5** | `trade_counterfactual_cases.calibration_eligible BOOLEAN` canonical surface for counterfactual labels | §3.4 Stage 1 sub-item 4 | Approve canonical surface in Phase 3D |
| **B-AI-010-8** | Versioned VIX spread width table — bilateral with HANDOFF_3 §16B (G-55) | §3.4 Stage 1 sub-item 10: VIX spread width recalibration baseline in Item 10 Layer 2 V0.2 (per Build Roadmap v1.5; cross-doc citation specificity refined per Cursor v1.4 review O-1) | Approve versioned table in Phase 3D |

The remaining 54 Class B items are absorbed by per-spec build commitments without separate operator decision — they ship as part of the relevant phase's sub-item count.

---

## 5 — PRE-P Findings Cross-Reference (18 unique items per Cursor v1.2 CR-1; v1.2 H-A "24" overshot by counting register §0.6 cross-reference re-cites)

The 18 unique PRE-P findings predate the per-item audits. Most are governance debt or pre-existing infrastructure findings. The ROI-relevant subset that affects activation/build sequencing:

| ID | Description | Owner | Status |
|---|---|---|---|
| **PRE-P11-3** | `_RISK_PCT` non-monotonic ladder bug (Phase 1 0.010 > Phase 2 0.0075) | Master ROI Plan Action 7b (Gate F) | Open — fix before Master ROI Plan Action 9 |
| **PRE-P11-4** | `counterfactual_pnl` is 3 columns on `trading_prediction_outputs`, NOT a separate table — migration filename `20260421_add_counterfactual_pnl.sql` is correct but artifact is `ALTER TABLE ... ADD COLUMN`. Affects how P1.2 / P1.3 audits and Item 10 V0.2 build treat the surface. (Source: register §0.2 line 54 + cross-reference §0.6 line 88) | Resolves via Item 10 V0.2 build commitment (AI Build Roadmap §3.4 Stage 1 — `trade_counterfactual_cases` is the canonical Layer 2 table; pre-existing `counterfactual_pnl` 3 columns on `trading_prediction_outputs` stay as observability-only legacy surface per [C-AI-010-1] default option 1) | Open — **resolves automatically when Phase 3D Item 10 V0.2-immediate ships** with `trade_counterfactual_cases` table. No separate operator action required beyond Phase 3D ship. |
| **PRE-P12-1** | `_safe_redis()` substrate gap (Phase 1 audit infra) — bundles with B-AI-001-6 + B-AI-005-16 + B-AI-006-17 + G-41 | AI Build Roadmap §3.15 Phase 3X | Open — fix in Phase 3X (Tier 1 substrate) |
| **PRE-P12-2** | AI-SPEC-001 → AI-SPEC-013 → AI-SPEC-012 (`risk_engine.py` module-level merge order) | AI Build Roadmap Phase 5D + Master ROI Plan Action 7b | Constraint satisfied automatically: Action 7b lands before Phase 5D |
| (Other 14 unique PRE-P items per Cursor v1.2 CR-1: 18 total − 4 ROI-relevant enumerated above = 14) | Phase 0 governance debt + pre-existing infrastructure | Out of scope for V0.1 activation | Open — deferred per `deferred-work-register.md` |

---

## 6 — D-015 / D-016 / D-021 Divergence Handling

Per `what-is-actually-built.md`, three approved decisions have open divergences between approved spec and built reality:

| Decision | Divergence | Resolution path |
|---|---|---|
| **D-015** LightGBM slippage | NOT BUILT — static dict at HEAD | Resolves via AI-SPEC-005 audit (P1.3.5 complete) + Phase 3E build per AI Build Roadmap. No new D-XXX required. |
| **D-016** Vol blending | PARTIALLY BUILT | Resolves via [C-AI-005-1] default option 2 (HAR-RV new advisory signal, D-016 unchanged). **No new D-XXX required for default.** |
| **D-021** HMM + LightGBM regime classifier | NOT BUILT — rule-based at HEAD | Resolves via [C-AI-006-4] default option 2 (new spec AI-SPEC-016 LightGBM Direction Model added to catalog). **Possible new D-XXX (e.g., D-024) if operator approves catalog extension.** |

**Operator action:** D-015 and D-016 require no further action beyond ratifying [C-AI-005-1] default in Action 6. D-021 requires deciding [C-AI-006-4] in Action 5a per Master ROI Plan §4.

---

## 7 — Out of Scope with Explicit Handling

These items appear in the audit register but are NOT operator-decision blockers for V0.1 activation:

- **Class A mechanical corrections** (5 items in §3 of register) — batch-cleared at Gate 1; no operator decision needed
- **§5 Cross-Spec Themes** (8 themes) — informational rollup; resolved as underlying findings close
- **`pgvector` infrastructure missing** — pre-V0.1 implementation prerequisite, not an operator decision; absorbed by AI Build Roadmap §3.1 sub-item 1
- **§0 PRE-P findings beyond PRE-P11-3 / PRE-P12-1 / PRE-P12-2** — pre-existing governance debt, deferred per `deferred-work-register.md` cross-reference (G-80 in spine §7)
- **Class B items not enumerated in §4 above** — 54 items; absorbed by per-spec build commitments in `AI_BUILD_ROADMAP.md`

---

## 8 — Findings Tracking (G-N IDs delegated to this document)

| ID | Finding | Source | Resolution path | Status |
|---|---|---|---|---|
| (G-vacant) | C-AI-002-2 (RESOLVED — `trade_counterfactual_cases` table-vs-column architectural divergence with Item 10 — register §4 line 234) | Cursor gap scan §3.B (no G-ID slot assigned because resolved before gap scan ran; Cursor v1.1 R-2 option (b) recommended explicit slot here for cross-§ visibility) | §1.0 stub (cross-reference only — no operator action pending) | [x] RESOLVED — option 1 (new table) chosen |
| G-17 | C-AI-001-1 size_multiplier_cap channel ownership | Cursor gap scan §3.B | §1.1 [C-AI-001-1] | [ ] D-023 enrichment (a) |
| G-18 | C-AI-001-2 LLM Card schema author / freeze-version policy | Cursor gap scan §3.B | §1.1 [C-AI-001-2] | [ ] D-023 enrichment (d) |
| G-19 | C-AI-001-3 Decision-card counting definition | Cursor gap scan §3.B | §1.1 [C-AI-001-3] | [ ] D-023 enrichment (c) |
| G-20 | C-AI-002-1 decision_outcome enum coordination | Cursor gap scan §3.B | §1.2 [C-AI-002-1] | [ ] D-023 enrichment (b) |
| G-21 | C-AI-002-3 Legacy attribution_* BOOLEAN columns | Cursor gap scan §3.B | §1.2 [C-AI-002-3] | [ ] No D-XXX; default option 1 |
| G-22 | C-AI-004-1 paper_phase_criteria vs item_promotion_records | Cursor gap scan §3.B | §1.3 [C-AI-004-1] | [ ] No D-XXX; default option 1 |
| G-23 | C-AI-004-2 Decision-card definition for ≥200 threshold | Cursor gap scan §3.B | §1.3 [C-AI-004-2] | [ ] D-023 enrichment (e) |
| G-24 | C-AI-004-3 D-023 startup-read contract | Cursor gap scan §3.B | §1.3 [C-AI-004-3] | [ ] D-023 enrichment (f) |
| **G-25** | **C-AI-004-4 chain archive substrate ⚠️ CRITICAL** | Cursor gap scan §3.B | §1.3 [C-AI-004-4] | [ ] **Operator decision required at Action 5a (default option 3)** |
| G-26 | C-AI-005-1 D-016 disposition (HAR-RV vs realized) | Cursor gap scan §3.B | §1.4 [C-AI-005-1] | [ ] D-023 enrichment (l); default option 2 |
| G-27 | C-AI-005-2 Item 5 Layer 1 cutover | Cursor gap scan §3.B | §1.4 [C-AI-005-2] | [ ] D-023 enrichment (l); default option 1 |
| G-28 | C-AI-005-3 Item 5 V0.x advisory-only bilateral with G-25 | Cursor gap scan §3.B | §1.4 [C-AI-005-3] | [ ] Resolves with G-25 |
| **G-29** | **C-AI-006-1 Authority Recovery ⚠️ CRITICAL FIRST AUTHORITY-BOUNDARY CLASS C** | Cursor gap scan §3.B | §1.5 [C-AI-006-1] | [ ] **Operator decision required at Action 6 (default option 2 — operator-mediated)** |
| G-30 | C-AI-006-2 Item 6 Layer 1 cutover | Cursor gap scan §3.B | §1.5 [C-AI-006-2] | [ ] D-023 enrichment (q); default option 1 |
| G-31 | C-AI-006-3 Bayesian prior parameter governance | Cursor gap scan §3.B | §1.5 [C-AI-006-3] | [ ] D-023 enrichment (s); default option 1 |
| G-31a | C-AI-006-4 LightGBM Direction Model spec ownership | Cursor gap scan §3.B | §1.5 [C-AI-006-4] | [ ] **Operator decision required at Action 5a (default option 2 — new spec AI-SPEC-016)** |
| G-31b | C-AI-010-1 Layer 1 §0/§3 contradiction | Cursor gap scan §3.B | §1.6 [C-AI-010-1] | [ ] No D-XXX; default option 1 |
| G-31c | C-AI-010-2 Cluster/tier classification discrepancy | Cursor gap scan §3.B | §1.6 [C-AI-010-2] | [ ] No D-XXX; informational |
| G-31d | C-AI-010-3 z-score producer authority | Cursor gap scan §3.B | §1.6 [C-AI-010-3] | [ ] D-023 enrichment (h); default option 3 |
| G-31e | C-AI-010-4 Item 3 vs Item 10 ownership | Cursor gap scan §3.B | §1.6 [C-AI-010-4] | [ ] No D-XXX; default option 1 |
| G-31f | C-AI-010-5 cutover anchor lock | Cursor gap scan §3.B | §1.6 [C-AI-010-5] | [ ] D-023 enrichment (j); default option 1 (concrete commit hash post-Commit-4) |
| **G-41** | **Freshness substrate buildout (3-audit safety-critical)** | Cursor gap scan §3.B | §4 ROI-relevant Class B (B-AI-001-6 + B-AI-005-16 + B-AI-006-17 cross-spec) | [ ] **Approve buildout via AI Build Roadmap §3.15 Phase 3X (Tier 1 substrate)** |
| G-74 | D-015 divergence open | Cursor gap scan §3.F | §6 D-015 row | [ ] Resolves via [C-AI-005-1] |
| G-75 | D-016 divergence open | Cursor gap scan §3.F | §6 D-016 row | [ ] Resolves via [C-AI-005-1] default option 2 |
| G-76 | D-021 divergence open | Cursor gap scan §3.F | §6 D-021 row | [ ] Resolves via [C-AI-006-4] default option 2 |
| G-77 | D-023 ratification scope (a)-(t) | Cursor gap scan §3.F | §2 of this document | [x] Enumerated |
| G-78 | D-024 candidate(s) | Cursor gap scan §3.F | §3 of this document | [x] Enumerated 3 candidates |
| G-79 | 18 unique PRE-P findings (Cursor gap scan §3.F text "22" was wrong; v1.2 H-A overshot to "24" by counting §0.6 cross-reference re-cites; actual register §0 contains **18 unique** PRE-P findings: PRE-P0-1 through PRE-P0-4 (4) + PRE-P11-1 through PRE-P11-7 (7) + PRE-P12-1 through PRE-P12-4 (4) + PRE-P130-1 (1) + PRE-P130B-1 through PRE-P130B-2 (2). §0.6 cross-reference table re-cites 6 of these 18 (PRE-P11-3, PRE-P11-4, PRE-P11-5, PRE-P11-6, PRE-P11-7, PRE-P12-1) for cross-section visibility — those are duplicates, not new findings; naive `grep '^\| PRE-P'` returns 24 rows because it counts §0.6 re-cites. Per Cursor v1.2 CR-1 fix.) | Cursor gap scan §3.F | §5 of this document | [x] ROI-relevant subset enumerated |
| G-80 | deferred-work-register.md cross-reference | Cursor gap scan §3.F | §7 out of scope | [x] Cross-referenced |

**Coverage check:** All G-N IDs from Cursor gap scan §3.B (G-17 through G-31f — 21 open Class C items + 1 resolved C-AI-002-2 with explicit (G-vacant) slot per Cursor v1.1 R-2 option (b)), §3.F (G-74 through G-80 — operator-decision tracking), and the safety-critical G-41 freshness substrate are present and resolved or assigned. **No silent drops detected post-draft.** The (G-vacant) slot for C-AI-002-2 prevents future agents from re-discovering the count mismatch (G-N space has a documented gap rather than an unexplained jump from G-16 to G-17).

---

## 9 — Maintenance Protocol

This document is sourced from `AUDIT_FINDINGS_REGISTER.md`. Updates flow:

1. New audit lands (P1.3.7 / P1.3.8 / etc.) → register §1 + §6 updated → this document patched in same session
2. Operator decision on a Class C item → register status changes from `open` → `resolved` → this document marks the row complete + updates status checkbox
3. New D-XXX surfaces → §3 of this document updated with bundling decision
4. Combined verification round runs → cosmetic items deferred patch-pass

**Cross-document consistency invariant:** AI Build Roadmap §0 dependency map MUST always match this document's §1 default positions for the 9 cited Class C items. If a default changes here, the build roadmap gets a corresponding patch (NOT a re-draft).

---

*End of Audit Disposition Plan v1.9 — DRAFT commit-ready as part of Phase 2 deliverable trio (Master Plan v2.0.3 + Build Roadmap v1.8 + this v1.9). All 7 Cursor v1.0 review items + all 5 Cursor v1.1 review residuals + 2 Cursor v1.2 review items + 1 Cursor v1.3 review item (N-1) + 1 Cursor v1.4 review item (O-1) + 2 combined-round items (H-1 + N-1) + 3 v1.6 → v1.7 cleanup items (Cursor O-2 site 1 + N-1 concurrent-note refresh + O-2-derived forward-pointer roll-forward) + 4 logical converged-state cleanup items (cross-doc version updates + forward-pointer roll + concurrent-note refresh + cumulative-fix-count math correction) + 3 Phase 1 factual-correction items (§268 item (m) canonical-list correction from "8" → migration-order 10 + citation chain widened to include `strategy_selector.py` `STATIC_SLIPPAGE_BY_STRATEGY` and corrected `risk_engine.py` line range; §273 item (r) Item 6 V0.2 build commitment corrected to ratify 2 long-side additions (`U_LC`, `U_LP`) and defer 3 not-yet-covered canonicals (`call_credit_spread`, `debit_put_spread`, `calendar_spread`) to D-023 default-and-alternative; §318 B-AI-006-12 Class B findings row mirror-updated to canonical-10 framing) fixed in v1.1 + v1.2 + v1.3 + v1.4 + v1.5 + v1.6 + v1.7 + v1.8 + v1.9 per operator standing rule (fix-now over defer-to-later applied symmetrically across all bounded items including derived ones). **Cumulative tally (math-corrected from inherited v1.6 typo): 7 + 5 + 2 + 1 + 1 + 2 + 3 + 4 + 3 = 28 items fixed across 8 review cycles + 1 combined-round + 1 cleanup-cycle + 1 converged-state-cleanup-cycle + 1 Phase 1 factual-correction-cycle (external pre-deployment audit, defect propagation closure).** Commit trio together.*
