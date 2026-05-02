# MarketMuse — Master ROI Plan v2.0.6
**Owner:** tesfayekb
**Drafted:** 2026-04-28 (ET)
**Last reconciled:** 2026-04-30 (ET) — v2.0.3 → v2.0.4 reconciliation per `MarketMuse_Master_Forward_Plan_v1.2.docx` Task 1 (Cluster B closure ratification + 5-PR LightGBM activation chain + Gate B/C/F closure markers + Action 8 trigger TRIPPED). v2.0.4 → v2.0.5 adds pointer to new `SUBSCRIPTION_REGISTRY.md` companion (canonical active-subs reference) + UI lockstep update at `src/pages/trading/SubscriptionsPage.tsx` (Polygon split into Options Developer + Stocks Advanced; Databento cost $150 → $199 reflecting OPRA Standard tier).
**Structural revision:** v1.6 (single document) → v2.0 (β-lite multi-plan governance) per Cursor v1.6 gap-scan structural recommendation. Patch v2.0.1 applied 4 must-fix items from Cursor v2.0 review (G-41 missing from §7; paused-flag enable order missing from §1.4; G-25 + G-29 missing from §7; §3 Gate E typo) plus 2 nice-to-haves.
**Patch v2.0.2 applies 3 cross-doc consistency items from combined verification round across Master Plan v2.0.1 + Build Roadmap v1.5 + DP v1.5:** **CR-1** (§1.6 + §1.7 misciation: "Phase A LightGBM training → Phase 3E" was wrong; canonical home is Phase 5B Item 13 retraining substrate per Build Roadmap §3.11; Phase 3E is Item 5 Vol Fair-Value Engine which has zero LightGBM training; this was a silent-drop-equivalent that pointed future agents at the wrong phase) + **M-1** (3 sites — Cursor flagged 2 but verification surfaced 3 — AI-SPEC-014 / AI-SPEC-016 dual-naming acknowledged across §1.3 P1.3.9 row + §3 Cluster B + §3 Action 4b; canonical name selection deferred to D-024 ratification per AUDIT_DISPOSITION_PLAN.md §3) + **M-2** (§7 G-25 chain archive cascade scope qualified — was "primary cascade for AI-SPEC-001 V0.2 + 004 + 005 + 010"; Build Roadmap §0 dependency map and DP §1.3 both list only Items 4/5/10 V0.2 as direct cascade; AI-SPEC-001 V0.2 paper-binding depends on chain archive only INDIRECTLY via Item 4 replay harness producing the ≥200 cards). **Per operator standing rule (fix-now over defer-to-later) applied symmetrically to all 5 combined-round items: 3 here, 2 in companion DP v1.5 → v1.6.** Combined verification round caught the natural "settling cost" of Master Plan staying static while companions iterated through 5 review cycles each.
**Patch v2.0.3 applies converged-state cleanup from second combined verification round (Cursor flagged 7 bounded residuals across the trio after O-2 cleanup advanced Build Roadmap v1.5 → v1.6 + DP v1.6 → v1.7 but didn't propagate companion-version references back to Master Plan). 3 sites in this document: status line (companion sub-plans Build Roadmap v1.5 + DP v1.6 → v1.7 + v1.8) + footer trio composition (Master Plan v2.0.2 + Build Roadmap v1.5 + DP v1.6 → v2.0.3 + v1.7 + v1.8). 4 logical fixes / 6 physical sites in companion Build Roadmap v1.6 → v1.7 (cross-doc version updates [2 sites] + forward-pointer roll-forward [1 site] + §6/§8/§8 H-1/H-2/H-3 carryover residuals from prior cycle [3 sites]). 4 logical fixes / 6 physical sites in companion DP v1.7 → v1.8 (cross-doc version updates [2 sites] + forward-pointer [1 site] + concurrent-note refresh [1 site] + cumulative-fix-count carryover with math correction [1 site] — inherited v1.6 typo "11 prior fixes" was mathematically wrong; should have been 16; v1.8 corrects to actually-correct count 21 prior fixes through v1.7).** Per operator standing rule (fix-now over defer-to-later) applied symmetrically including derived items per Cursor's "DO NOT INTRODUCE FURTHER REGRESSION" instruction. Trio settles at converged-state Master Plan v2.0.3 + Build Roadmap v1.7 + DP v1.8 with zero stale cross-doc version references.
**Patch v2.0.3 → v2.0.4 applies post-verification reconciliation per `MarketMuse_Master_Forward_Plan_v1.2.docx` Task 1, executed 2026-04-30 against HEAD `5162020`. Reconciles governance-doc drift between live system state and this document. 7 edit categories applied: (A.1) §1.3 audit-status table rows for P1.3.7 + P1.3.8 flipped from "📋 Next/After" to "✅ DONE" with PR + commit references; (A.2) §4 Action 3 + Action 4 + Action 4b status checkboxes flipped from "[ ] Pending" to current status (3 + 4 done; 4b contingent on C-AI-006-4 option 2 selection); (A.3) §3 Gate B + Gate C + Gate F closure markers added (Gate B locked Apr 28-29 baselines; Gate C closed per AUDIT_FINDINGS_REGISTER L9 Cluster B 4-of-4; Gate F closed PR #74); (A.4) Action 8 trigger flipped from "Conditional" to "TRIPPED" per Apr 28 baseline showing direction_signal_weak >50% pattern (table row L59 + section status L350); (A.5) new §1.8 LightGBM v1 activation chain documenting T-ACT-040 through T-ACT-044 / PRs #82-#86 / 5-PR sequence shipping 2026-04-30 (note: drafted as new §1.7 per Master Forward Plan v1.2 prescription but §1.7 slot already held by "TASK_REGISTER coverage statement", so inserted as new §1.8 to preserve no-cascade-rename intent); (A.6) §7 Findings Tracking Register row F-38 added for the 5-PR LightGBM activation milestone; (A.7) header version v2.0.3 → v2.0.4 + companion-version line updated. Companion sub-plan versions at HEAD: AI_BUILD_ROADMAP v1.8 (already post-audit ratified §3.9 + §3.10 in prior v1.7 → v1.8 cycle, NOT bumped this round per Master Forward Plan v1.2 reconciliation scope decision) + AUDIT_DISPOSITION_PLAN v1.9 (already at v1.9 in prior v1.8 → v1.9 cycle, NOT bumped this round; C-AI-006-4 disposition note deferred to Action 6 D-023 + D-024 ratification PR per operator scope decision). Per operator standing rule (fix-now over defer-to-later) applied symmetrically — but with reconciliation-scope discipline: only this document advances v2.0.3 → v2.0.4; companion sub-plans stay at their current correct versions (v1.8 + v1.9), not artificially bumped.**
**Patch v2.0.4 → v2.0.5** adds pointer to new `SUBSCRIPTION_REGISTRY.md` (in this PR) as the authoritative reference for active data subscriptions. Companion update: `src/pages/trading/SubscriptionsPage.tsx` `SERVICES` array updated in lockstep (Polygon split into Options Developer + Stocks Advanced; Databento cost $150 → $199 reflecting OPRA Standard tier). Forward-framing in Master Forward Plan v1.2 Part 4 + any "subscription decision pending" references are superseded — both Polygon tiers + Databento OPRA Standard are confirmed active per BeyeneQuant Subscriptions UI 2026-04-30. Companion sub-plan versions at HEAD: AI_BUILD_ROADMAP v1.9 (Edit Group D, §6 15A/15B/15D/15E coverage status updates) + AUDIT_DISPOSITION_PLAN v1.10 (Edit Group E, C-AI-004-4 substrate-now-present flag). C-AI-004-4 ratification to option 2 (calibration-grade replay) deferred to Action 5a / Action 6 governance session per scope discipline.
**Patch v2.0.5 → v2.0.6** adds 2026-05-01 session context to Action 6 (C-AI-004-4 substrate confirmed; PR #90 SPX delay remediation; HANDOFF A.6 discipline lesson). Pre-Action-6 prerequisite added: T-ACT-045 must validate post-PR-#90 SPX feed before Action 6 begins. No structural changes to gate framework. Companion sub-plan versions at HEAD unchanged: AI_BUILD_ROADMAP v1.9 + AUDIT_DISPOSITION_PLAN v1.10 (no version bumps this round — changes are operational follow-ups, not changes to the build sequence or audit dispositions).
**Status:** **READY-TO-MERGE v2.0.6** — applied via PR `docs/post-may-1-followups` 2026-05-01. Trio composition: Master Plan v2.0.6 + Build Roadmap v1.9 + DP v1.10. Companion: `SUBSCRIPTION_REGISTRY.md` (canonical active-subs reference); UI mirror at `src/pages/trading/SubscriptionsPage.tsx`. Cross-references: HANDOFF NOTE Appendix A.6 (phantom-alpha post-mortem) + TASK_REGISTER §14 (T-ACT-045/046/047 follow-up tasks).

---

## ⚠️ §0 — WHAT LIVES WHERE (READ-ME-FIRST POINTER TABLE)

**This document does not stand alone. Future agents reading cold MUST consult all 3 documents before forward action.**

| Concern | Document | Source register |
|---|---|---|
| **Activation path, gates A-F, Pre-AI fix track Commits 1-10, paused-flag enable order, operational items, V0.1 Path Y activation** | **THIS document — `MASTER_ROI_PLAN.md`** | `trading-docs/08-planning/TASK_REGISTER.md` (line-item tasks) |
| **13 AI-SPEC build commitments, Cluster A/B/C ladder, V0.1/V0.2 promotion gates, chain archive substrate, data improvements 15A-E** | **`AI_BUILD_ROADMAP.md`** | `trading-docs/04-modules/ai-architecture/archive/raw-locked-specs-2026-04-26/AI_ARCHITECTURE_IMPROVEMENT_REGISTRY.md` |
| **22 Class C operator decisions, ~20 ROI-relevant Class B items, PRE-P findings, D-023/D-024 ratification, D-015/D-016/D-021 divergences** | **`AUDIT_DISPOSITION_PLAN.md`** | `trading-docs/08-planning/ai-architecture-audits/AUDIT_FINDINGS_REGISTER.md` |
| **Active data subscriptions, operational recurring costs, deferred items, forward-looking trigger-based subscription decisions, Cluster B/C data substrate coverage** | **`SUBSCRIPTION_REGISTRY.md`** | `src/pages/trading/SubscriptionsPage.tsx` (UI mirror — `SERVICES` array kept in lockstep) |

**Authority hierarchy:** This document governs **when** things happen (activation gates, sequencing). The other two trio docs govern **what** is committed to (build commitments, operator decisions). The subscription registry is authoritative for subscription state (supersedes Master Forward Plan v1.2 Part 4 forward-framing). For any conflict, the relevant source register wins.

**If a forward-work item doesn't fit any of these three concerns, it goes in this document's §6 (Out of Scope with Explicit Handling).**

---

## ⚠️ READ-ME-FIRST FOR ANY AGENT

This document encodes the agreed-upon plan from a multi-day session ending 2026-04-28 with 3-reviewer consensus (Claude, GPT, Cursor) plus structural gap-scan (Cursor) producing 104 surfaced gaps that v1.6 was missing.

1. **The prime directive is ROI.** Every action below is justified by how it directly or indirectly increases net after-tax profitability.
2. **The destination is Path Y — activate `agents:ai_synthesis:enabled`.** This document is the path to get there safely.
3. **Sequencing is load-bearing.** Don't reorder. Each step has explicit "DO NOT PROCEED UNTIL" gates.
4. **Do not lose findings.** Each of the 3 documents tracks its own findings. F-N IDs in this doc are local; G-N IDs from Cursor's gap scan are mapped per-document. Audit register uses PRE-PN-N / B-AI-XXX-N / C-AI-XXX-N convention.
5. **Use the existing audit redline cadence** (P1.3.7 → P1.3.8 → contingent P1.3.9 → P1.3.10 → Cluster B closure → Cluster C audits per AI Build Roadmap).
6. **Update at every milestone.** Tick checkboxes. Add verification notes. Increment plan version on material updates.

**v2.0 structural change vs v1.0-v1.6:** Single-document approach repeatedly silently dropped ROI items because the synthesis step optimized for narrative coherence and 6-concern narratives don't cohere. v2.0 splits into 3 documents each governing one concern. **DO NOT regress to single-document approach without explicit operator decision** — the regression failure mode is the same silent drops that occurred 6 times during v1.0-v1.6.

---

## 1 — Where We Are Today (2026-04-28)

### 1.1 Code state (verified)
- origin/main HEAD: `fc6b0773823d57a1d3a22a9dab2e191c786f29d2` (Commit 3 PCS/CCS net-spread fix; PR #68; merged 2026-04-27 16:06:51 -0400) — verified via `git log origin/main -1` 2026-04-28
- Railway deployed Commit 3 at 16:08 ET on 2026-04-27
- Container healthy at last log review (~14:00 ET 2026-04-28); databento subscribed; tradier sandbox active

### 1.2 Pre-AI fix track status
| Commit | Description | Status | Verified SHA |
|---|---|---|---|
| 1 | IC/IB target_credit chain extraction | ✅ Shipped 2026-04-25 (PR #53) | `77af9aa8e841e0f2eaf12652bce968effe4a9c13` |
| 2 | databento LTRIM / GEX fix | ✅ Shipped 2026-04-27 (PR #66) | `17cd3cfd6595ae37346af8e0f8c253b0e61f81c3` |
| 3 | PCS/CCS target_credit net-spread fix | ✅ Shipped 2026-04-27 (PR #68) | `fc6b0773823d57a1d3a22a9dab2e191c786f29d2` |
| 4 | Re-mark + calibration cleanup + NULL slippage handling | ⏳ Pending — anchor for AI-SPEC-010 Layer 2 cutover (C-AI-010-5) | — |
| 5 | `_RISK_PCT` ladder monotonicity fix (PRE-P11-3 / Action 7b) | ⏳ Pending — Days 7-14 | — |
| 6 | VVIX z-score deferred fix (S7) — paired with `vix_daily_history` backfill primitive | ⏳ Pending — pre-Action-9 | — |
| 7 | Phase 0 commission model fix (per TASK_REGISTER §11 Phase 0) | ⏳ Pending — pre-Action-9 | — |
| 8 | `signal_weak` threshold change (TASK_REGISTER §11 Phase 0) | 🔴 TRIPPED — Apr 28 baseline showed `direction_signal_weak` at 100% of skips (146 outer + 73 inner over 73 cycles); Apr 29 append confirms dominance; trigger condition (>50%) exceeded by ~2× — queued for Days 7-14 as conviction-conditional sizing redesign | — |
| 9 | IV/RV no-trade filter (TASK_REGISTER §11 Phase 0; `prediction_engine.py:706`) | ⏳ Pending — pre-Action-9 | — |
| 10 | (TBD per FINAL_DEPLOY_PLAN_v2.md — operator paste required to enumerate) | ⏳ Pending paste | — |

**Note on Commits 5-10 enumeration:** Cursor gap scan SD-2 flagged that FINAL_DEPLOY_PLAN_v2.md is not in repo workspace; Commits 5-10 are reconstructed from TASK_REGISTER.md §11. Operator paste of FINAL_DEPLOY_PLAN_v2.md is required to verify exact content of Commit 10. Tracked as G-66 in §7 Findings Register.

### 1.3 Audit track status — see `AI_BUILD_ROADMAP.md` for build commitments
| Audit | Spec | Cluster | Status |
|---|---|---|---|
| P1.3.1 | AI-SPEC-001 AI Risk Governor | A | ✅ Merged (PR #60) |
| P1.3.2 | AI-SPEC-002 Strategy-Aware Attribution | A | ✅ Merged (PR #62) |
| P1.3.3 | AI-SPEC-004 Replay Harness | A | ✅ Merged (PR #63) |
| P1.3.4 | AI-SPEC-010 Counterfactual P&L | A | ✅ Merged (PR #64) |
| P1.3.5 | AI-SPEC-005 Vol Fair-Value | B | ✅ Merged (PR #65) |
| P1.3.6 | AI-SPEC-006 Meta-Labeler | B | ✅ Merged (PR #67) |
| P1.3.7 | AI-SPEC-008 OPRA Flow Alpha | B | ✅ DONE 2026-04-28 (PR #75 `ff7495a`) |
| P1.3.8 | AI-SPEC-009 Exit Optimizer | B | ✅ DONE 2026-04-29 (PR #77 `363a6ec` — CLOSES CLUSTER B + GATE C) |
| P1.3.9 | AI-SPEC-014 LightGBM Direction Model (renamed AI-SPEC-016 in AI Build Roadmap; operator selects canonical name at D-024 ratification per `AUDIT_DISPOSITION_PLAN.md` §3) | B | ⚠️ CONTINGENT on C-AI-006-4 → option 2 (default position per audit register). See `AUDIT_DISPOSITION_PLAN.md` |
| P1.3.10 | AI-SPEC-013 Drift Detection | C-promoted | 📋 First audit post-V0.1 (per AI Build Roadmap) |
| P1.3.11+ | Remaining Cluster C (AI-SPEC-003/007/011/012) | C | 📋 Per AI Build Roadmap sequencing |

### 1.4 Feature flag inventory (corrected from v1.6's stated 5; actual 7-8 paused per backend/main.py:1829-1863)

**7-8 paused feature flags (default OFF):**
- `agents:ai_synthesis:enabled` — destination flag for Path Y; activation governed by §3 Gates A-F
- `agents:flow_agent:enabled` — opa flow signals; gated until Action 7 + activation criteria
- `agents:sentiment_agent:enabled` — sentiment signals (Sentiment Agent built per `what-is-actually-built.md`); gated
- `strategy:iron_butterfly:enabled` — IB strategy gating
- `strategy:long_straddle:enabled` — long straddle strategy gating
- `strategy:calendar_spread:enabled` — calendar spread strategy gating
- `strategy:ai_hint_override:enabled` — strategy selector consumes AI hint when ≥0.65 confidence
- `strategy:earnings_straddle:enabled` — Earnings Straddle module built but default-OFF (separate `backend_earnings/` revenue stream); gated

**6 reverse-polarity signal flags (default ON; can be silently OFF if explicit "false" written):**
- `signal:vix_term_filter:enabled`
- `signal:entry_time_gate:enabled`
- `signal:gex_directional_bias:enabled`
- `signal:market_breadth:enabled`
- `signal:earnings_proximity:enabled`
- `signal:iv_rank_filter:enabled`

**Capital scaling levers (operator-tunable numerics, NOT booleans):**
- `capital:deployment_pct` — current value: `1.0` per `backend/main.py:1697`
- `capital:leverage_multiplier` — current value: `1.0` per `backend/main.py:1700`
- These are the 4th ROI lever, orthogonal to AI activation — operator can adjust post-Sharpe-positive sessions without audit/code/AI activation

**Paused-flag enable order (post-Action-9):**
The 7-8 paused flags are NOT all enabled at Action 9. Per Gate E orthogonality clause, their activation order is operator-controlled and does NOT gate Action 9. **Per-flag enable criteria (minimum closed trades / Sharpe thresholds / abort conditions / dependency on `agents:ai_synthesis:enabled` first being stable) are documented in D-024 and ratified in Action 6.** Future agents: do NOT silently re-derive enable order from this document; consult D-024 in `trading-docs/00-governance/ai-synthesis-activation-criteria.md` once ratified.

The intended enable sequence (subject to D-024 ratification) is approximately:
1. `agents:ai_synthesis:enabled` (Action 9 — this plan's destination)
2. `agents:flow_agent:enabled` + `agents:sentiment_agent:enabled` (parallel; both feed `synthesis_agent`)
3. `strategy:ai_hint_override:enabled` (consumes `ai:synthesis:latest` strategy_hint)
4. `strategy:iron_butterfly:enabled` + `strategy:long_straddle:enabled` + `strategy:calendar_spread:enabled` (per-strategy enable; gated on per-strategy V0.1 paper validation)
5. `strategy:earnings_straddle:enabled` (separate revenue stream; independent gate per `backend_earnings/`)

This is intent only — D-024 ratifies the binding sequence.

### 1.5 Trading reality (paper)
- **2 sessions logged** (5 closed trades total — all iron_butterfly or iron_condor)
- 22.6% rolling directional accuracy (n=2 SESSIONS, not trades — statistically meaningless given sample size)
- Total virtual P&L across the 2 sessions: -$1,616.31
- Action 9 abort SLA baselines for "hourly Sharpe < -1.0" reference rolling sessions, not single-trade outcomes (D-024 will define exact rolling window)

**Today's regime + skip-rate distribution: NOT YET VERIFIED.** Action 2 produces this evidence. Until then, claims about "X gate dominates" are unverified.

### 1.6 Critical operational items affecting ROI today
- Alert emails currently broken — affects operator situational awareness during V0.1 ramp (Action 11)
- Phase A LightGBM training pipeline gated on 90 sessions — `model_retraining.py` dormant (per AI Build Roadmap Phase 5B Item 13 retraining substrate, §3.11 — corrected from v2.0.1 "Phase 3E" misciation per combined-round CR-1; Phase 3E is Item 5 Vol Fair-Value Engine which has no LightGBM training)
- Dashboard observability sprint UI-1/2/3/4 partial completion — affects V0.2 promotion-gate visibility (Action 12)
- Edge Function deploy needed for Learning Dashboard (Action 12)
- system-state.md is stale (April 18 snapshot) — operator running newer state from TASK_REGISTER.md only (Action 13)

### 1.7 TASK_REGISTER coverage statement
**TASK_REGISTER.md §12 (BUILD-NOW QUEUE 12A-12N) is COMPLETE work** per HANDOFF_2 — all 14 items shipped between commits `c5a2b70` and `d11b8fd` between April 14-22 2026. Not pending; not subsumed; done.

**TASK_REGISTER.md §13 (Post-Section-12 Diagnostic Fixes) is COMPLETE work** per HANDOFF_2 — Batches 1+2 shipped at commits `fc64840` and `41bb1ab`. UI Observability Sprint partially shipped (`709a3db` + `0149877` + `0fdc7d2`); UI gaps absorbed by Action 12.

**TASK_REGISTER.md §11 (Profit Maximization Roadmap Phase 0/A/B/C/D/E)** subsumes into:
- Phase 0 → Pre-AI Commits 7/8/9 (Action 10)
- Phase A (LightGBM training) → AI Build Roadmap Phase 5B (Item 13 retraining substrate, §3.11 — corrected from v2.0.1 "Phase 3E" per combined-round CR-1)
- Phases B/C/D/E → AI Build Roadmap per-Cluster sequencing

**TASK_REGISTER.md §14A-F (AI architecture build phases)** subsumes into AI Build Roadmap §10 build commitments (G-1 through G-13).

If a TASK_REGISTER section is NOT named above, it is governed by other companion plans (AI Build Roadmap or Audit Disposition Plan) per §0 pointer table. No silent drops.

### 1.8 LightGBM v1 activation (2026-04-30, 5 sequential Fix PRs)

After ~8 hours of `DIAGNOSE-FIRST` debugging chained across 5 Fix PRs (T-ACT-040 through T-ACT-044, PRs #82-#86), LightGBM v1 went LIVE in production at commit `8094eff` (20:30 UTC), with full library version-pinning discipline locked at commit `5162020` (21:33 UTC).

System flipped from hardcoded placeholder probabilities (0.35 / 0.30 / 0.35) to real ML conviction signals at holdout-validated 52.9% win rate across 23,668 samples (~9σ from coin-flip).

**PR sequence (chronological, all merged 2026-04-30):**
- PR #82 (`94edb9a`) — T-ACT-040 — AI synthesis output unblock (TTL coupling fix in `prediction_engine.py` + `synthesis_agent.py` + Supabase schema migration adding `strategy_hint` / `sizing_modifier` / `source` columns to `trading_prediction_outputs`; resolves PGRST204 schema-mismatch persistence failure that was silently dropping AI synthesis predictions)
- PR #83 (`a77195a`) — T-ACT-041 — three-tier LightGBM model loader (`prediction_engine.py:_load_direction_model`: local file cache → Supabase storage download → silent miss) + Supabase storage `ml-models` bucket bootstrap + `lightgbm` bumped to `4.6.0` in `requirements.txt` + one-shot health probe + partial-state bug fix bundled
- PR #84 (`eaa7aa8`) — T-ACT-042 — `libgomp1` via `nixpacks.toml` (subsequently confirmed INERT — Railway uses Railpack, see PR #85) + `trading_system_health` CHECK constraint expansion via migration `20260430_add_direction_model_to_health_constraint.sql` to admit `service_name='direction_model'` for the loader's health probe
- PR #85 (`8094eff`) — T-ACT-043 — `railpack.json` `deploy.aptPackages: ["libgomp1"]` (the actually-effective fix — Railway's `railway.json` pins builder to RAILPACK, making `nixpacks.toml` inert) + `nixpacks.toml` deletion + audit corrections in `06-tracking/action-tracker.md` for T-ACT-042 inert state — **LIGHTGBM ACTIVATED** at this commit
- PR #86 (`5162020`) — T-ACT-044 — `scikit-learn==1.5.2` exact pin in `requirements.txt` (resolves `InconsistentVersionWarning` 1.8.0-trained vs 1.5.2-prod skew) + `_capture_training_environment()` in `backend/scripts/train_direction_model.py` (writes Python + library + OS metadata into `model_metadata.json` at save time) + new `backend/scripts/preflight_training_env.py` validator script for operator pre-training environment check (covers the 4 pickle-critical libraries: scikit-learn, numpy, pandas, scipy)

**Lessons-learned (HANDOFF NOTE Appendix A discipline additions, governance-grade):**
- **A.1** — Health-probe `service_name` values must be allowlist-checked against `trading_system_health_service_name_check` migration before adding new probe (T-ACT-042 / Fix PR 3)
- **A.2** — Deploy-config edits must validate the meta-config (Railway uses `railway.json` `builder` field to select between Nixpacks and Railpack; modifying the wrong builder's config is a silent no-op) (T-ACT-043 / Fix PR 4)
- **A.3** — Pickled ML artifacts depend on every library that participated in the original `pickle.dump()` call graph, not just the model class library; pin scikit-learn + numpy + scipy + pandas + lightgbm exactly, capture training environment metadata in `model_metadata.json` at save time, validate with preflight script before training (T-ACT-044 / Fix PR 5)
- **A.4** — Cumulative DIAGNOSE-FIRST pattern lesson — during the 5-PR saga, 3 of 5 PRs surfaced adjacent meta-discipline gaps that earlier DIAGNOSE rounds had missed (Fix PR 2 missed CHECK constraint allowlist; Fix PR 3 missed Railway builder-pin meta-config; Fix PR 5 missed numpy/pandas/scipy 3-library skew via Fix PR 2 Stage 0 freelance `pip install`); future DIAGNOSE rounds must explicitly check the "meta-config that determines what the config does" before authorizing the fix (ratified 2026-04-30 from cumulative T-ACT-040 through T-ACT-044 saga)

See `trading-docs/06-tracking/HANDOFF_NOTE_2026-04-28_POST_P1-3-7.md` Appendix A for full lesson-learned text and discipline-rule integration.

---

## 2 — The Decision That Defines This Plan

**Decision: Path Y, not Path X.**

| Path | What it does | Long-term effect |
|---|---|---|
| **X** — lower `signal_weak < 0.05` to `0.03` | More rule-based trades on borderline conviction | One-time volume tweak; rules don't learn from added trades; Sharpe likely degrades; phase ladder stalls |
| **Y** — flip `agents:ai_synthesis:enabled` ON | LLM (Claude/GPT) becomes directional judge | Every trade produces labeled training data; meta-labeler activates at 100 trades; direction model activates at 90 sessions; rule-based fallback gets smarter via meta-labeler calibration |

**Compounding-learning precondition verified:** AI synthesis output → `trading_prediction_outputs` row → `model_retraining.label_prediction_outcomes()` at `backend/model_retraining.py:23-150` labels post-30-min SPX move. Labeling job is scheduled and active at HEAD `fc6b077`. Compounding is real, not assumed.

**Timeline reality (corrected from v1.3):**
- Meta-label model: trade-gated (`MIN_CLOSED_TRADES = 100`); Path Y CAN accelerate
- Direction model: session-gated (`MIN_TRAINING_SESSIONS = 90`); Path Y CANNOT accelerate
- At current 2.5 trades/session: meta-label ~9 months; direction model ~18 weeks
- At Path Y 2× cadence: meta-label ~5 weeks; direction model ~18 weeks (UNCHANGED)
- At Path Y 3× cadence: meta-label ~13 sessions; direction model ~18 weeks (UNCHANGED)
- **Implication:** First trained meta-label model in 1-3 months post-activation conditional on cadence lift; first direction model in ~4 months regardless

**Capital scaling is a 4th ROI lever — orthogonal to AI activation.** `capital:deployment_pct` and `capital:leverage_multiplier` are operator-tunable independent of any AI activation, audit, or code change. Tuning discipline documented in `AUDIT_DISPOSITION_PLAN.md` D-024 governance.

Path Y is the only path that builds compounding value. Path X also has structural ROI risk (Sharpe degradation stalls phase advancement, capping ROI at Phase 1 sizing for 90+ days).

---

## 3 — Prerequisites for Path Y Activation (Hard Gates A-F)

Activating `agents:ai_synthesis:enabled` requires ALL of:

### Gate A — Bug-class prevention complete
- ✅ DO NOT activate if `bull_debit_spread`/`bear_debit_spread` strings still emitted as invalid
- 2 emitters (synthesis_agent.py:40-41 + surprise_detector.py:235-237) both write to `ai:synthesis:latest`
- 2 test files encode the wrong strings
- Strategy router silently drops invalid hints — no log warning today
- **Resolution:** Action 1 (Day 0)

### Gate B — Empirical baseline established
**Status:** ✅ LOCKED 2026-04-30 — Apr 28 baseline (PR #73) + Apr 29 append (PR #78) confirms `direction_signal_weak` >50% pattern (100% of skips at Apr 28 across 73 cycles; dominance pattern persists at Apr 29 append). Apr 30 skipped intentionally per regime contamination during the 5-PR LightGBM activation chain. Sufficient evidence to ratify Action 8 trigger as TRIPPED. See `trading-docs/08-planning/ROI_LOG_BASELINE_2026-04-28.md`.
- ✅ DO NOT activate without knowing post-Commit-3 no-trade-reason distribution (historical context, retained)
- 13 distinct skip paths exist (12 enumerated + 1 implicit min-contracts floor)
- Without baseline, AI-vs-rules attribution becomes impossible after activation
- **Resolution:** Action 2 (Day 0) — completed 2026-04-28 (PR #73) + 2026-04-29 append (PR #78)

### Gate C — Cluster B audit cadence complete
**Status:** ✅ CLOSED 2026-04-29 — Cluster B complete 4 of 4 audits (P1.3.5 + P1.3.6 + PR #75 P1.3.7 + PR #77 P1.3.8). Per `AUDIT_FINDINGS_REGISTER.md` L9 verbatim attribution: *"CLUSTER B AUDIT 4 of 4 — CLUSTER B COMPLETE; CLOSES GATE C OF PATH Y ACTIVATION"*. Contingent P1.3.9 path-fork (Action 4b + C-AI-006-4 disposition) is INDEPENDENT of Gate C closure — Gate C closes on Cluster B alone; P1.3.9 is a 5th-audit candidate triggered only if C-AI-006-4 → option 2 selected at Action 5a.
- ✅ DO NOT activate before Cluster B closes (historical context, retained)
- Cluster B = AI-SPEC-005 (✅ PR #65) + AI-SPEC-006 (✅ PR #67) + AI-SPEC-008 (✅ PR #75 `ff7495a` 2026-04-28) + AI-SPEC-009 (✅ PR #77 `363a6ec` 2026-04-29 — closes Cluster B + Gate C) + possibly AI-SPEC-014 / AI-SPEC-016 (same spec — register uses 014, Build Roadmap uses 016 per Cursor v1.0 H-1 collision avoidance with deferred Item 14 Tournament Engine; canonical name selected at D-024 ratification per `AUDIT_DISPOSITION_PLAN.md` §3; contingent on C-AI-006-4 resolution; INDEPENDENT of Gate C closure)
- **Resolution:** Actions 3, 4 complete (Days 1-2); Action 4b conditional on C-AI-006-4 option 2 at Action 5a

### Gate D — Activation criteria + governance ratified
- ✅ DO NOT activate without measurable success/abort thresholds
- Two distinct decisions, NOT conflated:
  - **D-023** = 13-spec AI authority boundary (Risk Governor scope, Meta-Labeler authority, Counterfactual cutover, etc. — folds 22 Class C escalations enumerated in `AUDIT_DISPOSITION_PLAN.md`)
  - **D-024** = Phase 2A `synthesis_agent.py` activation criteria + succession plan (Phase 2A is NOT modeled in any of the 13 locked specs)
- **Resolution:** Actions 5a, 5b, 6 (Days 5-7)

### Gate E — Commit 4 of pre-AI fix track shipped + ≥5 trading days elapsed
- ✅ DO NOT activate within 5 trading days of Commit 4 deploy
- Reason: clean Sharpe attribution
- **Sequencing math (3-way max):** Action 9 effective date = max(Day 14, Action 7 ship + 5 trading days, Action 8 ship + 5 trading days IF Action 8 ships)
- **7-8 paused flags orthogonality:** The 7-8 strategy/agent flags listed in §1.4 are orthogonal to Path Y. Their activation order is operator-controlled post-Commit-4 and does NOT gate Action 9.
- **Resolution:** Commit 4 (Action 7) runs in parallel with audit track

### Gate F — `_RISK_PCT` ladder monotonicity fix landed BEFORE Action 9
**Status:** ✅ CLOSED — PR #74 (`13d2b18`). Phase 2-4 core + satellite risk-pct values scaled 2× to preserve dollar-equivalent ladder post-2026-04-20 width widening; monotonicity restored across Phase 1 → 4 ladder. PRE-P11-3 closed in `AUDIT_FINDINGS_REGISTER.md`.
- ✅ DO NOT activate (Action 9) until `_RISK_PCT` ladder is fixed (historical context, retained)
- **Bug (now fixed):** `backend/risk_engine.py:78-83` previously had Phase 1 core risk = 0.010 BUT Phase 2 core risk = 0.0075 → Phase 1 → 2 advancement DROPPED sizing 25%
- **Already tracked as PRE-P11-3** in `AUDIT_FINDINGS_REGISTER.md:53` (now closed per PR #74)
- **Sequencing constraint from PRE-P12-2:** ladder fix must land BEFORE AI-SPEC-012 build begins; constraint satisfied — fix landed pre-Action-9
- **Resolution:** Action 7b — completed via PR #74 `13d2b18`

**Activation = ALL SIX GATES PASSED.**

---

## 4 — Sequenced Action Plan

### Day 0 — Today (2026-04-28)

#### Action 1 — Fix `bull_debit_spread`/`bear_debit_spread` string drift (Gate A)
**Owner:** Cursor
**Estimated work:** 1.5-2 hours
**ROI vector:** C (enabling-infrastructure — prerequisite for AI activation)
**Branch name:** `fix/ai-synthesis-strategy-string-drift`
**Scope (4 files + 3 enhancements):**
- `backend_agents/synthesis_agent.py:40-41` — replace LLM SYSTEM_PROMPT instruction strings with `debit_call_spread`, `debit_put_spread`
- `backend_agents/surprise_detector.py:235-237` — same string fix at the surprise-override emit site
- `backend/tests/test_phase_2a_agents.py:104,143` — update test fixtures
- `backend/tests/test_consolidation_s5.py:220` — update test fixtures
- **Bug-class prevention 1 — shared validator helper:** factor `_validate_synthesis_payload(synth: dict) -> Optional[dict]` into a shared location (e.g., `backend_agents/_synthesis_schema.py` or as a module-level function in `synthesis_agent.py` imported by `surprise_detector.py`). Helper validates `synth["strategy"] in {valid_set}` and returns `None` (with warning log) on invalid. Both writers MUST call it before `redis_client.setex("ai:synthesis:latest", ...)` at synthesis_agent.py:198 AND surprise_detector.py:239
- **Bug-class prevention 2 — invalid-hint warning:** add `logger.warning("ai_hint_invalid_strategy", hint=..., regime_top=...)` at `backend/strategy_selector.py:1027`
- **Bug-class prevention 3 — test for both writers:** new test asserts that surprise_detector + synthesis_agent both reject invalid strings via the shared validator
**Verification:**
- All 5-6 files updated in single commit (5 if helper colocated; 6 if extracted to new module)
- Pytest passes
- Validator catches synthesized invalid strings in test
- Warning fires when test feeds invalid strategy_hint
- Both write paths covered by validator
**Status:** [ ] Pending Cursor prompt

#### Action 2 — Pull Railway log baseline (Gate B)
**Owner:** Operator (with Claude guide)
**Estimated work:** 1-2 hours
**ROI vector:** Diagnostic (informs Action 8 + activation post-mortem)
**Time window:** **Post-Commit-3 deploy: 2026-04-27 16:08 ET onward.** Window is ≤2 trading days of clean data; alternative is contaminated data; accept the small-sample tradeoff.
**Scope:**
- Pull Railway logs for 2026-04-27 16:08 ET onward
- Grep for `no_trade_reason=` and produce distribution histogram
- Grep for `*_skip_trade` and `*_blocked_*` log keys (5 strategy_selector skip paths)
- **Also enumerate `contracts=0` / `min_contracts_floor` log occurrences as the implicit 13th skip path per F-37**
- Identify the actual dominant skip path (across all 13 paths)
- Save output as `trading-docs/08-planning/ROI_LOG_BASELINE_2026-04-28.md`
**Status:** [ ] Pending Claude log-pull guide

### Days 1-2 (2026-04-29 to 04-30)

#### Action 3 — P1.3.7 audit (AI-SPEC-008 OPRA Flow Alpha) (Gate C)
**Owner:** Cursor (audit producer); Claude (audit prompt drafter); operator (review + merge)
**Estimated work:** 1 day per existing P1.3.x cadence
**ROI vector:** C
**Status:** [x] DONE 2026-04-28 (PR #75 `ff7495a`). AI-SPEC-008 redline at `trading-docs/08-planning/ai-architecture-audits/AI-SPEC-008.md` (583 lines, 14 sections + §0 Pre-Audit Verification). Findings: 2 Class A + 18 Class B + 4 Class C in `AUDIT_FINDINGS_REGISTER.md` (A-AI-008-1..2 + B-AI-008-1..18 + C-AI-008-1..4). Recommended status `RATIFY-WITH-AMENDMENTS`. Post-audit handoff note PR #76 (`de62378`).

### Days 3-4 (2026-05-01 to 05-02)

#### Action 4 — P1.3.8 audit (AI-SPEC-009 Exit Optimizer) (Gate C)
**Owner:** Same roles as Action 3
**Status:** [x] DONE 2026-04-29 (PR #77 `363a6ec`). AI-SPEC-009 redline at `trading-docs/08-planning/ai-architecture-audits/AI-SPEC-009.md` (771 lines; 4 Class A + 20 Class B + 6 Class C findings). **Closes Cluster B (4 of 4) and Gate C of Path Y activation per `AUDIT_FINDINGS_REGISTER.md` L9 verbatim attribution.**

### Day 4 — late-day decision gate

#### Action 5a — C-AI-006-4 decision gate (Gate C, conditional path-fork)
**Owner:** Operator + Claude (consultation)
**Estimated work:** 30-45 minutes (single decision)
**Scope:** Operator decides among C-AI-006-4 options 1/2/3 per `AUDIT_DISPOSITION_PLAN.md` enumeration. Outcome triggers Action 4b OR skips it.
**Status:** [ ] PENDING operator decision — Action 4 dependency is ✅ DONE 2026-04-29 (PR #77) so this gate is now unblocked. C-AI-006-4 disposition note will be folded into the Action 6 (D-023 + D-024) ratification PR per Master Forward Plan v1.2 reconciliation scope decision (operator F4).

### Day 5 — CONTINGENT (only if Action 5a → option 2)

#### Action 4b — P1.3.9 audit (AI-SPEC-014 LightGBM Direction Model — renamed AI-SPEC-016 in AI Build Roadmap §3.6; canonical name resolved at D-024 ratification per `AUDIT_DISPOSITION_PLAN.md` §3)
**Trigger:** ONLY if Action 5a → option 2
**Owner:** Cursor / Claude / operator
**Estimated work:** 1 day per cadence
**Status:** [ ] CONTINGENT on C-AI-006-4 → option 2 operator decision (Action 5a). Cluster B is otherwise CLOSED (4 of 4 audits complete) without P1.3.9; option 2 selection triggers a 5th audit. AI-SPEC-014 / AI-SPEC-016 canonical naming pending D-024 ratification per `AUDIT_DISPOSITION_PLAN.md` §3. Action 4 (P1.3.8) and Cluster B closure are NOT blocked by this contingency.

### Days 5-6 — Activation criteria draft

#### Action 5b — D-024 activation criteria draft (Gate D)
**Owner:** Operator + Claude
**Estimated work:** Days 5-6 — 1 working session (~3 hours)
**Scope:**
- Operator decides Phase 2A `synthesis_agent.py` succession plan (open question F-22)
- Claude drafts D-024 activation criteria document specifying:
  - Minimum closed paper trades before flag flip
  - Required AI synthesis output validation rate (parse rate, schema compliance)
  - **Full JSON schema for synthesis payload validation** — Action 1's validator covers ONLY `strategy` field; D-024 extends to all required fields per SYSTEM_PROMPT contract at `backend_agents/synthesis_agent.py:32-58`
  - Sharpe / win-rate thresholds for AI-gated trades vs rule-based baseline
  - **Abort thresholds** — explicit numeric: parse rate <95% over 3 cycles per D-024 full schema, OR hourly Sharpe < -1.0, OR ≥3 invalid `strategy` payloads detected in Redis over 24h window, OR operator manual abort
  - **A/B comparison methodology — leverages existing `backend/shadow_engine.py`** (Portfolio A rule-based baseline → `shadow_predictions` table). When AI activates, AI synthesis becomes Portfolio B; existing infrastructure handles attribution. **No new A/B infrastructure required.**
  - **Capital scaling tuning discipline** — D-024 documents minimum sessions of positive Sharpe before increase, max increase per amendment, etc.
- Document committed to `trading-docs/00-governance/ai-synthesis-activation-criteria.md`
**Status:** [ ] PENDING Action 5a decision (and conditionally 4b). Action 4 (P1.3.8) is now ✅ DONE 2026-04-29 (PR #77), so the Action 4 dependency is satisfied; Action 5b D-024 drafting unblocks as soon as Action 5a operator decision lands. If Action 5a → option 2, additionally awaits Action 4b (P1.3.9) per Cluster B 5th-audit path-fork.

### Day 7 — Ratification

#### Action 6 — D-023 + D-024 ratification (Gate D)
**Owner:** Operator
**Estimated work:** Day 7 — 1 working session (~2 hours)
**Scope:**
- Update `trading-docs/08-planning/approved-decisions.md` with **D-023** AND **D-024**
- D-023 resolves all 22 Class C escalations enumerated in `AUDIT_DISPOSITION_PLAN.md`
- D-024 resolves: F-22 (succession plan), F-19 (activation criteria), F-13/F-14 (Path Y rationale), capital tuning discipline
- Update AUDIT_FINDINGS_REGISTER.md to close resolved items

**Context updates from 2026-05-01 session:**

In addition to the original D-023 + D-024 ratification scope, Action 6 now incorporates context from three discoveries during the 2026-05-01 trading session:

- **C-AI-004-4 substrate confirmed in place** — Databento OPRA Standard historical access from 2013-04-01 unblocks option 2 (calibration-grade replay) per AUDIT_DISPOSITION_PLAN v1.10. Ratification of option 2 is now a near-trivial sub-decision within Action 6.

- **15-min SPX feed delay (resolved via PR #90)** — pre-PR-#90 paper-trading evidence is invalid because the system was reading 15-min-stale SPX inputs. Post-PR-#90 paper-trading evidence is required before Action 6 ratification can proceed with confidence in baseline data quality. See HANDOFF NOTE Appendix A.6 for the post-mortem.

- **Empirical-validation-against-independent-source discipline (HANDOFF A.6)** — Action 6's ratification documentation should include explicit independent-source comparison evidence for any data-driven claim (per A.6 mitigation #1). This is a process change for how Action 6 evidence is presented; it does not change the underlying decision space.

**Pre-Action-6 prerequisites (added 2026-05-01):**

- T-ACT-045 (post-PR-#90 SPX validation) MUST complete with VALIDATED verdict before Action 6 begins. Without empirical confirmation that PR #90 closed the delay, Action 6's data-quality assumptions are unsupported.
- T-ACT-046 and T-ACT-047 are NOT prerequisites for Action 6; they can run in parallel.

**2026-05-03 update:** T-ACT-045 was attempted on 2026-05-03 against pre-PR-#90-merge data (last cycle 2026-05-01 19:55 UTC; merge 19:59 UTC). Cursor's independent review reversed an initial VALIDATED verdict to NOT-YET-VALIDATED on the grounds that the data set was structurally pre-deploy. T-ACT-045 status updated to PENDING-RE-RUN; target Monday 2026-05-04 ≥10 min after Railway deploy is confirmed stable. Action 6 prerequisite "T-ACT-045 must complete with VALIDATED verdict" remains the gate; it is now augmented (per N-2 finding) to require a validation artifact at `trading-docs/06-tracking/T-ACT-045-validation-artifact-2026-05-XX.md` to make the verdict independently re-verifiable. Until both T-ACT-045 = VALIDATED AND the validation artifact exists at the documented path, Action 6 is blocked. T-ACT-046 was implemented in Track B PR `docs/track-b-silent-staleness-and-governance` (2026-05-03) — bundles `tradier_feed.py:282-283` AND `polygon_feed.py:174-184` per Cursor recommendation; same root pattern; T-ACT-046 is no longer in-flight. T-ACT-047 (try/except discipline) remains pending, runnable in parallel. T-ACT-054 (cv_stress NULL-on-degenerate-input remediation) was added 2026-05-03 — it is NOT an Action 6 prerequisite (cv_stress is independent of the SPX delay question) and runs in parallel.

**Status (post 2026-05-03):** [ ] Pending — awaiting T-ACT-045 PENDING-RE-RUN completion AND validation artifact, then collaborative operator + Claude session as originally scoped.

### Days 7-14 — parallel tracks

#### Action 7 — Pre-AI fix track Commit 4 (Gate E)
**Owner:** Cursor (implementation); operator (merge)
**Scope:** Per FINAL_DEPLOY_PLAN_v2.md (re-mark + calibration cleanup + NULL slippage handling). Anchor for AI-SPEC-010 Layer 2 cutover (C-AI-010-5).
**Bundles F-17:** `feedback:counterfactual:enabled` + `model:meta_label:enabled` added to `_TRADING_FLAG_KEYS` (operator admin endpoint exposure)
**Status:** [ ] Parallel to audit track

#### Action 7b — `_RISK_PCT` ladder monotonicity fix (Gate F)
**Owner:** Cursor
**Estimated work:** 1 hour code + test + commit
**ROI vector:** A/B
**Branch name:** `fix/risk-pct-ladder-monotonicity`
**Scope:**
- `backend/risk_engine.py:78-83` — change Phase 2 from `{"core": 0.0075, "satellite": 0.00375}` to `{"core": 0.010, "satellite": 0.0050}`
- Update inline comment to reflect PRE-P11-3 resolution
- Add test asserting `_RISK_PCT[1]["core"] <= _RISK_PCT[2]["core"] <= _RISK_PCT[3]["core"] <= _RISK_PCT[4]["core"]`
- Update `AUDIT_FINDINGS_REGISTER.md:53` (PRE-P11-3) to mark closed
**Note on PRE-P12-2 sequencing:** Constraint satisfied automatically because AI-SPEC-012 / Cluster C is post-V0.1 per `AI_BUILD_ROADMAP.md`
**Status:** [ ] Hard Day 7-14 deliverable

#### Action 8 — TRIPPED: redesigned `signal_weak` change as conviction-conditional sizing
**Trigger:** TRIPPED 2026-04-30 — Apr 28 baseline showed `direction_signal_weak` at 100% of skips (146 outer + 73 inner over 73 cycles); Apr 29 append confirms dominance pattern. Trigger condition (>50%) exceeded by ~2×. Conditional status retired; conviction-conditional sizing redesign authorized for Days 7-14 sequencing per Gate E 3-way max formula.
**Decision rule:** Was "if logs show another gate dominates, Action 8 is a no-op" — superseded by Apr 28-29 baseline evidence.
**Scope (now committed for Days 7-14):**
- Lower threshold from 0.05 → 0.03
- ADD sizing modifier: trades in 0.03 ≤ |p_bull - p_bear| < 0.05 band get 0.5× contracts
- Trades with |p_bull - p_bear| ≥ 0.05 retain 1.0× sizing
- New test asserts borderline trades open at reduced size
- Sequence ≥5 trading days BEFORE Action 7 deploy for clean Sharpe attribution
- **Sequencing branch:** if Action 8 cannot ship ≥5 trading days before Action 7, defers to (Action 7 ship + 5 trading days) via Gate E 3-way max formula
**Status:** [ ] TRIPPED — queued for Days 7-14. Conviction-conditional sizing redesign authorized; implementation tracked in companion action-tracker (`trading-docs/06-tracking/action-tracker.md`) as new T-ACT-045 placeholder when build begins.

### Days 14-21 — Path Y activation

**Note on calendar slip:** Window may extend past Day 21 if Action 8 deferral pushes the Gate E 3-way max past Day 21. This is acceptable — sequencing correctness > calendar fidelity.

#### Action 9 — Path Y activation: flip `agents:ai_synthesis:enabled` to `true`
**Prerequisite:** Gates A/B/C/D/E/F ALL PASSED. Effective date = max(Day 14, Action 7 ship + 5 trading days, Action 8 ship + 5 trading days IF Action 8 ships).
**Owner:** Operator
**Scope:**
- Verify all 6 gates pass via published D-024 activation criteria document (Gate F = `_RISK_PCT` ladder fix landed)
- Flip flag via admin endpoint
- Confirm Redis value
- Set up monitoring per D-024
- Confirm frontend dashboard renders new synthesis brief
**Abort SLA (5-min response):**
- Parse rate < 95% over 3 cycles per D-024 full schema
- Hourly Sharpe < -1.0
- ≥3 synthesis payloads with invalid `strategy` field detected in Redis over 24h window (validator regression — metering source: Redis snapshots, NOT validator logs)
- Operator manual abort
**Status:** [ ] Conditional — pending all gates

### Days 21+ — post-activation

Continuous monitoring per D-024. Specific abort triggers documented above. **Cluster C build cadence resumes per `AI_BUILD_ROADMAP.md`** — P1.3.10 AI-SPEC-013 Drift Detection committed as first audit post-V0.1, no later than Day 60 post-activation.

### Operational items (parallel to all of the above; affect ROI directly)

#### Action 10 — Pre-AI Commits 5-10
**Owner:** Cursor (implementation); operator (merge)
**Scope:** Per FINAL_DEPLOY_PLAN_v2.md and TASK_REGISTER.md §11. Specifically:
- Commit 5 = Action 7b (`_RISK_PCT` ladder fix) — already enumerated above
- Commit 6 = VVIX z-score fix paired with `vix_daily_history` backfill primitive
- Commit 7 = Phase 0 commission model fix
- Commit 8 = Action 8 conditional (signal_weak → conviction-conditional sizing) — already enumerated above
- Commit 9 = IV/RV no-trade filter at `prediction_engine.py:706`
- Commit 10 = TBD per FINAL_DEPLOY_PLAN_v2.md — operator paste required
**Status:** [ ] Each commit tracked separately; bundle into Days 7-21+ window

#### Action 11 — Resend SMTP migration (alert emails currently broken)
**Owner:** Cursor + operator
**Estimated work:** ~30 min
**ROI vector:** Governance — operator situational awareness during V0.1 ramp
**Status:** [ ] Pending — bundle with Commit 7 or schedule standalone

#### Action 12 — Dashboard observability sprint completion (UI-1/2/3/4)
**Owner:** Operator + Cursor
**Estimated work:** Variable
**Scope:** Complete partial UI sprint per HANDOFF_2; deploy Edge Function for Learning Dashboard
**ROI vector:** Indirect (V0.2 promotion-gate visibility)
**Status:** [ ] Pending — schedule pre-V0.2 promotion (post-Day-21)

#### Action 13 — system-state.md synchronization
**Owner:** Operator or Claude
**Estimated work:** ~15 min
**Scope:** Update `Last Updated` to 2026-04-28; reflect Commits 1-3 shipped + this plan v2.0; reference 3 sub-plans per §0 pointer table
**Status:** [ ] Pending — bundle with v2.0 commit PR

---

## 5 — Decision Log Cross-Reference

D-numbers from `trading-docs/08-planning/approved-decisions.md`:

- **D-015** — LightGBM slippage (NOT BUILT — static dict). Divergence open. AI-SPEC-005 audit covers; full handling in `AUDIT_DISPOSITION_PLAN.md`
- **D-016** — Vol blending (PARTIALLY BUILT). Divergence open. AI-SPEC-005 audit covers; bilateral with C-AI-005-1; full handling in `AUDIT_DISPOSITION_PLAN.md`
- **D-018** — VVIX emergency z-score halt (3.0). Implemented; **input substrate has bug deferred to S7 — see Pre-AI Commit 6**. D-018 logic correct; reliability gated on Commit 6 fix
- **D-020** — Trade frequency cap. Implemented
- **D-021** — HMM + LightGBM regime classifier (NOT BUILT — rule-based). Divergence open. AI-SPEC audits cover; full handling in `AUDIT_DISPOSITION_PLAN.md`
- **D-022** — Capital preservation halt at 5 consecutive losses. Implemented
- **D-023** — RESERVED — 13-spec AI authority boundary. Ratification = Action 6. **Full enumeration of 22 Class C items folding into D-023 is in `AUDIT_DISPOSITION_PLAN.md`**
- **D-024** — RESERVED — Phase 2A activation criteria + succession plan + capital tuning discipline. Ratification = Action 6

---

## 6 — Out of Scope with Explicit Handling

These are NOT in this plan's scope but are explicitly tracked elsewhere or deferred with rationale:

- **`backend_earnings/` strategy track** — separate revenue stream; tracked via TASK_REGISTER.md
- **Frontend code changes (Lovable)** — out of scope; frontend IMPACT of Action 9 is in scope (verification only)
- **HANDOFF_3 §14 "AI Trading Agent" framing** — obsolete; superseded by Cluster B+C audits per `AI_BUILD_ROADMAP.md`
- **Data improvements 15D (cross-asset signals)** — V0.2+ deferral per `AI_BUILD_ROADMAP.md`
- **Data improvements 15E (retail sentiment)** — V2+ deferral per `deferred-work-register.md`
- **Cluster C audits 11/3/7/12** — post-V0.1 sequencing per `AI_BUILD_ROADMAP.md` (only AI-SPEC-013 Drift Detection committed within Day 60 post-activation)
- **Phase ladder performance-gating tweaks** — already dual-gated (Sharpe + calendar); no work needed beyond Action 7b monotonicity fix

---

## 7 — Findings Tracking Register (F-N IDs local to THIS document)

**Note:** F-N IDs from v1.0-v1.6 are preserved. New G-N IDs from Cursor's gap scan are mapped per-document — gaps that belong to AI Build Roadmap or Audit Disposition Plan are tracked in those documents, not here. This register holds findings governing the activation path and operational items.

| ID | Finding | Source | Status |
|---|---|---|---|
| F-1 | Phase 2A `synthesis_agent.py` exists, 628 LOC, dual-provider, Redis-flag-gated | Consensus | [ ] |
| F-8 | `signal_weak < 0.05` at lines 580/649 | Claude-in-chat | [ ] |
| F-9 | `direction_signal_weak` is one of 13 distinct skip paths | Cursor verification | [ ] |
| F-10 | `bull_debit_spread`/`bear_debit_spread` string drift in synthesis_agent.py:40-41 | Cursor inventory | [ ] |
| F-11 | Same drift in surprise_detector.py:235-237 (2nd emitter, 2nd writer at :239) | Cursor 3rd review | [ ] |
| F-12 | Same drift in test suite | Cursor 3rd review | [ ] |
| F-13 | AI synthesis path bypasses `signal_weak` gate | Cursor 3rd review | Informational — informed Path Y |
| F-14 | Phase ladder is dual-gated (calendar AND Sharpe) | Cursor 3rd review | Informational — informed Action 8 design |
| F-17 | `feedback:counterfactual:enabled` + `model:meta_label:enabled` not in `_TRADING_FLAG_KEYS` | Cursor inventory | [ ] Bundled into Action 7 |
| F-21 | 22 services, 15 healthy / 7 idle / 0 offline | Consensus | Informational |
| F-22 | Phase 2A `synthesis_agent.py` succession plan unresolved | Consensus | [ ] D-024 (Action 6) |
| F-29 | Frontend `trading_ai_briefs` will start rendering on Action 9 flip | Cursor v1.0 review M4 | [ ] |
| F-30 | `_RISK_PCT` ladder is non-monotonic — Phase 2 sizing collapse | Cursor v1.2 MISS-1 (PRE-P11-3) | [ ] Action 7b |
| F-31 | `polygon:vvix:z_score` mislabeled 100-min intraday window bug | Cursor v1.2 MISS-2 | [ ] Pre-AI Commit 6 |
| F-32 | Time-to-first-ML-model: meta-label is trade-gated; direction model is session-gated | Cursor v1.2 MISS-3 + v1.3 W3 | Informational |
| F-37 | Min-contracts implicit 13th skip path | Cursor v1.2 (less critical) | [ ] Action 2 baseline |
| F-38 | LightGBM v1 activation chain — 5 sequential Fix PRs (T-ACT-040 through T-ACT-044, PRs #82-#86) shipping 2026-04-30 from hardcoded 0.35/0.30/0.35 placeholder probabilities to real ML conviction signals at holdout-validated 52.9% win rate; activated at PR #85 (`8094eff`); version-pinning discipline locked at PR #86 (`5162020`); 4 governance-grade lessons-learned ratified into HANDOFF NOTE Appendix A.1-A.4 | Master Forward Plan v1.2 reconciliation (this PR) | [x] DONE 2026-04-30 — see `trading-docs/06-tracking/action-tracker.md` T-ACT-040..044 + §1.8 above |
| **G-2N** | **Source register references for cross-tracking with other 2 sub-plans:** | | |
| G-25 | Chain archive substrate operator decision (C-AI-004-4) — primary cascade dependency for AI-SPEC-004 V0.1 + AI-SPEC-005 V0.2 + AI-SPEC-010 V0.2 (per AI Build Roadmap §0 dependency map + AUDIT_DISPOSITION_PLAN §1.3); INDIRECT cascade to AI-SPEC-001 V0.2 paper-binding (≥200 cards via Item 4 replay harness — corrected from v2.0.1 "primary cascade for AI-SPEC-001 V0.2" overstatement per combined-round M-2); default position option 3 (V0.1-advisory-only) | Cursor gap scan §3.B | [ ] AUDIT_DISPOSITION_PLAN.md |
| G-29 | C-AI-006-1 Authority Recovery automatic-vs-operator-mediated — first authority-boundary Class C in Cluster B; bilateral with AI-SPEC-005 §5; CRITICAL — governs Items 5 + 6 simultaneously | Cursor gap scan §3.B | [ ] AUDIT_DISPOSITION_PLAN.md |
| G-41 | Freshness substrate buildout — `_safe_redis()` dead code at `prediction_engine.py:100` + `gex:updated_at` no-producer; 3-audit cross-spec confirmed (B-AI-001-6 + B-AI-005-16 + B-AI-006-17); SAFETY-CRITICAL given Item 6 admissibility authority depends on freshness gates | Cursor gap scan §3.B + this plan's non-negotiables | [ ] AUDIT_DISPOSITION_PLAN.md |
| G-49 | 15A Real-time news ingestion | Cursor gap scan §3.C | [ ] AI Build Roadmap |
| G-50 | 15B Options flow archival | Cursor gap scan §3.C | [ ] AI Build Roadmap |
| G-51 | 15C VIX term structure full curve | Cursor gap scan §3.C | [ ] AI Build Roadmap |
| G-55 | 16B VIX spread width recalibration | Cursor gap scan §3.C | [ ] AI Build Roadmap |
| G-56 | 16C OCO bracket orders pre-real-capital | Cursor gap scan §3.C | [ ] Action 10 (Commit 10 candidate) |
| G-57 | 17A Resend SMTP migration | Cursor gap scan §3.C | [ ] Action 11 |
| G-58 | 17B Edge Function deploy for Learning Dashboard | Cursor gap scan §3.C | [ ] Action 12 |
| G-59 | 17C Phase A LightGBM training pipeline | Cursor gap scan §3.C | [ ] AI Build Roadmap |
| G-66 | Commit 10 content TBD per FINAL_DEPLOY_PLAN_v2.md | Cursor gap scan SD-2 | [ ] Operator paste required |
| G-85 | system-state.md is stale | Cursor gap scan §3.G | [ ] Action 13 |
| G-86 | Sentiment Agent built but flag default-OFF | Cursor gap scan §3.G | [ ] Tracked in §1.4 |
| G-87 | Earnings Straddle module built but flag default-OFF | Cursor gap scan §3.G | [ ] Tracked in §1.4 |
| G-94 | Paused-flag count corrected (5 → 7-8) | Cursor gap scan §3.H | [x] Tracked in §1.4 |
| G-95 | 6 reverse-polarity signal flags state confirmation needed | Cursor gap scan §3.H | [ ] Operator inspection |

**For G-1 through G-13 (build commitments) and G-17 through G-31f (operator decisions): see `AI_BUILD_ROADMAP.md` and `AUDIT_DISPOSITION_PLAN.md` respectively.**

---

## 8 — Reviewer Consensus

Plan adopts:
- Cursor Sequence D + Operator Path Y (rounds v1.0-v1.6)
- Cursor structural recommendation Option β (v1.6 gap scan)
- Operator-modified β-lite (3 documents instead of 6)
- 3-reviewer consensus across 6 review rounds + 1 structural gap scan

Source reviews archived in conversation transcripts.

---

*End of Master ROI Plan v2.0.6 — applied via PR `docs/post-may-1-followups` 2026-05-01 against HEAD `16fd53c` (post v2.0.5 squash-merge of PR #88 → PR #89 → PR #90 chain). Trio composition at HEAD: Master Plan v2.0.6 + Build Roadmap v1.9 + DP v1.10. Companion: `SUBSCRIPTION_REGISTRY.md` (canonical active-subs reference); UI mirror at `src/pages/trading/SubscriptionsPage.tsx`. Cross-references added this round: HANDOFF NOTE Appendix A.6 (15-min Tradier sandbox SPX delay phantom-alpha post-mortem; ratified 2026-05-01) + TASK_REGISTER §14 (T-ACT-045 post-PR-#90 empirical SPX validation + T-ACT-046 tradier_feed silent-staleness fix + T-ACT-047 try/except discipline mitigation). Historical: v2.0.1 → v2.0.2 applied combined-round patches CR-1 + M-1 + M-2; v2.0.2 → v2.0.3 applied converged-state cleanup; v2.0.3 → v2.0.4 applied post-Cluster-B-closure governance reconciliation (§1.3 audit table flips + §1.8 LightGBM activation chain + §3 Gate B/C/F closure markers + §4 Action 3/4/4b/8 status flips + §7 F-38 milestone row); v2.0.4 → v2.0.5 applies SUBSCRIPTION_REGISTRY.md cross-references (§0 pointer table 4th row added; status line + footer trio-composition updated to reflect AI_BUILD_ROADMAP v1.9 + DP v1.10); v2.0.5 → v2.0.6 applies 2026-05-01 session context to Action 6 (C-AI-004-4 substrate confirmed; PR #90 SPX delay remediation noted as evidence-blocker for pre-PR-#90 paper-trading; HANDOFF A.6 empirical-validation discipline lesson; T-ACT-045 added as pre-Action-6 prerequisite). All edits operator-authorized per F1-a (T-ACT-045/046/047 consecutive numbering) + F2-c (action-tracker stub entries) DIAGNOSE-flag decisions for this PR.*
