# HANDOFF — 2026-05-04 PREDICTION OUTAGE DIAGNOSIS

**Date:** 2026-05-04 17:15 ET
**Investigator:** Cursor (read-only diagnostic per operator prompt)
**HEAD verified:** `origin/main` = `8f7607e` (matches expected per prompt §"Hard rules")
**Mode:** READ-ONLY. No code, governance, or config modifications. This file is the only artifact written.

---

## EXECUTIVE SUMMARY

The freshness guard is doing exactly what it was designed to do. Its **input is truthful**, the math is correct, and the threshold is enforced as documented. The real cause is **structural**: the operator's Polygon **Indices Starter ($49/m)** subscription provides **15-minute delayed** indices data, and the `/v3/snapshot?ticker.any_of=I:SPX` endpoint returns timestamps reflecting that delay. The 330-second freshness threshold was sized for a real-time feed and correctly rejects 15-min-delayed data. The **trigger** was not PR #90 (T-ACT-045) on Friday — it was **PR #92 (T-ACT-046, Track B silent-staleness fix) merged Saturday 2026-05-02 12:00 ET**, which flipped `polygon:spx:current.fetched_at` from `datetime.now(timezone.utc)` to the upstream Polygon timestamp. Monday's first RTH cron at 09:30 ET was the first opportunity for the change to manifest. Best next step: a **manual API probe** to confirm Indices-Starter tier is returning ~15-min-old `last_updated` values from the unified snapshot, before any code change is drafted. **Do not roll back or retune thresholds without operator decision on subscription tier.**

---

## Section 1 — SPX feed code path

**1.1.** Trace from cron → SPX fetch:
- `backend/main.py:1364-1372` — APScheduler cron registers `run_prediction_cycle` mon-fri 9-15 minute=*/5.
- `backend/main.py:107` — `run_prediction_cycle` is the cron handler.
- `backend/prediction_engine.py:run_cycle` — invoked by the cron handler; freshness guard at L1323-1391.
- `backend/polygon_feed.py:117` — `async def _poll_loop` runs continuously while `_is_market_hours()` returns True; on each iteration calls `_fetch_spx_price` (L164).
- `backend/polygon_feed.py:822-927` — `async def _fetch_spx_price` performs the HTTP fetch.

**1.2. Exact endpoint:**
```
backend/polygon_feed.py:849-854
GET https://api.polygon.io/v3/snapshot
    headers: Authorization: Bearer ${POLYGON_API_KEY}
    params:  ticker.any_of=I:SPX
```
This is the **Polygon unified snapshot endpoint** with the `I:SPX` index ticker. It is **not** `/v3/snapshot/options/I:SPX` (the options-chain endpoint) shown in the operator's Polygon-dashboard screenshot — see §8.2.

**1.3. Price field extraction:**
```
backend/polygon_feed.py:858-864
result0       = results[0]
session_data  = result0.get("session", {}) or {}
price         = float(session_data.get("close")
                      or session_data.get("last")
                      or 0.0)
```
The price is read from `results[0].session.close` with `session.last` as fallback.

**1.4. Timestamp field extraction (priority chain):**
```
backend/polygon_feed.py:884-898
upstream_ts_raw = (
    session_data.get("last_updated")        # PRIORITY 1
    or value_data.get("last_updated")       # PRIORITY 2
    or result0.get("last_updated")          # PRIORITY 3
    or None
)
self._last_spx_upstream_ts = self._normalize_polygon_timestamp(upstream_ts_raw)
```
**`session.last_updated` is the first-priority field** — this is load-bearing for the diagnosis (see §5.1).

**1.5. Age computation (full chain):**
- `backend/polygon_feed.py:929-967` — `_normalize_polygon_timestamp`: converts ns/μs/ms/s epoch or ISO 8601 → ISO 8601 UTC string. Heuristic: ts > 1e18 → ns; > 1e14 → μs; > 1e11 → ms; else seconds. Math is correct for all four cases.
- `backend/polygon_feed.py:202-218` — poll-loop `setex("polygon:spx:current", 600, json.dumps({"price": ..., "fetched_at": upstream_ts, "fetched_at_source": "polygon_upstream" | "missing", "source": "polygon_v3_snapshot"}))`.
- `backend/prediction_engine.py:1362-1365` — freshness guard:
  ```python
  fetched_at  = datetime.fromisoformat(fetched_at_raw)
  age_seconds = (datetime.now(timezone.utc) - fetched_at).total_seconds()
  ```
- `backend/prediction_engine.py:1366` — comparison: `if age_seconds <= 330: spx_fresh = True`.

**Units, tz, conversion:** Polygon returns ns-since-epoch for `last_updated` (most common). `_normalize_polygon_timestamp` divides by 1e9 → seconds, then `datetime.fromtimestamp(seconds, tz=timezone.utc)` produces a UTC-aware datetime with `.isoformat()`. The freshness guard parses with `fromisoformat` (UTC-aware) and subtracts from `datetime.now(timezone.utc)`. **No timezone bug, no unit bug, no clock-drift introduction in the code.**

---

## Section 2 — VVIX feed code path (comparison)

**2.1.** Endpoint: `backend/polygon_feed.py:592, 601` — `GET https://api.polygon.io/v3/snapshot?ticker.any_of=I:VVIX`. **Same endpoint, same plan tier as SPX.**

**2.2.** Field extraction:
```
backend/polygon_feed.py:602-606
session = results[0].get("session", {})
vvix    = float(session.get("close")
                or session.get("prev_close")
                or 120.0)
```
VVIX reads `session.close` (same field as SPX). **No timestamp extraction — VVIX writes only `polygon:vix:current` (and similar for VVIX/VIX9D) as a raw float string at L130-132 / L152-156, no `fetched_at` payload.**

**2.3. Structural difference SPX vs VVIX:**
- Same HTTP client, same endpoint, same parsing function shape.
- VVIX: writes raw float, no freshness check, **no guard at the consumer side**.
- SPX: writes JSON payload `{price, fetched_at, fetched_at_source, source}`, **guarded at consumer** (prediction_engine.run_cycle).
- **Implication:** VVIX is silently 15-min stale every cycle but no log fires because nothing checks. The operator's "VVIX path is healthy" observation is true at the HTTP layer (`polygon_vvix_fetched` succeeds) but NOT verified at the staleness layer.

---

## Section 3 — Freshness guard

**3.1.** Threshold definition: `backend/prediction_engine.py:1373` — hardcoded constant `threshold_seconds=330` in the `spx_price_stale` log statement; the comparison literal `330` appears at L1366. There is no module-level constant; the value is inline at both sites.

**3.2.** Comparison code (verbatim):
```
backend/prediction_engine.py:1361-1374
else:
    fetched_at = datetime.fromisoformat(fetched_at_raw)
    age_seconds = (
        datetime.now(timezone.utc) - fetched_at
    ).total_seconds()
    if age_seconds <= 330:
        spx_fresh = True
    else:
        logger.warning(
            "spx_price_stale",
            age_seconds=round(age_seconds, 1),
            source="polygon",
            threshold_seconds=330,
        )
```

**3.3. Walk-through for `age_seconds=911.8` (typical observed value):**
1. Poll cycle T₀: `_fetch_spx_price` calls `/v3/snapshot?ticker.any_of=I:SPX`. Response includes `session.last_updated = T₀ - 912s` (Polygon's session aggregate, delayed by Indices-Starter tier).
2. `_normalize_polygon_timestamp` converts the ns-epoch to ISO 8601: e.g. `"2026-05-04T19:30:00+00:00"` when wall-clock is `19:45:12+00:00`.
3. `setex` stores `{"fetched_at": "2026-05-04T19:30:00+00:00", ...}` to `polygon:spx:current` with TTL=600s.
4. Cron fires at `19:45:30+00:00`. Guard reads `fetched_at_raw = "2026-05-04T19:30:00+00:00"`.
5. `age_seconds = (19:45:30 - 19:30:00).total_seconds() = 930s` (close to the observed 911.8).
6. `930 > 330` → guard fires `spx_price_stale` warning, returns `no_trade_signal`.

The math is correct. **The 911.8s value is the actual age of the timestamp Polygon returned**, not an artifact of clock drift, timezone misalignment, or unit confusion.

---

## Section 4 — Git history of the SPX path

**4.1.** Commits touching `backend/polygon_feed.py` since 2026-04-28 (full set):
| SHA | Date (ET) | PR | What changed |
|---|---|---|---|
| `16fd53c` | 2026-05-01 15:59 | #90 | T-ACT-045: ADDS the polygon:spx:current setex with `fetched_at: datetime.now(utc)` (wall-clock-now). Adds the freshness guard to prediction_engine. |
| `8c5b644` | 2026-05-02 12:00 | #92 | T-ACT-046: ADDS `_last_spx_upstream_ts` side-channel + `_normalize_polygon_timestamp` helper + flips setex `fetched_at` to upstream_ts. Adds `_fetch_spx_price` upstream-timestamp extraction (the priority chain at L884-889). |

(PR #93 / `e887c39` touched `tradier_feed.py` and governance docs; no code change to `polygon_feed.py` per `git log -- backend/polygon_feed.py`.)

**4.2.** Commits touching `backend/prediction_engine.py` since 2026-04-28:
| SHA | Date (ET) | PR | What changed re: freshness guard |
|---|---|---|---|
| `94edb9a` | 2026-04-30 13:09 | #82 | T-ACT-040: AI synthesis output unblock. No freshness guard impact. |
| `a77195a` | 2026-04-30 15:46 | (#83) | T-ACT-041: three-tier LightGBM loader. No freshness guard impact. |
| `16fd53c` | 2026-05-01 15:59 | #90 | T-ACT-045: **ADDS the freshness guard** at the run_cycle persist site (current L1323-1391). |
| `8c5b644` | 2026-05-02 12:00 | #92 | T-ACT-046: amends guard with `spx_price_upstream_timestamp_missing` log branch (observability only — `spx_fresh = False` semantics unchanged per the commit message). |
| `575e79d` | 2026-05-02 13:04 | #94 | T-ACT-054 cv_stress NULL-on-degenerate. No freshness guard impact. |
| `96a16e5` | 2026-05-02 14:21 | #95 | T-ACT-047 postgrest error classification. No freshness guard impact. |

**4.3.** What did **PR #90 (T-ACT-045)** actually change for the age computation?
- **Endpoint:** unchanged — `_fetch_spx_price` already used `/v3/snapshot?ticker.any_of=I:SPX` at L851 (verified by `git show 16fd53c -- backend/polygon_feed.py` — the diff is +31 lines additive).
- **Field extracted as price:** unchanged.
- **Field extracted as timestamp:** **NONE pre-PR-#90**. Pre-PR-#90, polygon:spx:current didn't exist as a Redis key — SPX was read from `tradier:quotes:SPX`. PR #90 introduces the polygon-first chain.
- **Age computation:** PR #90 sets `fetched_at = datetime.now(timezone.utc).isoformat()` — i.e., wall-clock at the moment of the setex write. Combined with the 330s guard, this means age is always ~0-300s (within the 5-min poll-cycle freshness slack). **PR #90's guard could NOT have fired in production because its input was self-defeating** (the wall-clock-now timestamp was always fresh by construction).

**4.4.** What did **PR #92 (T-ACT-046)** actually change?
The diff at `8c5b644 -- backend/polygon_feed.py` (verbatim, abbreviated):
```diff
+    upstream_ts = self._last_spx_upstream_ts
     try:
         self.redis_client.setex(
             "polygon:spx:current",
             600,
             json.dumps({
                 "price": float(spx_price),
-                "fetched_at": datetime.now(timezone.utc).isoformat(),
+                "fetched_at": upstream_ts,
+                "fetched_at_source": (
+                    "polygon_upstream" if upstream_ts is not None else "missing"
+                ),
                 "source": "polygon_v3_snapshot",
             }),
```
And in `_fetch_spx_price`, PR #92 added the upstream-timestamp extraction priority chain at L884-889 + the `_normalize_polygon_timestamp` helper at L929-967. **This is the breaking change.** The freshness guard's input went from "wall-clock-now (always fresh)" → "true upstream timestamp (subject to plan-tier delay)".

**4.5. Were there earlier `age_seconds` log entries pre-Friday?**
Searched `git log -L /spx_price_stale/,+5:backend/prediction_engine.py` — the `spx_price_stale` warning was introduced in `16fd53c` (PR #90, 2026-05-01 15:59 ET) and has not been touched since. **No production log entry of `spx_price_stale` could exist before 2026-05-01 15:59 ET.** Operator can confirm via Railway log search but the codebase didn't emit this event before Friday close.

---

## Section 5 — Polygon endpoint semantics

**5.1.** What does `/v3/snapshot?ticker.any_of=I:SPX` return? Based on the field-set log at `polygon_feed.py:903-916` (`polygon_spx_snapshot_fields_observed` — emitted once per process startup), the response shape is:
```
results: [
  {
    "ticker": "I:SPX",
    "session": { "open", "high", "low", "close", "previous_close", "change", "change_percent", "last_updated", ...},
    "value":   { ... } | <numeric>     # for indices, sometimes a scalar
    "last_updated": <ns-epoch>,
    ...
  }
]
```

Polygon's documentation for the unified `/v3/snapshot` endpoint (https://polygon.io/docs/indices) describes this as the unified snapshot — for indices, `session` carries the per-session OHLC aggregate and `value` carries the live index value. **`session.last_updated` reflects the most recent SESSION-AGGREGATE update**, which on a 15-min-delayed Indices Starter tier is the bar-aggregation timestamp shifted back by the tier's delay. (The Polygon docs page I fetched at the time of writing only returned a stub; the field-set observability log inside our codebase is the authoritative empirical source for what fields are populated.)

**5.2. Different endpoints to consider for live SPX index price:**
| Endpoint | Use case | Plan-tier delay on Indices Starter |
|---|---|---|
| `/v3/snapshot?ticker.any_of=I:SPX` (current) | Unified snapshot — what we use | **15-min delayed** (empirically) |
| `/v3/snapshot/indices?ticker.any_of=I:SPX` | Indices-specific snapshot | Likely same tier-delay (subscription-bound, not endpoint-bound) |
| `/v2/aggs/ticker/I:SPX/prev` | Previous session close | Static; not live |
| `/v2/aggs/ticker/I:SPX/range/1/minute/...` | Historical 1-min bars | 15-min-delayed bars on Starter tier |
| `/v2/last/trade/I:SPX` | Last trade tick | Indices don't have trades; not applicable |
| `/v2/snapshot/locale/us/markets/stocks/tickers/SPY` | SPY ETF (real-time on Stocks Advanced $199/m) | **REAL-TIME** if mapped via SPY×10≈SPX |

**5.3. Operator's plan entitlement (per prompt screenshots):**
- **Indices Starter — $49/m (active)** — covers I:SPX/I:VIX/I:VVIX/I:VIX9D snapshots **with 15-min delay**.
- **Options Developer — $79/m (active)** — covers options chain (real-time on this tier).
- **Stocks Advanced — $199/m (active)** — covers stocks/ETFs real-time. **SPY (an ETF tracking SPX) IS real-time on this tier.**

**The empirical age clustering (~903-1531s, mean ~1100s) is structurally consistent with 15-min delayed indices data**, NOT with code-introduced bugs:
- 900s = exactly 15 min (just after Polygon publishes the next delayed bar)
- 1200-1500s = 20-25 min (poll catches Polygon mid-update-cycle)
- 1531s outlier = Polygon-side hiccup (single occurrence)

A real-time feed would show ages of 0-300s (1 poll period). The observed values are in a different distribution by orders of magnitude.

---

## Section 6 — Diagnosis

**6.1. Root cause:**

The Polygon **Indices Starter ($49/m)** subscription provides 15-minute delayed indices data. The unified `/v3/snapshot?ticker.any_of=I:SPX` endpoint returns `session.last_updated` reflecting that 15-min delay. The freshness guard at `backend/prediction_engine.py:1366` (`if age_seconds <= 330`) was sized for a real-time feed and **correctly** rejects 15-min-delayed data with `spx_price_stale_or_unavailable`.

The reason this manifested **starting Monday 2026-05-04 09:30 ET** (and not earlier):
1. **Pre-2026-05-01 16:00 ET:** SPX was read from Tradier (15-min delayed in sandbox). No freshness guard. Predictions wrote with stale data, silently.
2. **2026-05-01 15:59 ET (Friday close +1 min):** PR #90 (T-ACT-045) merged. Adds the polygon:spx:current write path AND the freshness guard. BUT: `fetched_at` was set to `datetime.now(timezone.utc)` at the moment of the setex — wall-clock-now. The guard always saw 0-300s age and always passed. The change was effectively a no-op for the freshness gate. (Friday's last RTH cycle was 15:55 ET, BEFORE PR #90 deployed — so Friday's predictions used the legacy Tradier path, not the new Polygon path.)
3. **2026-05-02 12:00 ET (Saturday):** PR #92 (T-ACT-046, Track B) merged. Adds the upstream-timestamp side-channel. Flips `fetched_at` from wall-clock-now to the upstream Polygon timestamp. **This is the breaking change.** No RTH activity Saturday/Sunday — cron is `mon-fri`.
4. **2026-05-04 09:30 ET (Monday open):** First RTH cron after PR #92 deploy. Polygon poll writes upstream timestamp (~15 min stale) to Redis. Freshness guard correctly rejects → `cycle_skipped reason=spx_price_stale_or_unavailable`. Every subsequent 5-min cycle hits the same path. Zero predictions write.

**6.2. Confidence: HIGH.** Evidence base:
- Empirical age clustering at ~900-1500s matches 15-min-delayed feed precisely (independent confirmation: 903.9, 904.6, 908.1, 911.8 cluster within 8 seconds of 900 = 15 min).
- Code chain fully traced and verified for unit/timezone/conversion correctness.
- Git diff confirms PR #92 is the structural flip; PR #90 alone would not have produced the outage (its `fetched_at` was self-defeating).
- VVIX uses the same endpoint and tier and would also be 15-min-stale, but no freshness guard exists there — silent corroboration.

**To raise confidence to "definitive":** §7's recommended manual API probe will produce a bit-for-bit verification of `session.last_updated` from the live Polygon response.

**6.3. Match against H1-H5:**
- **H1 (upstream stale `last_updated`):** PARTIALLY correct — the upstream is stale, but not because Polygon is broken. It's stale because the **subscription tier doesn't entitle real-time**.
- **H2 (wrong endpoint / wrong field):** REJECTED — code uses the correct unified-snapshot endpoint and reads `session.last_updated` (the most appropriate field). Switching to a different endpoint at the same tier won't help.
- **H3 (age computation incorrect):** REJECTED — the math is sound (verified §3.3).
- **H4 ("guard correctly exposing pre-existing data quality problem"):** **CLOSEST MATCH but mis-attributed.** H4 names T-ACT-045 (PR #90); the actual breaking change is **T-ACT-046 (PR #92)**. The "pre-existing data quality problem" is NOT a feed regression — it's a **subscription-tier mismatch** between the codebase's real-time assumption and the operator's $49/m delayed entitlement.
- **H5 (something else):** the 25-min spike (1531s) is explained naturally as a Polygon-side update hiccup; it does NOT require an additional hypothesis.

**Therefore: H6 (Cursor's diagnosis):**
> **Subscription-tier mismatch.** The codebase + freshness guard assume real-time SPX indices data. The operator's Polygon Indices Starter tier ($49/m) provides 15-minute delayed indices snapshots. The pre-existing 15-min delay was masked from 2026-05-01 15:59 ET (PR #90) to 2026-05-02 12:00 ET (PR #92) by the wall-clock-now `fetched_at` field, which made every poll appear 0s stale. PR #92 fixed `fetched_at` to reflect the upstream Polygon timestamp, exposing the underlying subscription-tier delay. Monday's first RTH cron at 09:30 ET was the first opportunity for the change to manifest, since cron fires `mon-fri` only.

**6.4. Does the diagnosis explain all three observations?**
| Observation | Explanation |
|---|---|
| SQL: zero predictions since Friday 15:55 ET | Friday 15:55 was the last cron of the week (cron is mon-fri 9-15 minute=*/5). Saturday/Sunday: no RTH cycles by design. Monday: every cron cycle hits `spx_price_stale_or_unavailable` and early-returns before the persist site at `prediction_engine.py:run_cycle` writes to `trading_prediction_outputs`. |
| Logs: `age_seconds` ~900-1500 with reasonable variation | 900s = 15 min = the Indices Starter tier delay floor. The 5-min poll cadence + Polygon's bar-aggregation cadence produce a sawtooth oscillating between ~900s (just after a Polygon publish) and ~1500s (just before next). |
| Polygon: 200 OK on requests | Subscription IS valid; the API IS up; the data IS being returned. It's just delayed by 15 min as per the entitlement. The 200 OK is consistent with the diagnosis, not contradictory. |

**No observation is left unexplained.**

---

## Section 7 — Recommended next step

**7.1. ONE next step: manual API probe (10 min, ZERO code change).**

Run the following from any machine with the production Polygon API key:

```bash
# Probe 1: the exact endpoint our code uses
curl -sH "Authorization: Bearer ${POLYGON_API_KEY}" \
  "https://api.polygon.io/v3/snapshot?ticker.any_of=I:SPX" \
  | python3 -c '
import json, sys, time
data = json.load(sys.stdin)
r = data["results"][0]
session = r.get("session", {})
last_upd = session.get("last_updated")
now_ns   = time.time_ns()
if last_upd:
    age_s = (now_ns - last_upd) / 1e9
    print(f"session.last_updated = {last_upd} (age: {age_s:.1f}s = {age_s/60:.1f} min)")
print(f"session keys: {sorted(session.keys())}")
print(f"result keys:  {sorted(r.keys())}")
print(f"close:        {session.get(\"close\")}")'
```

Run during RTH (e.g., Tuesday 10:00 ET if not Monday-night-late). **Expected outcome (confirms diagnosis):** `age` reports ~880-1500 seconds (~15-25 min). **Refutation outcome:** `age` reports < 60 seconds (would mean tier IS real-time and the code path has a bug we missed).

**7.2. Scope/risk of the probe:** ZERO files modified. ONE HTTP request to Polygon. Risk = LOW (uses operator's existing key, hits a single endpoint).

**7.3. Why not a code fix tonight:**
The diagnostic confidence is HIGH but not yet DEFINITIVE. The subscription-tier mismatch is a **product-decision question**, not a code question:
- **Path A:** Upgrade to **Indices Developer / Advanced** — gets real-time entitlement; ~$150-199/m incremental. (Per `SUBSCRIPTION_REGISTRY.md` from the prior session, this was the T-ACT-050 recommended target.)
- **Path B:** Switch SPX source to **SPY×10** via Stocks Advanced (already paid $199/m, includes ETF real-time). Code change would be ~30-50 lines in `polygon_feed.py` to add `/v2/snapshot/locale/us/markets/stocks/tickers/SPY` and translate. New observability needed for `last_quote` vs `session.last_updated`.
- **Path C:** Increase the 330s threshold to ~1800s (30 min). Defeats the guard's purpose — a 30-min-stale signal is unfit for 30-min-horizon predictions.
- **Path D:** Roll back PR #92 (T-ACT-046) — restores the wall-clock-now `fetched_at` and unblocks predictions. **But re-introduces the silent-staleness bug T-ACT-046 was created to fix**, and the system would be making predictions on 15-min-old SPX data without knowing it. **Consequential alpha decay.**

The probe (§7.1) takes 10 min, reduces ambiguity to zero, and tees up the right product decision (A vs B). **Do not rush a code fix without the probe result.**

---

## Section 8 — STOP-and-disagree

**8.1. Misleading framing in the prompt:**

- **Prompt §"Note on T-ACT-045 deploy timing"** correlates the outage with PR #90 and frames the question as "did T-ACT-045 introduce a regression?" **This frames the wrong PR.** The breaking change is **PR #92 (T-ACT-046, Track B)** on Saturday 2026-05-02 12:00 ET, not PR #90 on Friday. The Friday 15:55 → Monday silence boundary is governed by the cron schedule (`mon-fri` only), not by the deploy timing of PR #90 specifically. Anchoring on PR #90 would lead toward "roll back PR #90" — which would lose the Polygon-real-time switching but leave the underlying tier-delay condition unaddressed.

- **H4 framing:** "the endpoint was always returning stale data, but pre-T-ACT-045 the system silently used the stale value" — directionally correct intuition, but the **mechanism is wrong**. Pre-T-ACT-045 the system read **Tradier sandbox** (also 15-min delayed, but a different vector). T-ACT-045 introduced the Polygon-first chain AND the guard; T-ACT-046 made the guard's input truthful. The "silent-failure-class family A.7" framework documented in the codebase (`HANDOFF_NOTE_2026-04-28_POST_P1-3-7.md` per prior session) explicitly anticipates this pattern — masked-by-defaults vs surfaced-by-truthful-inputs.

- **Implicit anchor on "code bug":** the prompt's H1-H3 are all code-bug hypotheses. The actual cause is **subscription entitlement vs. code assumption**. The code is correct; the assumption embedded in the 330s threshold is incompatible with the operator's plan tier. This is a **specification gap**, not a code defect.

**8.2. Operator's Polygon dashboard screenshot — endpoint that does NOT match our code:**

The screenshot shows `/v3/snapshot/options/I:SPX` (200 OK, 25,275 bytes, 57 ms). **This endpoint is NOT called by any file in `backend/`** (verified by exhaustive grep: `grep -rn 'snapshot/options' backend/ --include='*.py'` returns 0 matches). The 25KB body size is consistent with a **full options chain payload**, not a single index snapshot. Likely sources:
1. A different service or CLI tool (Cursor MCP, manual probe, Polygon's web dashboard's own pre-fetch for billing display).
2. Frontend code (not in `backend/`).
3. Stale request from a deleted code path.

The dashboard screenshot is **not evidence about our SPX index path**. The relevant request would be `/v3/snapshot?ticker.any_of=I:SPX` — search the dashboard for that pattern instead.

The `/v2/snapshot/locale/us/marke...` requests every 1-2 minutes (truncated in screenshot 3) are also **not in `backend/`** (verified). Possibly the Polygon dashboard itself or another service.

**8.3. Things in the codebase that prior sessions may not have considered:**

- **VVIX is silently 15-min stale every cycle** (§2.3). VVIX has no freshness guard. The model's `vvix_z_score`, `vvix_close`, `vix_term_ratio` features are all derived from data with the same 15-min lag. This was **invisible during the entire pre-T-ACT-045 era and is still invisible today** because no consumer checks. Likely contributed to the accuracy issue diagnosed in Sunday's session.
- **The `session.last_updated` priority chain** (`polygon_feed.py:884-889`) prefers `session.last_updated` first. For indices, `result0.last_updated` (the result-level field) might be a closer-to-live tick timestamp than the session-aggregate timestamp. **If the operator decides to keep Indices Starter and try the result-level timestamp**, that's a 1-line code experiment. But the empirical age values are too consistent for this to recover meaningful real-time-ness — the 900s floor is a tier limit, not a field-priority artifact.
- **Threshold of 330s is hardcoded inline at two locations** (`prediction_engine.py:1366` and `:1373`) with no module-level constant. Drift between the comparison and the log message is a future-bug-class concern. Out of scope tonight.
- **The `_normalize_polygon_timestamp` heuristic at `polygon_feed.py:954-961`** has a unit-detection range issue: a microsecond-timestamp from 1973 (`ts > 10**14` covers ts > ~3.17 years post-epoch in seconds) overlaps with millisecond-timestamps from year 5138 (`ts > 10**11` covers 1970-onward in ms). For current dates the heuristic is correct but it's brittle. Out of scope tonight.
- **PR #92's commit message asserts "spx_fresh = False semantics unchanged"** — this is technically true but materially wrong: the SET OF cycles where `spx_fresh = False` evaluated changed dramatically (from "essentially never" pre-PR-#92 to "always" post-PR-#92 on the Indices Starter tier). The conservative-skip semantic is preserved; the practical incidence is not.

---

## Final summary line

**The freshness guard is doing its job. The Polygon Indices Starter $49/m subscription is structurally 15-min delayed, and PR #92 made that delay visible to the guard. Run the §7.1 manual API probe before deciding between subscription upgrade (Path A), SPY proxy (Path B), or another option. Do not roll back PR #92 (Path D) without explicit operator awareness that doing so re-buries the pre-existing 15-min staleness silently.**

---

## Post-script — Operator decision and closure forward references (added 2026-05-04 evening)

**Operator action taken:** Path A (Polygon Indices subscription upgrade) — Indices Starter $49/m → Indices Advanced $99/m. Subscription change executed via Polygon billing dashboard 2026-05-04 evening. Tier comparison matrix recorded at `trading-docs/08-planning/SUBSCRIPTION_REGISTRY.md` §1 (post-upgrade) confirms Advanced provides "Real-time" timeframe entitlement vs. Starter's "15-min Delayed."

**§7.1 manual API probe** (defined above) is preserved as the verification gate for upgrade closure. Probe will be operator-executed during the next RTH window (Tuesday 2026-05-05 ~10:00 ET unless executed Monday evening). Expected outcome confirming upgrade efficacy: `age_seconds < 60s`. Refutation outcome (`age_seconds > 800s`) would indicate either (a) the dashboard upgrade has not propagated to the API entitlement, (b) a different code-path bug, or (c) tier description mismatch — all of which require additional diagnosis before declaring closure.

**File relocation note (2026-05-04 evening):** This file was originally drafted at the repo root as `HANDOFF_2026-05-04_OUTAGE_DIAGNOSIS.md` and relocated to `trading-docs/06-tracking/HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md` at PR `docs/post-incident-indices-advanced-2026-05-04` to match existing repo HANDOFF convention. Content is unchanged from the original diagnostic draft (lines 1–335 above); only this post-script section was appended.

**Closure cross-references:**
- **HANDOFF NOTE Appendix A.8** (in `trading-docs/06-tracking/HANDOFF_NOTE_2026-04-28_POST_P1-3-7.md`) — governance-grade lessons-learned entry for this incident (added in same PR as this relocation).
- **TASK_REGISTER §14 T-ACT-061** — subscription-upgrade closure entry (closed-resolved on subscription change; verification gated on §7.1 probe).
- **TASK_REGISTER §14 T-ACT-062** — VVIX/VIX/VIX9D freshness guard + 330s constant extraction follow-up (queued, post-§7.1-probe).
- **TASK_REGISTER §14 T-ACT-063** — Email alert egress investigation follow-up (queued).
- **TASK_REGISTER §14 T-ACT-064** — Post-upgrade retraining decision tracking (informational).
- **SUBSCRIPTION_REGISTRY.md** §1 — current-state recording of Indices Starter cancellation + Indices Advanced activation + tier comparison matrix.

*End of post-script.*
