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
| Iron Butterfly | ✅ wired (Phase 2B) | `strategy:iron_butterfly:enabled` (default OFF) | No | Phase 2B activation |
| Long Straddle | ✅ wired (Phase 2B) | `strategy:long_straddle:enabled` (default OFF) | No | Phase 2B activation |
| Bull Call Spread | ✅ wired via AI hint (Phase 2B) | `strategy:ai_hint_override:enabled` (default OFF) | No | Phase 2B activation |
| Bear Put Spread | ✅ wired via AI hint (Phase 2B) | `strategy:ai_hint_override:enabled` (default OFF) | No | Phase 2B activation |
| Calendar Spread | No | OFF | No | Phase 3C |

## Intelligence Agents — Actual Status (Phase 2A + 2C)

All agents live in `backend_agents/` and communicate with `backend/` only
via Redis. Every external API call has a try/except fallback. Each agent
has its own feature flag; flags default OFF so deployment alone changes
nothing.

| Agent | In Codebase | Redis Output | Feature Flag | Schedule | Status |
|---|---|---|---|---|---|
| Economic Calendar | ✅ (Phase 2A) | `calendar:today:intel` (24hr) | N/A — always reads, classifies day-type | 04:30 ET cron | Active |
| Macro Agent | ✅ (Phase 2A) | `ai:macro:brief` | N/A — always runs when calendar present | 06:00 ET cron | Active |
| Synthesis Agent (Claude) | ✅ (Phase 2A) | `ai:synthesis:latest` (30min) | `agents:ai_synthesis:enabled` (default OFF) | 08:50 ET cron | Wired, gated |
| Surprise Detector | ✅ (Phase 2A) | updates `ai:synthesis:latest` | N/A — only runs on catalyst days | 10:00, 14:00 ET cron | Active |
| Flow Agent (Unusual Whales + Polygon P/C) | ✅ (Phase 2C) | `ai:flow:brief` (8hr) | `agents:flow_agent:enabled` (default OFF) | 08:45 ET cron + every 30min | Wired, gated |
| Sentiment Agent (NewsAPI + F&G + gap) | ✅ (Phase 2C) | `ai:sentiment:brief` (8hr) | `agents:sentiment_agent:enabled` (default OFF) | 08:30 ET cron | Wired, gated |

Synthesis agent now reads flow + sentiment briefs from Redis on every
run (Phase 2C), computes a `confluence_score` ∈ [0.0, 1.0] across macro
/ flow / sentiment directions, and includes them in the Claude prompt.
When the per-agent flags are OFF the briefs are simply absent from
Redis, so confluence collapses to macro-only and the prompt's flow /
sentiment sections fall back to neutral defaults — synthesis output
remains valid.
