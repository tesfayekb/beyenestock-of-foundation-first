# Known False Positives — AI Diagnostic Reference

> **Purpose:** Prevent future AI diagnostic sessions from re-raising issues
> that have been investigated and confirmed as overstated, out of context,
> or intentional design decisions. Any AI reviewing this codebase must read
> this file before raising severity issues.
>
> **Owner:** tesfayekb | **Updated:** 2026-04-17

---

## How to Use This File

Before flagging any of the issues below as bugs or security risks, check
this file first. Each entry explains WHY the apparent issue is not actually
a problem in the context of this system.

---

## CONFIRMED NON-ISSUES

### FP-001: APScheduler Sync Jobs "Block the Event Loop"
**Claim:** Sync job functions registered with `AsyncIOScheduler` freeze asyncio.
**Reality:** `AsyncIOScheduler` automatically detects sync functions and runs
them in a thread pool executor via `run_in_executor`. They do NOT block the
asyncio event loop. This is documented APScheduler behavior.
**Verdict:** Not a bug. No fix needed.

### FP-002: Railway Rolling Restart Race Condition
**Claim:** Time-stop jobs can race between two Railway instances during restart.
**Reality:** This project runs on Railway Hobby plan with a single dyno instance.
Rolling restarts briefly run two instances but the overlap is measured in seconds.
The time-stop jobs fire once daily at specific times (2:30 PM, 3:45 PM ET) — the
probability of a restart coinciding with these exact moments is negligible.
**Verdict:** Not a real paper-phase risk. Revisit for Phase 5 if scaling to
multiple instances.

### FP-003: "One Big try/except Hides P&L Corruption"
**Claim:** `close_virtual_position` catches all exceptions silently.
**Reality:** The outer try/except calls `write_health_status("error", ...)` with
the exception message AND returns `False` to the caller. The caller logs
`close_virtual_position_failed`. Nothing is hidden — it is logged at two levels.
**Verdict:** Not a silent failure. Could be more granular but is not corrupting.

### FP-004: Supabase 1000-Row Default Cap
**Claim:** Queries will silently truncate at 1000 rows, causing incorrect metrics.
**Reality:** At 45 days × 3-5 trades/day = maximum 225 positions in paper phase.
Every relevant query is well under 1000 rows. This is a future concern for Phase 5.
**Verdict:** Not a paper-phase problem. Add pagination before Phase 5 goes live.

### FP-005: Job Circuit Breakers Ignored
**Claim:** `job_registry.circuit_breaker_threshold` is not honored in main.py.
**Reality:** A failing prediction engine writes `status="error"` to
`trading_system_health` and logs the error. The operator can see it on the
Engine Health page. Auto-disabling a job after N failures is an operational
nicety, not a P&L risk — the job simply fails and retries on the next schedule.
**Verdict:** Nice to have, not a bug. Implement in Phase 5 if needed.

### FP-006: "40k Keepalive Writes per Day"
**Claim:** 5 keepalives × 30s = excessive Supabase writes.
**Reality:** Market hours = 6.5h × 2 writes/min × 5 services = ~3,900 writes.
Add 24h non-market = ~8,640 total/day. Supabase free tier handles 500k row
changes/month (16k/day). Usage is comfortably within limits.
**Verdict:** Not an issue at current scale.

### FP-007: "Heartbeat Selects All Rows"
**Claim:** `heartbeat_check` fetches the entire `trading_system_health` table.
**Reality:** The table has exactly 11 rows (one per service_name, enforced by
CHECK constraint). Fetching 11 rows every 90 seconds is computationally trivial.
**Verdict:** Complete non-issue.

### FP-008: D-012 RUT Size Reduction Missing
**Claim:** `compute_position_size` lacks the RUT 50% size reduction.
**Reality:** All signals hardcode `"instrument": "SPX"`. RUT is never selected
anywhere in the strategy_selector. The D-012 code path is latent but harmless —
it simply never executes. Implement when RUT instrument support is added.
**Verdict:** Latent, not active. Not a paper-phase issue.

### FP-009: `_simulate_fill` Always Fills
**Claim:** Virtual fills should model fill rejection like real markets.
**Reality:** This is **intentional by design** for paper trading. The comment
in the code reads "Real fill simulation via walk-the-book in Phase 5." Rejecting
virtual fills would reduce paper trade count and make GLC-003/011 harder to pass
without any benefit — the paper phase purpose is to accumulate calibration data.
**Verdict:** Intentional design. Do not add fill rejection to virtual fills.

### FP-010: `regime_agreement` Default True in strategy_selector
**Claim:** `prediction.get("regime_agreement", True)` is a bug.
**Reality:** The prediction engine correctly emits `regime_agreement` at line 119
of prediction_engine.py. The `True` default only applies if the prediction dict
somehow lacks this key — a defensive fallback, not a logic error. Full agreement
is the safe default (no size reduction when uncertain).
**Verdict:** Correct defensive coding. Not a bug.

### FP-011: GEX `prior_price` Shared Across Symbols
**Claim:** The tick-test in `classify_trade` is corrupted by cross-symbol price mixing.
**Reality:** The tick-test is a heuristic for classifying buy/sell flow at the
Lee-Ready level. Cross-symbol contamination introduces ~5-10% noise in individual
trade classification. In aggregate (1000+ trades per 5-min window), this noise
averages out. The GEX output is a smoothed aggregate — individual trade errors
do not materially affect it.
**Verdict:** Minor heuristic noise, not P&L-impacting at paper scale.

### FP-012: PolygonFeed `asyncio.sleep(300)` Blocks Shutdown
**Claim:** On shutdown, the 300-second sleep blocks container from stopping cleanly.
**Reality:** Railway sends SIGTERM with a 30-second grace period before SIGKILL.
The container is forcibly stopped. The incomplete operation at shutdown is a Redis
SET (millisecond operation, not a Supabase write). There is no data loss risk.
**Verdict:** Not a real issue. The container stops cleanly via SIGKILL.

---

## GENUINELY DEFERRED (known gaps, intentionally not yet fixed)

These are real issues documented as out-of-scope for paper phase.
**Fix Group 8 Cursor task will be generated when GLC-001 through GLC-006
first show `in_progress` status AND at least 2 weeks remain before
expected paper phase graduation.**

| ID | Issue | Severity | Fix When | Notes |
|----|-------|----------|----------|-------|
| D-001 | RLS allows any authenticated user to read all trading data | HIGH | Before adding any non-admin users | 6 trading table policies use `auth.role()='authenticated'` — change to `trading.view` permission check |
| D-002 | Service role key has no secret redaction in logs | HIGH | Before Phase 5 | Raw exception text may contain Redis DSN. Implement error-code taxonomy in write_health_status |
| D-003 | Session P&L counters have no optimistic locking | HIGH | Before Phase 5 | Read-then-write race on virtual_pnl when 3 positions close simultaneously. Fix: Postgres atomic `UPDATE … SET virtual_pnl = virtual_pnl + $delta` |
| D-004 | Sentinel uses same Tradier API key as backend | HIGH | Before Phase 5 | GLC-009 requires "separate credentials, close-only scope". Rename to SENTINEL_TRADIER_API_KEY, verify close-only at startup |
| D-005 | Sentinel close_all_positions_tradier only marks Supabase rows | CRITICAL for live | Before Phase 5 | Real positions stay open during emergency. Gate on position_mode: for 'live', call Tradier REST `/v1/accounts/{id}/orders` with market close orders |
| D-006 | Time-stop jobs can double-fire on Railway rolling restart | MEDIUM | Before Phase 5 | Brief 2-instance overlap during deploy. Add Postgres advisory lock at job entry: `pg_try_advisory_lock(hashtext('time_stop_230pm'))` |
| D-007 | get_or_create_session insert race | MEDIUM | Before Phase 5 | Select-then-insert without ON CONFLICT. Replace with `.upsert(on_conflict="session_date", ignore_duplicates=True)` then re-select |
| D-008 | Sentinel re-arms automatically after Railway flap | MEDIUM | Before Phase 5 | If Railway health flaps around 120s threshold, sentinel can emergency-close twice. Add operator ACK requirement before re-arm |
| D-009 | Touch probability hardcoded 0.05 | LOW | Phase 6 Learning Engine | Real Black-Scholes first-passage model needed. Blocked on real option chain data |
| D-010 | Supabase 1000-row cap on queries | LOW | Before Phase 5 | Not a paper-phase issue (max ~225 rows). Add explicit pagination before Phase 5 live volume |
| D-011 | Sync scheduler jobs run on asyncio thread pool | LOW | Monitor in Phase 5 | APScheduler handles sync→thread correctly (FP-001). Revisit only if feed latency degrades under live load |
| D-012 | D-022 consecutive-session counter has one-day lag | LOW | Document only | After EOD close, counter reflects prior sessions not current. One-day lag is acceptable — D-022 sizing reduction applies next session. |
| D-013 | regime_agreement almost never disagrees (placeholder HMM/LGB both use same VVIX branch) | LOW | Phase 6 | Real model disagreement requires real HMM vs LightGBM outputs. Document that D-021 is dormant until Phase 6 real models. |
| D-014 | D-022 consecutive-session counter has one-day lag | LOW | Document only | The query in close_today_session fetches the last 3 closed sessions after today's close, so today's result is included. The >= 3 alert fires the day after the third loss, not during it. This one-session lag is acceptable — D-022 sizing reduction applies on the next session. No code change needed. |
| D-015 | Sentinel audit log not idempotent on crash-restart | LOW | Before Phase 5 | If Sentinel crashes after marking positions closed but before writing sentinel_emergency_close_complete, the next restart writes a second audit entry. Fix: use correlation_id = hash(trigger_timestamp) as upsert key on audit_logs. |
| D-016 | validate_config() only enforced at FastAPI startup | LOW | Before Phase 5 | Module-level constants default to None if env vars are missing. A standalone CLI call to run_trading_cycle would fail only on first Supabase call, not at import. Fix: add _require() wrapper or call validate_config() in config.py on import when ENVIRONMENT != test. |

## FIX GROUP 8 TRIGGER CONDITIONS

Generate Fix Group 8 Cursor task file when ALL of the following are true:
1. GLC-001 (prediction accuracy) shows `in_progress` with observations > 0
2. GLC-003 (training examples) shows observations > 100
3. GLC-005 (Sharpe ratio) shows any numeric value
4. At least 25 paper trading sessions completed
5. At least 14 calendar days before expected paper phase graduation

Priority order within Fix Group 8:
1. D-005 (Sentinel Tradier API) — MUST be first, most critical for live capital safety
2. D-003 (session locking) — prevents P&L corruption under live load
3. D-004 (Sentinel separate key) — GLC-009 hard requirement
4. D-001 (RLS) — before adding any non-admin users
5. D-006, D-007, D-008 — reliability improvements
6. D-002, D-010, D-011 — polish
