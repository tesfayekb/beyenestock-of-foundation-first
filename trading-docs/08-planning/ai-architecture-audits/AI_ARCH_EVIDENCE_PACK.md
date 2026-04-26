# AI Architecture Evidence Pack — Phase 1 P1.1

> **Status:** Read-only snapshot of repository state at HEAD as of the snapshot date below.
> **Purpose:** Ground truth for the 13 AI architecture spec audits in Phase 1 P1.3 and the cross-cutting evidence matrix in P1.2.
> **Authority:** This document is referenced (NOT modified) by all 13 spec audits. Re-snapshot only when the operator decides the baseline has materially drifted (e.g., new module deployments, new D-XXX decisions, structural TASK_REGISTER changes).
> **Verification rule:** Produced under the SPEC VERIFICATION PROTOCOL added to `.cursorrules` and `.lovable/rules.md` in Phase 0 P0.2. Every concrete reference in this document was verified against the actual repository at the snapshot HEAD; unverifiable claims are explicitly flagged "UNVERIFIED — needs Phase 1 P1.3 audit attention".

---

## 1. Snapshot Metadata

**Snapshot date:** 2026-04-26

**Repo HEAD commit:** `60dea4537eeb78492c69bb7fe3970acfb23c0e65`

**Repo HEAD message:** `docs(ai-arch): P0.2/P0.3/P0.4 - SPEC VERIFICATION PROTOCOL + audit template stub + drafts staging dir (#55)`

**Branch the snapshot was taken from:** `main`

**Latest Supabase migration applied:** `supabase/migrations/20260427_trading_feature_flags.sql`

**Total Supabase migration files in `supabase/migrations/`:** 68

**Phase 0 commits referenced:**

| Phase | PR | Squash-merge commit on `main` |
|-------|----|-------------------------------|
| P0.1 — `feature-proposals.md` | #54 | `7e87515` |
| P0.2 / P0.3 / P0.4 — SVP + template stub + drafts dir | #55 | `60dea45` |

Note: PR #54 and #55 were both merged using GitHub's squash-merge style, so the listed commit hashes are themselves the on-`main` introduction points (not separate merge commits with two parents).

---

## 2. Governance Documents Inventory

Last-modified dates are the most-recent commit touching the file (`git log -1 --format=%ai`). Line counts use `wc -l`.

### 2.1 `trading-docs/00-governance/`

| Path | Lines | Last Modified | Purpose |
|------|-------|---------------|---------|
| `trading-docs/00-governance/constitution.md` | 58 | 2026-04-18 | Trading system constitution: Prime Directive + 10 T-Rules + scope reference + authority hierarchy. T-Rule 4 binds D-001..D-022. T-Rule 1 mandates foundation isolation. |
| `trading-docs/00-governance/system-state.md` | 49 | 2026-04-18 | Current trading phase YAML and gate state (`trading_phase: phase_1_stabilizing`, `code_generation: allowed`, `live_trading: blocked_until_90day_AB_test_passes`, sizing phase, daily loss limit). |
| `trading-docs/00-governance/ai-operating-model.md` | 87 | 2026-04-16 | Trading-side AI operating model description (governance posture for AI agents). |
| `trading-docs/00-governance/cursorrules-trading.md` | 118 | 2026-04-16 | Trading-side cursor rules (separate from repo-root `.cursorrules`). |
| `trading-docs/00-governance/what-is-actually-built.md` | 67 | 2026-04-18 | Honest snapshot of what is currently shipped in `backend/` and adjacent dirs. |

### 2.2 `trading-docs/08-planning/`

| Path | Lines | Last Modified | Purpose |
|------|-------|---------------|---------|
| `trading-docs/08-planning/MASTER_PLAN.md` | 443 | 2026-04-19 | The approved execution plan (v3.2). Vision, architecture principles (Rules 1–6), backend module map, console architecture, strategy library, profit register, ROI projection, 5-phase roadmap, locked strategic decisions, operating costs. |
| `trading-docs/08-planning/TASK_REGISTER.md` | 1728 | 2026-04-21 | Sections 1–13 of all pending and recently-shipped tasks. Section 12 = build-now queue (12A–12N, 14 items, marked complete 2026-04-20). Section 13 = post-Section-12 diagnostic fixes (Batch 1, Batch 2, UI sprint). |
| `trading-docs/08-planning/approved-decisions.md` | 125 | 2026-04-18 | All 22 locked decisions D-001 through D-022 (per T-Rule 4). |
| `trading-docs/08-planning/feature-proposals.md` | 126 | 2026-04-26 | **Created in P0.1 (PR #54).** Trading-docs FP-NNN namespace. Proposal Register currently empty. |
| `trading-docs/08-planning/plan-changelog.md` | 27 | 2026-04-18 | Plan version changelog. |
| `trading-docs/08-planning/deferred-work-register.md` | 96 | 2026-04-16 | Deferred items registry. |
| `trading-docs/08-planning/known-false-positives.md` | 158 | 2026-04-17 | Known-FP register for trading signals/tests. |
| `trading-docs/08-planning/paper-phase-criteria.md` | 92 | 2026-04-16 | 12 go-live criteria for paper-phase exit gate (per D-013). |
| `trading-docs/08-planning/README.md` | 3 | 2026-04-16 | Folder README. |

### 2.3 `trading-docs/08-planning/ai-architecture-audits/`

| Path | Lines | Last Modified | Purpose |
|------|-------|---------------|---------|
| `trading-docs/08-planning/ai-architecture-audits/_template.md` | 40 | 2026-04-26 | **Created in P0.3 (PR #55).** Stub for the per-spec audit template; full template developed in Phase 1 P1.3. Referenced by the SPEC VERIFICATION PROTOCOL added in P0.2. |
| `trading-docs/08-planning/ai-architecture-audits/AI_ARCH_EVIDENCE_PACK.md` | (this file, P1.1) | 2026-04-26 | This evidence pack. |

### 2.4 `trading-docs/08-planning/ai-architecture-drafts/`

| Path | Bytes | Last Modified | Purpose |
|------|-------|---------------|---------|
| `trading-docs/08-planning/ai-architecture-drafts/.gitkeep` | 202 (1-line comment) | 2026-04-26 | **Created in P0.4 (PR #55).** Staging-directory marker. The directory will hold corrected AI architecture spec drafts during Phase 2 → Phase 4 of the consolidated plan; cleaned at the end of Phase 4. |

> The `.gitkeep` is intentionally non-empty: per the P0.4 spec it contains a single descriptive comment line. Conventional `.gitkeep` is empty; the deviation was approved by the operator and is documented in PR #55.

### 2.5 Repo-root governance files

| Path | Lines | Last Modified | Purpose |
|------|-------|---------------|---------|
| `.cursorrules` | 277 | 2026-04-26 | Cursor binding contract. SPEC VERIFICATION PROTOCOL added in P0.2 (line 197). |
| `.lovable/rules.md` | 280 | 2026-04-26 | Lovable binding contract. SPEC VERIFICATION PROTOCOL added in P0.2 (line 211, byte-identical to `.cursorrules` SVP block). |
| `README.md` | 43 | 2026-04-09 | Repo README (foundation-layer; minimal trading content). |

---

## 3. Approved Decisions Snapshot

**Total decisions:** 22

**ID range:** D-001 through D-022 (contiguous, no gaps)

**File:** `trading-docs/08-planning/approved-decisions.md` (125 lines, last modified 2026-04-18)

`approved-decisions.md` does not store a per-decision `status` field or `last_updated` timestamp. Per the SPEC VERIFICATION PROTOCOL, those columns are filled with `n/a` rather than guessed. Where a decision carries an `IMPLEMENTATION NOTE`, the note's date is shown in the Last Updated column.

| ID | Title | Status | Last Updated |
|----|-------|--------|--------------|
| D-001 | Instruments — SPX, XSP, NDX, RUT only (Section 1256) | n/a | n/a |
| D-002 | Primary Mode — 0DTE | n/a | n/a |
| D-003 | Secondary Mode — 1–5 day swing, regime-gated, system decides | n/a | n/a |
| D-004 | Capital Allocation — Core + Satellites + Reserve (RCS-dynamic) | n/a | n/a |
| D-005 | Daily Loss Limit — −3% hardcoded, no override (T-Rule 5) | n/a | n/a |
| D-006 | Broker — Tradier API only, OCO pre-submitted at every fill | n/a | n/a |
| D-007 | Execution — Fully automated, single operator account | n/a | n/a |
| D-008 | Data Budget — ~$150–200/month | n/a | n/a |
| D-009 | X/Twitter Sentiment — Tier-3 only, ±5% max weight, ≥2 accounts to confirm | n/a | n/a |
| D-010 | Short-Gamma Exit — 2:30 PM EST, automated, no override (T-Rule 6) | n/a | n/a |
| D-011 | Long-Gamma Exit — 3:45 PM EST, automated, no override (T-Rule 6) | n/a | n/a |
| D-012 | RUT Handling — Satellite-only, 50% size, stricter liquidity requirements | n/a | n/a |
| D-013 | Paper Phase — 45 days minimum, 12 go-live criteria, all required (T-Rule 9) | n/a | n/a |
| D-014 | Position Sizing — 4 phases with advance criteria and automatic regression | n/a | n/a |
| D-015 | Slippage Model — Predictive LightGBM, not static | IMPLEMENTATION NOTE present (predictive model never built; static dict in use; meta-label model in Phase 3A will capture data) | April 2026 |
| D-016 | Volatility Blending — sigma = max(realized, 0.70 × implied) | n/a | n/a |
| D-017 | CV_Stress Exit Condition — Only triggers when P&L ≥ 50% of max profit | n/a | n/a |
| D-018 | VVIX Thresholds — Adaptive Z-score vs 20-day rolling baseline | n/a | n/a |
| D-019 | Execution Feedback — If actual > predicted × 1.25 → tighten for session | n/a | n/a |
| D-020 | Trade Frequency — Max trades per regime type per session | n/a | n/a |
| D-021 | Regime Guard — HMM ≠ LightGBM → size 50% reduction | IMPLEMENTATION NOTE present (HMM/LightGBM not built; VVIX Z-score + `regime_agreement` flag achieves equivalent 50% reduction; do not build HMM/LightGBM until explicitly tasked in Phase 3A) | April 2026 |
| D-022 | Capital Preservation — 3 consecutive losses → size 50%; 5 → halt session (T-Rule 5) | n/a | n/a |

---

## 4. MASTER_PLAN State

**File:** `trading-docs/08-planning/MASTER_PLAN.md` (443 lines, last modified 2026-04-19)

**Plan version:** v3.2 (declared on line 1: "MarketMuse — Master Strategic Plan v3.2")

**Total Phases defined:** 5 (Phase 1 through Phase 5)

The current MASTER_PLAN does NOT use the `PLAN-{MODULE}-NNN` stable-ID convention internally. Section IDs in this doc are written as natural-language phase labels ("PHASE 1 — Stabilize", "2A: Catalyst Gate + Iron Butterfly + Long Straddle", etc.). The `PLAN-{MODULE}-NNN` IDs that appear in `.cursorrules` (PLAN-AUTH-001, PLAN-RBAC-001, PLAN-ADMIN-001, etc.) are foundation-layer plan section IDs from `docs/08-planning/master-plan.md`, not the trading-docs MASTER_PLAN.

### 4.1 Phase status snapshot

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| Phase 1 | Stabilize | COMPLETE | "Real SPXW symbols in Redis + predictions in DB + positions opening" — exit gate satisfied. |
| Phase 2 | Multi-Strategy + AI Brain | COMPLETE | Sub-phases 2A (Catalyst Gate + Iron Butterfly + Long Straddle), 2B (Bull/Bear Debit Spreads), 2C (Multi-Agent AI Brain in `backend_agents/`) all marked complete. |
| Phase 3A | Meta-Label Model | INFRASTRUCTURE BUILT, DORMANT | Activates at ≥100 closed paper trades. Scaffold shipped 2026-04-20 in `bf41175` (TASK_REGISTER 12K). |
| Phase 3B | 90-Day A/B Paper Test | COMPLETE | Migration `20260426_ab_shadow_tables.sql` shipped; `ab_session_comparison` table live; `backend/shadow_engine.py` running daily; `useAbComparison` hook feeding Activation Dashboard. |
| Phase 3C | Calendar Spread | COMPLETE (per MASTER_PLAN line 277) | MTM pricing for calendar spread is flagged as a follow-up build (NEXT BUILDS line 286). |
| Phase 4A | Multi-User Auth | NOT YET BUILT | |
| Phase 4B | User Dashboard | NOT YET BUILT | |
| Phase 4C | Trading Console — Options Module | COMPLETE | |
| Phase 4D | Optional Broker Mirror | NOT YET BUILT | Requires governance/disclaimer review before implementation (T-Rule 3). |
| Phase 5A | Earnings Volatility System (`backend_earnings/`) | COMPLETE (April 2026) | Strategy `earnings_straddle` wired; `strategy:earnings_straddle:enabled` flag default OFF. |
| Phase 5B | Futures Momentum (`backend_futures/`) | NOT YET BUILT | 12–16 weeks; new broker (Interactive Brokers); 15% capital allocation. |

### 4.2 Stable IDs currently in use in `MASTER_PLAN.md`

`grep -nE '^PLAN-[A-Z]+-[0-9]+' trading-docs/08-planning/MASTER_PLAN.md` returns no matches. The MASTER_PLAN does not currently use `PLAN-XXX-NNN` IDs. AI architecture spec audits in P1.3 should treat phase labels (`Phase 2A`, `Phase 3A`, etc.) as the addressing convention until a future revision introduces stable IDs to MASTER_PLAN.

### 4.3 Next Builds (line 283 of MASTER_PLAN)

The "NEXT BUILDS (in priority order as of April 2026)" list — important context for AI architecture spec audits because it shows what is queued *outside* the AI architecture work:

1. HARD-B: External alerting (Gmail/Slack on halt/drawdown events)
2. VVIX daily history fix (mirrors S6 E-2 — deferred, tracked in S8 xfail test)
3. Calendar spread MTM pricing (replace entry-value stub with real far/near differential)
4. Loop 2 meta-label model training (requires 100+ clean closed trades post-S4)
5. Real capital deployment (requires A/B gate: 90 days + 100 trades + +8% B lead)
6. Phase 4A/4B/4D: User platform expansion (post real-capital validation)

---

## 5. TASK_REGISTER Sections

**File:** `trading-docs/08-planning/TASK_REGISTER.md` (1728 lines, last modified 2026-04-21)

**Total sections:** 13 (numbered SECTION 1 through SECTION 13)

**Latest section number:** 13

| # | Title | Header line | Status |
|---|-------|-------------|--------|
| 1 | Ongoing Operational Tasks | line 19 | Active |
| 2 | Feature Flag Activation (In Order) | line 157 | Active |
| 3 | Trade Count Milestones | line 197 | Active |
| 4 | Phase 3 Tasks (After 100 Closed Trades) | line 221 | Pending data threshold |
| 5 | Phase 4 Tasks (Months 3-6) | line 249 | Partially complete (4C done) |
| 6 | Phase 5 Tasks (Months 6-18) | line 283 | Partially complete (5A done) |
| 7 | Completed Phases (April 2026) | line 305 | Historical record |
| 8 | Ongoing Hardening (Any Sprint) | line 398 | Active |
| 9 | Future Roadmap Items (Year 2+) | line 516 | Backlog |
| 10 | Current System Status | line 543 | Active |
| 11 | Profit Maximization Roadmap | line 588 | Active |
| 12 | Build-Now Queue (Auto-Activation on Data Threshold) | line 720 | **ALL 14 ITEMS COMPLETE — 2026-04-20** (per line 722) |
| 13 | Post-Section-12 Diagnostic Fixes (2026-04-20) | line 1377 | Multi-batch (Batch 1 + Batch 2 + UI Sprint) |

### 5.1 Section 12 sub-items (12A–12N) — all marked complete 2026-04-20

| Sub-ID | Title | Header line | Build status (per TASK_REGISTER) |
|--------|-------|-------------|-----------------------------------|
| 12A | True 20-Day Daily Realized Vol | 731 | Listed in Section 12 |
| 12B | Butterfly Gate Instrumentation | 753 | SHIPPED (commit `7983d6c`) |
| 12C | GEX Wall Stability (30-Min Rolling Check) | 770 | SHIPPED (commit `acccfd7`) |
| 12D | D3 Regime × Strategy Performance Matrix | 800 | Listed |
| 12E | D4 Counterfactual Engine | 841 | SHIPPED (commit `2400e98`, file `backend/counterfactual_engine.py`, migration `20260421_add_counterfactual_pnl.sql`) |
| 12F | Phase C Adaptive Halt Threshold | 899 | Listed |
| 12G | Butterfly Threshold Auto-Tuning | 936 | Listed |
| 12H | Phase A LightGBM Feature Engineering Scaffold | 997 | ✅ COMPLETE 2026-04-20 (commit `8bc3c85`) |
| 12I | OCO Bracket Orders (C1) | 1062 | Listed |
| 12J | Phase 5B Earnings Learning Loop Scaffold | 1115 | Listed |
| 12K | Loop 2 Meta-Label Model Scaffold | 1190 | ✅ COMPLETE 2026-04-20 (commit `bf41175`) |
| 12L | D1 Daily Outcome Loop Drift Alert | 1230 | ✅ COMPLETE 2026-04-20 (commit `db4c9d9`) |
| 12M | D2 Weekly Champion/Challenger Retrain Scaffold | 1254 | ✅ COMPLETE 2026-04-20 (commit `12cffd7`) |
| 12N | Sizing Phase Auto-Advance (Phase E1/E2) | 1285 | Listed |

### 5.2 Section 13 — Post-Section-12 Diagnostic Fixes

Three sub-blocks:

- **Batch 1 — ROI-Positive Fixes**: B1-1 through B1-5, all marked ✅ COMPLETE 2026-04-20 in commit `fc64840`.
  - B1-1 — Fix `_RISK_PCT` phase ladder (`backend/risk_engine.py`) — see Section 9.4 caveat below.
  - B1-2 — Fix 12A EOD gate from 19 → 21 UTC (`backend/polygon_feed.py`).
  - B1-3 — Add `earnings_proximity_score` writer (`backend_agents/economic_calendar.py`).
  - B1-4 — Drop `signal_weak` from 12K/12M feature vectors.
  - B1-5 — Wire feature flags for counterfactual and meta-label.
- **Batch 2 — Cleanup and Observability**: B2-1 through B2-5, all marked ✅ COMPLETE 2026-04-20 in commit `41bb1ab`.
- **UI Observability Sprint (Item 11)**: UI-1 (`/trading/learning` page) and CHANGE 0 (`get-learning-stats` Edge Function) shipped 2026-04-20 in commit `0149877`.

### 5.3 AI architecture cross-references

| AI architecture spec | TASK_REGISTER entry it leans on |
|----------------------|----------------------------------|
| Item 6 (Meta-Labeler) | 12K (scaffold complete, dormant until 100 closed trades) |
| Item 10 (Counterfactual P&L Attribution) | 12E (counterfactual engine shipped, observability-only) |
| Item 13 (Realized-vs-Modeled Drift Detection) | 12L (drift alert shipped, model-output drift only) |
| Phase ladder fix (referenced by Item 12) | Section 13 B1-1 (nominally complete; see Section 9.4) |

---

## 6. Backend Module Map

Line counts: `wc -l`. Last-modified: most recent commit touching the file (`git log -1 --format=%ai`). Purpose: extracted from MASTER_PLAN's "BACKEND MODULE MAP" section (lines 71–112) where listed; otherwise inferred from the file header / one-paragraph code scan.

### 6.1 `backend/` (26 Python modules)

| File | Lines | Purpose | Last Modified |
|------|-------|---------|---------------|
| `backend/main.py` | 2650 | APScheduler entrypoint; all job wiring; admin HTTP endpoints | 2026-04-22 |
| `backend/strategy_selector.py` | 1541 | Picks strategy from prediction output + feature flags + butterfly gates | 2026-04-20 |
| `backend/model_retraining.py` | 1177 | Accuracy tracking, Kelly from DB, **meta-label scaffold (12K)**, **drift alerts (12L)**, **champion/challenger retrain (12M)** | 2026-04-20 |
| `backend/prediction_engine.py` | 999 | Regime classifier (GEX/ZG rule-based today; AI in Phase 2C) | 2026-04-20 |
| `backend/calibration_engine.py` | 934 | Weekly parameter recalibration; sizing-phase advance; adaptive halt threshold | 2026-04-20 |
| `backend/execution_engine.py` | 870 | Tradier order placement; meta-label inference gate; OCO bracket orders | 2026-04-20 |
| `backend/position_monitor.py` | 858 | Open-position monitoring; exit firing; time-stop enforcement | 2026-04-21 |
| `backend/risk_engine.py` | 688 | Kelly sizing; position limits; -3% drawdown halt; `_RISK_PCT` phase ladder | 2026-04-21 |
| `backend/strike_selector.py` | 528 | Strike price selection per strategy (iron condor/butterfly target_credit fix shipped 2026-04-25 in commit `77af9aa`/PR #53) | 2026-04-25 |
| `backend/criteria_evaluator.py` | 502 | 12 go-live criteria evaluation (per D-013) | 2026-04-17 |
| `backend/shadow_engine.py` | 456 | Phase 3B A/B shadow infrastructure; daily AB comparison | 2026-04-20 |
| `backend/mark_to_market.py` | 450 | Position MTM valuation | 2026-04-19 |
| `backend/databento_feed.py` | 447 | Real-time OPRA options trade stream (fixed April 2026 with real SPXW symbols) | 2026-04-20 |
| `backend/counterfactual_engine.py` | 406 | **Item 10 / 12E counterfactual engine — observability-only** | 2026-04-20 |
| `backend/polygon_feed.py` | 956 | VIX, VVIX, indices data; SPX daily-return EOD gate (fixed in B1-2) | 2026-04-20 |
| `backend/tradier_feed.py` | 327 | SPX quotes; options chain | 2026-04-18 |
| `backend/db.py` | 291 | Supabase client wrapper (lazy import) | 2026-04-19 |
| `backend/session_manager.py` | 270 | Daily session lifecycle (fixed April 2026) | 2026-04-19 |
| `backend/capital_manager.py` | 266 | Capital allocation tracking | 2026-04-19 |
| `backend/gex_engine.py` | 265 | GEX from Databento options flow; nearest-wall computation; wall-stability history | 2026-04-20 |
| `backend/strategy_performance_matrix.py` | 229 | D3 regime × strategy performance matrix (12D) | 2026-04-20 |
| `backend/alerting.py` | 217 | Internal alerting plumbing | 2026-04-19 |
| `backend/trading_cycle.py` | 216 | Trading cycle orchestration | 2026-04-21 |
| `backend/market_calendar.py` | 113 | NYSE market calendar (open/close, holidays) | 2026-04-18 |
| `backend/config.py` | 104 | Backend configuration loader | 2026-04-20 |
| `backend/logger.py` | 44 | `structlog` configuration | 2026-04-19 |

**Total `backend/` lines:** approximately 16,000+ Python LOC.

### 6.2 `backend_agents/` (8 Python modules — Phase 2C AI decision layer)

| File | Lines | Purpose | Last Modified |
|------|-------|---------|---------------|
| `backend_agents/synthesis_agent.py` | 628 | Claude API synthesis → trade recommendation (writes `ai:synthesis:latest`) | 2026-04-19 |
| `backend_agents/feedback_agent.py` | 474 | Outcome-feedback to learning loop | 2026-04-19 |
| `backend_agents/economic_calendar.py` | 437 | FRED earnings/macro calendar; **`earnings_proximity_score` writer (B1-3)** | 2026-04-20 |
| `backend_agents/flow_agent.py` | 343 | Unusual Whales / put-call ratio agent | 2026-04-19 |
| `backend_agents/sentiment_agent.py` | 313 | NewsAPI headlines + Fear & Greed | 2026-04-19 |
| `backend_agents/surprise_detector.py` | 260 | Earnings/news surprise detector | 2026-04-19 |
| `backend_agents/macro_agent.py` | 243 | Macro / Fed watch / yield curve | 2026-04-19 |
| `backend_agents/__init__.py` | 0 | Empty package marker | 2026-04-18 |

### 6.3 `backend_earnings/` (7 Python modules — Phase 5A earnings volatility)

| File | Lines | Purpose | Last Modified |
|------|-------|---------|---------------|
| `backend_earnings/edge_calculator.py` | 408 | Historical-vs-implied move comparison | 2026-04-20 |
| `backend_earnings/earnings_monitor.py` | 295 | Earnings position monitoring | 2026-04-20 |
| `backend_earnings/option_pricer.py` | 254 | Earnings-strategy option pricing | 2026-04-19 |
| `backend_earnings/earnings_executor.py` | 227 | Earnings entry/exit execution | 2026-04-19 |
| `backend_earnings/main_earnings.py` | 210 | Standalone earnings scheduler | 2026-04-19 |
| `backend_earnings/earnings_calendar.py` | 205 | AAPL/NVDA/META/TSLA/AMZN/GOOGL schedule | 2026-04-19 |
| `backend_earnings/__init__.py` | 23 | Package init | 2026-04-19 |

### 6.4 `backend_futures/`

Not present at HEAD. MASTER_PLAN line 107 lists it as Phase 5B (12–16 week future build, deferred). The directory does not exist on disk.

---

## 7. Supabase Schema Snapshot

**Total migration files in `supabase/migrations/`:** 68

**Migration files containing at least one `CREATE TABLE` statement:** 14

**Latest migration (lexicographic):** `20260427_trading_feature_flags.sql`

**Latest migration date (from filename):** 2026-04-27

**Earliest migration:** `20260410041231_0271722c-...sql`

### 7.1 Tables defined by `CREATE TABLE` across all migrations (28 unique)

Extraction method: `grep -ihE '^\s*create\s+table\s+(if\s+not\s+exists\s+)?(public\.)?[a-zA-Z_][a-zA-Z0-9_]*' supabase/migrations/*.sql | sort -u`. Subsequent `ALTER TABLE` migrations may have added columns; this list captures table existence only.

| Table | Originating migration | Notes |
|-------|----------------------|-------|
| `public.trading_operator_config` | `20260416172751_*.sql` | Single-row operator config (sizing phase, halt threshold, etc.) |
| `public.trading_sessions` | `20260416172751_*.sql` | **Referenced by AI specs Items 1, 12, 13.** Daily trading session record. |
| `public.trading_prediction_outputs` | `20260416172751_*.sql` | **Referenced by AI specs Items 1, 6, 13.** Prediction outputs row-per-prediction. ALTERed by `20260421_add_counterfactual_pnl.sql` to add 3 counterfactual columns. ALTERed by `20260422_add_prediction_features.sql` and `20260422_ensure_prediction_outcome_columns.sql`. |
| `public.trading_signals` | `20260416172751_*.sql` | Trade-signal record (per D-001 affected modules list). |
| `public.trading_positions` | `20260416172751_*.sql` | **Referenced by AI specs Items 1, 2, 9, 10, 12.** Core trade record. |
| `public.trading_system_health` | `20260416172751_*.sql` | Trading-engine health (per T-Rule 2 isolation: separate from foundation `system_health_snapshots`). |
| `public.trading_model_performance` | `20260416172751_*.sql` | Model accuracy tracking. |
| `public.trading_calibration_log` | `20260416172751_*.sql` | Weekly calibration log. |
| `public.paper_phase_criteria` | `20260417000001_paper_phase_criteria.sql` | 12 go-live criteria state per D-013. |
| `earnings_positions` | `20260426_earnings_system.sql` | Phase 5A earnings positions. |
| `earnings_calendar` | `20260426_earnings_system.sql` | Phase 5A AAPL/NVDA/META/TSLA/AMZN/GOOGL calendar. |
| `public.earnings_trade_outcomes` | `20260422_earnings_trade_outcomes.sql` | Phase 5A earnings outcomes. |
| `earnings_upcoming_scan` | `20260427_earnings_upcoming_scan.sql` | Earnings upcoming scan. |
| `shadow_predictions` | `20260426_ab_shadow_tables.sql` | Phase 3B shadow predictions. |
| `ab_session_comparison` | `20260426_ab_shadow_tables.sql` | Phase 3B A/B comparison (drives `useAbComparison` hook). |
| `trading_ai_briefs` | `20260427_trading_ai_briefs.sql` | Phase 2C AI brief storage. |
| `trading_feature_flags` | `20260427_trading_feature_flags.sql` | Feature-flag table (per `model:meta_label:enabled`, `feedback:counterfactual:enabled`). |
| `public.system_config` | `20260414000221_*.sql` | Foundation: system config |
| `public.invitations` | `20260414000221_*.sql` | Foundation: invitation records |
| `public.job_registry` | `20260412050217_*.sql` | Foundation: job registry |
| `public.job_executions` | `20260412050217_*.sql` | Foundation: job execution log |
| `public.job_idempotency_keys` | `20260412050217_*.sql` | Foundation: idempotency keys |
| `public.mfa_recovery_codes` | `20260412080405_*.sql` | Foundation: MFA recovery codes (per active D-RBAC decision: 10 codes, 8 alphanumeric chars) |
| `public.mfa_recovery_attempts` | `20260412152155_*.sql` | Foundation: MFA recovery attempts |
| `public.system_metrics` | `20260412044940_*.sql` | Foundation: system metrics |
| `public.alert_configs` | `20260412044940_*.sql` | Foundation: alert configs |
| `public.alert_history` | `20260412044940_*.sql` | Foundation: alert history |
| `public.system_health_snapshots` | `20260412043940_*.sql` | Foundation: system health (NOT trading_system_health — T-Rule 2 isolation) |

### 7.2 Tables NOT YET CREATED but referenced by AI architecture specs

For each, "no migration exists for this table name" was verified by `grep -i "<tablename>" supabase/migrations/*.sql` returning no matches across all 68 migration files.

| Table referenced | Spec citing it | Verification |
|------------------|----------------|--------------|
| `item_promotion_records` | Items 1, 4, 12, 13 | NO MIGRATION (verified by grep across all 68 migration files) |
| `strategy_attribution` | Item 2 | NO MIGRATION |
| `trade_counterfactual_cases` | Item 2 | NO MIGRATION |
| `strategy_utility_labels` | Item 2 | NO MIGRATION |
| `capital_allocation_snapshots` | Item 12 | NO MIGRATION |
| `drift_metric_snapshots` | Item 13 | NO MIGRATION |
| `drift_alerts` | Item 13 | NO MIGRATION |
| `drift_policy_versions` | Item 13 | NO MIGRATION |
| `replay_eval_runs` | Item 4 | NO MIGRATION |
| `replay_eval_cases` | Item 4 | NO MIGRATION |
| `replay_eval_results` | Item 4 | NO MIGRATION |

### 7.3 Important schema clarification — `counterfactual_pnl`

The migration `20260421_add_counterfactual_pnl.sql` does NOT create a table named `counterfactual_pnl`. It uses `ALTER TABLE public.trading_prediction_outputs ADD COLUMN IF NOT EXISTS` to add three columns:

| Column added to `trading_prediction_outputs` | Type | Purpose |
|----------------------------------------------|------|---------|
| `counterfactual_pnl` | `NUMERIC(10,2)` | Simulated P&L (1-contract basis, USD) had the no-trade signal instead opened a position. |
| `counterfactual_strategy` | `TEXT` | Strategy type used for the counterfactual simulation (defaults to `iron_condor`). |
| `counterfactual_simulated_at` | `TIMESTAMPTZ` | UTC timestamp when the counterfactual simulation labeled the row. |

Plus a partial index to accelerate the "no-trade rows not yet simulated" query path. Per the migration header: "Pure observability — never read by any trading-decision path."

This is flagged in **Risks / Follow-up** because the prompt's Section 7 boilerplate listed `counterfactual_pnl` as a table referenced by AI Spec Item 10. **It is a column triple, not a table.** Phase 1 P1.3 audits for Item 10 and Item 12 should treat `counterfactual_pnl` as a column-on-`trading_prediction_outputs`, not as a standalone table.

---

## 8. Existing Partial Implementations Relevant to AI Architecture Specs

For each spec item, claims were verified by reading the actual referenced commit (`git show`), inspecting the named files, and grepping for relevant patterns. Where the prompt's claim was inaccurate, the corrected fact is in **bold** with a note.

### Item 1 — AI Risk Governor

- **Status:** NOT YET IMPLEMENTED.
- **Verification:** `ls backend/ | grep -iE 'governor|risk_governor'` returns no matches.
- **Closest existing logic:** `backend/risk_engine.py` (688 lines) — rule-based risk caps, Kelly sizing, daily -3% halt, `_RISK_PCT` phase ladder (lines 78–83), `_DEBIT_RISK_PCT` strategy-specific overrides (lines 103–111).

### Item 2 — Strategy Attribution

- **Status:** NOT YET IMPLEMENTED.
- **Verification:** No file matches "attribution" in `backend/`. No `strategy_attribution` / `trade_counterfactual_cases` / `strategy_utility_labels` migrations.
- **Closest existing logic:** `backend/strategy_performance_matrix.py` (229 lines, 12D — D3 Regime × Strategy Performance Matrix) provides regime × strategy aggregation but not per-trade attribution.

### Item 3 — Synthetic Counterfactual Case Generation

- **Status:** NOT YET IMPLEMENTED.
- **Verification:** No "synthetic" or "case_generation" files. The existing `counterfactual_engine.py` is observability over real no-trade signals (Item 10 / 12E), not synthetic case generation.

### Item 4 — Replay Harness

- **Status:** NOT YET IMPLEMENTED.
- **Verification:** `ls backend/ | grep -iE 'replay'` returns no matches. No `replay_eval_*` migrations exist.

### Item 5 — Volatility Fair-Value Engine (HAR-RV)

- **Status:** NOT YET IMPLEMENTED.
- **Verification:** No HAR-RV file in `backend/`. Closest existing logic is `backend/polygon_feed.py:realized_vol_20d` Redis writer (12A, fixed in B1-2 to use 21:00 UTC EOD gate).

### Item 6 — Meta-Labeler

- **Status:** SCAFFOLD EXISTS (dormant — activates at ≥100 closed paper trades).
- **TASK_REGISTER reference:** Section 12K (line 1190) — ✅ COMPLETE 2026-04-20 (commit `bf41175`).
- **Commit verification:** `git show bf41175` confirms the commit message `feat(ml): Loop 2 meta-label model scaffold (12K)`.
- **Files added/touched by `bf41175`:**
  - `backend/model_retraining.py` (+203 lines) — `train_meta_label_model()` and `run_meta_label_champion_challenger()` (later refined in 12M).
  - `backend/execution_engine.py` (+82 lines) — meta-label inference gate before order placement.
  - `backend/main.py` (+14 lines) — scheduler wiring.
  - `backend/tests/test_meta_label_model.py` (new, +493 lines) — test coverage.
- **Correction vs. prompt boilerplate:** The prompt's "grep for meta_label in backend/ — list files" yields no top-level `backend/meta_label*.py` file. The scaffold lives **inside** `backend/model_retraining.py` and `backend/execution_engine.py`, plus the dedicated test file. There is no standalone meta-label module.
- **Feature flag:** `model:meta_label:enabled` (Redis key, fail-open ENABLED) — wired in B1-5.
- **Feature vector dimensionality:** 9 features (was 10 before B1-4 dropped the constant `signal_weak`).

### Item 7 — Adversarial Pre-Trade Review

- **Status:** NOT YET IMPLEMENTED.
- **Verification:** No file matches "adversarial" or "pretrade_review" in `backend/` or `backend_agents/`.

### Item 8 — OPRA Flow Alpha

- **Status:** NOT YET IMPLEMENTED.
- **Verification:** No "opra_alpha" file. The existing `backend/databento_feed.py` (447 lines) ingests OPRA trades but only writes `databento:opra:trades` Redis list — no alpha-extraction logic. `backend_agents/flow_agent.py` (343 lines) is the closest relevant agent.

### Item 9 — Exit Optimizer

- **Status:** NOT YET IMPLEMENTED.
- **Verification:** No "exit_optimizer" file. Existing exit logic lives in `backend/position_monitor.py` (858 lines) — rule-based time stops (D-010 2:30 PM short-gamma, D-011 3:45 PM long-gamma) and CV_Stress conditions (D-017).

### Item 10 — Counterfactual P&L Attribution

- **Status:** SCAFFOLD EXISTS (observability-only, never read by trading-decision path).
- **TASK_REGISTER reference:** Section 12E (line 841) — D4 Counterfactual Engine, marked SHIPPED.
- **Commit verification:** `git show 2400e98` confirms `feat(learning): counterfactual engine D4 (12E)` (2026-04-20).
- **Files added/touched by `2400e98`:**
  - `backend/counterfactual_engine.py` (new, +349 lines at commit time; **currently 406 lines** at HEAD due to subsequent edits).
  - `backend/main.py` (+63 lines) — EOD job wiring.
  - `backend/tests/test_counterfactual_engine.py` (new, +332 lines).
  - `supabase/migrations/20260421_add_counterfactual_pnl.sql` (new, +36 lines) — adds 3 columns to `trading_prediction_outputs`, NOT a separate table (see §7.3).
- **EOD job:** runs at 4:25 PM ET; processes `no_trade_signal=True` predictions; writes simulated P&L back to `trading_prediction_outputs.counterfactual_pnl`.
- **Feature flag:** `feedback:counterfactual:enabled` (Redis key, fail-open ENABLED) — wired in B1-5.

### Item 11 — Event-Day Playbooks

- **Status:** NOT YET IMPLEMENTED.
- **Verification:** No "playbook" file. Closest existing logic: `backend_agents/economic_calendar.py:_compute_earnings_proximity_score()` (B1-3, 2026-04-20) — produces a 0–1 proximity score consumed by `prediction_engine`, but is not a playbook.

### Item 12 — Dynamic Capital Allocation

- **Status:** NOT YET IMPLEMENTED.
- **Verification:** No `capital_allocation_snapshots` migration. Existing capital tracking lives in `backend/capital_manager.py` (266 lines) but does not expose a snapshot table or dynamic-allocation engine. Sizing-phase auto-advance (12N, ladder per `_RISK_PCT` in `risk_engine.py`) is the closest existing surface.

### Item 13 — Realized-vs-Modeled Drift Detection

- **Status:** SCAFFOLD EXISTS (model-output drift only — does NOT yet cover realized-vs-modeled metric drift).
- **TASK_REGISTER reference:** Section 12L (line 1230) — ✅ COMPLETE 2026-04-20 (commit `db4c9d9`).
- **Commit verification:** `git show db4c9d9` confirms `feat(learning): D1 daily outcome loop drift alert (12L)` (2026-04-20).
- **Files added/touched by `db4c9d9`:**
  - `backend/model_retraining.py` (+117 lines) — drift-alert logic. Confirmed: 37 occurrences of `drift` in this file at HEAD.
  - `backend/main.py` (+38 lines) — scheduler wiring.
  - `backend/tests/test_prediction_drift.py` (new, +264 lines).
- **Correction vs. prompt boilerplate:** The prompt says "File: backend/model_retraining.py ([line count, grep for drift])". The drift logic is a sub-section of `model_retraining.py` (1177 lines total), not a standalone file. No `drift_metric_snapshots` / `drift_alerts` / `drift_policy_versions` migrations exist — those tables remain part of the proposed Item 13 spec.

### All other items (none currently shipped)

Items 1, 2, 3, 4, 5, 7, 8, 9, 11, 12 — no existing partial scaffolds at HEAD.

---

## 9. Known Governance Debt (Pre-existing, Acknowledged, Deferred)

Each item below was re-verified against the actual repo state at this snapshot.

### 9.1 `trading-docs/00-governance/change-control-policy.md` missing

- **Verification:** `ls trading-docs/00-governance/change-control-policy.md` returns "No such file or directory".
- **Referenced from:**
  - `.cursorrules` — "Follow the exact 9-step workflow in `trading-docs/00-governance/change-control-policy.md`..."
  - `.lovable/rules.md` — same wording.
  - `trading-docs/08-planning/feature-proposals.md` — Related Documents link to `../00-governance/change-control-policy.md`.
- **Status:** STILL ACTIVE GOVERNANCE DEBT.
- **Decision:** Deferred to a separate cleanup task per consolidated plan §1; explicitly out of scope for Phase 0 / Phase 1 P1.1.

### 9.2 Reference indexes missing in `trading-docs/07-reference/`

- **Files currently in `trading-docs/07-reference/`:**
  - `README.md`
  - `component-inventory.md`
  - `database-migration-ledger.md`
  - `permission-index.md`
  - `route-index.md`
- **Files mandated by `.cursorrules` "REFERENCE INDEX MAINTENANCE":**
  - `trading-docs/07-reference/function-index.md` — **MISSING**
  - `trading-docs/07-reference/permission-index.md` — present
  - `trading-docs/07-reference/route-index.md` — present
  - `trading-docs/07-reference/event-index.md` — **MISSING**
  - `trading-docs/07-reference/config-index.md` — **MISSING**
  - `trading-docs/07-reference/env-var-index.md` — **MISSING**
- **Status:** STILL ACTIVE GOVERNANCE DEBT (4 missing indexes).
- **Decision:** Deferred to a separate cleanup task per consolidated plan §1; explicitly out of scope for Phase 1 P1.1.

### 9.3 `master-plan.md` case mismatch in `feature-proposals.md`

- **Verification:** `sed -n '24,30p' trading-docs/08-planning/feature-proposals.md` and `sed -n '82,86p'` confirm both literal `master-plan.md` references are still present:
  - **Line 26:** `- **NO** proposal may bypass the master plan — approved proposals MUST be added to `master-plan.md` before implementation begins`
  - **Line 84:** `| `plan_section_id` | When approved | Reference to PLAN-XXX-NNN in master-plan.md |`
- **Status:** STILL ACTIVE GOVERNANCE DEBT.
- **Decision:** Deferred to Phase 4 of the consolidated plan, when `feature-proposals.md` is next opened to add FP-001 (AI architecture).
- **Note:** The Enforcement Rule's `master-plan.md` reference was preserved verbatim during P0.1 because the P0.1 spec mandated copying that section verbatim from the foundation file. Step 5 references inside `feature-proposals.md` *were* updated in P0.1 to use `trading-docs/08-planning/MASTER_PLAN.md`. The remaining lowercase references on lines 26 and 84 are the only residue.

### 9.4 Phase 2 risk ladder non-monotonic in `backend/risk_engine.py`

- **Current `_RISK_PCT` (verified at HEAD, lines 78–83 of `backend/risk_engine.py`):**
  ```
  1: {"core": 0.010,  "satellite": 0.0050},    # Phase 1: 2× prior baseline — paired w/ 2026-04-20 width widening
  2: {"core": 0.0075, "satellite": 0.00375},   # Phase 2: E1 gate (UNCHANGED — see ladder follow-up in Item 13)
  3: {"core": 0.010,  "satellite": 0.0050},    # Phase 3: E2 gate (UNCHANGED — see ladder follow-up in Item 13)
  4: {"core": 0.010,  "satellite": 0.0050},    # Phase 4: manual only — same as phase 3
  ```
- **Status:** STILL ACTIVE GOVERNANCE DEBT — but with nuance.
  - TASK_REGISTER Section 13 Batch 1 B1-1 (commit `fc64840`, 2026-04-20) declares this fixed: *"Phase 1 UNCHANGED (0.005/0.0025). Test: assert phase1 ≠ phase2 ≠ phase3."*
  - But the actual Phase 1 value at HEAD is **0.010 / 0.0050** (doubled from the pre-B1-1 baseline of 0.005 / 0.0025), per the inline comment "2× prior baseline — paired w/ 2026-04-20 width widening".
  - Net result: Phase 1 (0.010) > Phase 2 (0.0075). The ladder is **non-monotonic again**, for a different reason than the original B1-1 fix targeted. The inline file comments label phases 2 and 3 as "UNCHANGED — see ladder follow-up in Item 13" — but Item 13 does not contain a re-fix follow-up entry for this regression.
- **AI Spec Item 12 (Capital Allocation):** Per the consolidated plan, Item 12 explicitly does NOT fix this. Decision: separate task, target before Day 40 of paper trading.
- **Risk implication:** B1-1's regression test (`assert phase1 ≠ phase2 ≠ phase3`) currently passes (0.010 ≠ 0.0075 ≠ 0.010 ≠ 0.010 — well, phases 3 and 4 are equal but the original test was phases 1/2/3). The test does not enforce monotonicity, only inequality between adjacent phases.

### 9.5 `.cursorrules` vs `.lovable/rules.md` structural divergence

- **Verification:** `grep -n '^## ' .cursorrules` and `.lovable/rules.md`:
  - `.cursorrules` section order: ... `## FEATURE PROPOSAL PROTOCOL` (185) → `## SPEC VERIFICATION PROTOCOL` (197) → `## QUALITY MANDATE` (217) → `## PHASE GATE VERIFICATION PROTOCOL` (264) → `## FINAL WARNING` (275).
  - `.lovable/rules.md` section order: ... `## REFERENCE INDEX MAINTENANCE AND RECONCILIATION` (123) → `## PHASE GATE VERIFICATION PROTOCOL` (136) → `## DEPENDENCY ORDER` (148) → ... → `## FEATURE PROPOSAL PROTOCOL` (199) → `## SPEC VERIFICATION PROTOCOL` (211) → `## QUALITY MANDATE` (231) → `## FINAL WARNING` (278).
- **Differences observed:**
  - Section name: `.cursorrules` says `## REFERENCE INDEX MAINTENANCE`; `.lovable/rules.md` says `## REFERENCE INDEX MAINTENANCE AND RECONCILIATION` (latter has an extra paragraph defining the reconciliation rule).
  - Position of `PHASE GATE VERIFICATION PROTOCOL`: AFTER Quality Mandate in `.cursorrules` (line 264); BEFORE Quality Mandate in `.lovable/rules.md` (line 136).
- **Status:** STILL ACTIVE GOVERNANCE DEBT.
- **Decision:** Pre-existing (predates Phase 0); flagged by Cursor during P0.2 work; parity audit deferred to a separate cleanup task. The SVP block added in P0.2 IS byte-identical across both files (`diff` exit 0 verified at P0.2 commit time).

### 9.6 (NEW) `counterfactual_pnl` semantic mismatch in consolidated plan

- **Discovery during P1.1:** The consolidated plan and the P1.1 task prompt both refer to `counterfactual_pnl` under "Section 7 — Supabase Schema Snapshot" alongside `trading_positions`, `trading_prediction_outputs`, etc. — implying it is a table.
- **Reality (verified):** It is three columns on `trading_prediction_outputs`, added by `supabase/migrations/20260421_add_counterfactual_pnl.sql` via `ALTER TABLE ... ADD COLUMN`. There is no table named `counterfactual_pnl`.
- **Status:** NEW GOVERNANCE DEBT discovered during P1.1.
- **Recommendation:** Phase 1 P1.3 audits for Item 10 (Counterfactual P&L Attribution) and Item 12 (Capital Allocation) should treat `counterfactual_pnl` as a column triple on `trading_prediction_outputs`. The consolidated plan's wording should be tightened in Phase 5 P5.X (or earlier) to avoid downstream confusion.

---

*Phase 1 P1.1 — produced 2026-04-26 by Cursor AI under SPEC VERIFICATION PROTOCOL. Owner: tesfayekb.*
