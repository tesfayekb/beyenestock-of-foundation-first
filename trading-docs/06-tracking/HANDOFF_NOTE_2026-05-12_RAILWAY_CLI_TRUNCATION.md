# HANDOFF NOTE — Railway CLI Log Truncation Discipline (2026-05-12)

**Author:** Claude + Cursor (multi-AI governance discipline at end of T-ACT-065 closure session)
**Owner:** tesfayekb
**Trigger:** Sixth verification-surface foot-gun in 2026-05-08 → 2026-05-12 session (T-ACT-065 evaluation revealed Railway CLI silently truncated multi-day log queries; dashboard had the real data)
**Cross-references:** TASK_REGISTER §14 T-ACT-065 closure entry (2026-05-12); HANDOFF NOTE Appendix A.8 in `HANDOFF_NOTE_2026-04-28_POST_P1-3-7.md` (subscription/entitlement claims as present-day factual questions — same family of "verify your verification surface" discipline); HANDOFF NOTE Appendix A.9 (new pointer to this file)

---

## Executive summary

When using Railway CLI to query logs over a multi-day window via `railway logs --since <iso> --until <iso>`, **NEVER trust a "zero count" or "low count" result without independent cross-validation.** Railway CLI 4.57.5 silently caps the historical query to a recent window (likely retention-related on the operator's plan tier) without surfacing the truncation. The `--since` flag is accepted without warning even when the requested range exceeds retention.

The Railway web dashboard is the authoritative source for multi-day historical log queries; the CLI is reliable only for short-horizon streaming/recent-window queries.

---

## Section 1 — Symptom

The operator ran the following command on 2026-05-12 ~16:00 ET as part of T-ACT-065 evaluation:

```bash
railway logs --service diplomatic-mercy \
  --since 2026-05-05T11:50:35Z \
  --until 2026-05-12T19:50:00Z 2>/dev/null \
  | wc -l
```

Expected: tens of thousands of log lines (the service runs every 5 min with multi-line output per cycle). Actual: **500 lines total across 7 days.**

Cross-validation queries returned similar low counts:
- `grep -c '"event":[[:space:]]*"vix_price_stale"'` → 0
- `grep -c '"event":[[:space:]]*"vvix_price_stale"'` → 0
- `grep -c '"event":[[:space:]]*"vix9d_price_stale"'` → 0
- `grep -c '"event":[[:space:]]*"trading_cycle_skipped"'` → 0 (suspicious — should fire EVERY 5-min RTH cycle when session is halted; expected hundreds of matches)

The `trading_cycle_skipped` count of 0 was the critical tell: this event fires unconditionally at `trading_cycle.py:92` whenever `session_status not in ("active", "pending")`, and the session has been halted via dashboard since 2026-05-12 ~11:28 ET. Zero matches over a 7-day window where hundreds were expected indicated the log retrieval — not the emission — was the issue.

Operator then exported logs via Railway web dashboard for the same date range. The dashboard returned 38 VIX-family stale events. The CLI's "zero" answer was wrong; the dashboard had the real data.

---

## Section 2 — Required cross-validation before accepting any low/zero log count as evidence

1. **Run a guaranteed-firing event count for the same window.** Pick an event that MUST fire many times — e.g., `trading_cycle_skipped` (every 5-min RTH cycle when halted; hundreds per day), `prediction_cycle_done` (every cycle), or any other ubiquitous structured-log event your service produces.

2. **If the guaranteed-firing event also returns 0 or low count, the CLI is truncating.** Do NOT proceed with the original query as evidence. Treat the result as "log retrieval incomplete" not "no events."

3. **Fall back to the Railway web dashboard** (https://railway.app → project → service → Logs tab). The dashboard typically exposes the full retention history with a date-range selector and export functionality. Export the relevant range as JSON or text; apply the same grep patterns locally to the exported file.

4. **Document the discrepancy in the closing artifact.** If a T-ACT closure relies on log evidence, note explicitly which surface (CLI vs dashboard) the evidence came from. For multi-day windows, dashboard-sourced evidence is the default.

---

## Section 3 — Verification-surface rule generalized

This is the sixth verification-surface foot-gun in the 2026-05-08 → 2026-05-12 multi-AI session where a check returned a misleading answer without warning:

1. PR-A halt short-circuit at `trading_cycle.py:89-97` (DIAGNOSE §9 assumed PR-A gate fires during halt; it doesn't)
2. PR-A audit-row event-regime short-circuit at `strategy_selector.py:1111-1113` (Cursor §3 Alt D assumed PR-A audit row fires post-14:30 ET on event regime; it doesn't — the L1112 short-circuit fires first)
3. T-ACT-065 §2.1 regex direction (Cursor's "strict" regex `(^|[^9])vix_price_stale` was supposed to exclude substring contamination from `vix9d_price_stale`; actual contamination was from `vvix_price_stale` because the trailing 15 chars match — wrong direction)
4. Cursor's SPX hard-gate query used non-existent event name `spx_price_stale_or_unavailable` (which is a `no_trade_reason` DB-column value, NOT a WARN-event name; the actual WARN events emitted by `_check_index_freshness` for `label="spx"` are `spx_price_stale` / `spx_price_upstream_timestamp_missing` / `spx_freshness_check_failed`)
5. Railway CLI `railway logs` silently truncates at ~500 lines / recent-window for multi-day queries (this incident — sixth foot-gun)
6. Cursor's SHORT ANSWER on T-ACT-065 finalization misread UTC cluster timestamps as ET (16:30 UTC vs 16:30 ET) — same retract-in-session pattern, exemplifies the verification-surface class

**Rule:** every "X count is N" or "X is excluded" or "X surface is healthy" claim deserves an independent corroboration query against a DIFFERENT surface BEFORE being used as decision input.

**Acceptable corroboration pairs (non-exhaustive):**

| Primary surface | Corroboration surface |
|---|---|
| Railway CLI log counts | Supabase row counts (different storage) |
| Railway CLI counts | Railway dashboard counts (different access path to same storage) |
| Code-grep ("X is excluded") | AST/regex test against a representative input string |
| Production-cycle log | Scheduled-task evidence (cron logs / scheduler) |
| "Event X fires for case Y" | Trace through every short-circuit between cycle entry and X's emission site |

**Single-surface "zero/clean/healthy" claims are NEVER sufficient** when the verdict has operational impact (matrix flips, code-path guarantees, schema CHECK widening, subscription-tier assumptions, etc.).

---

## Section 4 — Adjacent finding: Cursor's SPX query event-name error (foot-gun #4 above)

Documented for the institutional record. Cursor's T-ACT-065 DIAGNOSE §2.2 included a "SPX hard-gate firings (comparison)" query that used event names that don't exist in the emitting code:

**Cursor's query (incorrect event names):**
```bash
grep -cE '"event":[[:space:]]*"(spx_price_stale_or_unavailable|spx_price_upstream_timestamp_missing|spx_freshness_check_failed)"'
```

**Actual event names emitted** (per `prediction_engine.py:514-528` `_check_index_freshness` helper):
- `spx_price_stale` (when `age_seconds > 330`)
- `spx_price_upstream_timestamp_missing` (when `fetched_at is None`)
- `spx_freshness_check_failed` (on exception)

The string `spx_price_stale_or_unavailable` is the `reason` field value passed to the INFO log `cycle_skipped` at L1472-1473 AND the `no_trade_reason` DB column value at L1478. It is NEVER an event name.

**Why it didn't break the T-ACT-065 closure:** The Supabase query (b) on `no_trade_reason ILIKE '%stale%'` returned 0 rows independently, providing authoritative confirmation that the SPX hard-gate did NOT fire during the window. The flawed Railway-log SPX query happened to also return 0 (compounded by the truncation issue), so the verdict "SPX healthy" was correct by accident of two independent zeros, not by Cursor's flawed query.

**Why it matters for future audits:** if SPX had been firing the hard-gate during the window, the Railway-log query would have STILL returned 0 (wrong event names) but the Supabase query would have shown the rows. Cursor + reviewer would have caught the contradiction and surfaced the event-name error. Future audits: always query DB rows AND Railway logs for the same surface; contradictions surface real bugs in one or both queries.

**Verification rule restatement:** the actual emission site (the `logger.warning(f"{label}_price_stale", ...)` call in `_check_index_freshness`) is authoritative for event names. Always read the emission code before constructing a grep pattern — never reconstruct event names from `no_trade_reason` values or other downstream artifacts.

---

## Section 5 — Adjacent finding: boot-time stale-event artifact

The 3 events on 2026-05-07T14:10:00Z (10:10 ET Thursday) with age ~64514.5s (~17.9 hours) are a deploy-restart artifact, NOT steady-state production behavior. The age arithmetic resolves to `fetched_at ≈ 2026-05-06 16:14:45 ET` — 14.8 minutes after market close on the previous day. This is consistent with a final post-close producer write on 5/6 followed by a producer (or service) restart sometime between 5/6 close and 5/7 10:10 ET, with the next read happening at 5/7 10:10 ET against the stale 5/6 16:14 value.

**Recommendation for any future hard-gate PR** (α-flip or γ partial): implement a deploy-warmup grace period. Two implementation options:

1. **Time-bounded:** suppress the hard-gate for the first 5-10 min post-startup
2. **Event-bounded** (more robust to variable deploy-to-first-data latency): suppress until the first non-stale fetch is observed for that feed

Without this grace period, the hard-gate would unnecessarily skip the first cycle after every deploy. T-ACT-102 acceptance criteria already include this.

---

## Section 6 — Operator action items beyond this PR

This is documentation-only; the operator action items are:

1. **For the next Railway log query** (any future T-ACT, any future audit): default to dashboard for multi-day windows. Only use CLI for short (< 24h) queries OR when streaming live logs.
2. **For T-ACT-102 execution** (queued for next session): expect to use Railway dashboard for the producer-side cycle-timing data pull.
3. **For team training** (if/when MarketMuse adds a second engineer): walk through this note as part of onboarding.

---

*HANDOFF NOTE authored 2026-05-12 ~17:00 ET by Claude (review) + Cursor (drafting) at end of T-ACT-065 closure session. Owner: tesfayekb. Cross-referenced from HANDOFF_NOTE_2026-04-28_POST_P1-3-7.md Appendix A.9. End of note.*
