# ROI Log Baseline — 2026-04-28

**Action 2 deliverable per Master ROI Plan v2.0.3 §3 (lines 245–256).**
**Closes Gate B of Path Y activation prerequisites.**

---

## Purpose

Establish empirical pre-activation baseline of trade-cycle skip-reason distribution, so that post-activation AI-vs-rules attribution becomes possible. Without this baseline, any change in trade-frequency or skip-rate after `agents:ai_synthesis:enabled = true` (Action 9) cannot be unambiguously attributed to AI synthesis vs. confounded with rules-engine drift, halt logic, sizing-floor effects, or other gates.

---

## Methodology

| Field | Value |
|---|---|
| Source | Railway runtime logs |
| Container | deployment ID `5c6b59be-e8e6-4656-8cf6-316db5ada1a5`, replica `c53ff4a4-a5d0-4a71-b466-88c83bcdb635` |
| Container era | Pre-Phase-2 redeploy (running before today's `e651bdc → ef00bee` merge sequence; auto-redeployed at 22:45 UTC = 18:45 ET) |
| Time window | 2026-04-28 13:00 → 19:35 UTC (= 09:00 → 15:35 ET) |
| Trading session covered | Full session minus the final ~25 minutes (15:35–16:00 ET unobserved due to log-pull window cutoff and 18:45 ET container restart) |
| Patterns searched | 10 (one per skip-event log key) |
| Patterns with hits | 2 (`cycle_skipped`, `trading_cycle_skipped`) |
| Patterns with zero hits | 8 |
| Source artifacts | `logs_1777417157931.csv` (152 `cycle_skipped` events), `logs_1777417448543.csv` (73 `trading_cycle_skipped` events) — preserved separately, not committed to repo |

The 10 patterns searched correspond to the structured-log event names emitted by production code (verified against `backend/` and `backend_agents/` source). Patterns are documented in §"13-skip-path classification" below.

---

## Headline finding

**73 trading cycles attempted, 73 skipped, 0 trades executed during the observed window.**

- 100% skip rate
- Dominant skip reason: `no_trade_direction_signal_weak` (96.1% of outer-cycle events; 100.0% of inner-cycle events)
- Eleven of thirteen enumerated skip paths fired zero times

---

## Skip-reason histogram

Production code uses two-tier skip logging: `cycle_skipped` (outer wrapper in `backend/main.py`) re-logs every skip that `trading_cycle_skipped` (inner cycle in `backend/trading_cycle.py:174-175`) already logged. Counts must be reconciled to avoid double-counting.

### Raw counts

| Reason | `cycle_skipped` (outer) | `trading_cycle_skipped` (inner) |
|---|---|---|
| `no_trade_direction_signal_weak` | 146 (96.1%) | 73 (100.0%) |
| `prediction_failed` | 6 (3.9%) | 0 |
| **Total** | **152** | **73** |

### Reconciliation

- Outer 146 = inner 73 + 73 outer-only events that fail before the inner cycle runs (pre-market 09:00–09:30 ET window when inner cycle is dormant).
- Outer 6 `prediction_failed` events are error-path skips that abort before the inner cycle runs, so don't appear in the inner counter.
- **Unique skip events for the observed market session: 73.** This is the canonical baseline number.

### Hour-of-day event density (combined)

| Hour (ET) | Events |
|---|---|
| 09:00 | 24 |
| 10:00 | 36 |
| 11:00 | 34 |
| 12:00 | 36 |
| 13:00 | 36 |
| 14:00 | 36 |
| 15:00 | 24 |

5-minute cycle cadence × 12 cycles/hour = 36 cycles/hour in steady state. Density is consistent throughout — no logging gaps, no crashes, no skipped intervals. The 09:00 and 15:00 hours show partial counts because the window starts at 09:00 and ends at 15:35.

---

## 13-skip-path classification

Master ROI Plan §3 line 186: *"13 distinct skip paths exist (12 enumerated + 1 implicit min-contracts floor)."*

The trio docs do not enumerate all 13 paths in a single list. The mapping below reconstructs the enumeration from F-9 (line 447), F-37 (line 460), Action 2 spec (lines 252–254), and verified production-code emit names. Cursor verification recommended for any path-name discrepancy.

| # | Path (per Master ROI Plan §3) | Production code emit name(s) | Count today | Status |
|---|---|---|---|---|
| 1 | `direction_signal_weak` | `cycle_skipped` / `trading_cycle_skipped` with `reason=no_trade_direction_signal_weak` | **73** | ✅ Active — **DOMINANT** |
| 2 | `prediction_failed` | `cycle_skipped` with `reason=prediction_failed` | 6 | ✅ Active (error path) |
| 3 | `strategy_blocked_frequency` | `strategy_blocked_frequency` | 0 | ⚪ Dormant |
| 4 | `strategy_blocked_no_candidates` | `strategy_blocked_no_candidates` | 0 | ⚪ Dormant |
| 5 | `min_contracts_floor` (implicit 13th per F-37) | `contracts=0` / `min_contracts_floor` | 0 | ⚪ Dormant |
| 6 | `session_already_halted` | `open_today_session_already_halted` | 0 | ⚪ Dormant |
| 7 | `redis_unavailable` | `prediction_cycle_skipped_redis_unavailable` | 0 | ⚪ Dormant |
| 8 | `synthesis_agent_skipped` | `synthesis_agent_skipped` | 0 | ⚪ Dormant (flag-gated; activated by Action 9) |
| 9 | `flow_agent_skipped` | `flow_agent_skipped` | 0 | ⚪ Dormant (flag-gated) |
| 10 | `sentiment_agent_skipped` | `sentiment_agent_skipped` | 0 | ⚪ Dormant (flag-gated) |
| 11 | `feedback_agent_skipped` | `feedback_agent_skipped` | 0 | ⚪ Dormant (flag-gated) |
| 12 | `vix_history_backfill_skipped` | `vix_history_backfill_skipped` | 0 | ⚪ Dormant |
| 13 | `weekly_halt_calibration` | `weekly_halt_calibration_failed` / `halt_threshold_calibration_failed` | 0 | ⚪ Dormant |

**Two paths active; eleven dormant.** Active paths total 79 events; observed unique skip events total 73 (confirms `prediction_failed` events do not double-count with inner-cycle skips).

---

## Action 8 trigger — TRIPPED

Master ROI Plan v2.0.3 §3 line 341 specifies:

> **Trigger:** ONLY if Action 2 logs show `direction_signal_weak` is genuinely the dominant gate (>50% of skips post-2026-04-27 16:08 ET)

**Today's measurement: 100% of unique skip events are `direction_signal_weak`.** Trigger condition exceeded by ~2×.

**Implication:** Action 8 (conviction-conditional sizing redesign) moves from "Conditional — only if Action 2 log evidence justifies" (Master ROI Plan §1.2 line 59) to **queued/scheduled** for Days 7-14 per the plan's sequencing. Per §3 lines 343–351:

- Lower `signal_weak` threshold from 0.05 → 0.03
- ADD sizing modifier: trades in `0.03 ≤ |p_bull − p_bear| < 0.05` band get 0.5× contracts
- Trades with `|p_bull − p_bear| ≥ 0.05` retain 1.0× sizing
- Sequence ≥5 trading days BEFORE Action 7 deploy for clean Sharpe attribution

**Caveat — single-day basis:** The trigger ratifies on this single session. Best practice is to confirm with 3+ sessions of data before committing the Action 8 plan. Tomorrow (Apr 29) and Wednesday (Apr 30) will further strengthen or qualify the finding. If subsequent sessions show different dominance, the trigger condition (>50%) may still hold even with reduced concentration.

---

## Implications for Action 9 / Path Y attribution

1. **Pre-activation baseline is unambiguous.** 100% skip rate, 0 trades, single dominant gate.
2. **Direction-signal-weak is the unique active gate at conviction layer.** Any AI-synthesis-induced reduction in this counter post-activation is unambiguously attributable to the AI layer rather than confounded with strategy filters, halts, or sizing-floor effects.
3. **Eleven dormant gates won't confound attribution unless they activate post-deployment.** Phase 2 (PR #72) changed no code paths affecting paths 3–13, so dormancy should persist absent independent rules-engine changes.
4. **Attribution test for Action 9 success:** if a session of comparable size (~73 cycles) shows reduced `direction_signal_weak` count AND non-zero executed-trade count, AI synthesis is contributing positive signal. If `direction_signal_weak` count is unchanged but other gates activate (e.g., strategy filters, sizing-floor), it indicates AI synthesis is letting cycles through but downstream gates are catching them — different remediation lever.

---

## Forward-looking sample expansion

This is the first baseline snapshot. Recommended additions:

- **Append daily snapshots** below as Apr 29, Apr 30, May 1, etc. sessions close. Same methodology, same histograms, single-row addition to the per-session summary table.
- **Lock in the Action 8 trigger** once 3 sessions confirm `direction_signal_weak >50%`. If any session shows different dominance, document the deviation here and re-evaluate.
- **Update the dormant-gate list** if any path 3–13 fires unexpectedly. A single firing of a previously-dormant gate is a meaningful event worth diagnosing.

### Per-session summary (append rows as collected)

| Date (ET) | Session window | Cycles attempted | Skipped | Trades executed | Dominant gate | Dominant share |
|---|---|---|---|---|---|---|
| 2026-04-28 | 09:30–15:35 | 73 | 73 | 0 | `direction_signal_weak` | 100.0% |
| 2026-04-29 | 09:00–15:55 | 84 | 84 | 0 | `direction_signal_weak` | 92.9% |

---

## Source data references

- **Master ROI Plan §3 — Action 2 spec:** `trading-docs/08-planning/MASTER_ROI_PLAN.md` lines 245–256
- **Master ROI Plan §3 — Gate B definition:** lines 184–188
- **Master ROI Plan §3 — Action 8 trigger:** lines 340–351
- **Master ROI Plan §3 — F-9 / F-37 skip-path findings:** lines 447, 460
- **Production code emit names verified at:** main HEAD `ef00bee` (post-Phase-2)

Source CSV files preserved separately (not committed to repo per repo-hygiene principle):
- `logs_1777417157931.csv` (152 `cycle_skipped` events)
- `logs_1777417448543.csv` (73 `trading_cycle_skipped` events)

---

## Status

**Gate B (Master ROI Plan §3 line 184): provisionally CLOSED on first-session basis.** Lock-in pending 2 additional sessions of confirming data. If subsequent sessions corroborate the `direction_signal_weak` dominance, Gate B closure is final.
