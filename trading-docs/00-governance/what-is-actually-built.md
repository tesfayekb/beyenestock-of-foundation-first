# What Is Actually Built vs What Was Planned

This file bridges the original MARKETMUSE_MASTER spec (aspirational)
with what actually exists in the codebase today. Cursor and Lovable
must read this to avoid implementing things that already exist or 
trying to use models that were never built.

## Models Referenced in approved-decisions.md — Build Status

| Decision | Spec Said | Reality | Status |
|---|---|---|---|
| D-021 | HMM + LightGBM regime classifiers | VVIX Z-score rule-based | Not built — rule-based is what runs |
| D-015 | Predictive LightGBM slippage | Static dict by strategy type | Not built — static dict is what runs |
| D-016 | Vol blending: max(realized, 0.70×implied) | Basic IV/RV filter | Partially built |

When D-021 says "HMM ≠ LightGBM → size 50% reduction" — the
current implementation replaces this with regime_agreement flag.
If prediction_engine and GEX agree on direction → full size.
If they disagree → 50% size. Do not try to implement HMM or LightGBM
until explicitly instructed in a Phase 3A task.

## Phase Numbering Bridge

| Old Spec Phase | New Plan Phase | Status |
|---|---|---|
| Phase 1 (Data Infrastructure) | Phase 1 (Stabilize) | Complete |
| Phase 2 (Virtual Trade Engine) | Phase 1 (Stabilize) | Complete |
| Phase 3 (Admin Console) | Phase 1 (Stabilize) | Complete |
| Phase 4 (Paper Phase 45 days) | Phase 1-2 (ongoing) | In progress |
| Phase 5 (Live Execution) | After Phase 3 A/B gate | Blocked |
| Phase 6 (Learning Engine) | Phase 3A (Meta-label) | Blocked until 100 trades |
| Phase 7 (Phase 3 Sizing) | After Phase 3 validates | Blocked |

## Strategy Library — Actual Status

| Strategy | In Codebase | Feature Flag | Paper Tested | Production Ready |
|---|---|---|---|---|
| Iron Condor | ✅ | N/A (default) | Backtest only | ✅ with monitoring |
| Iron Butterfly | Partial | OFF | No | Phase 2A |
| Long Straddle | No | OFF | No | Phase 2A |
| Bull Call Spread | Slippage table only | OFF | No | Phase 2B |
| Bear Put Spread | Slippage table only | OFF | No | Phase 2B |
| Calendar Spread | No | OFF | No | Phase 3C |
