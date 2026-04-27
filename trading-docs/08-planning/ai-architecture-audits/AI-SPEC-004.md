# Spec Verification Audit — AI-SPEC-004

> **Status:** First-pass redline (P1.3.3). Cursor primary-auditor sections (§1, §3, §4, §10.1) populated; first-pass drafts of §2, §5–§13 for Claude cross-check and GPT validation.
> **Binding format:** Follows `trading-docs/08-planning/ai-architecture-audits/_template.md` (P1.3.0).
> **Created:** 2026-04-26 (Phase 1 P1.3.3 of `CONSOLIDATED_PLAN_v1.2_APPROVED.md`).
> **Source spec:** `trading-docs/04-modules/ai-architecture/archive/raw-locked-specs-2026-04-26/ITEM_4_REPLAY_HARNESS_LOCKED.md` (1145 lines, locked 2026-04-26, immutable).

---

## 1. Audit Header

| Field | Value |
|-------|-------|
| Spec ID | AI-SPEC-004 |
| Spec name | Pre-V0.1 Replay Harness for Threshold Calibration |
| Stable ID | PLAN-REPLAY-001 |
| Tier | V0.1 |
| Cluster | A (foundational) |
| Audit date | 2026-04-26 |
| Repo HEAD at audit time | `b0bcdaad9be9128fe31f65cf9b6fee2588e6a49f` (P1.3.2 merged; AI-SPEC-002 audit landed) |
| Primary auditor | Cursor |
| Cross-check auditor | Claude |
| Architectural validator | GPT-5.5 Pro |
| Cross-cutting matrix reference | `CROSS_CUTTING_EVIDENCE_MATRIX.md` §3 (AI-SPEC-004 block, lines 158–179), §5 (`paper_phase_criteria` lines 553–561 + `item_promotion_records` lines 565–574 + `replay_eval_*` lines 576–585), §6 (`databento:opra:*` archival boundary lines 653–660), §7 (dependency graph — Item 4 as critical-path root, lines 671, 678–679, 684, 688) |
| Evidence pack reference | `AI_ARCH_EVIDENCE_PACK.md` §6.1 (backend module map — confirms no `replay` files), §7.2 (proposed tables — `item_promotion_records` line 356, `replay_eval_runs/cases/results` lines 364–366 all absent), §8 Item 4 (lines 405–408 — NOT YET IMPLEMENTED), §10 (Redis key inventory — no `replay:*` namespace) |

---

## 2. Spec Intent Summary (verified by GPT)

**(First-pass draft for GPT-5.5 Pro to refine.)**

AI-SPEC-004 introduces "the promotion court" — a research-only offline replay harness whose architectural keystone is the contrapositive **"no replay reconstruction, no promotion."** Items 1 (Risk Governor), 5 (Vol Fair-Value), and 6 (Meta-Labeler) may still log or advise without it, but they cannot earn binding authority until Item 4 reconstructs point-in-time pricing, model state, paths, and slippage cleanly enough to evaluate per-item promotion gates. The spec's load-bearing safety property is **structural research-vs-production isolation**, enforced at three layers (database-level CHECK constraints on `replay_eval_runs.environment = 'research'` and `replay_eval_cases.environment = 'research'`; default `retrieval_enabled = false` on every replay case; dual-namespace separation between `decision_inputs` and `evaluation_outcomes` in code paths) so replay cases can never enter production case memory or contaminate live training. The four-table architecture (`replay_eval_runs` / `replay_eval_cases` / `replay_eval_results` / `item_promotion_records`) plus the `item_promotion_records` startup-read contract ("if no current record exists for an item/scope: default to advisory or disabled, NEVER production") collectively prevent items from inventing their own promotion status. The hard prerequisite is archived option-chain data: without it, chain-dependent replay is explicitly NOT calibration-grade (spec §1 line 49–50, "Hard Rule: No Theoretical Pricing").

---

## 3. Repo Evidence (verified by Cursor)

**Cursor primary ownership.** Every concrete claim verified against actual repo state at HEAD `b0bcdaa`.

### 3.1 File/Module References

Item 4's spec is forward-design — it cites file paths the harness *will* live in (Spec §4 lines 531–554), none of which exist at HEAD. Verified `ls backend/ | grep -iE 'replay'` returns zero matches (consistent with `AI_ARCH_EVIDENCE_PACK.md` §8 Item 4 lines 405–408).

| Spec citation | Reality at HEAD `b0bcdaa` | Status |
|---|---|---|
| `backend/replay_harness.py` (Spec §4 line 532) | File does not exist. | **proposed-only** |
| `backend/replay_data_reconstructor.py` (Spec §4 line 535) | File does not exist. | **proposed-only** |
| `backend/replay_feature_builder.py` (Spec §4 line 538) | File does not exist. | **proposed-only** |
| `backend/replay_decision_stack.py` (Spec §4 line 541) | File does not exist. | **proposed-only** |
| `backend/replay_threshold_optimizer.py` (Spec §4 line 544) | File does not exist. | **proposed-only** |
| `backend/replay_leakage_guard.py` (Spec §4 line 547) | File does not exist. | **proposed-only** |
| `backend/replay_validator.py` (Spec §4 line 550) | File does not exist. | **proposed-only** |
| `backend/replay_reporter.py` (Spec §4 line 553) | File does not exist. | **proposed-only** |
| Spec §1 line 33 (`Supabase: trading_sessions / trading_positions / trading_prediction_outputs / strategy_attribution / trade_counterfactual_cases / ai_governor_decisions / model/version tables`) — implicit reads | `trading_sessions` (verified migration `20260416172751_*.sql:14`), `trading_positions` (verified line 160), `trading_prediction_outputs` (verified). `strategy_attribution`, `trade_counterfactual_cases`, `ai_governor_decisions` — **all absent at HEAD**, per AI-SPEC-002 P1.3.2 audit + AI-SPEC-001 P1.3.1 audit findings. | **partial — 3 reads land, 3 reads block on Items 1 + 2 + 10 schemas** |
| Spec §1 line 42 (`Polygon: SPX / I:SPX historical 1-min bars`) | `backend/polygon_feed.py` uses Polygon API, but ONLY `/v2/aggs/ticker/I:VIX/range/1/day` (line 706) and `/v2/aggs/ticker/I:SPX/prev` (line 525, 831) — daily aggregates and prev-day endpoints. No 1-minute historical fetch exists. Polygon API supports `/range/1/minute/...` but no current code path uses it. | **partial — historical 1-min is a NEW capability** |
| Spec §1 line 47 (`Tradier: archived option chains / marks / greeks if stored`) | `backend/tradier_feed.py` (327 lines) fetches live chains for active sessions; no archive logic. `grep -rln "archived_chain\|chain_snapshot\|option_chain_archive\|trading_market_archive" backend/ supabase/migrations/` returns **zero matches**. No `tradier_chain_archive` table in 68 migrations. | **absent — HARD prerequisite missing** |
| Spec §1 line 52 (`Databento: historical OPRA replay / GEX / flow reconstruction`) | `backend/databento_feed.py` (447 lines) writes `databento:opra:trades`, `databento:opra:gex_block`, `databento:opra:confidence_impact` to Redis with 300s TTL (cross-cutting matrix §6 lines 656–658). Redis values expire — no historical archive. | **absent — Redis-only, not replay-safe** |
| Spec §1 line 57 (`Redis archives: only if Redis briefs were durably copied to Supabase`) | Some Redis briefs are mirrored: `trading_ai_briefs` table exists (migration `20260427_trading_ai_briefs.sql:25`) with one row per `brief_kind` (calendar/macro/flow/sentiment/synthesis). However, this stores ONLY the latest brief per kind (PRIMARY KEY on `brief_kind`), not a time-series. Replay over historical briefs is impossible from this table. | **partial — latest-only, not time-series** |

**Closest-existing-logic file (NOT cited by spec but architecturally relevant):**

| File | Lines | Function | Replay Harness relationship |
|---|---|---|---|
| `backend/shadow_engine.py` | 456 | Forward-time A/B comparison (Portfolio A rule-based vs Portfolio B AI). Writes per-cycle to `shadow_predictions` table; EOD compares to `trading_sessions` and writes to `ab_session_comparison` table with simplified iron-condor synthetic P&L (`a_synthetic_pnl = 120 / -50 / -300` based on `move_pct` thresholds — line 311–319, "Rough by design — adequate for 90-day A/B comparison"). | **DIFFERENT MECHANISM.** Forward-time, not historical. Synthetic P&L approximated, not chain-replayed. Does NOT satisfy spec §1's "no theoretical pricing" rule. **No table or Redis namespace overlap with proposed `replay_eval_*` / `replay:*`.** Could share decision-card *concept* (B-AI-001-8 in AI-SPEC-001 §10.2 references "≥200 replay/advisory decision cards" — ambiguous whether `shadow_predictions` rows count). |
| `backend/scripts/backtest_gex_zg.py` | 470 | One-shot historical backtest of GEX/ZG signals on 2022–2023 SPX 0DTE. Reads `backend/data/historical/options_features.parquet` and `spx_daily.parquet`. Approximates entry credit as `ATM_IV × spread_width × sqrt(1/252) × 0.5` (line 19–20 docstring). | **NOT calibration-grade per Spec §1.** Uses theoretical pricing approximations; spec §1 line 49 is explicit: "No archived chain = no calibration-grade option pricing replay." Additionally, `backend/data/historical/` directory exists but is **empty** (verified by `ls -la backend/data/historical/` returning 2 entries — `.` and `..`). Script cannot execute today even on its own approximation basis. |

### 3.2 Supabase Schema References

#### Tables proposed by Spec §4 — all four absent at HEAD

Verified by `grep -rln "<table>" supabase/migrations/` against 68 migration files (count confirmed by `ls supabase/migrations/ | wc -l = 68`):

| Table | Spec section | Status at HEAD | Verification |
|---|---|---|---|
| `replay_eval_runs` | Spec §4 lines 348–382 | **absent** | Zero matches across 68 migrations. Confirmed by evidence pack §7.2 line 364. |
| `replay_eval_cases` | Spec §4 lines 388–432 | **absent** | Zero matches. Evidence pack §7.2 line 365. |
| `replay_eval_results` | Spec §4 lines 442–457 | **absent** | Zero matches. Evidence pack §7.2 line 366. |
| `item_promotion_records` | Spec §4 lines 465–498 | **absent** | Zero matches. Evidence pack §7.2 line 356. Cross-cutting matrix §5 lines 565–574 confirms multi-spec interest (Items 1, 4, 12, 13). |

#### Existing tables Item 4 reads from — verification of column compatibility

| Table | Spec assumes | Reality at HEAD | Status |
|---|---|---|---|
| `trading_positions` | Read for closed-trade replay (Spec §1 line 34, §2 Test A line 174, §2 Test D line 220–222) | Exists at `20260416172751_*.sql:160`. PK is `id UUID` (not `position_id`). Has `entry_at`, `exit_at`, `entry_credit`, `exit_credit`, `gross_pnl`, `slippage_pct` columns — sufficient for spec's Pricing Reconstruction Test A. | **landing OK** |
| `trading_prediction_outputs` | Read for prediction baseline + counterfactual data (Spec §1 line 35) | Exists. Has `counterfactual_pnl`, `counterfactual_strategy`, `counterfactual_simulated_at` columns (per `20260421_add_counterfactual_pnl.sql:8–14`) — column-shaped, NOT table-shaped (PRE-P11-4 carry-forward applies). | **landing OK on existing columns; table-vs-column conflict delegated to AI-SPEC-002 `C-AI-002-2` and AI-SPEC-010 future audit** |
| `trading_sessions` | Read for session-level baselines (Spec §1 line 33) | Exists at `20260416172751_*.sql:14`. Has `session_date`, `virtual_pnl`, `virtual_trades_count` etc. | **landing OK** |
| `strategy_attribution` | Read for utility-aware labels and outcome enums (Spec §1 line 36, §12 line 1068 — "training accessors require calibration_eligible = true / simulation_status = calibration_grade") | **DOES NOT EXIST.** Item 2 is the producer, audited as AI-SPEC-002 P1.3.2 with `B-AI-002-1` (engine missing) + `B-AI-002-2` (table missing). | **blocked on AI-SPEC-002 ship** |
| `trade_counterfactual_cases` | Read for counterfactual case integration (Spec §1 line 37) | **DOES NOT EXIST as a table.** PRE-P11-4 carry-forward + AI-SPEC-002 `C-AI-002-2` document Item 10's existing scaffold is column-shaped on `trading_prediction_outputs`. | **blocked on AI-SPEC-002 + AI-SPEC-010 disposition** |
| `ai_governor_decisions` | Read for Governor decision history (Spec §1 line 38) | **DOES NOT EXIST.** AI-SPEC-001 `B-AI-001-4` proposed canonical name; awaiting Item 1 ship. | **blocked on AI-SPEC-001 ship** |
| `paper_phase_criteria` | (Not directly cited by Item 4 spec, but cross-cutting matrix §5 line 558 flags as a touchpoint — "Replay Harness may add a 'replay validation' criterion") | Exists at `20260417000001_paper_phase_criteria.sql:5–21`. 12 GLC rows per D-013, status enum `('not_started','in_progress','passed','failed','pending','blocked')`. NO `authority_level` field, NO `replay_run_id` field. | **landing OK; coordination question — see §10.3 C1** |
| `trading_calibration_log` | (Spec implies via Spec §10 ongoing schedule + matrix §5 line 547 — "AI-SPEC-005 / AI-SPEC-006 / AI-SPEC-013 write retrain events"; Item 4 likely writes promotion events too) | Exists at `20260416172751_*.sql:392`. Append-only. | **landing OK** |

### 3.3 Redis Key References

Item 4's spec does not name a specific `replay:*` Redis namespace. Cross-cutting matrix §3 line 168 marked it `None at HEAD; potential new namespace per spec ('replay:*', TBD)`. Verified by `redis-cli` namespace inventory in evidence pack §10:

| Spec assumption | HEAD reality | Status |
|---|---|---|
| `replay:*` (proposed by spec implicitly) | **No `replay:*` keys at HEAD.** Evidence pack §10.2 inventory has no `replay:*` entries. `databento:opra:*`, `gex:*`, `polygon:*`, `strategy_matrix:*`, `risk:*`, `capital:*`, `model:meta_label:*`, `feedback:counterfactual:*`, `strategy:*:enabled`, `ai:*` are the only existing namespaces. | **proposed-only — clean** |
| Spec §1 line 57–60 ("Redis archives: only if Redis briefs were durably copied to Supabase / raw Redis TTL state is NOT replay-safe") | Confirmed: `gex:net`, `gex:nearest_wall`, `gex:flip_zone`, `gex:by_strike`, `gex:confidence` have **no TTL** (matrix §6 lines 597–601), but their values overwrite each cycle — there is no time-series archive. `polygon:spx:realized_vol_20d` has 86400s TTL (matrix §6 line 612). `databento:opra:*` keys have 300s TTL (matrix §6 line 657–658). All values are *current* values, not history. Spec is correct: "raw Redis TTL state is NOT replay-safe." | **spec correctly identifies a constraint** |

### 3.4 Commit Hash References

Spec is pure forward-design and cites no commit hashes. Mark as **n/a — pure future design** per template §3.4 guidance.

The audit references the following commits for context (verified via `git log --oneline`):

| Commit | Subject | Relevance |
|---|---|---|
| `b0bcdaa` | docs(ai-arch): P1.3.2 - audit AI-SPEC-002 (Strategy Attribution) (#62) | Audit HEAD anchor. AI-SPEC-002's findings cascade into Item 4 (which reads from `strategy_attribution`). |
| `f456922` | docs(ai-arch): P1.3.1 - audit AI-SPEC-001 (AI Risk Governor) (#60) | AI-SPEC-001's `B-AI-001-4` (canonical `ai_governor_decisions` name) and `B-AI-001-8` (≥200 decision cards gate) cascade into Item 4. |
| `bf41175` | feat(ml): Loop 2 meta-label model scaffold (12K) | Item 6 dormant scaffold — Item 4 ultimately validates Item 6 promotion. Confirms `model_retraining.py` + `execution_engine.py` paths. |

---

## 4. Existing Partial Implementation (verified by Cursor)

Per `AI_ARCH_EVIDENCE_PACK.md` §8 Item 4 (lines 405–408): **NOT YET IMPLEMENTED.** No `backend/replay_*.py` files; no `replay_eval_*` migrations.

**Closest-existing-logic surfaces** (architecturally adjacent but mechanically distinct):

1. **`backend/shadow_engine.py` (456 lines)** — Phase 3B forward-time A/B comparison. Writes one `shadow_predictions` row per cycle (line 73), one `ab_session_comparison` row per session date (line 337). Synthetic P&L is approximated by an iron-condor heuristic table (`a_synthetic_pnl = 120 / -50 / -300` based on `move_pct < 0.005 / 0.010 / else`, line 314–319). The 90-day A/B gate logic at `get_ab_gate_status()` (line 359–456) tracks `days_elapsed >= 90 AND closed_trades >= 100 AND b_lead >= 8.0` — this is the D-013 90-day A/B gate, NOT Item 4's per-item promotion gate. Mechanism:
   - Forward-time, runs daily during paper trading
   - No chain replay, no point-in-time reconstruction
   - Synthetic P&L explicitly "rough by design" (docstring line 263)
   - **Does NOT satisfy any of Spec §2 Step 0 binary gates** (Test A pricing within $0.10 of Commit-4-corrected re-marked value, Test B SPX path 99% bars match, Test C VIX correlation > 0.99, Test D slippage median absolute error < $0.10)
   - Implication for B-AI-001-8 / Spec §12: Item 1's V0.2 paper-binding promotion requires "≥200 replay/advisory decision cards." Whether shadow_engine.py's `shadow_predictions` rows count toward this or only Item 4's `replay_eval_cases` rows count is **ambiguous in spec §12 wording**. Cross-spec implication captured as `C-AI-004-2` / cross-spec theme.

2. **`backend/scripts/backtest_gex_zg.py` (470 lines)** — One-shot historical backtest harness of GEX/ZG signals on 2022–2023 SPX 0DTE data. Architecturally a precursor of Item 4 but **not calibration-grade**:
   - Reads `backend/data/historical/options_features.parquet` and `backend/data/historical/spx_daily.parquet` (file paths declared at line 29–30, also line 47–48)
   - **The input parquet files do not exist:** `ls -la backend/data/historical/` returns an empty directory (only `.` and `..`). Verified at HEAD. Script cannot execute today.
   - Approximates option pricing: `entry_credit = ATM_IV × spread_width × sqrt(1/252) × 0.5` (docstring line 19–21)
   - Uses theoretical pricing — exactly what Spec §1 line 49 forbids ("Hard Rule: No Theoretical Pricing — No archived chain = no calibration-grade option pricing replay")
   - Hard-coded thresholds + fixed commission ($1.40/contract/4-leg) + fixed slippage ($0.10) — not driven by replay-estimated slippage model per Spec §2 Test D
   - **Implication:** Item 4's `replay_threshold_optimizer.py` should NOT extend this script — it should replace it. Document as Class B "scheduled deprecation" rather than "scheduled extension." See §10.2 B5.

3. **`backend/tests/` test suite** — Unit tests, not historical replay. No `test_replay_*` files at HEAD. `test_b2_backtest.py` (62 lines) and `test_backtest_gex_zg.py` (87 lines) test the deprecated `backtest_gex_zg.py` script's helper functions in isolation.

4. **`paper_phase_criteria` table** (existing) — partially overlaps with `item_promotion_records` proposal but operates at a different granularity. See §10.3 C1.

5. **Polygon feed** — `backend/polygon_feed.py` (956 lines) supports `/range/1/day` for VIX backfill and `/aggs/ticker/I:SPX/prev` for prev-day SPX. Polygon API supports `/range/1/minute/{from}/{to}` historical 1-min bars (per Polygon docs), but **no current code path uses this**. Spec §1 line 43 requires "Polygon SPX / I:SPX historical 1-min bars" — this is a **NEW capability** Item 4 must add. May require Polygon paid-tier subscription (operator question; out of scope for this audit beyond flagging).

6. **News/event ingestion** — `backend_agents/economic_calendar.py`, `backend_agents/sentiment_agent.py`, `backend/main.py` synthesis pipeline write to `trading_ai_briefs` (one row per `brief_kind`, latest-only) and Redis (`ai:macro:brief`, `ai:flow:brief`, `ai:sentiment:brief`, `ai:synthesis:latest`). **No `published_at` field anywhere** — only `generated_at` (when WE generated the brief). `earnings_calendar` table has only `earnings_date DATE` and `announce_time TEXT` ('pre' / 'post' / 'unknown'). Spec §1 line 45 ("news/events only if published_at <= replay timestamp") and §5 Timestamp Boundary line 609 ("news where published_at <= T") cannot be enforced at minute-level granularity at HEAD. Class B finding — see §10.2 B6.

---

## 5. The Ten Audit Dimensions

Per `_template.md` §5. Each dimension records a falsifiable claim about Item 4's spec vs HEAD. Cross-cutting matrix §3 AI-SPEC-004 block (lines 158–175) is the starting point; per-item depth added below.

| # | Dimension | Finding | Source |
|---|-----------|---------|--------|
| 1 | File/module exists | **NO.** Eight `backend/replay_*.py` files (Spec §4 lines 532–554) absent at HEAD. Closest-existing surfaces: `shadow_engine.py` (forward A/B, different mechanism) and `scripts/backtest_gex_zg.py` (470-line approximation script with empty input data dir). | §3.1 + Evidence pack §8 Item 4 |
| 2 | DB table/column | **NO.** Four proposed tables (`replay_eval_runs`, `replay_eval_cases`, `replay_eval_results`, `item_promotion_records`) absent. Read-side dependencies on `strategy_attribution` (Item 2 deliverable, blocked) and `ai_governor_decisions` (Item 1 deliverable, blocked) and `trade_counterfactual_cases` (Item 10 column-vs-table dispute) further compound. | §3.2 + AI-SPEC-001 `B-AI-001-4` + AI-SPEC-002 `B-AI-002-2` / `C-AI-002-2` |
| 3 | Redis keys | **NO `replay:*` keys at HEAD.** Spec correctly identifies that raw Redis TTL state is not replay-safe. New namespace introduction is clean (no conflict). | §3.3 |
| 4 | Current behavior matches spec | **NO.** Forward-time A/B (`shadow_engine.py`) and approximation backtest (`scripts/backtest_gex_zg.py`) are mechanically distinct from offline calibration-grade replay. Neither satisfies Spec §2 Step 0 binary gates. | §4 + cross-cutting matrix §3 line 169 |
| 5 | Future design? | **YES — proposed, not existing.** | Evidence pack §8 Item 4. |
| 6 | Governance conflict | **POTENTIAL — `paper_phase_criteria` vs `item_promotion_records` authority overlap.** Both gate "promotion" but operate at different granularities (paper-go-live system gate vs per-item authority promotion). Spec is silent on coordination. See §10.3 C1. Also: T-Rule 2 (Governance Documents Are Authoritative) — item_promotion_records becomes a NEW gate authority that must be cross-referenced from D-013 (paper phase) and any future D-XXX governing per-item authority (see C-AI-001-1 / C-AI-001-2 / C-AI-001-3 D-023 disposition). | constitution.md T-Rule 2; matrix §3 line 171; §10.3 C1 |
| 7 | Authority level proposed | **advisory for replay results; binding for `item_promotion_records` records that downstream items read at startup.** Spec §4 line 521–525: "Items 1, 5, 6 read item_promotion_records at startup. If no current record exists for an item/scope: default to advisory or disabled, NEVER production." Architecturally clean. | Spec §4 lines 521–525; matrix §3 line 172 |
| 8 | Calibration dependencies | **CRITICAL.** Item 4 has a **HARD architectural prerequisite**: archived option-chain data (Spec §1 line 49 "No archived chain = no calibration-grade option pricing replay"). At HEAD, `tradier_feed.py` does NOT persist chains, no `tradier_chain_archive` migration exists, `databento:opra:*` keys are 300s-TTL Redis. Cross-cutting matrix §6 line 660: "Item 4 (Replay Harness) needs an archive of these data outside Redis to replay over historical OPRA flow." Calendar implication: chain-archive backfill is months-long if it must accumulate forward; if Tradier offers historical chain data via API, that becomes a contract dependency (paid tier? operator question). **This dimension alone may move risk rating to CRITICAL.** | §3.1 + §3.2 + §6 + matrix §6 |
| 9 | Training contamination risk | **HIGH on archive completeness; LOW on production-leakage given structural enforcement.** Two distinct risks: (a) Replay correctness depends on chain-archive fidelity — missing strikes/expiries silently corrupt eval results (matrix §3 line 174). Mitigated by `reconstruction_status = 'quote_incomplete'` + `calibration_eligible = false` (Spec §1 line 88–90). (b) Production-leakage: replay cases entering production case memory. **Mitigated structurally** by CHECK constraints `replay_eval_runs.environment = 'research'` (Spec §4 line 359) + `replay_eval_cases.environment = 'research'` (line 428) + default `retrieval_enabled = false` (line 429). Strong DB-level enforcement, not application convention. | §3.2 + Spec §4 lines 358–435 + Spec §12 Item 3 Conflict resolution lines 1058–1062 |
| 10 | Implementation owner | Cursor. | T-Rule 1 (Foundation Isolation) |

---

## 6. Missing Pieces

What the spec assumes exists but doesn't, at HEAD `b0bcdaa`. Each missing piece is also represented in §10.2 (Class B) or §10.3 (Class C) with proposed correction.

| # | Spec assumption | Reality | §10 reference |
|---|-----------------|---------|---------------|
| M1 | 4 new tables (`replay_eval_runs`, `replay_eval_cases`, `replay_eval_results`, `item_promotion_records`) with full DDL — Spec §4 | Absent from 68 migrations. | B1 |
| M2 | 8 `backend/replay_*.py` files — Spec §4 lines 532–554 | Absent from `backend/`. | B2 |
| M3 | Archived option-chain substrate — Spec §1 line 47, "Hard Rule: No Theoretical Pricing" line 62–66 | No archive logic in `tradier_feed.py`; no `tradier_chain_archive` migration; `databento:opra:*` Redis keys are 300s-TTL. **HARD prerequisite.** | B3 (HIGH) |
| M4 | Polygon historical 1-min bar fetch capability — Spec §1 line 43 | `polygon_feed.py` only uses `/range/1/day`. Polygon API supports 1-min via `/range/1/minute/{from}/{to}` but no caller. May require paid tier (operator question). | B4 |
| M5 | News/event `published_at` (vs `ingested_at`) field — Spec §1 line 45, §5 line 609 | No `published_at` anywhere. `trading_ai_briefs.generated_at` is when WE generated. `earnings_calendar.earnings_date DATE` is date-level only. | B6 |
| M6 | `strategy_attribution` table reads — Spec §1 line 36 + §12 Item 2/10 Conflict line 1064–1068 | Item 2 deliverable; absent at HEAD per AI-SPEC-002 P1.3.2 audit. | B7 (FK cascade) |
| M7 | `ai_governor_decisions` table reads — Spec §1 line 38 | Item 1 deliverable; absent at HEAD per AI-SPEC-001 P1.3.1 audit. | B7 (FK cascade) |
| M8 | `trade_counterfactual_cases` table reads — Spec §1 line 37 | PRE-P11-4 carry-forward: existing scaffold is column-shaped on `trading_prediction_outputs`. AI-SPEC-002 `C-AI-002-2` operator decision required. | B8 (defers to AI-SPEC-002 / AI-SPEC-010 disposition) |
| M9 | Decision card schema specification — implicit in Spec §4 lines 388–432 (`replay_eval_cases.governor_output JSONB / item5_snapshot / item6_output / market_state_card / baseline_action / candidate_action / realized_outcome` all JSONB) | Spec gives column shapes but does not formalize the JSON sub-schemas (e.g., what fields inside `governor_output` JSONB? what fields inside `market_state_card`?). Cross-spec implication: AI-SPEC-001 §12 V0.2 promotion gate requires "≥200 replay/advisory decision cards" — Item 4 produces these cards, but the count contract is ambiguous (does shadow_engine.py count? only Item 4? are advisory and replay separate?). | B9 + §10.3 C2 |
| M10 | LightGBM model artifact daily logging — Spec §3 lines 306–336, §5 line 686 ("Going forward: log model artifacts daily") | At HEAD, `model_retraining.py` (12K) trains models in-process; no artifact-log table or model-versioning surface enforces "daily artifact + prediction outputs" persistence. Item 4 spec assumes this going forward but does not specify the artifact-log substrate. | B10 |
| M11 | Walk-forward implementation (rolling 60/20/20 split, step 10 sessions) — Spec §6 lines 698–703 | Absent. (Distinct from `scripts/backtest_gex_zg.py`'s one-shot 2022–2023 sweep.) | Bundled into B2 (`replay_threshold_optimizer.py` / `replay_validator.py`) |
| M12 | Step 0 validation tests (4 binary checks: Pricing within $0.10 / SPX 99% bars match / VIX correlation > 0.99 / Slippage median absolute error < $0.10) — Spec §2 lines 168–229 | Absent. | Bundled into B2 (`replay_validator.py`) |
| M13 | `paper_phase_criteria` integration disposition — cross-cutting matrix §5 line 558 | Spec is silent on whether `paper_phase_criteria` should add a "GLC-013 Replay Validation" criterion or remain independent. | §10.3 C1 |
| M14 | Coordination with AI-SPEC-001 D-023 wording on per-item authority promotion — implicit cross-spec | Spec §4 lines 521–525 documents the "default to advisory or disabled, NEVER production" startup contract, but does not align with D-023's pending wording (proposed in AI-SPEC-001 §11 + AI-SPEC-002 P1.3.2 §11 addendum). | §10.3 C3 |

---

## 7. Contradictions

**(First-pass for Claude to refine.)**

### 7.1 Internal Contradictions

| # | Claim A | Claim B | Tension |
|---|---------|---------|---------|
| I1 | Spec §2 Step 0 line 234: "no downstream calibration runs" if reconstruction validation fails | Spec §10 Pre-V0.1 Failure Mode lines 985–989: "If the replay harness cannot produce calibration-grade evidence: V0.1 ships advisory only / All items default to authority_level = 'advisory' or 'disabled'" | No internal contradiction — the second is the consequence of the first. **NOT a contradiction; consistency note.** |
| I2 | Spec §2 line 244: "Item 5 features feed Items 6 and 1" → ordered as (Step 1) Item 5, (Step 2) Item 1, (Step 3) Item 6 | Matrix §7 line 673: "AI-SPEC-001 (Risk Governor) → depends on → AI-SPEC-002 (attribution for sizing inputs)" — Item 1 needs Item 2 too | **NOT a contradiction.** Item 1 needs both Item 2 (attribution for outcome labels) and Item 4-derived Item 5 features (vol fair-value inputs to risk_score). Both are upstream. Spec's calibration-order claim is about *threshold tuning order within Item 4*, not architectural dependency order. |
| I3 | Spec §1 line 28: "Item 4 is the promotion court" — implies Item 4 is the binding authority | Spec §6 line 734: "Critical: 'Full production eligibility' does NOT mean automatic production. The item still must pass its own promotion gates. Item 4 is the promotion court, not a rubber stamp." | **NOT a contradiction.** Spec is internally consistent — Item 4 is the empirical authority but it gates ON the per-item criteria, not by fiat. Worth flagging as a clarity strength of the spec. |

**Net:** No material internal contradictions in the spec itself. Spec is internally well-formed.

### 7.2 Cross-Spec Contradictions

| # | Item 4 says | Other spec says | Resolution |
|---|-------------|-----------------|------------|
| X1 | Spec §1 line 38: reads from `ai_governor_decisions` table | AI-SPEC-001 P1.3.1 audit `B-AI-001-4`: "No table at HEAD. Spec defines the row shape; persistence target name should be set in TASK_REGISTER §14A.2. Recommended canonical name: `ai_governor_decisions`." | **Compatible.** Both audits agree on the canonical name. Sequencing: Item 1's migration must land before Item 4 can read this table. Captured as B-AI-004-7 (FK cascade). |
| X2 | Spec §1 line 36: reads from `strategy_attribution` table | AI-SPEC-002 P1.3.2 audit `B-AI-002-2`: table absent at HEAD; Item 2 ships it as part of V0.1 scaffold | **Compatible.** Sequencing: Item 2's migration must land before Item 4 can read. Captured as B-AI-004-7 (FK cascade). |
| X3 | Spec §1 line 37: reads from `trade_counterfactual_cases` table | AI-SPEC-002 P1.3.2 audit `C-AI-002-2`: existing Item 10 scaffold is column-shaped (`counterfactual_pnl` columns on `trading_prediction_outputs`), not table-shaped. Operator decision required between three options. | **Awaiting operator decision on `C-AI-002-2`.** If option 2 is chosen (Item 2 + Item 4 reference existing column-shaped scaffold), Item 4's spec wording at §1 line 37 needs to update to reference `trading_prediction_outputs.counterfactual_*` columns. Captured as B-AI-004-8 (cross-spec sequencing). |
| X4 | Spec §12 Item 3 Conflict line 1056–1062: "Replay cases must NOT enter production synthetic memory. Resolution: replay_eval_cases only / environment = 'research' (CHECK constraint) / retrieval_enabled = false (default)" | AI-SPEC-003 (Synthetic Counterfactual, future P1.3.X audit): generates synthetic cases for live retrieval | **Compatible.** Spec's structural enforcement (CHECK constraint + default) is precisely the boundary mechanism. Item 3's audit will need to verify its retrieval queries respect the boundary (`WHERE environment = 'production' AND retrieval_enabled = true AND case_available_at <= :as_of_timestamp` per Spec §5 lines 651–655). |
| X5 | Item 4's `replay_eval_cases.governor_output` / `item5_snapshot` / `item6_output` JSONB columns assume Items 1, 5, 6 produce structured outputs Item 4 can capture | AI-SPEC-001 §3.B `GovernorDecisionRecord` row shape (proposed, see B-AI-001-4) — Item 4 must capture this shape. AI-SPEC-005 / AI-SPEC-006 specs (future audits) will define their respective output shapes. | **Compatible in principle, but requires bilateral schema confirmation.** Item 4's spec does not formalize the JSONB sub-schemas — see §10.2 B9 + §10.3 C2 (decision card schema ambiguity). |
| X6 | Item 4 produces "≥ 200 replay/advisory decision cards" toward AI-SPEC-001 §12 V0.2 paper-binding gate — AI-SPEC-001 audit `B-AI-001-8` | AI-SPEC-001 §12 wording is ambiguous between "replay" and "advisory" cards; whether `shadow_engine.py`'s `shadow_predictions` rows count toward the 200 is unclear | **Cross-spec ambiguity.** Spec §4 lines 388–432 defines `replay_eval_cases` as the canonical card surface for replay; `shadow_predictions` is a different table for forward A/B. Resolution: D-023 wording (see AI-SPEC-001 §11 + AI-SPEC-002 §11) should clarify "decision cards" = `replay_eval_cases.calibration_eligible = true`. Captured as `C-AI-004-2` (D-023 enrichment). |

### 7.3 Governance Contradictions

| # | Spec claim | Governance rule | Tension |
|---|------------|-----------------|---------|
| G1 | Spec §4 line 465–498: `item_promotion_records` is a per-item authority-level enum (`production / reduced / advisory / diagnostic_only / disabled`) that Items 1, 5, 6 read at startup | D-013 Paper Phase mandates a 12-criterion gate for paper-to-live transition (paper_phase_criteria seeds GLC-001 through GLC-012); T-Rule 9 mandates 45-day paper minimum with 12 GLC criteria | **Coordination question, not contradiction.** Both gates can coexist: `paper_phase_criteria` is a system-level "is paper phase complete?" gate; `item_promotion_records` is per-item "what authority does this item have?" `paper_phase_criteria.GLC-005` (Sharpe ≥ 1.5) is not the same as `item_promotion_records.governor_v1.short_gamma_veto.authority_level = 'production'`. Resolution: spec must explicitly state these are independent, or operator approves a unified gate model (e.g., add `GLC-013: Replay Validation Complete` as a 13th criterion, then `item_promotion_records` becomes a sub-detail Item 4 writes when GLC-013 passes). See §10.3 C1. |
| G2 | Spec §4 line 521–525: "If no current record exists for an item/scope: default to advisory or disabled, NEVER production." | T-Rule 4 (Locked Decisions Are Final) + D-014 (Position Sizing) + AI-SPEC-001 `C-AI-001-1` D-023 placeholder for AI authority boundary | **Aligned.** Item 4's startup-read contract is precisely the kind of architectural constraint D-023 should ratify. See §10.3 C3 (D-023 enrichment). |
| G3 | Spec §10 Pre-V0.1 Failure Mode lines 985–989: "If the replay harness cannot produce calibration-grade evidence: V0.1 ships advisory only" | T-Rule 9 (Paper Phase Is Mandatory) + system-state.md `live_trading: blocked_until_90day_AB_test_passes` | **Aligned.** Both say live trading is gated; spec adds the per-item layer ON TOP of D-013. No conflict. |

---

## 8. Carry-Forward Findings From P1.1 / P1.2 + P1.3.2 New Themes

For Item 4, evaluating the 5 P1.1/P1.2 carry-forwards + the 4 new themes that emerged in P1.3.2.

| # | Finding | Yes/No for AI-SPEC-004 | Implication |
|---|---------|-----------------------|-------------|
| 1 | `gex:updated_at` consumer-only orphan (PRE-P11-1) | **NO.** Item 4 does not gate on Redis freshness — it reconstructs from archived data. | n/a |
| 2 | `gex:atm_iv` consumer-only orphan (PRE-P11-2) | **NO.** Same rationale. | n/a |
| 3 | Debit-spread feature flag missing (PRE-P11-7) | **YES, indirectly.** Spec §9 Strategy Sample Size Tiers groups `debit_call_spread`, `debit_put_spread`, `long_call`, `long_put` as `directional_debit`. The strategy-class taxonomy theme (now confirmed in 2 audits: AI-SPEC-001 + AI-SPEC-002) confirms: Item 4 must use `debit_call_spread` / `debit_put_spread` (matching `risk_engine.py:105–106` and migration `20260419_add_strategy_types.sql:11–22`), NOT `bull_debit_spread` / `bear_debit_spread`. **Item 4's spec already uses the canonical names** (Spec §9 line 916) — no correction needed; carry-forward is silently honored. Strengthens cross-spec theme to "confirmed in 3 audits." |
| 4 | `_safe_redis()` dead code (PRE-P11-3) | **NO.** Item 4 is offline replay over historical data; no live freshness gate. | n/a |
| 5 | `counterfactual_pnl` column-not-table (PRE-P11-4) | **YES, HIGH-IMPACT.** Spec §1 line 37 references `trade_counterfactual_cases` as a table. PRE-P11-4 + AI-SPEC-002 `C-AI-002-2` document Item 10's existing scaffold is column-shaped on `trading_prediction_outputs`. Item 4 inherits the table-vs-column dispute through its read dependency. Cross-spec coordination required — see §10.2 B8. |
| **P1.3.2-T1** | **FK dependency cascade** (new theme from P1.3.2) | **YES.** Item 4 has FK / read dependencies on `ai_governor_decisions` (Item 1, blocked), `strategy_attribution` (Item 2, blocked), `trade_counterfactual_cases` (Item 10 disputed), and Items 5/6 decision tables (future P1.3.5/P1.3.6 audits). Captured as B-AI-004-7. |
| **P1.3.2-T2** | **`closed_trade_path_metrics` substrate gap** (new theme from P1.3.2) | **YES, indirectly.** Item 4 reads path metrics during reconstruction (Spec §2 Step 0 Test A, §2 Step 1 Item 5 Vol calibration likely needs path metrics for vol-edge validation). AI-SPEC-002 `B-AI-002-2` documents the substrate is missing entirely. Item 4's reconstruction quality is bounded by AI-SPEC-002 V0.1 ship scope on path metrics. Captured as B-AI-004-9. |
| **P1.3.2-T3** | **`decision_outcome` enum coordination** (new theme from P1.3.2) | **YES.** Item 4's `replay_eval_cases` rows must encode decision outcomes consistently with Item 2's `decision_outcome` enum (8 values: `opened_traded`, `blocked_governor`, `blocked_meta_labeler`, `blocked_adversarial`, `skipped_rules`, `blocked_constitutional`, `halted_blocked_cycle`, `synthetic_case`). Item 4's `replay_eval_cases.realized_outcome JSONB` (Spec §4 line 408) must internally use this enum. Captured as B-AI-004-10. |
| **P1.3.2-T4** | **Legacy `attribution_*` BOOLEAN columns on `trading_positions`** (new theme from P1.3.2) | **NO.** Item 4 reads `trading_positions` for closed-trade replay but does not interact with the dead `attribution_*` columns. Disposition is bilateral with AI-SPEC-002 + AI-SPEC-009 / AI-SPEC-010 / AI-SPEC-011, not Item 4. | n/a |

---

## 9. Risk Rating

**Risk:** **CRITICAL**

**Rationale:**

1. **Hard prerequisite gap (chain archive).** Spec §1 line 49 makes calibration-grade replay impossible without archived option chains. At HEAD, no chain archive exists — `tradier_feed.py` does not persist chains, no `tradier_chain_archive` migration in 68 migrations, `databento:opra:*` keys are 300s-TTL Redis. This is not a coding task; it's a months-of-data-collection task (forward archival) or a contract negotiation (paid Tradier/Databento historical chain access). V0.1 timeline cannot guarantee calibration-grade replay until this is resolved.

2. **FK / read cascade on un-shipped specs.** Item 4 reads from 3 tables that don't exist at HEAD (`strategy_attribution` / Item 2; `ai_governor_decisions` / Item 1; `trade_counterfactual_cases` / Item 10 disputed). Sequencing: Item 4 cannot reach calibration-grade without these, but Items 1, 5, 6 cannot be promoted to binding authority without Item 4 — making the V0.1 critical path fragile.

3. **Impact if delayed.** Item 4 is the **second most-depended-on item** in Cluster A. Items 1, 5, 6 require Item 4 for promotion to binding (per AI-SPEC-001 P1.3.1 `B-AI-001-8`). Items 3, 6, 13 require replay-validated baselines. If Item 4 V0.1 ships only as scaffolding (failure mode per Spec §10 lines 985–989), the entire system defaults to `authority_level = 'advisory' or 'disabled'` — a major calendar slip relative to the V0.1 plan.

4. **Mitigation strength.** The spec itself is well-formed (no internal contradictions; structural research-vs-production isolation via DB CHECK constraints; explicit failure mode that defaults to advisory). The risk is not the spec design — the risk is the data substrate underneath it.

**Comparison with prior audits:**

| Audit | Risk rating | Primary driver |
|---|---|---|
| P1.3.1 AI-SPEC-001 (Risk Governor) | HIGH | LLM authority + 3 Class C escalations |
| P1.3.2 AI-SPEC-002 (Strategy Attribution) | HIGH | FK cascade + substrate gaps |
| **P1.3.3 AI-SPEC-004 (Replay Harness)** | **CRITICAL** | **Hard prerequisite (chain archive) + FK cascade on Items 1, 2, 10** |

---

## 10. Spec Corrections Required

Per `CONSOLIDATED_PLAN_v1.2_APPROVED.md` §3, three correction classes.

### 10.1 Class A — Mechanical Errors

**Cursor primary ownership.** Mechanical wrongness verified against repo at HEAD. Rubber-stamped at end of audit phase (Gate 1).

| # | Spec Section | Spec Says | Correct Value | Source of Truth |
|---|--------------|-----------|---------------|----------------|
| (none) | — | — | — | — |

**No Class A corrections.** Item 4's spec is pure forward-design and does not cite specific `backend/<file>.py:NN` line numbers, table primary-key column names, or other mechanically verifiable constants that could drift from repo reality. The cross-cutting findings around `paper_phase_criteria` schema location, `trading_positions` PK name, `counterfactual_pnl` table-vs-column shape, and decision-table canonical names are all captured as Class B (implementation-status drift) or Class C (architectural-intent decisions) below.

(Per `CONSOLIDATED_PLAN_v1.2_APPROVED.md` §3, Class A captures wrong file paths, stale line numbers, wrong counts, naming inconsistencies that are mechanically verifiable. Item 4's wording uses generic phrases like "model/version tables" rather than naming specific tables that could be wrong; reads from `trading_positions` are FK-shape-correct since spec doesn't write the SQL itself.)

### 10.2 Class B — Implementation Status / Content Omissions

**(First-pass for Claude/GPT to refine; operator approves consolidated list, not per-correction.)**

| # | Spec Section | Spec Says | Reality | Proposed Correction |
|---|--------------|-----------|---------|--------------------|
| B1 | Spec §4 lines 348–498 + §13 V0.1 Ship Scope items 1–4 | 4 new tables (`replay_eval_runs`, `replay_eval_cases`, `replay_eval_results`, `item_promotion_records`) with full DDL | All 4 absent from 68 migrations at HEAD. Verified by `grep -rln "<table>" supabase/migrations/`. | No correction to spec wording — tag as "scheduled buildout"; clarify in Spec §13 that Item 4's V0.1 scope must include the 4 migrations and that `item_promotion_records` should be seeded with default `'advisory' or 'disabled'` rows for Items 1, 5, 6 at first-time deploy (per Spec §4 line 521–525). |
| B2 | Spec §4 lines 532–554 + §13 V0.1 Ship Scope items 5–12 | 8 `backend/replay_*.py` files (`replay_harness.py` orchestrator, `replay_data_reconstructor.py`, `replay_feature_builder.py`, `replay_decision_stack.py`, `replay_threshold_optimizer.py`, `replay_leakage_guard.py`, `replay_validator.py`, `replay_reporter.py`) | None exist. `ls backend/ \| grep -iE 'replay'` returns zero matches. Closest existing surface (`backend/scripts/backtest_gex_zg.py`, 470 lines) uses theoretical pricing approximations and has empty input data dir — explicitly forbidden by Spec §1 line 62 ("Hard Rule: No Theoretical Pricing"). | Add Class B note: V0.1 ship scope includes deprecation-and-replacement of `backend/scripts/backtest_gex_zg.py` (the existing script's approximation approach is incompatible with Spec §1's hard rule). The 8 new files form the canonical replay infrastructure; the legacy script either deletes or moves to `backend/scripts/_legacy/` with a deprecation note. Tests in `test_b2_backtest.py` / `test_backtest_gex_zg.py` similarly retire or restructure. |
| B3 | Spec §1 line 47–50 (Tradier archived option chains) + Spec §1 line 62–66 ("Hard Rule: No Theoretical Pricing") | Hard prerequisite: archived option chains | **No archive infrastructure at HEAD.** `tradier_feed.py` (327 lines) does not persist chains. No `tradier_chain_archive` migration. `databento:opra:*` keys are 300s-TTL Redis (matrix §6 line 657–658). Spec correctly states "if no historical chain archive exists, chain-dependent replay is NOT calibration-grade" (Spec §1 line 49–50). | Add Class B note: V0.1 ship scope must EITHER (a) include a `tradier_chain_archive` (or `databento_opra_archive`) migration + writer wired into `tradier_feed.py` / `databento_feed.py` with operator-approved retention policy + months-long forward archival window before calibration-grade replay can be claimed, OR (b) explicitly accept Spec §10 Pre-V0.1 Failure Mode (lines 985–989) — V0.1 ships advisory only, no items promote to binding authority. **This is the load-bearing decision for Item 4 V0.1 calendar.** Operator decision required (escalates to Class C — see §10.3 C4). |
| B4 | Spec §1 line 43 (Polygon SPX / I:SPX historical 1-min bars) | Polygon historical 1-min fetch | `polygon_feed.py` only uses `/range/1/day` for VIX (line 706) and `/aggs/ticker/I:SPX/prev` (lines 525, 831). Polygon API supports `/range/1/minute/{from}/{to}` but no current code path uses it. May require Polygon paid tier (operator question; out of scope to verify). | Add Class B note: V0.1 ship scope must add a historical-fetch helper to `polygon_feed.py` (or in `replay_data_reconstructor.py`) wrapping `/v2/aggs/ticker/I:SPX/range/1/minute/{from}/{to}`. Operator must verify the Polygon subscription tier supports historical 1-min bars; if it requires upgrade, that's a contract dependency to be documented. |
| B5 | Spec §13 V0.1 Ship Scope item 6 (`backend/replay_data_reconstructor.py with Commit 1-4 corrections`) — implies Commit-4-corrected re-marking is the source-of-truth | Spec §1 lines 70–138 define Commit 1 (IC/IB target_credit), Commit 2 (Databento LTRIM/GEX), Commit 3 (PCS/CCS), Commit 4 (re-mark + slippage) corrections, but **does not specify which production commit hashes those Commits map to.** | Add Class B note: Spec §1 should reference the production commit hashes that introduced each Commit-N correction (e.g., "Commit 1 = `b2b65c9` IC/IB target_credit fix" — verifiable from git log). At HEAD, the recent commit `77af9af` ("fix(strikes): extract target_credit from Tradier chain for iron_condor and iron_butterfly") may be the IC/IB Commit 1 anchor. Without explicit commit-hash anchoring, future replay runs cannot be deterministically tied to "the corrected logic" version. |
| B6 | Spec §1 line 45 + §5 Timestamp Boundary line 609 ("news where published_at <= T") | News/event ingestion has minute-level `published_at` field | **No `published_at` field exists.** Sentiment agent stores `generated_at` (when WE generated brief, line 82, 135, 303 of `sentiment_agent.py`); economic_calendar uses `event_date` (date-level only); `earnings_calendar` has `earnings_date DATE` and `announce_time TEXT` ('pre' / 'post' / 'unknown') only. `trading_ai_briefs.generated_at` is NOT publish time. | Add Class B note: V0.1 ship scope must extend news/event ingestion to capture `published_at TIMESTAMPTZ` (when the event was originally announced/published) distinct from `ingested_at`/`generated_at` (when we received/generated). Affects: `sentiment_agent.py` raw news fetch, `economic_calendar.py` calendar rows, `earnings_calendar` table. Without this, Spec §5 Timestamp Boundary line 609 cannot be enforced at sub-day granularity — a leakage risk. |
| B7 | Spec §1 line 36 + line 38 (reads from `strategy_attribution` and `ai_governor_decisions`) | Reads from Items 2 + 1 production tables | `strategy_attribution` — AI-SPEC-002 P1.3.2 `B-AI-002-2` documents absent at HEAD. `ai_governor_decisions` — AI-SPEC-001 P1.3.1 `B-AI-001-4` documents absent at HEAD. | Add Class B note: cross-spec FK dependency cascade — Item 4's V0.1 ship cannot run calibration-grade until at least the schema-shipping milestones of Items 1 + 2 land. Coordinate with the master sequencing plan in MASTER_PLAN.md — Item 4's "scaffolding ship" (4 tables + 8 files + Step 0 validation logic) can land independently, but its first calibration-grade run is blocked on Items 1 + 2. Captures cross-spec theme **FK dependency cascade** (now confirmed in 2 audits: AI-SPEC-002 + AI-SPEC-004). |
| B8 | Spec §1 line 37 (reads from `trade_counterfactual_cases`) | Reads from Item 10 production table | PRE-P11-4 / AI-SPEC-002 `C-AI-002-2`: existing scaffold is column-shaped on `trading_prediction_outputs`, not table-shaped. Operator decision pending. | Add Class B note: cross-spec — Item 4's spec wording at §1 line 37 should be updated PENDING the resolution of `C-AI-002-2`. If option 1 (Item 10 ships table), spec stays as-is. If option 2 (Item 2 + Item 4 reference existing column-shaped scaffold), Item 4 spec wording becomes "reads `counterfactual_pnl` / `counterfactual_strategy` / `counterfactual_simulated_at` columns from `trading_prediction_outputs`." If option 3 (defer to V0.2), Item 4 V0.1 ships without counterfactual-case integration. **Bilateral with AI-SPEC-002 / AI-SPEC-010 audits.** |
| B9 | Spec §4 lines 388–432 (`replay_eval_cases.governor_output JSONB / item5_snapshot JSONB / item6_output JSONB / market_state_card JSONB / baseline_action JSONB / candidate_action JSONB / realized_outcome JSONB`) | Decision card schema | Spec gives column shapes (all JSONB) but does not formalize the JSON sub-schemas. The cross-spec implication for AI-SPEC-001 §12 V0.2 promotion gate ("≥200 replay/advisory decision cards") is a counted-thing whose definition is ambiguous at the spec boundary. | Add Class B note: V0.1 ship scope should include a JSON Schema specification (or at minimum a documented field list) for each of the 7 JSONB columns above — landed as a sub-doc at `trading-docs/04-modules/ai-architecture/replay-decision-card-schema.md` or similar. Bilateral with AI-SPEC-001 §12 wording: "decision card" = one row in `replay_eval_cases` where `calibration_eligible = true`. **shadow_engine.py's `shadow_predictions` rows do NOT count toward the 200-card threshold** (different table, different mechanism, different calibration-grade). See §10.3 C2. |
| B10 | Spec §3 lines 306–336 (LightGBM Model State Policy) + Spec §5 line 686 ("Going forward: log model artifacts daily") | Daily artifact + prediction-output logging substrate | At HEAD, `model_retraining.py` (12K, dormant; bf41175 commit) trains models in-process. No artifact-log table; `trading_calibration_log` exists (matrix §5 line 542) but is event-log not artifact-log. No prediction-correlation > 0.95 substrate to evaluate Spec §3 case 3 ("reconstruct model"). | Add Class B note: V0.1 ship scope should include either (a) daily artifact serialization to S3-equivalent + a `model_artifact_log` table to track artifact paths + hashes, OR (b) explicit V0.1 deferral with `model_state_source = 'unavailable'` for all Item 6 / Item 1 calibration paths until artifact-log is ready (which means Spec §3 case 3 does not fire and Spec §3 case 4 is the V0.1 default). |
| B11 | Spec §6 lines 698–703 (rolling 60/20/20 window, step 10 sessions) | Walk-forward implementation | No walk-forward implementation at HEAD. `scripts/backtest_gex_zg.py` does one-shot 2022–2023 sweep (not walk-forward; explicitly forbidden by spec — Spec §6 line 692 "Use rolling window, NOT expanding window"). | Bundled into B2 (`replay_threshold_optimizer.py` / `replay_validator.py`). Walk-forward fold logic must be explicit in `replay_validator.py` per Spec §6 lines 738–744. |
| B12 | Spec §2 lines 168–229 (Step 0 validation tests — 4 binary checks: Pricing $0.10 / SPX 99% / VIX correlation 0.99 / Slippage MAE $0.10) | 4 binary tests | Absent. | Bundled into B2 (`replay_validator.py` + Step 0 validation tests in `backend/tests/test_replay_validator.py` per Spec §13 V0.1 Ship Scope item 13). |
| B13 | Spec §1 implicit (model/version tables) — bridging `trading_calibration_log` and a future `model_artifact_log` | Versioning substrate | `trading_calibration_log` is append-only event log; no `model_artifact_log` or `prompt_version_log` table at HEAD. Spec §10 Prompt Versioning lines 1018–1026 ("challenger runs on captured historical cards / promotion only if challenger beats champion on replay + paper shadow") — "captured historical cards" requires a substrate that doesn't yet exist. | Bundled into B10 + B9. Future audit P1.3.X for prompt-versioning specs (if any) should cross-reference. |

### 10.3 Class C — Architectural Intent Corrections

**(First-pass for GPT-5.5 Pro to validate; operator-only authority.)** Default position: reject unless clear reason. Resolution requires NEW D-XXX or spec revision to comply with existing D-XXX or to set governance scope.

| # | Spec Section | Issue | Conflicting D-XXX or Rule | Resolution Required |
|---|--------------|-------|--------------------------|--------------------|
| C1 | Spec §4 lines 465–498 (`item_promotion_records`) + cross-cutting matrix §5 line 558 (`paper_phase_criteria` "Replay Harness may add a 'replay validation' criterion") | Two independent gate authorities at HEAD/proposed: `paper_phase_criteria` (existing, 12 GLC criteria per D-013, system-wide go-live gate) and `item_promotion_records` (proposed, per-item authority promotion enum). Spec §4 does not address how they coordinate. Risk: ambiguous authority — does GLC-005 (Sharpe ≥ 1.5) failing block all item promotions, or only the system go-live? Does `item_promotion_records.governor_v1.short_gamma_veto.authority_level = 'production'` require GLC-005 to pass first? | T-Rule 2 (Governance Documents Are Authoritative); D-013 Paper Phase + T-Rule 9 (Paper Phase Is Mandatory, 12 GLC); T-Rule 4 (Locked Decisions Are Final) for any new D-XXX | Operator decision required between three options: (option 1) **independent gates** — Spec §4 explicitly states `paper_phase_criteria` and `item_promotion_records` are independent (paper_phase = system-level, item_promotion = per-item-within-system); both must pass before any item is `production`. Lowest-cost; preserves D-013. (option 2) **unified gate** — add `GLC-013: Replay Validation Complete (per Item 4 promotion gate evaluation for at least one item)` as a 13th paper_phase_criteria row; `item_promotion_records.is_current = true` becomes the verification token GLC-013 reads. Tighter but requires D-013 amendment via D-024 (or similar). (option 3) **hierarchical** — `item_promotion_records` is binding ONLY for paper-phase per-item authority; production-binding still requires `paper_phase_criteria` + 90-day A/B per D-013. **Default position (per consolidated plan §5 conservative-first principle):** option 1 (independent gates with explicit non-conflict statement). |
| C2 | Spec §4 lines 388–432 (`replay_eval_cases` schema as decision-card surface) + AI-SPEC-001 §12 V0.2 paper-binding gate ("≥ 200 replay/advisory decision cards" — `B-AI-001-8`) | Cross-spec contract ambiguity: what counts as a "decision card" toward the 200-card threshold? At least three candidates: (i) one row in `replay_eval_cases` with `calibration_eligible = true` (Item 4's surface); (ii) one row in `shadow_predictions` (existing forward A/B surface); (iii) one row in some "advisory" surface that doesn't yet exist. Without explicit coordination, the gate cannot be evaluated. | T-Rule 4 (Locked Decisions Are Final) + cross-spec coordination via D-023 (proposed in AI-SPEC-001 §11 + AI-SPEC-002 §11 addendum) | Operator decision required: (option 1) **canonical = `replay_eval_cases.calibration_eligible = true`** — most rigorous; matches Spec §1 line 49 hard rule. Excludes shadow_engine.py rows. Lower throughput; the 200-card calendar may slip. (option 2) **canonical = (`replay_eval_cases.calibration_eligible = true`) UNION (`shadow_predictions` rows where `regime` is non-degenerate AND timestamp is post-spec-locked HEAD)** — broader; faster to 200 but mixes mechanisms. (option 3) **two separate gates** — D-023 splits into "≥200 replay cards" (Item 4) AND "≥X shadow cards" (shadow_engine.py); both must pass. **Default position:** option 1 (rigorous; matches spec architectural intent). Encode resolution in D-023 wording alongside AI-SPEC-001 / AI-SPEC-002 dispositions. |
| C3 | Spec §4 lines 521–525 ("Items 1, 5, 6 read item_promotion_records at startup. If no current record exists for an item/scope: default to advisory or disabled, NEVER production.") | Item 4's startup-read contract becomes a system-wide architectural rule that Items 1, 5, 6 must comply with. Currently no D-XXX codifies this. AI-SPEC-001 P1.3.1 `C-AI-001-1` proposed D-023 for AI authority boundary. | T-Rule 4 + pending D-023 (per AI-SPEC-001 §11) | Operator decision: extend the pending D-023 wording to additionally enforce the "default to advisory or disabled, NEVER production" startup contract. Specifically, D-023 must include a clause: "any item subject to AI authority (Items 1, 5, 6, and any future per-item-promotion-gated specs) MUST read its current authority level from `item_promotion_records` at startup; absence of a current row defaults to `advisory` (for items already paper-binding-eligible) or `disabled` (for items not yet paper-binding-eligible); items MUST NOT invent their own promotion status." Folds into existing pending D-023 — no new D-XXX needed. |
| C4 | Spec §1 line 47–66 (Tradier archived option chains as HARD PREREQUISITE) + Spec §10 Pre-V0.1 Failure Mode lines 985–989 ("If the replay harness cannot produce calibration-grade evidence: V0.1 ships advisory only / All items default to authority_level = 'advisory' or 'disabled'") | Hard architectural prerequisite (chain archive) is months-long to backfill via forward archival OR requires paid-tier historical-chain access (operator contract). Spec acknowledges the failure mode (V0.1 advisory-only) but does not require operator to formally accept that failure mode at audit close. The implicit risk: operator approves Item 4 V0.1 ship scope without explicitly accepting the calendar implication. | T-Rule 1 (Foundation Isolation) — operator owns the data-substrate decision; T-Rule 9 (Paper Phase Is Mandatory) — D-013 90-day A/B test still runs regardless of Item 4 status | Operator decision required between three options: (option 1) **forward archival (months-long)** — start chain-archival now; Item 4 V0.1 ships with scaffolding + Step 0 validation but produces no calibration-grade results until archive is sufficient (estimated 6+ months for 90 sessions per Spec §6 sample-size tiers; possibly 12+ months for full-stack confidence). All Items 1, 5, 6 default to advisory until archive matures. (option 2) **paid historical archive** — operator negotiates paid Tradier or Databento historical chain access; Item 4 V0.1 can run calibration-grade replay over (e.g.) 2024–2025 data. Cost: TBD; contractual dependency. (option 3) **explicit V0.1 advisory-only acceptance** — operator formally accepts Spec §10 Failure Mode; V0.1 ships per spec scaffolding; Items 1, 5, 6 stay advisory; production-binding deferred to V0.2 calendar. **Default position (per consolidated plan §5 conservative-first principle):** option 3 with parallel-track exploration of options 1 and 2; operator revisits the V0.1-vs-V0.2 promotion line at end-of-V0.1. |

---

## 11. Governance Updates Required

- [x] **approved-decisions.md — D-023 scope must include `item_promotion_records` startup-read contract + decision-card-counting wording** (per §10.3 C2 + C3). D-023 is already proposed in AI-SPEC-001 §11 as the AI authority boundary D-XXX; AI-SPEC-002 P1.3.2 §11 added the `decision_outcome` enum coordination clause; AI-SPEC-004 P1.3.3 audit confirms the same D-023 must additionally encode (a) the "default to advisory or disabled, NEVER production" startup contract for any item subject to per-item authority promotion, and (b) the canonical "decision card" definition (= `replay_eval_cases.calibration_eligible = true`) used by Spec §12 thresholds. Folds into existing pending D-023 wording, not a new D-XXX.
- [ ] **approved-decisions.md — D-013 Paper Phase non-amendment** (per §10.3 C1 default position). If operator chooses option 1 (independent gates), D-013 is NOT amended; Spec §4 documentation explicitly states `paper_phase_criteria` and `item_promotion_records` are independent surfaces. If operator chooses option 2 (unified gate), D-013 requires amendment via a new D-XXX (e.g., D-024) adding GLC-013. **Default: option 1 — no D-013 amendment.**
- [ ] **approved-decisions.md — possible new D-XXX for "calibration-grade chain archive substrate"** (per §10.3 C4). If operator chooses option 1 or option 2 (paid or forward archival), a new D-XXX may be warranted to formalize the data-substrate ownership and retention policy. If operator chooses option 3 (V0.1 advisory-only acceptance), no new D-XXX needed. **Default: option 3 — no new D-XXX; explicit operator acceptance of Spec §10 Failure Mode logged in `system-state.md`.**
- [ ] **MASTER_PLAN.md — new phase entry: Phase 3C (or equivalent) — Replay Harness V0.1.** Per Spec §13 V0.1 Ship Scope: 14 build items (4 migrations + 8 files + Step 0 validation tests + walk-forward implementation). Estimated 6–10 weeks for scaffolding-only ship; calibration-grade ship blocked on operator decision on `C-AI-004-4` (chain archive substrate path). Sequencing: must follow Phase 3A (Item 1) and Phase 3B (Item 2) schema-landing milestones to read FK targets.
- [ ] **TASK_REGISTER.md — new section: §14C — Replay Harness implementation.** Sub-items per `AI-SPEC-004.md` §12.2 (14C.0 schema bootstrap; 14C.1 chain-archive substrate or formal V0.1 deferral; 14C.2 Polygon historical 1-min fetch; 14C.3 news/event `published_at` field; 14C.4 8 `replay_*.py` files; 14C.5 Step 0 validation; 14C.6 walk-forward; 14C.7 decision-card JSON sub-schema; 14C.8 LightGBM artifact-log substrate or V0.1 NULL deferral; 14C.9 deprecate `backend/scripts/backtest_gex_zg.py`; 14C.10 `item_promotion_records` startup-read wiring in Items 1 / 5 / 6).
- [ ] **system-state.md — operational state addition: `replay_harness` field.** Tracks `{ phase: 'not_started' | 'v0.1_scaffolding' | 'v0.1_active' | 'v0.1_advisory_only' | 'v0.1_calibration_grade' | 'demoted', last_run_id: uuid | null, last_run_status: 'success' | 'partial' | 'failed' | null, last_step0_validation_pass: bool | null, calibration_grade_capable: bool, chain_archive_status: 'absent' | 'forward_archival_in_progress' | 'paid_historical_acquired' | 'sufficient' }`. Tracks the C4 architectural decision and Step 0 binary-gate outcomes.
- [ ] **system-state.md — operational state addition: `item_promotion_records_status` field.** Tracks per-item authority levels (Items 1 / 5 / 6) read from `item_promotion_records.is_current = true` rows; mirror state for dashboard / UI consumption. Default initial values: all items = `'advisory' or 'disabled'` per Spec §4 line 521–525.
- [ ] **constitution.md — pointer note only — no rule change.** If D-023 is ratified to include the `item_promotion_records` startup-read contract and decision-card-counting wording, T-Rule 4 needs a one-line note pointing to D-023 as the authoritative AI-authority record. T-Rule 9 already covers paper-phase 12-GLC compliance and is unaffected by Item 4's per-item layer (independent gates). T-Rule 10 (Silent Failures Are Forbidden) — Item 4's Spec §2 Step 0 explicit "no downstream calibration runs" on Step 0 failure aligns with T-Rule 10.

---

## 12. TASK_REGISTER Implications

Decompose Item 4 V0.1 build into ordered sub-items.

### 12.1 Pre-implementation tasks (must complete before P1.3 audit can close)

| # | Task | Owner | Blocking |
|---|------|-------|----------|
| P1 | Operator decision on `C-AI-004-1` (paper_phase_criteria vs item_promotion_records authority) | Operator | §10.3 C1 |
| P2 | Operator decision on `C-AI-004-2` (decision-card definition for Spec §12 200-card gate) | Operator + GPT validation | §10.3 C2; bilateral with AI-SPEC-001 `C-AI-001-1` D-023 |
| P3 | Operator decision on `C-AI-004-3` (D-023 enrichment for startup-read contract) | Operator + GPT validation | §10.3 C3; folds into D-023 |
| P4 | Operator decision on `C-AI-004-4` (chain-archive substrate path: forward / paid / V0.1-advisory-only) | Operator | §10.3 C4 — load-bearing for V0.1 calendar |
| P5 | Bilateral confirmation on `C-AI-002-2` resolution (Item 4 read from `trade_counterfactual_cases`) | Operator + future P1.3.10 audit | B8; depends on AI-SPEC-002 disposition |

### 12.2 Implementation tasks (Cursor work after Phase 4 doc integration)

Per Spec §13 V0.1 Ship Scope (lines 1094–1109):

| # | Task | Spec ref | Notes |
|---|------|----------|-------|
| 14C.0 | Migrations: `replay_eval_runs`, `replay_eval_cases`, `replay_eval_results`, `item_promotion_records` (4 files); seed `item_promotion_records` initial rows for Items 1 / 5 / 6 with default `'advisory' or 'disabled'` | Spec §4 lines 348–498 + Spec §13 items 1–4 | DB-level CHECK constraints (`environment = 'research'`) provide structural research-isolation per Spec §9 dimension 9 |
| 14C.1 | Chain-archive substrate: `tradier_chain_archive` table OR `databento_opra_archive` table + writer hook in `tradier_feed.py` / `databento_feed.py` OR formal V0.1 deferral with operator-accepted advisory-only ship | §10.3 C4 resolution | Load-bearing for V0.1 calibration-grade ship; operator decision determines path |
| 14C.2 | Polygon historical 1-min fetch helper: `polygon_feed.py.fetch_spx_1min_history(start, end)` wrapping `/v2/aggs/ticker/I:SPX/range/1/minute/{from}/{to}` | Spec §1 line 43 + B4 | Verify subscription tier supports historical 1-min |
| 14C.3 | News/event `published_at` field: ALTER on `trading_ai_briefs` OR new news-event table; migrate existing rows with NULL `published_at` (legacy rows excluded from Spec §5 line 609 enforcement) | Spec §1 line 45 + B6 | Affects sentiment_agent.py, economic_calendar.py, earnings_calendar |
| 14C.4 | 8 `backend/replay_*.py` files: `replay_harness.py`, `replay_data_reconstructor.py`, `replay_feature_builder.py`, `replay_decision_stack.py`, `replay_threshold_optimizer.py`, `replay_leakage_guard.py`, `replay_validator.py`, `replay_reporter.py` | Spec §4 lines 532–554 + Spec §13 items 5–12 | Walk-forward in `replay_threshold_optimizer.py` per Spec §6 |
| 14C.5 | Step 0 validation tests (4 binary checks): pricing $0.10, SPX 99% bars, VIX correlation 0.99, slippage MAE $0.10 | Spec §2 lines 168–229 + Spec §13 item 13 | Tests live at `backend/tests/test_replay_validator.py` |
| 14C.6 | Walk-forward implementation: rolling 60/20/20 + 10-session step + graduated-authority sample-size tier table | Spec §6 lines 698–732 | Inside `replay_threshold_optimizer.py` |
| 14C.7 | Decision-card JSON sub-schema: documented spec for the 7 JSONB columns of `replay_eval_cases` (`governor_output`, `item5_snapshot`, `item6_output`, `market_state_card`, `baseline_action`, `candidate_action`, `realized_outcome`) | B9 + §10.3 C2 | Land at `trading-docs/04-modules/ai-architecture/replay-decision-card-schema.md` |
| 14C.8 | LightGBM artifact-log substrate: `model_artifact_log` table OR V0.1 NULL deferral with `model_state_source = 'unavailable'` for all calibration paths | B10 | Bilateral with future Item 6 audit (P1.3.6) |
| 14C.9 | Deprecate `backend/scripts/backtest_gex_zg.py` (470 lines): move to `backend/scripts/_legacy/` with deprecation note OR delete; retire `test_b2_backtest.py` + `test_backtest_gex_zg.py` | B2 + B5 | Preserves git history; avoids confusion with calibration-grade replay |
| 14C.10 | `item_promotion_records` startup-read wiring in Items 1, 5, 6 (per Spec §4 line 521–525); each item reads its current row at startup and applies authority-level constraints to its enforcement code path | Spec §4 lines 521–525 + §10.3 C3 | Cross-spec — adds dependency from each Item's V0.1 build on `item_promotion_records` table existence |

### 12.3 Calibration / Data dependencies

| # | Dependency | Status | Resolution path |
|---|------------|--------|-----------------|
| D1 | Archived option-chain data (≥90 calibration-grade sessions per Spec §6 sample-size tiers) | **HARD prerequisite, currently absent** | §10.3 C4 operator decision |
| D2 | `strategy_attribution` table populated with calibration-grade rows | Blocked on AI-SPEC-002 V0.1 ship | Sequencing in MASTER_PLAN |
| D3 | `ai_governor_decisions` table populated with logged outputs | Blocked on AI-SPEC-001 V0.1 ship | Sequencing in MASTER_PLAN |
| D4 | `trade_counterfactual_cases` (or column-shaped equivalent per `C-AI-002-2`) | Blocked on AI-SPEC-002 / AI-SPEC-010 disposition | §10.3 C2 + C-AI-002-2 |
| D5 | News/event `published_at` substrate populated with historical data | Blocked on B6 | Either backfill from primary sources (limited) or accept missing-published_at rows as `event_unavailable` per Spec §1 line 151 |
| D6 | LightGBM model artifacts logged daily | Blocked on B10 | V0.1 default = `model_state_source = 'unavailable'` for all paths until artifact-log ships |

---

## 13. Recommended Status

- [ ] **spec_accurate_repo_missing** — Spec is correct as written; nothing exists in repo yet; ready for clean buildout.
- [ ] **spec_accurate_repo_partial** — Spec is correct; partial scaffold exists (cite); spec describes the full target.
- [ ] **spec_needs_factual_correction_only** — Spec has Class A errors only; intent is sound; mechanical fixes will land in Phase 2.
- [x] **spec_has_semantic_drift_from_locked_intent** — Spec has Class B corrections that change implementation meaning but not architectural goal. Phase 2 corrections + operator approval.
- [ ] **spec_conflicts_with_existing_governance** — Spec contains Class C item(s) requiring new D-XXX or revision before integration.
- [ ] **spec_should_be_split_into_separate_proposal** — Spec scope is too broad and should be decomposed before integration. Operator decision.

**Justification for the chosen status:** The 13 Class B corrections are substantive and change implementation meaning (substrate gaps for chain archive + Polygon 1-min + news `published_at` + LightGBM artifact-log; FK cascade on Items 1 / 2 / 10; deprecation of approximation backtest; decision-card schema formalization) but the architectural goal — a research-only offline replay harness as the empirical authority for Items 1 / 5 / 6 promotion — is sound and unaltered. The 4 Class C items are cross-spec coordination questions (C1 paper_phase vs item_promotion gates; C2 decision-card-counting for D-023; C3 D-023 startup-read contract enrichment; C4 chain-archive substrate path). C1, C2, C3 fold into pending D-023 wording; C4 is a load-bearing operator decision but has an explicit-acceptance default path (Spec §10 Failure Mode = V0.1 advisory-only) that requires operator sign-off rather than new D-XXX. So `spec_conflicts_with_existing_governance` would over-state — no NEW D-XXX is strictly required for V0.1 ship even in the worst-case operator-decision branch. `spec_has_semantic_drift_from_locked_intent` correctly captures: spec architectural intent is preserved; implementation as written would not work without the substrate corrections (especially B3 chain archive, B4 Polygon 1-min, B6 news `published_at`).

**Note on CRITICAL risk vs `spec_has_semantic_drift_from_locked_intent` status:** The CRITICAL risk rating in §9 reflects calendar/data-substrate risk (chain archive months-to-acquire), not specification-drift severity. The spec itself is well-formed; the risk is operational, mitigated by Spec §10 Failure Mode (V0.1 advisory-only acceptance path). Status checkbox reflects spec quality; risk rating reflects environmental constraints.

---

## 14. Sign-Off

| Auditor | Sign-off Status | Date | Notes |
|---------|----------------|------|-------|
| Primary (Cursor) | approved (first-pass redline; primary sections §1, §3, §4, §10.1 fully populated; first-pass drafts of §2, §5–§13 for cross-check refinement) | 2026-04-26 | Class A: 0 items. Class B: 13 items (substrate gaps + cross-spec FK cascade + decision-card schema + LightGBM artifact-log + deprecation of backtest_gex_zg.py). Class C: 4 items (paper_phase vs item_promotion gates; decision-card definition for D-023; D-023 startup-read enrichment; chain-archive substrate path). Risk rating: CRITICAL. Recommended status: `spec_has_semantic_drift_from_locked_intent`. |
| Cross-check (Claude) | pending | — | §7 cross-spec contradictions and §8 carry-forward findings drafted first-pass; awaiting Claude refinement. |
| Validator (GPT-5.5 Pro) | pending | — | §2 intent summary and §10.3 Class C escalations drafted first-pass; awaiting GPT validation. |
| Operator | pending | — | Class C items require operator decisions before redline closes (C1 / C2 / C3 / C4 dispositions). |

If all four sign-offs are "approved", the redline is closed and the spec moves to Phase 2 correction application.

---

## Appendix — Verification Notes

**Repo HEAD verification:** `git rev-parse HEAD` at audit time returned `b0bcdaad9be9128fe31f65cf9b6fee2588e6a49f` (P1.3.2 merge — AI-SPEC-002 audit landed). Branch: `feature/PLAN-AIARCH-000-phase-1-p1-3-3-audit-spec-004-replay-harness`.

**Migration count verification:** `ls supabase/migrations/*.sql | wc -l` returned `68`. All searches for absent tables (`replay_eval_runs`, `replay_eval_cases`, `replay_eval_results`, `item_promotion_records`, `tradier_chain_archive`, `databento_opra_archive`) confirmed against this count.

**File-existence verification:**
- `ls backend/ | grep -iE 'replay'` → zero matches
- `ls backend/data/historical/` → 2 entries (`.` and `..` only — directory empty)
- `wc -l backend/shadow_engine.py` → 456
- `wc -l backend/scripts/backtest_gex_zg.py` → 470
- `wc -l backend/polygon_feed.py` → 956
- `wc -l backend/tradier_feed.py` → 327
- `wc -l backend/databento_feed.py` → 447

**Cross-references to running register at HEAD `b0bcdaa`:**
- `B-AI-001-4` (running register §2) — basis for §3.2 + §10.2 B7 `ai_governor_decisions` canonical name claim.
- `B-AI-001-8` (running register §2) — basis for §10.3 C2 "≥200 decision cards" cross-spec coordination claim.
- `C-AI-001-1` (running register §1) — basis for §10.3 C3 D-023 enrichment claim (cross-spec authority boundary).
- `B-AI-002-1` / `B-AI-002-2` (running register §2) — basis for §3.2 + §10.2 B7 + §10.2 B8 (Item 4 reads from `strategy_attribution` and `closed_trade_path_metrics`).
- `C-AI-002-2` (running register §1) — basis for §10.2 B8 (`trade_counterfactual_cases` table-vs-column).
- `PRE-P11-4` (running register §0.2) — basis for §8 carry-forward #5 + §10.2 B8.
- `PRE-P11-7` (running register §0.2) — basis for §8 carry-forward #3 (silently honored — Spec §9 line 916 uses canonical names).

**Methodology footnote:** Class B / C distinctions follow `CONSOLIDATED_PLAN_v1.2_APPROVED.md` §3 + template `_template.md` §10. Class B captures implementation-meaning drift that does not change architectural goal; Class C captures architectural-intent conflicts that require operator authority. The 4 Class C items in this audit each represent a genuine multi-option decision space rather than a mechanical or known-correct fix. The 0 Class A finding is consistent with Item 4's pure-forward-design nature (no cited file:line mechanical errors to verify).

