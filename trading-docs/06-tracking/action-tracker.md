# Trading System — Action Tracker

> **Owner:** tesfayekb | **Version:** 1.0

## Purpose

Single register of every trading change action. Every change to trading code, schema, or governance MUST have an entry here.

---

## Entry Schema

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Sequential: `T-ACT-NNN` |
| `date` | Yes | ISO date the action was completed |
| `action` | Yes | Short description |
| `type` | Yes | `migration`, `code`, `documentation`, `governance`, `verification` |
| `phase` | Yes | Trading build phase (e.g. `phase_1`, `pre_phase_1`) |
| `impact` | Yes | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `owner` | Yes | Who/what performed the action (Lovable, Cursor, Operator) |
| `modules_affected` | Yes | List of trading and/or foundation modules touched |
| `docs_updated` | Yes | List of trading-docs files updated |
| `foundation_impact` | Yes | `NONE`, or description of foundation files touched (with justification) |
| `verification` | Yes | How the action was verified |
| `t_rules_checked` | Yes | List of T-Rules verified during action (T-Rule 1, T-Rule 2, etc.) |

---

## Register

### T-ACT-042 — LightGBM runtime deps unblock (libgomp1 + CHECK constraint)

- **id:** T-ACT-042
- **date:** 2026-04-30
- **action:** Two production-only defects discovered during T-ACT-041
  deploy validation at Railway commit `a77195a`. Both block the
  LightGBM model from actually executing in production. Without
  this PR, the 1.56 MB `direction_lgbm_v1.pkl` artifact uploaded
  to Supabase storage delivers correctly but unpickles to an
  OSError, the Tier 2 path falls through to Tier 3 (GEX/ZG
  fallback per the Q-D10 design), and the system runs entirely
  on the GEX/ZG edge — the 52.9% directional edge from PR 2 stays
  inert.
  - **Defect A — `libgomp.so.1` missing in Railway container:**
    Railway log at commit `a77195a`:
      `direction_model_supabase_downloaded pkl_bytes=1638141 meta_bytes=929`
      `direction_model_supabase_fetch_failed error=libgomp.so.1: cannot open shared object file: No such file or directory`
      `direction_model_unavailable message=local cache and Supabase fallback both missed; GEX/ZG fallback active at L545`
    Root cause: LightGBM 4.6.0 manylinux wheel intentionally does
    NOT vendor `libgomp.so.1` (per `lightgbm-org/LightGBM#7141`
    and `microsoft/LightGBM#3041` — design choice to avoid
    OpenMP runtime conflicts; documented on the PyPI page). The
    failure site is `pickle.load(f)` inside
    `_load_pickle_and_metadata()` → Unpickler resolves
    `LGBMClassifier` → triggers `import lightgbm.basic` →
    `_lib_lightgbm.so.dlopen("libgomp.so.1")` → OSError because
    Railway's Nixpacks base image (Ubuntu) doesn't include the
    OpenMP runtime by default. The Q-D10 fall-through design
    correctly prevented uvicorn from crashing — but it also
    correctly prevented inference from happening.
    Fix: 1-line addition to `nixpacks.toml` `[phases.setup]`:
      `aptPkgs = ["libgomp1"]`
    `libgomp1` is the canonical Debian package providing
    `libgomp.so.1`. Confirmed via 3 independent sources: official
    LightGBM PyPI page docs, lightgbm-org issue #7141 wheel
    inspector output, and Stack Overflow Q-55036740 (9.5K views,
    accepted answer with `apt-get install libgomp1`).
    Establishes the project's first use of Nixpacks `aptPkgs`;
    cited in commit body so future contributors have a reference.
  - **Defect B — CHECK constraint rejects `service_name='direction_model'`:**
    Railway log at commit `a77195a`:
      `health_write_failed error={'code': '23514', 'details': 'Failing row contains (..., direction_model, error, ...)', 'message': 'new row for relation "trading_system_health" violates check constraint "trading_system_health_service_name_check"'}`
    Root cause: PR 2's DIAGNOSE Q-D6 verified `direction_model`
    didn't collide with the 23 existing service names in
    `write_health_status()` call sites, but missed that
    `service_name` has a CHECK constraint with an explicit
    allowlist (defined originally at
    `20260416172751_0ef832ac-fab6-4da7-a0d0-050df61b399f.sql:222`
    and last updated at
    `20260421_health_service_name_eod_jobs.sql:11-42`). The
    `_safe_write_health()` wrapper at `prediction_engine.py`
    correctly logs and swallows the constraint violation so the
    model load is unaffected — but the Engine Health admin page
    can't surface model state.
    Fix: new migration
    `20260430_add_direction_model_to_health_constraint.sql`
    follows the established DROP IF EXISTS + ADD pattern from
    20260419 and 20260421. Preserves all 23 prior allowlist
    entries and appends `'direction_model'` with an inline
    comment documenting the state semantics ('degraded' is the
    expected steady state on Railway cold start, not an error
    condition).
  - **Lessons-learned (Q-D6 diagnostic checklist addition):**
    For any new health-probe `service_name` in future PRs, the
    DIAGNOSE round MUST validate against migration files
    defining CHECK constraints, NOT just runtime call sites.
    "No collision with existing names" is a necessary but not
    sufficient check. Add to the future Q-D6 template:
    "(b) verify `service_name` is in the most-recent migration
    that defines `trading_system_health_service_name_check`; if
    not, add a DROP+ADD migration in the same PR." This is a
    one-line discipline addition that would have caught Defect
    B in PR 2's DIAGNOSE round and saved a deploy cycle.
- **type:** infrastructure + migration
- **phase:** phase_5_post_action_8_unblock
- **impact:** HIGH — activation gate for T-ACT-041's full ROI
  trajectory. Without this PR, the LightGBM model from PR 2 is
  effectively a no-op in production (loads from Supabase but
  fails to unpickle). With this PR, the next Railway redeploy
  unpickles successfully on first cold start, `lgbm_v1` source
  rows appear in `trading_prediction_outputs`, and the Engine
  Health admin page reflects model state correctly. Combined
  with T-ACT-040 (AI synthesis output unblock) and T-ACT-041
  (LightGBM hybrid deployment), this completes the chain that
  unlocks Action 8 (Conviction-Conditional Sizing) authorization
  once 3+ trading days of real-conviction data accumulate.
- **owner:** Cursor (DIAGNOSE + EXECUTE) + Operator (production
  log capture + per-defect authorization + post-merge migration
  application + redeploy)
- **modules_affected:**
  - `nixpacks.toml` (adds `aptPkgs = ["libgomp1"]`)
  - `supabase/migrations/20260430_add_direction_model_to_health_constraint.sql`
    (NEW, expands the CHECK allowlist by 1 entry)
- **docs_updated:**
  - `trading-docs/06-tracking/action-tracker.md` (this entry)
- **foundation_impact:** NONE — Nixpacks change is trading-image-
  scoped (the `sentinel/Dockerfile` GCP service has its own
  separate base image and does not consume nixpacks.toml).
  Migration is additive + idempotent + scoped to the trading-
  owned `trading_system_health` table.
- **verification:**
  - Pre-merge static checks: `nixpacks.toml` parses cleanly
    (1-line additive change), migration SQL parses cleanly
    (idempotent DROP IF EXISTS + ADD).
  - Pre-merge Q-A2 triangulation: `libgomp1` confirmed canonical
    package via 3 independent authoritative sources (LightGBM
    PyPI docs, lightgbm-org/LightGBM#7141 wheel inspector,
    Stack Overflow Q-55036740 accepted answer).
  - Pre-merge Q-B-conflict-scan: no other branches or pending
    PRs touch `supabase/migrations/`; established 2-prior-migration
    precedent (20260419, 20260421) for the DROP+ADD pattern.
  - Post-deploy operator verification (after migration applied
    + branch merged + Railway redeploys):
      a. Railway log grep: `direction_model_loaded source=supabase-fallback`
         appears (no more `direction_model_supabase_fetch_failed`).
      b. Supabase: `SELECT * FROM trading_system_health WHERE
         service_name='direction_model';` returns exactly 1 row
         with `status='degraded'` (Tier 2 Supabase fallback hit
         on cold start, expected steady state) and
         `last_error_message LIKE '%supabase fallback%'`.
      c. Constraint-applied SQL probe (operator runs immediately
         after migration + before merge):
         `SELECT pg_get_constraintdef(oid) FROM pg_constraint
          WHERE conname='trading_system_health_service_name_check';`
         Expect `'direction_model'` in the returned IN list.
      d. T-ACT-041 verification SQL (Step 4 of PR 2 EXECUTE
         summary) — `lgbm_v1` source rows now appear in
         `trading_prediction_outputs` within the 1-hour
         post-deploy window.
- **t_rules_checked:** T-Rule 1 (no foundation drift; sentinel
  image untouched), T-Rule 2 (migration is additive + idempotent
  + matches established pattern), T-Rule 7 (action-tracker
  updated this turn), T-Rule 9 (no out-of-scope edits — strictly
  the 3 files listed).

---

### T-ACT-041 — LightGBM model deployment via hybrid path (env-var gate + Supabase storage fallback)

- **id:** T-ACT-041
- **date:** 2026-04-30
- **action:** Closes the dominant blocker behind the "no trades"
  pattern: the LightGBM direction model
  (`direction_lgbm_v1.pkl`) had never been produced anywhere
  reachable (verified: 0 .pkl files in repo / git history / local
  fs / Railway), causing ~95% of prediction cycles to fall through
  to the regime-fallback placeholder triplet (`0.35/0.30/0.35`).
  PR establishes the hybrid path A + B-Supabase recommended in
  the Fix PR 2 PREP report.
  - **Operator one-time training (Phases A2 + A3):** Phase A2
    (`download_historical_data.py`) downloaded 32K training rows
    + 23.7K holdout rows from Polygon + CBOE. Phase A3
    (`train_direction_model.py`) produced `direction_lgbm_v1.pkl`
    + `model_metadata.json` with `win_rate=0.5292` (gate 0.52,
    PASSED with ~9σ margin on a 23.7K sample), 25 features, top
    contributors `vwap_distance, rv_20d, return_4h, iv_rv_ratio,
    vvix_z_score`. Polygon plan limited 5-min depth to ~3 years
    instead of spec'd 5; operator marked acceptable for v1.
  - **Stage 1 — Env-var-ize gate:** `train_direction_model.py:46`
    now reads `MIN_LABELED_SESSIONS_FOR_TRAINING` from env
    (`LGBM_MIN_LABELED_SESSIONS`), defaulting to 90. Operator's
    one-time bootstrap used `LGBM_MIN_LABELED_SESSIONS=0` to
    bypass the gate (live system has ~3-5 organic labeled
    sessions; gate exists to defer training until 90, but the
    training data itself comes from historical SPX bars not the
    label stream). Default 90 preserved for any future scheduled
    invocation. Documented in `backend/.env.example`.
  - **Stage 3 — Three-tier model loader:** Extracted L67-89 inline
    block into `prediction_engine.PredictionEngine._load_direction_model()`
    (per DIAGNOSE D5 for test ergonomics). Three tiers:
      Tier 1 — local cache:
        1a. `backend/models/` (operator's training output; absent
            on Railway since `.gitignore` blocks committing model
            files).
        1b. `/tmp/lightgbm_cache/` (populated by previous Tier 2
            invocation in same container; lost on Railway cold
            restart).
      Tier 2 — Supabase storage download from
        `ml-models/direction/v1/{direction_lgbm_v1.pkl,
        model_metadata.json}`, atomically staged to
        `/tmp/lightgbm_cache/.staging-<pid>/` before move-into-
        place via `os.replace()`. Both files succeed or neither
        moves — no partial cache state on disk.
      Tier 3 — total miss: `_direction_model` stays None;
        falls through to GEX/ZG path at L545. Per Q-D10:
        fall-through over fail-fast — keeps trading running at
        degraded conviction rather than crashing uvicorn on a
        dependency hiccup.
  - **Bundled bug fix (D3):** Pre-existing inline block had a
    silent failure mode — if local `.pkl` existed but `.json` did
    not, the model loaded but `_direction_features` stayed None,
    and inference at L545 short-circuited because of the AND
    check. New `_load_pickle_and_metadata()` raises on empty
    features list and the three-tier loader requires BOTH files
    present at every Tier 1 sub-path. The partial-state condition
    now correctly cascades to Tier 2 instead of silently dropping
    to GEX/ZG with a misleading `direction_model_loaded` log.
  - **Health probe (Q-D6):** One-shot at `_load_direction_model()`
    call site, writes `("direction_model", state, ...)` via
    `db.write_health_status()`. State enum:
      `healthy`  — Tier 1 hit (local cache).
      `degraded` — Tier 2 hit (loaded from Supabase fallback).
      `error`    — Tier 3 (both tiers missed, GEX/ZG active).
    Health write failures never block model load (`_safe_write_health`
    wrapper logs but swallows).
  - **Concurrent instantiation (D4):** `main.py:1283` and
    `trading_cycle.py:34` BOTH instantiate PredictionEngine —
    structural, not theoretical. Atomic-rename pattern keeps
    cache writes safe under the race; in practice the second
    instance hits the cache populated by the first (sub-second
    Tier 1b hit) so the doubled bandwidth is a worst-case bound,
    not the typical case.
  - **Storage client constraint (D2):** supabase-py 2.10 uses a
    SEPARATE httpx client for storage (NOT the HTTP/1.1-patched
    postgrest client at `db.py:132-167`). Safe at startup
    (single-threaded). Documented inline at the call site so any
    future scheduler-thread storage caller knows to extend the
    HTTP/2 patch.
  - **Operator-side artifacts (separate session post-merge):**
    Create `ml-models` Supabase storage bucket
    (RLS service-role-only); upload
    `direction_lgbm_v1.pkl` to `direction/v1/direction_lgbm_v1.pkl`
    and `model_metadata.json` to `direction/v1/model_metadata.json`
    via dashboard/CLI. Files NOT committed to git per the
    `.gitignore` approval-gate rule (lines 38-40).
  - **Tests (4):** Three required + one D3 partial-state regression
    guard. Tier 1 hit / Tier 2 fallback / Tier 3 total miss /
    partial-state-as-cache-miss. Real picklable `_FakeLGBM` class
    avoids `unittest.mock` pickling edge cases; `tmp_path` fixture
    isolates each test from production paths and from each other.
  - **lightgbm version pin (D6):** Bumped
    `backend/requirements.txt:13` from `lightgbm==4.5.0` to
    `lightgbm==4.6.0` to exactly match operator's training-env
    version. Removes pickle forward/backward-compatibility risk
    across minor versions.
- **type:** code + dependency
- **phase:** phase_5_post_action_8_unblock
- **impact:** HIGH — closes the dominant signal source. Combined
  with T-ACT-040 (AI synthesis output unblock), the system now
  has TWO independent conviction-signal sources reaching
  `trading_prediction_outputs`: LightGBM (~95% of cycles when
  fresh) and AI synthesis (~5% of cycles). Action 8
  (Conviction-Conditional Sizing) becomes safe to authorize once
  3+ days of real-conviction prediction data is captured
  post-deploy.
- **owner:** Cursor + Operator (joint — operator ran A2/A3
  locally; Cursor did all repo edits)
- **modules_affected:**
  - `backend/scripts/train_direction_model.py` (env-var gate)
  - `backend/.env.example` (operator-local override
    documentation)
  - `backend/prediction_engine.py` (three-tier loader, partial-
    state guard, health probe wrapper)
  - `backend/requirements.txt` (lightgbm 4.5.0 → 4.6.0)
  - `backend/tests/test_consolidation_s5.py` (4 regression
    tests)
- **docs_updated:**
  - `trading-docs/06-tracking/action-tracker.md` (this entry)
- **foundation_impact:** NONE — all changes within trading
  module boundaries. No `src/integrations/`, no shared
  foundation Python.
- **verification:**
  - Pytest: 4 new tests pass; full PR 1 ai_synth regression
    set (5 tests) still passes; pre-existing `test_phase_a3.py`
    failures (3, `ModuleNotFoundError: lightgbm` from training
    script import) UNCHANGED — confirmed not a regression by
    git-stash + re-run baseline check (matches T-ACT-040
    methodology).
  - Operator post-deploy verification SQL provided in
    commit body (group-by source against
    `trading_prediction_outputs`, 1-hour post-deploy window).
  - Schema migration: NONE — no new columns. Reuses
    `direction_model` as a `service_name` in the existing
    `trading_system_health` table (no collision with the 12+
    existing service_name values).
- **t_rules_checked:** T-Rule 1 (no foundation drift), T-Rule 2
  (no migration needed; reuses existing health table), T-Rule 5
  (4 new tests added; baseline + regression set passes), T-Rule 7
  (action-tracker updated this turn), T-Rule 9 (no out-of-scope
  edits — strictly the 5 files listed; trading_cycle.py NOT
  refactored despite D4-Option-B being viable, per operator's
  "increase ROI not clamp down" rule).

---

### T-ACT-040 — Fix PR: AI synthesis output loss (TTL/freshness coupling + schema migration)

- **id:** T-ACT-040
- **date:** 2026-04-30
- **action:** Two coupled bugs unblocked AI synthesis output flow
  to `trading_prediction_outputs`.
  - **Bug A (TTL + freshness gate, both 30 min, coterminous):**
    `backend_agents/synthesis_agent.py:201` set
    `ai:synthesis:latest` Redis TTL = 1800s and
    `backend/prediction_engine.py:466` rejected payloads at
    `age_s >= 1800`. Synthesis runs once per weekday at 09:15 ET via
    cron, so AI synth was consumable for ~30 min/day; rest of day
    fell through to LightGBM (missing) → GEX/ZG (insufficient) →
    regime fallback (`0.35/0.30/0.35` placeholder). Both gates
    extended to 28800s (8 hours) so synthesis covers the full
    trading day after the morning cron.
  - **Bug B (AI synth dict schema mismatch):**
    `backend/prediction_engine.py:498-510` AI synth return dict
    emitted three keys (`strategy_hint`, `sizing_modifier`,
    `source`) that are NOT columns in the production
    `trading_prediction_outputs` schema. PostgREST rejected each
    insert with PGRST204; the outer `try/except Exception` at
    `:985-991` swallowed the error; cycle returned None; no row
    persisted. Production schema query (operator-run via
    `information_schema.columns`) confirmed these 3 columns were
    absent while regime-fallback's extras (`signal_weak`,
    `allocation_tier`, `gex_conf_at_regime`,
    `gex_flip_zone_used`) WERE present as operator-induced drift.
    New migration `20260430_add_ai_synthesis_columns.sql` adds
    `strategy_hint TEXT`, `sizing_modifier NUMERIC(8,4)`,
    `source TEXT` (all NULLable, idempotent). AI synth dict also
    gained the 3 schema-aligned keys other paths emit
    (`signal_weak`, `expected_move_pts`, `expected_move_pct`).
  - **B1 guard on `signal_weak`:** AI synth direction='neutral'
    produces `p_bull == p_bear` by construction. A naive
    `abs(p_bull - p_bear) < 0.05` check would flag every neutral
    AI synth prediction as `signal_weak=True`, blocking iron_condor
    (the literal strategy for high-conviction range-bound
    predictions). Guard wraps the comparison with
    `direction != "neutral" and ...` so neutral cycles proceed to
    strategy_selector.
  - **Empirical confirmation pre-fix:** Apr 30 13:30-13:45 UTC had
    4 `prediction_from_ai_synthesis` Railway log events; same
    window in supabase: 0 rows. After 13:45 UTC: key TTL expired;
    0 events for rest of day. All 22 cycles for Apr 30 in supabase
    show `0.35/0.30/0.35` placeholder.
  - **Why ADD columns instead of REMOVE keys:** `strategy_hint` is
    consumed by `strategy_selector.py:1019-1075` (the
    `strategy:ai_hint_override:enabled` feature flag's logic);
    `source` is consumed at `strategy_selector.py:1517` (telemetry
    routing of `ai_hint` vs `regime`). Removing them would silently
    regress two existing capabilities and 4 existing tests. Adding
    3 columns is the cheaper + schema-disciplined path. This is
    Phase 5A schema-hardening starting here.
  - **Manual trigger script:** new
    `backend/scripts/trigger_synthesis_now.py` enables same-day
    operator validation post-deploy without waiting for next
    morning's cron. Cost ~$0.05/call.
- **type:** code + migration
- **phase:** phase_5_pre_action_8
- **impact:** HIGH — unblocks AI synthesis as a real conviction
  signal source for the prediction engine. Once both this fix and
  Fix PR 2 (LightGBM model deployment) land, the system has two
  independent conviction sources instead of running entirely on
  regime-fallback placeholders. Action 8 (Conviction-Conditional
  Sizing) stays in DRAFT until both PRs land.
- **owner:** Cursor
- **modules_affected:**
  - `backend_agents/synthesis_agent.py` (TTL extension)
  - `backend/prediction_engine.py` (freshness gate + AI synth dict
    shape)
  - `backend/tests/test_consolidation_s5.py` (regression tests)
  - `backend/scripts/trigger_synthesis_now.py` (NEW, validation
    helper)
  - `supabase/migrations/20260430_add_ai_synthesis_columns.sql`
    (NEW, schema migration)
- **docs_updated:**
  - `trading-docs/06-tracking/action-tracker.md` (this entry)
- **foundation_impact:** NONE — all changes within trading module
  boundaries; no `src/integrations/`, no foundation Python, no
  shared types beyond the trading_prediction_outputs schema (which
  is a trading-owned table per migration 20260416172751).
- **verification:**
  - Pytest: all 6 baseline tests
    (`test_consolidation_s5.py -k "ai_synthesis or synthesis"` and
    `test_iron_butterfly_safety_gates.py -k "ai_hint"`) still pass
    post-edit.
  - 2 new regression tests added:
    `test_ai_synthesis_return_dict_matches_persistence_schema` and
    `test_ai_synthesis_neutral_does_not_trigger_signal_weak_gate`.
  - Schema migration is idempotent (`IF NOT EXISTS`); operator
    applies via `npx supabase db push` per DEPLOYMENT SEQUENCING
    section in PR commit body.
  - Post-deploy: operator runs
    `python backend/scripts/trigger_synthesis_now.py` and verifies
    a row appears in `trading_prediction_outputs` with `p_bull`
    matching the AI synth's confidence (e.g., 0.62 for the morning
    Bull rec) instead of `0.35` placeholder.
- **t_rules_checked:** T-Rule 1 (no foundation drift), T-Rule 2
  (migration is additive + idempotent), T-Rule 5 (tests pass at
  baseline pre-edit and post-edit), T-Rule 7 (action tracker
  updated this turn), T-Rule 9 (no out-of-scope edits — strictly
  bounded to the 6 files listed).

---

### T-ACT-039 — Phase 3C: Calendar Spread (post-catalyst IV crush)

- **id:** T-ACT-039
- **date:** 2026-04-19
- **action:** Phase 3C — added calendar_spread strategy on branch
  `feature/phase-3c-calendar-spread`. Structure: SELL near-term (0DTE)
  ATM straddle + BUY far-term (next-Friday) ATM straddle as the hedge,
  net credit ≈ $1.50 per contract when near-term IV is still elevated
  relative to next-week IV (typical post-catalyst condition).
  - Selector wiring: `strategy_selector.py` adds `calendar_spread` to
    `STATIC_SLIPPAGE_BY_STRATEGY` (0.30), `PLACEHOLDER_CREDIT_BY_STRATEGY`
    (1.50), `_NEUTRAL_PREFERRED`, and `REGIME_STRATEGY_MAP["event"]`
    (now `["long_straddle", "calendar_spread", "iron_condor"]`).
  - Post-announcement gate: a new block AFTER the AI-hint override and
    BEFORE `get_strikes()`/sizing checks the
    `strategy:calendar_spread:enabled` flag and reads
    `calendar:today:intel` from Redis. Calendar fires only when the
    flag is ON AND a major event has already announced
    (`now_et >= event_et AND now_et.hour >= 14`). Otherwise it falls
    back to `long_straddle` (preferred) or `iron_condor`. Logs
    `calendar_spread_too_early_using_straddle` when the timing gate
    downgrades. NOTE: spec said "after event_size_mult block" but that
    block runs AFTER strikes/sizing — placement was moved earlier so
    strikes and sizing always see the final strategy_type.
  - Strikes: `strike_selector.py` adds `_get_next_friday_expiry()`
    helper and ATM-strike calendar-spread branches in BOTH `get_strikes`
    (chain path) and `_fallback_strikes`. All four legs at the same
    ATM strike (rounded to $5), `spread_width=0`, `near_expiry`
    (today/0DTE) and `far_expiry` (next Friday) returned alongside.
  - Sizing: `risk_engine.py` adds `calendar_spread: 0.003` to
    `_DEBIT_RISK_PCT` and a cost-based sizing branch BEFORE the
    `spread_width <= 0` guard (same pattern as long_straddle):
    contracts = `account_value × 0.3% / $150 per contract`.
  - DB persistence: `execution_engine.py` passes
    `signal.get("far_expiry_date")` into the `trading_positions` insert
    so calendar near/far legs are both tracked. The new column was
    added by migration `20260419_add_strategy_types.sql` (committed to
    main, must be applied via Supabase dashboard before Monday).
  - Feature flag: `strategy:calendar_spread:enabled` (default OFF).
- **type:** code
- **phase:** phase_3c
- **impact:** MEDIUM — adds post-catalyst alpha capture (~15–20 trading
  days/year on FOMC/CPI/NFP/PCE/PPI). Zero impact in production until
  the operator flips the flag, and even then only fires after a major
  catalyst has already announced.
- **owner:** Cursor
- **modules_affected:**
  - `backend/strategy_selector.py` (constants + post-announcement gate
    + far_expiry_date in signal)
  - `backend/strike_selector.py` (`_get_next_friday_expiry` + calendar
    branches in `get_strikes` and `_fallback_strikes`)
  - `backend/risk_engine.py` (debit risk pct + cost-based sizing)
  - `backend/execution_engine.py` (far_expiry_date in DB insert)
  - `backend/tests/test_phase_3c.py` (new — 7 tests)
- **docs_updated:**
  - `trading-docs/00-governance/what-is-actually-built.md` (Calendar
    Spread row updated to ✅ wired Phase 3C)
  - `trading-docs/08-planning/TASK_REGISTER.md` (Section 3C marked
    built; Section 7 already records the 20260419 migration)
  - `trading-docs/06-tracking/action-tracker.md` (this entry)
- **foundation_impact:** NONE — no foundation, frontend, or shared
  schema files touched. The Supabase schema change ships separately as
  `supabase/migrations/20260419_add_strategy_types.sql` (committed to
  main) and must be applied via the dashboard SQL editor before Monday.
- **verification:**
  - `python -m pytest tests/ -q` → **238 passed, 1 skipped, 0 failures**
    (231 pre-3C + 7 new Phase 3C tests).
  - `git diff --name-only main` confirms changes scoped to four
    `backend/` files + one new test + the three docs files.
  - All new behavior is gated behind
    `strategy:calendar_spread:enabled = true` (default OFF) — calendar
    spread can never enter the strategy pipeline by accident in
    production.
  - Pre-flight: the post-announcement gate is wrapped in try/except
    that falls back to `iron_condor` on any failure, so a malformed
    `calendar:today:intel` payload or a Redis outage cannot cause
    strategy selection to crash.
- **t_rules_checked:** T-Rule 1 (capital preservation — calendar
  sizing is cost-based at 0.3% account risk; the post-announcement
  gate prevents firing before IV crush actually starts), T-Rule 5
  (every external dependency has a fallback — Redis miss / malformed
  intel / parse error all fall back to iron_condor), T-Rule 8
  (modular separation — only the four allowed backend modules and the
  new test file are touched; no agents and no foundation files)

---

### T-ACT-038 — Phase 2C: Options Flow + Sentiment Agents + Enriched Synthesis

- **id:** T-ACT-038
- **date:** 2026-04-16
- **action:** Phase 2C — added two new Tier-2 intelligence agents and
  enriched the synthesis prompt with multi-signal confluence on branch
  `feature/phase-2c-agents`. Built across two sessions.

  **Session 1 — New agents + synthesis enrichment + scheduling.**
  - New `backend_agents/flow_agent.py`: pulls SPX/SPXW unusual options
    activity from Unusual Whales (paid, primary) and the SPX put/call
    ratio from Polygon (already-paid fallback). Computes a `flow_score`
    in [-100, +100] from the put/call ratio (bearish ≥1.2, bullish ≤0.7,
    neutral otherwise) plus an unusual-activity tally and a directional
    label (`bullish` / `bearish` / `neutral`). Output dict written to
    Redis key `ai:flow:brief` (TTL 8hr).
  - New `backend_agents/sentiment_agent.py`: combines NewsAPI top-headline
    keyword scoring (bullish/bearish lexicon), CNN Fear & Greed Index
    (extreme-fear contrarian uplift, extreme-greed warning), and the
    SPX overnight gap (read from `polygon:spx:overnight_gap` if present)
    into a `sentiment_score` in [-100, +100] and a `sentiment_direction`.
    Output dict written to Redis key `ai:sentiment:brief` (TTL 8hr).
  - `backend_agents/synthesis_agent.py` updated to read
    `ai:flow:brief` and `ai:sentiment:brief` from Redis on every run,
    compute a confluence score via new `_compute_confluence(macro, flow,
    sentiment)` (1.0 = all three signals agree, 0.0 = any pair opposes),
    and pass all three into a rewritten `_build_prompt()` that now has
    dedicated **SIGNAL CONFLUENCE**, **OPTIONS FLOW**, and **MARKET
    SENTIMENT** sections. The synthesis output dict gained three new
    fields: `confluence_score`, `flow_direction`, `sentiment_direction`.
    Schema/validation, the existing `agents:ai_synthesis:enabled` feature
    flag gate, and the `ai:synthesis:latest` Redis write are unchanged.
  - `backend/main.py` got two new job functions
    (`_run_flow_agent_job`, `_run_sentiment_agent_job`) following the
    same `sys.path.insert` + Redis-init pattern as the Phase 2A jobs,
    plus three scheduler entries: flow agent at **08:45 ET cron**,
    flow refresh **every 30 min during market hours**, sentiment agent
    at **08:30 ET cron**. All three log start/end and never raise.
  - `backend/config.py` adds `UNUSUAL_WHALES_API_KEY` (default empty
    string — system unchanged until the operator sets it on Railway).

  **Session 2 — Per-agent feature flag gates + documentation.** Added
  Redis-backed flag gates on the WRITE path of both new agents:
  `agents:flow_agent:enabled` for `flow_agent.py` and
  `agents:sentiment_agent:enabled` for `sentiment_agent.py`. Both
  default OFF. Pattern: agent always computes and returns the brief
  in-process; the `redis.setex(...)` to `ai:flow:brief` / `ai:sentiment:brief`
  is only executed when the flag is `"true"` (str or bytes). The flag
  read itself is wrapped in try/except — any Redis exception fails
  closed (no write). When flag is OFF a `*_flag_off_skipping_redis_write`
  debug log is emitted so operators can confirm gating in production.
  This means Phase 2C agents have ZERO downstream influence on
  `synthesis_agent.py` until the operator explicitly flips the flags,
  matching the safety contract used in Phase 2A and 2B.

- **type:** code
- **phase:** phase_2c
- **impact:** MEDIUM — new agents shipped behind dual feature flags;
  synthesis prompt structure changed but only fires when
  `agents:ai_synthesis:enabled=true` (also default OFF since Phase 2A);
  no production strategy/order path touched
- **owner:** Cursor
- **modules_affected:**
  - `backend_agents/flow_agent.py` (new)
  - `backend_agents/sentiment_agent.py` (new)
  - `backend_agents/synthesis_agent.py` (enriched: confluence + new
    prompt sections + 3 new output fields)
  - `backend/config.py` (added `UNUSUAL_WHALES_API_KEY`)
  - `backend/main.py` (2 new job functions + 3 scheduler entries)
  - `backend/tests/test_phase_2c.py` (new — 15 tests)
- **docs_updated:**
  - `trading-docs/06-tracking/action-tracker.md` (this entry)
  - `trading-docs/00-governance/what-is-actually-built.md` (flow +
    sentiment agent rows added with Phase 2C activation status and the
    two new feature-flag keys)
- **foundation_impact:** NONE — no foundation, frontend, migration, or
  shared-schema files touched
- **verification:**
  - `python -m pytest tests/ -v` → **227 passed, 1 skipped, 0 failures**
    (Session 1 added 11 new tests; Session 2 added 4 more covering both
    flag-OFF skip and flag-ON write paths for both agents).
  - `git diff --name-only origin/main` confirms changes are scoped to
    `backend/` (config + main + tests), `backend_agents/` (3 files), and
    `trading-docs/` only — no production strategy/risk/order code
    touched.
  - All four feature flags relevant to Phase 2C
    (`agents:ai_synthesis:enabled`, `agents:flow_agent:enabled`,
    `agents:sentiment_agent:enabled`, plus the existing
    `strategy:ai_hint_override:enabled` from Phase 2B) default OFF, so
    deployment alone changes nothing; operator must enable explicitly.
- **t_rules_checked:** T-Rule 1 (capital preservation — both new agents
  wrap every external call in try/except with safe fallbacks; flag read
  fails closed; Redis write failure is silently ignored), T-Rule 5
  (every external dependency has a fallback — Unusual Whales failure →
  Polygon-only; NewsAPI failure → F&G + gap only; F&G failure → 50;
  every agent returns `_empty_brief()` on total failure), T-Rule 8
  (modular separation — all new agent code lives exclusively in
  `backend_agents/`; production `backend/` modules never import from
  `backend_agents/` and only read the briefs through Redis)

---

### T-ACT-037 — Phase 2A Complete: Economic Intelligence Layer (3 sessions)

- **id:** T-ACT-037
- **date:** 2026-04-19
- **action:** Phase 2A — built the full three-tier Economic Intelligence
  Layer in three sessions on branch `feature/phase-2a-intelligence`.

  **Session 1 — Tier 1 Economic Calendar.** New module
  `backend_agents/economic_calendar.py` fetches today's macro events from
  Finnhub (paid, primary) with FRED release-dates fallback (free) and a
  major earnings filter (NVDA/AAPL/MSFT/META/AMZN/GOOGL/GOOG/TSLA/NFLX/
  AMD/AVGO). Output is a classified intel dict written to Redis key
  `calendar:today:intel` (TTL 24hr). Day classifications:
  `catalyst_major`, `catalyst_minor`, `earnings_major`, `normal`.
  Recommended postures: `straddle`, `reduced_size`, `normal`, `sit_out`.
  `pre_market_scan()` in `backend/main.py` reads the calendar BEFORE the
  VVIX heuristic; major catalysts force `day_type=event` with confidence
  0.95, otherwise the existing VVIX classifier runs unchanged.

  **Session 2 — Tier 2 AI Brain + Tier 3 Surprise Detector + Priority 0
  wiring.** Three new agents and one prediction-engine integration:
  - `backend_agents/macro_agent.py` reads `calendar:today:intel`,
    fetches CME FedWatch on FOMC days, computes consensus-based
    direction bias (CPI/PCE/PPI inflation logic, NFP heuristic, FOMC
    neutral) and estimates daily SPX move from `gex:atm_iv` or VIX
    proxy. Writes `ai:macro:brief` (TTL 8hr).
  - `backend_agents/synthesis_agent.py` reads macro brief + GEX
    context, calls Claude `claude-sonnet-4-5` with a structured-JSON
    system prompt, validates schema (direction/confidence/strategy/
    rationale/risk_level/sizing_modifier) and enforces safety bounds
    (confidence ≤0.85, sizing ≤1.2). Writes `ai:synthesis:latest`
    (TTL 30min) **only when feature flag `agents:ai_synthesis:enabled`
    is `true` in Redis** (default OFF). Skips entirely if
    `ANTHROPIC_API_KEY` is absent.
  - `backend_agents/surprise_detector.py` runs on catalyst days only,
    compares actual vs consensus, classifies surprises (inflation,
    jobs, FOMC), aggregates with magnitude weighting (large=2x,
    small=0.5x), and updates `ai:synthesis:latest` with a
    surprise-informed direction + strategy override (large bull →
    `debit_call_spread`, large bear → `debit_put_spread`).
  - `backend/prediction_engine.py` `_compute_direction()` gains
    **Priority 0** that reads `ai:synthesis:latest` before Priority 1
    LightGBM. Activates only when (a) the key exists, (b) age <30 min,
    (c) confidence ≥0.55. Returns `source: "ai_synthesis"`. Hardened
    with `getattr` + try/except so tests that bypass `__init__` via
    `__new__()` (5 pre-existing tests) continue to pass.
  - `backend/main.py` schedules four new APScheduler cron jobs (ET):
    8:25 calendar, 8:30 macro, 8:45 surprise detector, 9:15 synthesis.
    Each job uses `sys.path.insert` to load from `backend_agents/` and
    is wrapped in try/except — never blocks the rest of the scheduler.

  **Session 3 — smoke test, validation, documentation.** Smoke test via
  `railway run` confirmed all four agent modules import cleanly in the
  deployed Python environment and `get_todays_market_intelligence()`
  executes end-to-end against external networks (Finnhub key empty in
  Railway today, so it correctly falls back to FRED). Live Redis read
  verification deferred to post-merge because Railway's
  `redis.railway.internal` is only reachable from inside the deployed
  container, and the deployed container does not yet contain the new
  `backend_agents/` modules until this PR is merged.

  **Two intentional deviations from the original task spec, both
  required to make the spec's own tests pass:**
  1. `synthesis_agent.py` — `import config` moved from inside
     `run_synthesis_agent()` to module top so `patch("synthesis_agent.config")`
     can mock it (committed as `e24e75e`).
  2. `prediction_engine.py` Priority 0 — wrapped the `_read_redis` call
     in try/except plus `getattr(self, "redis_client", None)` guard so
     5 pre-existing tests that bypass `__init__` do not crash. Behaviour
     in production is identical to the spec snippet.

- **type:** code
- **phase:** phase_2a
- **impact:** HIGH — AI brain wired into prediction pipeline; first
  macro-aware classifier; first LLM-driven trade recommendation path
- **owner:** Cursor
- **modules_affected:**
  - Trading (new): `backend_agents/__init__.py`,
    `backend_agents/economic_calendar.py`,
    `backend_agents/macro_agent.py`,
    `backend_agents/synthesis_agent.py`,
    `backend_agents/surprise_detector.py`
  - Trading (modified): `backend/main.py` (pre_market_scan reads
    calendar, four new job functions, four new scheduler.add_job calls,
    `import json`),
    `backend/prediction_engine.py` (Priority 0 in `_compute_direction()`),
    `backend/config.py` (FINNHUB_API_KEY, ANTHROPIC_API_KEY, NEWSAPI_KEY
    — all optional, default empty),
    `backend/requirements.txt` (anthropic>=0.40.0, finnhub-python>=2.4.19)
  - Trading (tests): `backend/tests/test_phase_2a_calendar.py` (6 tests),
    `backend/tests/test_phase_2a_agents.py` (7 tests)
- **docs_updated:**
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** NONE — no files outside `backend/`,
  `backend_agents/`, or `trading-docs/` modified
- **verification:**
  - 199/199 unit tests passing (1 skipped). 13 new Phase 2A tests cover
    Session 1 calendar fallback / classifications / Redis-write
    contract, and Session 2 macro fallback, surprise CPI/PCE direction,
    synthesis no-API-key skip, and synthesis feature-flag-OFF
    write-suppression.
  - `railway run python` smoke test confirmed: all four agent modules
    import cleanly in the deployed env; `economic_calendar` runs end to
    end and writes a structured-log line; FRED fallback path works when
    Finnhub key is absent.
  - All API keys default to empty — system behaviour is unchanged from
    pre-Phase-2A until `FINNHUB_API_KEY` and/or `ANTHROPIC_API_KEY` are
    added to Railway. Feature flag `agents:ai_synthesis:enabled` is OFF
    by default — Priority 0 falls through to LightGBM/GEX-ZG until the
    operator explicitly sets the key to `true`.
  - `git diff --name-only origin/main` confirms all changes are scoped
    to `backend/`, `backend_agents/`, and `trading-docs/06-tracking/`.
    No frontend, foundation, migration, or other module touched.
- **t_rules_checked:** T-Rule 1 (capital preservation — never blocks
  trading on any failure; every agent has try/except + safe fallback),
  T-Rule 5 (every external dependency has a fallback — Finnhub→FRED,
  Claude→empty dict, Redis→Priority 1), T-Rule 8 (modular separation —
  agent code lives exclusively in `backend_agents/`; `backend/` only
  reads from Redis or imports inside scoped functions, never at module
  top, except for the prediction-engine's Priority 0 read which uses the
  existing `_read_redis` helper)

---

### T-ACT-017 — Fix Group 5: Paper Phase Critical

- **id:** T-ACT-017
- **date:** 2026-04-17
- **action:** Fix Group 5 paper-phase critical — maybeSingle→maybe_single (7 files,
  unblocks all DB lookups in production), commission legs fixed (spreads=4,
  iron condor/butterfly=8), heartbeat threshold 360→90s, error_count_1h stops
  resetting on keepalives (GLC-006 now meaningful), debit strategy exit logic
  (take profit at 100% gain, stop at full loss), credit spread stop-loss moved
  to 200% of credit, VVIX endpoint fixed to I:VVIX with Authorization header.
- **type:** code
- **phase:** phase_4
- **impact:** CRITICAL
- **owner:** Cursor
- **modules_affected:**
  - Trading: `backend/db.py` (remove error_count_1h reset on healthy),
    `backend/main.py` (heartbeat threshold 360→90s),
    `backend/execution_engine.py` (LEGS_BY_STRATEGY dict, correct commission per strategy),
    `backend/position_monitor.py` (debit strategies exit logic, credit stop at 200%,
    current_pnl in initial SELECT),
    `backend/polygon_feed.py` (I:VVIX endpoint, Authorization header, 403 fallback),
    `backend/criteria_evaluator.py` (explicit EOD error_count_1h reset after GLC-006 read),
    `backend/calibration_engine.py` (maybeSingle rename),
    `backend/session_manager.py` (maybeSingle rename),
    `backend/tests/test_fix_group5.py` (9 new tests)
- **docs_updated:**
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** NONE — no files outside /backend/ or trading-docs/ modified
- **verification:** 67/67 unit tests passing. All imports clean. `git diff --name-only origin/main` confirms only backend files modified. No frontend or migration files touched. Zero `.maybeSingle()` calls remain in backend/.
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ No foundation files modified
  - T-Rule 5 (Capital Preservation): ✅ D-010/D-011 time stops now apply correctly to both debit and credit strategy exit logic
  - T-Rule 10 (No Silent Failures): ✅ error_count_1h now accumulates correctly; DB lookup failures no longer silently produce AttributeError

---

### T-ACT-016 — Fix Group 4: Performance Fixes

- **id:** T-ACT-016
- **date:** 2026-04-17
- **action:** Fix Group 4 performance — GEX engine uses Redis pipeline (N round-trips → 1), heartbeat_check made async (no longer blocks event loop), EOD job DST-safe timing (hour=22 UTC covers both EDT/EST), calibration_engine 90-day date filter on slippage MAE, model_retraining 60-day date filter on per-regime accuracy, criteria_evaluator GLC-003 now filters closed positions only.
- **type:** code
- **phase:** phase_4
- **impact:** LOW
- **owner:** Cursor
- **modules_affected:**
  - Trading: `backend/gex_engine.py` (pipeline), `backend/main.py` (async heartbeat + DST fix), `backend/calibration_engine.py` (date filter), `backend/model_retraining.py` (date filter), `backend/criteria_evaluator.py` (closed-only filter), `backend/tests/test_fix_group4.py` (new)
- **docs_updated:**
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** NONE
- **verification:** 59/59 unit tests passing. Imports clean. Only 5 backend files + 1 new test file modified. No frontend or migration files touched.
- **t_rules_checked:** T-Rule 1 (Foundation Isolation): PASS

---

### T-ACT-015 — Fix Group 3: Medium Priority Security & Reliability Fixes

- **id:** T-ACT-015
- **date:** 2026-04-17
- **action:** Fix Group 3 — thread-safe Supabase singleton (double-checked lock), lazy feed initialization in on_startup (Redis must be ready first), Sentinel Supabase singleton (prevents connection exhaustion during emergency), Sentinel config wrapped in try/except with structured logging before sys.exit, prediction_engine Redis defaults changed from fake confidence to neutral.
- **type:** code
- **phase:** phase_4
- **impact:** MEDIUM
- **owner:** Cursor
- **modules_affected:**
  - Trading: `backend/db.py` (double-checked locking), `backend/main.py` (lazy feed init), `backend/prediction_engine.py` (Redis defaults guard), `sentinel/main.py` (Supabase singleton + config hardening), `backend/tests/test_fix_group3.py` (new)
- **docs_updated:**
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** NONE
- **verification:** 54/54 unit tests passing. `db._client_lock` confirmed present. Only 4 backend/sentinel files + 1 new test file modified. No frontend or migration files touched.
- **t_rules_checked:** T-Rule 1 (Foundation Isolation): PASS, T-Rule 10 (No Silent Failures): Sentinel config crash now logs before sys.exit(1)

---

### T-ACT-014 — Fix Group 2: High Priority Data Integrity Fixes

- **id:** T-ACT-014
- **date:** 2026-04-17
- **action:** Fix Group 2 — error_count_1h incremented on error writes (GLC-006 now meaningful), GEX nearest wall returns closest to SPX price not lowest, TRADIER_ACCOUNT_ID added to REQUIRED_KEYS, D-019 check_execution_quality called on position close, session status transitions pending→active→closed wired to 9:30 AM and 4:30 PM ET scheduler jobs.
- **type:** code
- **phase:** phase_4
- **impact:** HIGH
- **owner:** Cursor
- **modules_affected:**
  - Trading: `backend/db.py` (error_count_1h), `backend/gex_engine.py` (nearest wall), `backend/config.py` (REQUIRED_KEYS), `backend/execution_engine.py` (D-019), `backend/session_manager.py` (open/close transitions), `backend/main.py` (market open/close jobs), `backend/tests/test_fix_group2.py` (new)
- **docs_updated:**
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** NONE
- **verification:** 50/50 unit tests passing. `session_manager` and `gex_engine` import cleanly. Only 6 backend files + 1 new test file modified. No frontend, migration, or other files touched.
- **t_rules_checked:** T-Rule 1 (Foundation Isolation): PASS, T-Rule 9 (Audit Trail): session open/close both write audit logs, T-Rule 10 (No Silent Failures): all job wrappers catch and log exceptions

---

### T-ACT-013 — Fix Group 1: Critical Blocking Fixes

- **id:** T-ACT-013
- **date:** 2026-04-17
- **action:** Fix Group 1 critical — position monitor + time stops (D-010/D-011), polygon_feed timezone fix (ET-aware market hours + real VVIX API call), target_credit placeholder pricing by strategy type, Sharpe ratio corrected to % returns. Unblocks GLC-001/002/003/005/011.
- **type:** code
- **phase:** phase_4
- **impact:** CRITICAL
- **owner:** Cursor
- **modules_affected:**
  - Trading: `backend/position_monitor.py` (new), `backend/main.py` (3 jobs added), `backend/polygon_feed.py` (timezone + VVIX), `backend/strategy_selector.py` (target_credit), `backend/model_retraining.py` (Sharpe formula), `backend/tests/test_position_monitor.py` (new)
- **docs_updated:**
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** NONE
- **verification:** 44/44 unit tests passing. `position_monitor` imports cleanly. Only 5 backend files + 1 new test file modified. No frontend, migration, or other files touched.
- **t_rules_checked:** T-Rule 1 (Foundation Isolation): PASS, T-Rule 5 (Capital Preservation): D-010/D-011 now enforced via time stops, T-Rule 10 (No Silent Failures): all job wrappers catch and log exceptions

---

### T-ACT-010 — Phase 4A: Paper Phase Criteria Tracker

- **id:** T-ACT-010
- **date:** 2026-04-17
- **action:** Built Phase 4A paper phase criteria tracker. Created `supabase/migrations/20260417000001_paper_phase_criteria.sql` — new `paper_phase_criteria` table with all 12 GLC criteria pre-seeded, RLS via `trading.view` permission, `updated_at` trigger. Created `backend/criteria_evaluator.py` with 8 automated evaluation functions (GLC-001 through GLC-006, GLC-011, GLC-012) plus `run_criteria_evaluation` orchestrator. Manual criteria (GLC-007 through GLC-010) are intentionally skipped to preserve operator sign-off. GLC-012 starts as `blocked` pending CBOE DataShop approval. Updated `backend/main.py` with EOD cron job at 21:30 UTC (4:30 PM ET). Replaced `ConfigPage.tsx` 3-item placeholder with full 12-criteria live dashboard: progress bar, pass/fail summary banners, per-criterion detail rows with status badges, observation counts, and manual tags.
- **type:** code
- **phase:** phase_4
- **impact:** HIGH
- **owner:** Cursor
- **modules_affected:**
  - Trading: `supabase/migrations/20260417000001_paper_phase_criteria.sql` (new), `backend/criteria_evaluator.py` (new), `backend/main.py` (EOD job added), `src/pages/admin/trading/ConfigPage.tsx` (criteria section replaced), `backend/tests/test_criteria_evaluator.py` (new)
- **docs_updated:**
  - trading-docs/08-planning/master-plan.md (TPLAN-PAPER-004-A, G: not_started → implemented)
  - trading-docs/00-governance/system-state.md (Phase 4: blocked → in_progress ✅ Phase 4A started)
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** NONE — no foundation files modified; ConfigPage update is additive (new query + new UI section replacing placeholder)
- **verification:** 31/31 unit tests passing (28 existing + 3 new). `criteria_evaluator` imports cleanly. `git diff --name-only origin/main` returns only backend/, src/, supabase/, trading-docs/ files. Zero TypeScript linter errors on ConfigPage.tsx.
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ Only trading/* files modified; no foundation components or routes touched
  - T-Rule 2 (Table Prefix Isolation): ✅ New table uses `paper_phase_criteria` (trading namespace, no prefix required per schema design)
  - T-Rule 5 (Capital Preservation Absolute): ✅ D-013 enforced — all 12 criteria required; no partial pass; evaluator never auto-advances live trading
  - T-Rule 7 (Security Inheritance): ✅ RLS on `paper_phase_criteria` with `trading.view` permission gate
  - T-Rule 10 (No Silent Failures): ✅ `_upsert_criterion` never raises; all evaluation functions catch exceptions; `run_criteria_evaluation` returns error dict on failure

---

### T-ACT-009 — Phase 3B: Positions, Signals, Performance & Config Pages

- **id:** T-ACT-009
- **date:** 2026-04-16
- **action:** Built Phase 3B — replaced all 4 placeholder pages with full implementations. `PositionsPage.tsx`: filterable table (All/Open/Closed tabs), stat cards, complete position details with P&L coloring and status badges. `SignalsPage.tsx`: prediction engine output log with direction badges, RCS/CV_Stress coloring, no-trade signal indicators. `PerformancePage.tsx`: session history table (last 30 sessions), model performance metrics grid (5/20/60-day accuracy, drift status, profit factor, challenger active), stat summary cards. `ConfigPage.tsx`: Tradier connection status with sandbox warning, sizing phase visual indicator (4 steps), paper phase go-live criteria (3 pending items), danger zone kill switch wired to live session. Phase 3 complete.
- **type:** code
- **phase:** phase_3
- **impact:** HIGH
- **owner:** Cursor
- **modules_affected:**
  - Trading: `src/pages/admin/trading/PositionsPage.tsx` (replaced), `src/pages/admin/trading/SignalsPage.tsx` (replaced), `src/pages/admin/trading/PerformancePage.tsx` (replaced), `src/pages/admin/trading/ConfigPage.tsx` (replaced)
- **docs_updated:**
  - trading-docs/08-planning/master-plan.md (TPLAN-CONSOLE-003-D, E, F, G: in_progress → implemented)
  - trading-docs/00-governance/system-state.md (Phase 3: in_progress → complete ✅ Passed; module statuses updated)
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** NONE — only trading page files modified; no foundation components or routes touched
- **verification:** Zero TypeScript/linter errors across all 4 pages. Tab switching in PositionsPage changes displayed data. Direction badge colors correct (bull=green, bear=red, neutral=grey). PerformancePage shows empty states for both sections when no data. ConfigPage shows sandbox amber warning when is_sandbox=true. KillSwitchButton in ConfigPage uses existing component with confirmation dialog.
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ Only trading page files modified; no foundation components or pages touched
  - T-Rule 3 (Route Namespace Isolation): ✅ All pages live under /admin/trading/*
  - T-Rule 7 (Permission Gating): ✅ ConfigPage already gated with trading.configure in App.tsx; others with trading.view
  - T-Rule 10 (No Silent Failures): ✅ All pages show ErrorState on query failure; EmptyState on no data

---

### T-ACT-008 — Phase 3A: War Room + Navigation + Hooks + Shared Components

- **id:** T-ACT-008
- **date:** 2026-04-16
- **action:** Built Phase 3A complete admin console foundation. Added 5 trading nav items to `admin-navigation.ts` (War Room, Positions, Signals, Performance, Config). Registered 5 lazy routes in `App.tsx` under `/admin/trading/*` with `PermissionGate`. Created 4 trading data hooks (`useTradingSession`, `useTradingPrediction`, `useTradingPositions`, `useTradingSystemHealth`). Created 5 shared components (`RegimePanel`, `CVStressPanel`, `PredictionConfidence`, `KillSwitchButton`, `CapitalPreservationStatus`). Built full `WarRoomPage.tsx` operator cockpit with live stat cards, regime/CV_Stress/prediction panels, kill-switch, capital preservation, open positions list, engine health summary, and data freshness footer. Created 4 placeholder pages (Positions, Signals, Performance, Config) for Phase 3B.
- **type:** code
- **phase:** phase_3
- **impact:** HIGH
- **owner:** Cursor
- **modules_affected:**
  - Trading: `src/config/admin-navigation.ts` (5 items added), `src/App.tsx` (5 lazy routes added), `src/hooks/trading/useTradingSession.ts` (new), `src/hooks/trading/useTradingPrediction.ts` (new), `src/hooks/trading/useTradingPositions.ts` (new), `src/hooks/trading/useTradingSystemHealth.ts` (new), `src/components/trading/RegimePanel.tsx` (new), `src/components/trading/CVStressPanel.tsx` (new), `src/components/trading/PredictionConfidence.tsx` (new), `src/components/trading/KillSwitchButton.tsx` (new), `src/components/trading/CapitalPreservationStatus.tsx` (new), `src/pages/admin/trading/WarRoomPage.tsx` (new), `src/pages/admin/trading/PositionsPage.tsx` (new), `src/pages/admin/trading/SignalsPage.tsx` (new), `src/pages/admin/trading/PerformancePage.tsx` (new), `src/pages/admin/trading/ConfigPage.tsx` (new)
- **docs_updated:**
  - trading-docs/00-governance/system-state.md (Phase 2: blocked → complete; Phase 3: blocked → in_progress; module statuses updated)
  - trading-docs/08-planning/master-plan.md (TPLAN-CONSOLE-003-A, B, C, H, I → implemented; D, E, F, G, J → in_progress)
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** Additive only — appended trading nav items, appended lazy imports and nested routes in App.tsx. No foundation routes, components, pages, or logic modified.
- **verification:** Zero TypeScript/linter errors in all 16 new/modified files. All hooks export correctly. KillSwitchButton shows confirmation dialog before executing. RegimePanel shows disagreement warning when `regime_agreement=false`. No imports from foundation components except allowed set (PageHeader, StatCard, LoadingSkeleton, ErrorState, EmptyState, Card, Badge, Button, Alert, AlertTitle, AlertDescription).
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ Only trading/* files created; additive-only changes to routes/nav/App; no foundation components modified
  - T-Rule 3 (Route Namespace Isolation): ✅ All 5 new routes live under /admin/trading/*
  - T-Rule 7 (Permission Gating): ✅ All trading routes use PermissionGate with trading.view or trading.configure
  - T-Rule 10 (No Silent Failures): ✅ KillSwitchButton catches all errors and shows toast; hooks surface errors to callers

---

### T-ACT-012 — Sentinel Deployed to GCP Cloud Run

- **id:** T-ACT-012
- **date:** 2026-04-16
- **action:** Sentinel watchdog deployed to GCP Cloud Run (us-east1, min-instances=1, always-on).
  Service URL: https://marketmuse-sentinel-208163021541.us-east1.run.app.
  Sentinel pings Railway backend every 30s, closes all positions if heartbeat lost > 120s.
  GLC-009 tracking begins — manual verification required after 7 days of operation.
- **type:** deployment
- **phase:** phase_4
- **impact:** HIGH
- **owner:** Manual (GCP Cloud Shell)
- **modules_affected:** sentinel/main.py, trading_system_health
- **foundation_impact:** NONE
- **t_rules_checked:** T-Rule 9 ✅ (audit log on emergency), T-Rule 10 ✅ (no silent failures)

---

### T-ACT-001 — Initial Trading Schema Migration Applied

- **id:** T-ACT-001
- **date:** 2026-04-16
- **action:** Applied T-MIG-001 — initial trading database schema (8 new tables, profiles ALTER, 5 permissions seed, role_permissions seed, 10 job_registry entries, 20 alert_configs entries)
- **type:** migration
- **phase:** pre_phase_1 (schema is a Phase 1 prerequisite, not a Phase 1 deliverable completion)
- **impact:** HIGH (database schema change affecting profiles + 8 new tables)
- **owner:** Lovable (Supabase migration tool)
- **modules_affected:**
  - Trading: trading_operator_config, trading_sessions, trading_prediction_outputs, trading_signals, trading_positions, trading_system_health, trading_model_performance, trading_calibration_log
  - Foundation: profiles (3 new columns: trading_tier, tradier_connected, tradier_account_id), permissions (5 new rows), role_permissions (admin role), job_registry (10 new rows), alert_configs (20 new rows)
- **docs_updated:**
  - trading-docs/07-reference/database-migration-ledger.md (T-MIG-001 status: pending → applied)
  - trading-docs/00-governance/system-state.md (Trading Database Schema: not_started → implemented; added trading_schema_migration: T-MIG-001_applied)
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** Approved per MARKETMUSE_MASTER.md Part 4.1 — `profiles` ALTER adds 3 trading-specific columns. Inserts into `permissions`, `role_permissions`, `job_registry`, `alert_configs` use `ON CONFLICT DO NOTHING` to avoid affecting existing foundation rows. No foundation schemas modified or destroyed.
- **verification:**
  - Migration completed successfully (Supabase migration tool confirmation)
  - Security linter: 8 pre-existing warnings unchanged, 0 new warnings from this migration
  - All 8 new tables have RLS enabled with appropriate policies
  - All trading_* tables follow naming convention
  - PENDING: Manual post-migration checklist from regression-strategy.md (sign-in, /admin/health, /admin/jobs, /admin/audit, /admin/permissions, /profile, /admin/users)
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ Only approved profiles ALTER, no other foundation modifications
  - T-Rule 2 (Table Prefix Isolation): ✅ All 8 new tables use trading_ prefix
  - T-Rule 4 (Locked Decisions): ✅ Schema implements D-005, D-006, D-010, D-011, D-013, D-014, D-018, D-022 storage requirements
  - T-Rule 7 (Security Inheritance): ✅ RLS on every table, service_role writes, authenticated reads (calibration log: service_role only)
  - T-Rule 10 (No Silent Failures): ✅ trading_system_health table created for heartbeat monitoring

---

### T-ACT-002 — Engine Health Page Implemented (TPLAN-INFRA-001-I)

- **id:** T-ACT-002
- **date:** 2026-04-16
- **action:** Implemented `/admin/trading/health` (Engine Health). Added `ADMIN_TRADING_*` route constants, "Trading System" navigation section, lazy-loaded `TradingHealthPage` with `RequirePermission` (`trading.view`), 10s polling on `trading_system_health`, market-hours CRITICAL banner, and last-10 trading alerts panel.
- **type:** code
- **phase:** phase_1
- **impact:** MEDIUM (new admin page, isolated trading namespace, no foundation logic touched)
- **owner:** Lovable
- **modules_affected:**
  - Trading: `src/pages/admin/trading/HealthPage.tsx` (new)
  - Foundation routing/nav (additive only): `src/config/routes.ts`, `src/config/admin-navigation.ts`, `src/App.tsx`
- **docs_updated:**
  - trading-docs/07-reference/route-index.md (ADMIN_TRADING_HEALTH: planned → implemented)
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** Additive only — appended trading route constants, appended a "Trading System" nav section, appended one nested route under `/admin`. No foundation routes, components, or behavior modified.
- **verification:**
  - Page queries `trading_system_health` (NOT `system_health_snapshots`) — confirmed in code
  - `refetchInterval: 10_000` set unconditionally per route-index.md
  - Empty state ("Services not yet reporting") shown when table is empty — not an error
  - CRITICAL banner gated on `isMarketHoursET()` (9:30–16:00 America/New_York, weekdays) AND offline count > 0
  - Permission gate `trading.view` enforced at route level via `PermissionGate`
  - Single combined `Promise.all` query for health + alerts (matches existing pattern)
  - PENDING: Operator E2E sign-in + visit `/admin/trading/health` to confirm empty state renders
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ Only additive changes to routes/nav/App; foundation pages untouched
  - T-Rule 2 (Table Prefix Isolation): ✅ Reads from `trading_system_health` and filters `alert_history` by `trading.%` metric_key
  - T-Rule 3 (Route Namespace Isolation): ✅ Lives under `/admin/trading/*`
  - T-Rule 7 (Security Inheritance): ✅ Reuses `RequirePermission`, `AdminLayout`, `trading.view` permission from index
  - T-Rule 10 (No Silent Failures): ✅ Empty state distinguishes "no backend yet" from errors; ErrorState shown on real failures

---

### T-ACT-003 — Phase 1 Python Backend Scaffold

- **id:** T-ACT-003
- **date:** 2026-04-16
- **action:** Created Python backend data infrastructure: config.py, db.py,
  logger.py, tradier_feed.py, polygon_feed.py, databento_feed.py, gex_engine.py,
  main.py, requirements.txt, .env.example, unit tests
- **type:** code
- **phase:** phase_1
- **impact:** HIGH
- **owner:** Cursor
- **modules_affected:** data_ingestor, gex_engine, tradier_websocket, databento_feed
- **docs_updated:** system-state.md, master-plan.md, action-tracker.md
- **foundation_impact:** NONE — no files outside /backend/ or .gitignore modified
- **verification:** All unit tests pass. No hardcoded keys. No foundation files touched.
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ No foundation files modified
  - T-Rule 2 (Table Prefix Isolation): ✅ Only writes to trading_* tables
  - T-Rule 7 (Security Inheritance): ✅ Service role key, no keys in code
  - T-Rule 10 (No Silent Failures): ✅ Every exception logged, health status updated

---

### T-ACT-007 — Phase 2B: Strategy Selector, Risk Engine & Virtual Execution

- **id:** T-ACT-007
- **date:** 2026-04-16
- **action:** Built Phase 2B complete virtual trading pipeline. Created `risk_engine.py` (position sizing D-014, daily drawdown halt D-005, trade frequency gate D-020, execution quality feedback D-019), `strategy_selector.py` (Stage 0-4 pipeline, time gates D-010/D-011, static slippage D-015, regime/direction filtering), `execution_engine.py` (virtual position open/close, D-022 audit logging at 3rd and 5th consecutive loss, full P&L accounting), `trading_cycle.py` (full orchestrator: session → drawdown → predict → select → execute). Updated `main.py` to use `run_trading_cycle`. All 10 TPLAN-VIRTUAL-002 deliverables now implemented. 10 new unit tests (28 total passing).
- **type:** code
- **phase:** phase_2
- **impact:** HIGH
- **owner:** Cursor
- **modules_affected:**
  - Trading: `backend/risk_engine.py` (new), `backend/strategy_selector.py` (new), `backend/execution_engine.py` (new), `backend/trading_cycle.py` (new), `backend/main.py` (cycle wired), `backend/tests/test_risk_engine.py` (new), `backend/tests/test_strategy_selector.py` (new)
- **docs_updated:**
  - trading-docs/00-governance/system-state.md (Strategy Selector, Risk Engine, Execution Engine: not_started → in_progress)
  - trading-docs/08-planning/master-plan.md (TPLAN-VIRTUAL-002-A through J: all → implemented)
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** NONE — no files outside /backend/ or trading-docs/ modified
- **verification:** 28/28 unit tests passing. All 4 new modules import cleanly. `git diff --name-only origin/main` confirmed only `backend/main.py` tracked (new files untracked). No foundation files touched.
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ No foundation files modified
  - T-Rule 2 (Table Prefix Isolation): ✅ Writes only to trading_positions, trading_sessions, trading_system_health, audit_logs
  - T-Rule 3 (Single Operator): ✅ V1 single-operator scope — no multi-user logic
  - T-Rule 5 (Capital Preservation Absolute): ✅ D-005 -3% daily halt hardcoded; D-022 halt at 5 losses hardcoded; neither can be disabled
  - T-Rule 10 (No Silent Failures): ✅ Every exception caught, logged, written to trading_system_health; D-022 triggers audit log at 3rd and 5th consecutive loss

---

### T-ACT-006 — Phase 2A: Prediction Engine + Session Manager

- **id:** T-ACT-006
- **date:** 2026-04-16
- **action:** Built Phase 2A prediction engine core. Created `prediction_engine.py` with Layer A (regime placeholder using VVIX Z-score), CV_Stress computation proxy, and Layer B direction prediction (placeholder — real LightGBM on 93 features in Phase 4). Implemented D-018 VVIX emergency circuit breaker (Z≥3.0 → no-trade), D-021 regime disagreement guard (HMM≠LightGBM → RCS-15 penalty + audit log), and D-022 capital preservation no-trade trigger (5 consecutive losses → halt). Created `session_manager.py` for `trading_sessions` CRUD. Updated `main.py` with 5-minute prediction cycle scheduler, session init on startup. 9 unit tests added and all passing.
- **type:** code
- **phase:** phase_2
- **impact:** HIGH
- **owner:** Cursor
- **modules_affected:**
  - Trading: `backend/prediction_engine.py` (new), `backend/session_manager.py` (new), `backend/main.py` (prediction cycle + session init), `backend/tests/test_prediction_engine.py` (new), `backend/tests/test_session_manager.py` (new)
- **docs_updated:**
  - trading-docs/00-governance/system-state.md (Prediction Engine: not_started → in_progress)
  - trading-docs/08-planning/master-plan.md (TPLAN-VIRTUAL-002-A, B, C, D: not_started → in_progress)
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** NONE — no files outside /backend/ or trading-docs/ modified
- **verification:** 9/9 unit tests passing. Clean imports for both modules. No foundation files in `git diff --name-only origin/main`. D-018, D-021, D-022 logic verified by dedicated test cases.
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ No foundation files modified
  - T-Rule 2 (Table Prefix Isolation): ✅ Writes only to trading_prediction_outputs, trading_sessions, trading_system_health
  - T-Rule 3 (Single Operator): ✅ V1 single-operator scope — no multi-user logic
  - T-Rule 5 (Capital Preservation Absolute): ✅ D-022 halt at 5 losses hardcoded, cannot be disabled
  - T-Rule 10 (No Silent Failures): ✅ Every exception caught, logged, and written to trading_system_health; audit logged on D-021 disagreement and no-trade signals

---

### T-ACT-005 — Phase 1 Complete + GEX Heartbeat Keepalive Fix

- **id:** T-ACT-005
- **date:** 2026-04-16
- **action:** Closed Phase 1 — Python backend deployed to Railway on Python 3.11, all 4 data feeds connected (Tradier, Databento, Polygon/VVIX, GEX), Engine Health page showing live data, all Phase 1 gate criteria met. Added `gex_heartbeat_keepalive()` scheduled job (30s interval, always-on) to ensure GEX engine reports healthy during market-closed periods when no computation is running.
- **type:** code
- **phase:** phase_1
- **impact:** MEDIUM
- **owner:** Cursor
- **modules_affected:**
  - Trading: `backend/main.py` (new `gex_heartbeat_keepalive` function + APScheduler registration)
- **docs_updated:**
  - trading-docs/00-governance/system-state.md (Phase 1: not_started → complete, Go/No-Go: ❌ Not evaluated → ✅ Passed)
  - trading-docs/08-planning/master-plan.md (TPLAN-INFRA-001-C, D, F, G: in_progress → implemented)
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** NONE — no files outside /backend/ or trading-docs/ modified
- **verification:** All Phase 1 gate criteria met: Python 3.11 via .python-version + nixpacks.toml, all 4 feeds connected and writing to Supabase, Engine Health page live, GEX heartbeat keepalive prevents false-offline status during market-closed hours.
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ No foundation files modified
  - T-Rule 2 (Table Prefix Isolation): ✅ Only writes to trading_system_health (trading_ prefix)
  - T-Rule 10 (No Silent Failures): ✅ gex_heartbeat_keepalive logs exceptions, never swallows errors

---

### T-ACT-011 — Phase 4B: Calibration and Model Retraining Infrastructure

- **id:** T-ACT-011
- **date:** 2026-04-16
- **action:** Built Phase 4B calibration and model retraining infrastructure. Created `calibration_engine.py` (slippage MAE via trading_calibration_log, CV_Stress CWER classification error rate, touch probability Brier score — all functions return gracefully with insufficient data). Created `model_retraining.py` (directional accuracy 5d/20d/60d, per-regime accuracy for GLC-002, drift detection D-016 with audit log on warning/critical, Sharpe ratio GLC-005, profit factor, capital preservation trigger count, champion/challenger infra placeholder). Added calibration log write to `execution_engine.py` on every virtual position close (feeds TPLAN-PAPER-004-J intraday feedback loop). Updated `main.py` with two weekly cron jobs: Sunday 23:00 UTC (calibration) and Sunday 23:30 UTC (model performance). 7 new unit tests (38 total passing).
- **type:** code
- **phase:** phase_4
- **impact:** HIGH
- **owner:** Cursor
- **modules_affected:**
  - Trading: `backend/calibration_engine.py` (new), `backend/model_retraining.py` (new), `backend/execution_engine.py` (calibration log on close), `backend/main.py` (two weekly jobs), `backend/tests/test_calibration_engine.py` (new), `backend/tests/test_model_retraining.py` (new)
- **docs_updated:**
  - trading-docs/08-planning/master-plan.md (TPLAN-PAPER-004-B/C/D/F/J: not_started → implemented, E: blocked, H/I: not_started)
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** NONE — no files outside /backend/ or trading-docs/ modified
- **verification:** 38/38 unit tests passing. Both modules import cleanly. `git diff --name-only origin/main` confirmed only backend files modified. No foundation files touched. Weekly cron triggers verified in scheduler registration.
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ No foundation files modified
  - T-Rule 2 (Table Prefix Isolation): ✅ Writes only to trading_calibration_log, trading_model_performance, trading_system_health, audit_logs
  - T-Rule 10 (No Silent Failures): ✅ All compute functions catch exceptions and return gracefully; drift detection fires audit log on warning/critical; calibration log write failure is logged as warning, never raises

---

### T-ACT-012 — Phase 4C: Sentinel Watchdog on GCP Cloud Run

- **id:** T-ACT-012
- **date:** 2026-04-16
- **action:** Built Phase 4C Sentinel watchdog. Created `sentinel/` directory as a fully isolated, separately deployable GCP Cloud Run service. `sentinel/main.py` pings Railway backend /health every 30s; if heartbeat missed > 120s, triggers emergency close of all open positions in Supabase and halts today's session. Emergency close is idempotent (will not fire twice per process lifecycle) and resets if Railway recovers. Writes health status to trading_system_health (service_name='sentinel') on every cycle. Full GCP deploy instructions in DEPLOYMENT.md. 3 smoke tests all passing.
- **type:** code
- **phase:** phase_4
- **impact:** HIGH
- **owner:** Cursor
- **modules_affected:**
  - Sentinel (new deployable): `sentinel/main.py`, `sentinel/requirements.txt`, `sentinel/Dockerfile`, `sentinel/.env.example`, `sentinel/DEPLOYMENT.md`, `sentinel/test_sentinel.py`
- **docs_updated:**
  - trading-docs/08-planning/master-plan.md (TPLAN-PAPER-004-I: not_started → in_progress)
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** NONE — no backend/ or src/ files modified; sentinel/ is an independent deployable
- **verification:** 3/3 smoke tests passing. sentinel/main.py imports cleanly. Emergency idempotency verified. TRADIER_SANDBOX=true default. No foundation files in diff.
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ Only sentinel/ and trading-docs/ modified — zero backend/ or src/ changes
  - T-Rule 9 (Audit Trail): ✅ trigger_emergency_close writes audit_log with reason and result; recovery also logged
  - T-Rule 10 (No Silent Failures): ✅ All network/DB calls wrapped in try/except; every failure logged; sentinel_health written on every cycle

---

### T-ACT-018 — Fix Group 6: Data Quality

- **id:** T-ACT-018
- **date:** 2026-04-17
- **action:** Fix Group 6 data quality — slippage perturbation (D-019 meaningful),
  D-017 CV_Stress exit implemented (P&L >= 50% gate), D-022 consecutive-loss-sessions
  computed and written at EOD, allocation_tier wired into compute_position_size (D-004),
  pre_market_scan implemented (VVIX Z → day_type classifier, fixes GLC-002 hard fail),
  scheduler timing corrected to 14:00 UTC (9 AM ET).
  Also created trading-docs/08-planning/known-false-positives.md to prevent
  future AI diagnostic sessions from re-raising confirmed non-issues.
- **type:** code
- **phase:** phase_4
- **impact:** HIGH
- **owner:** Cursor
- **modules_affected:**
  - `backend/execution_engine.py` — _simulate_fill: actual slippage perturbed ±20% noise (D-019 now yields real feedback signal for LightGBM)
  - `backend/position_monitor.py` — D-017 CV_Stress exit (cv_stress>70 AND P&L>=50% max profit), current_cv_stress added to SELECT
  - `backend/session_manager.py` — D-022 consecutive_loss_sessions computed from last 3 closed sessions at EOD; fires audit log when >=3
  - `backend/risk_engine.py` — allocation_tier parameter added to compute_position_size; TIER_MULTIPLIERS applied (full/moderate/low/pre_event/danger); danger tier returns contracts=0 immediately
  - `backend/strategy_selector.py` — allocation_tier=prediction.get("allocation_tier","full") passed to compute_position_size
  - `backend/main.py` — pre_market_scan implemented (VVIX Z-score → trend/open_drive/range/reversal/event/unknown); update_session imported at module level; scheduler corrected from 9 UTC to 14 UTC (9 AM ET), day_of_week="mon-fri" added
  - `backend/tests/test_fix_group6.py` — 9 new unit tests (76 total passing)
  - `trading-docs/08-planning/known-false-positives.md` — new file, 12 confirmed false positives and 9 genuinely deferred issues documented
- **docs_updated:**
  - trading-docs/06-tracking/action-tracker.md (this entry)
  - trading-docs/08-planning/known-false-positives.md (new)
- **foundation_impact:** NONE — no frontend (src/) or migration (supabase/) files modified
- **verification:** 76/76 unit tests passing. danger contracts=0 confirmed. slippage varies=True confirmed. git diff --name-only origin/main shows only backend/ files modified.
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ No frontend or migration files modified
  - T-Rule 4 (Locked Decisions): ✅ D-017 CV_Stress exit implemented; D-022 session-level consecutive loss tracking now active
  - T-Rule 10 (No Silent Failures): ✅ All new code blocks wrapped in try/except with logger.error; D-022 failure logs error but does not interrupt session close

---

### T-ACT-019 — Fix Group 7A: Real Data Feeds (Tradier SSE + Databento Live)

- **id:** T-ACT-019
- **date:** 2026-04-17
- **action:** Fix Group 7A — real data feeds. tradier_feed.py: replaces sleep stub
  with real SSE stream (POST session → GET stream), writes quotes to Redis with
  60s TTL, plus REST fallback for single symbol fetch. databento_feed.py: replaces
  sleep stub with real Databento Live SDK subscription to OPRA.PILLAR/trades,
  runs in thread executor, parses OCC symbology to extract strike/expiry/type.
- **type:** code
- **phase:** phase_4
- **impact:** HIGH
- **owner:** Cursor
- **modules_affected:**
  - `backend/tradier_feed.py` — `_run_stream_loop`: real httpx SSE stream; POST to `/v1/markets/events/session` for sessionid, then GET SSE stream; handles quote/summary/heartbeat event types; `fetch_quote_rest()` added as REST fallback for single symbol; `import httpx` added
  - `backend/databento_feed.py` — `_run_stream_loop`: real Databento Live SDK (`db.Live`), subscribes to OPRA.PILLAR/trades, runs blocking iterator in `asyncio.run_in_executor` (thread pool); OCC symbology parser extracts root/expiry/option_type/strike; SPX underlying read from Redis; `import re` added
  - `backend/tests/test_fix_group7a.py` — 4 new unit tests (80 total passing)
- **docs_updated:**
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** NONE — only tradier_feed.py and databento_feed.py modified; no frontend, migration, or other backend files touched
- **verification:** 80/80 unit tests passing. TradierFeed and DatabentoFeed import cleanly. git diff --name-only shows only the two feed files modified.
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ Only two feed files and test file modified
  - T-Rule 10 (No Silent Failures): ✅ All network/parse errors caught with logger.warning/error; backoff retry handled by parent start() loop

---

### T-ACT-020 — Fix Group 7B: Strike Selection + Mark-to-Market

- **id:** T-ACT-020
- **date:** 2026-04-17
- **action:** Fix Group 7B — strike selection + mark-to-market. strike_selector.py:
  fetches Tradier option chain (16-delta target), falls back to SPX±1.5% heuristic.
  mark_to_market.py: prices open positions every minute using live quotes or
  Black-Scholes fallback, updates current_pnl and peak_pnl. strategy_selector.py:
  wires real strikes into every signal. execution_engine.py: populates short_strike,
  long_strike, expiry_date on position open. main.py: mark-to-market job every
  minute during market hours.
- **type:** code
- **phase:** phase_4
- **impact:** HIGH
- **owner:** Cursor
- **modules_affected:**
  - `backend/strike_selector.py` (new) — Tradier option chain fetch (GET /v1/markets/options/chains with greeks=true), delta-based strike selection (16-delta for credit, 25-delta for debit), SPX±pct fallback, all 8 strategy types covered; `get_strikes()` public API
  - `backend/mark_to_market.py` (new) — `run_mark_to_market(redis_client)`: fetches open virtual positions with strike/expiry columns, prices each via live Redis quote or Black-Scholes fallback, writes current_pnl + peak_pnl to trading_positions every minute; `_bs_option_price()` uses scipy.stats.norm
  - `backend/strategy_selector.py` — added `StrategySelector.__init__` with redis_client; `from strike_selector import get_strikes`; strike lookup before signal build; real `spread_width` (not hardcoded 5.0) passed to `compute_position_size`; signal dict populated with short_strike, long_strike, short_strike_2, long_strike_2, expiry_date, real target_credit
  - `backend/execution_engine.py` — `open_virtual_position` now reads expiry_date, short_strike, long_strike, short_strike_2, long_strike_2 from signal dict (was hardcoded None)
  - `backend/main.py` — `from mark_to_market import run_mark_to_market`; `run_mark_to_market_job()` function; `trading_mark_to_market` cron job every minute market hours (mon-fri, 9-15 UTC)
  - `backend/tests/test_fix_group7b.py` (new) — 6 tests; 85 passed + 1 skipped (scipy ATM call test skipped; scipy in requirements.txt but not in local dev env)
- **docs_updated:**
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** NONE — no frontend, migration, or out-of-scope backend files modified
- **verification:** 85 passed, 1 skipped (scipy), 0 failed. strike_selector and mark_to_market import cleanly. git diff --name-only confirms only execution_engine.py, main.py, strategy_selector.py modified (new files untracked).
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ No frontend or migration files modified
  - T-Rule 10 (No Silent Failures): ✅ strike_selector returns fallback on any error; mark_to_market returns {errors:1} on outer failure; all per-position errors caught and counted

---

### T-ACT-021 — Fix Group 9: Critical Paper Phase Integrity

- **id:** T-ACT-021
- **date:** 2026-04-17
- **action:** Fix Group 9 critical integrity — (1) AsyncIOScheduler now uses
  America/New_York timezone, all cron hours changed to ET: D-010 14:30,
  D-011 15:45, market open 09:30, market close 16:30, pre-market 09:00,
  EOD 17:00, weekly 18:00/18:30. (2) Prediction cycle changed to cron
  market hours only (9-15 ET Mon-Fri). (3) Debit strategy fill records
  real cost abs(credit)+slippage not max(0.05). (4) Exit credit uses
  MTM current_pnl derivation not fabricated 50%. (5) Calibration log
  actual_slippage writes fill slippage not P&L delta. (6) entry_spx_price
  reads tradier:quotes:SPX from Redis, fallback 5200.0 not 5000.0.
  (7) _upsert_criterion uses .upsert() not .update().
- **type:** code
- **phase:** phase_4
- **impact:** CRITICAL
- **owner:** Cursor
- **modules_affected:**
  - `backend/main.py` — `from zoneinfo import ZoneInfo`; `AsyncIOScheduler(timezone=ZoneInfo("America/New_York"))`; all cron jobs converted from UTC to ET (D-010 hour=14/min=30, D-011 hour=15/min=45, market open hour=9/min=30, market close hour=16/min=30, pre-market hour=9/min=0, EOD hour=17/min=0, weekly Sunday hour=18/min=0 and hour=18/min=30); prediction cycle converted from `trigger="interval", minutes=5` to `trigger="cron", day_of_week="mon-fri", hour="9-15", minute="*/5"`
  - `backend/execution_engine.py` — `_simulate_fill`: branches on `base_credit < 0`; debit returns `abs(base_credit) + actual_slippage` (no longer clamped to 0.05 floor); credit path unchanged; `is_debit` boolean added to return dict. `close_virtual_position`: when `exit_credit is None`, derives from `pos["current_pnl"]` (MTM from `mark_to_market.py`) using inverse of P&L formula; handles debit (negative entry_credit) and credit cases separately; falls back to 50% only if current_pnl is None. Calibration log `actual_slippage` = `pos.get("entry_slippage") or exit_slip` (was `abs(entry_credit - exit_credit)`).
  - `backend/prediction_engine.py` — new `_get_spx_price()` method reads `tradier:quotes:SPX` from Redis, parses JSON, returns `last / ask / bid / 5200.0`; `run_cycle()` now returns `"spx_price": self._get_spx_price()` (was `5000.0`).
  - `backend/criteria_evaluator.py` — `_upsert_criterion` uses `.upsert({criterion_id, ...}, on_conflict="criterion_id")` (was `.update({...}).eq("criterion_id", id)`).
  - `backend/tests/test_fix_group9.py` (new) — 9 tests: scheduler timezone string check, debit fill > 2.50 for target -3.00, credit fill < target, calibration log no P&L delta, `_get_spx_price` fallback 5200.0, `run_cycle` source has no 5000.0, `_upsert_criterion` uses `.upsert(`, prediction cycle uses `cron` not `interval`, D-010/D-011 registered at ET hours.
- **docs_updated:**
  - trading-docs/06-tracking/action-tracker.md (this entry)
  - trading-docs/08-planning/known-false-positives.md (added D-012, D-013 to GENUINELY DEFERRED table)
- **foundation_impact:** NONE — no frontend, migration, or out-of-scope backend files modified
- **verification:** 94 passed, 1 skipped (scipy pre-existing), 0 failed. `git diff --name-only origin/main` confirms only backend/main.py, backend/execution_engine.py, backend/prediction_engine.py, backend/criteria_evaluator.py, backend/tests/test_fix_group9.py, and trading-docs changed. Manual: `_simulate_fill(-3.00, 'long_put')` → fill_price ≈ 3.05, is_debit=True; `_simulate_fill(1.50, 'put_credit_spread')` → fill_price ≈ 1.36, is_debit=False.
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ No frontend or migration files modified
  - T-Rule 5 (Paper Phase Integrity): ✅ Fill economics, exit pricing, calibration slippage, SPX attribution all now record truthful values
  - T-Rule 6 (Time Stops D-010/D-011 correctness): ✅ Scheduler timezone America/New_York — D-010 fires at 14:30 ET and D-011 at 15:45 ET in both EDT and EST (previously 1 hour late in EDT = 8 months/year)
  - T-Rule 10 (No Silent Failures): ✅ _upsert_criterion now creates the row if missing instead of silently matching zero rows

---

### T-ACT-022 — Fix Group 10: GEX Data + Signal Quality

- **id:** T-ACT-022
- **date:** 2026-04-17
- **action:** Fix Group 10 GEX + signal quality — (1) Tradier SSE now subscribes
  to 0DTE SPXW option chain at startup (capped at 200 symbols); GEX engine has
  REST fallback for missing quotes so GEX is no longer always zero. (2) Prediction
  cycle skips on Redis unavailable or when all feed signals (VVIX Z + GEX
  confidence) are both None — prevents garbage rows poisoning GLC-001/002.
  (3) D-005 daily drawdown now includes unrealized MTM P&L from open positions —
  large open losses now count toward the -3% halt. (4) GLC-006 now uses
  session_error_snapshot audit entries written at EOD close, scoped to actual
  sessions rather than the rolling 1h time window.
- **type:** code
- **phase:** phase_4
- **impact:** HIGH
- **owner:** Cursor
- **modules_affected:**
  - `backend/tradier_feed.py` — `_run_stream_loop` now calls `_get_0dte_expiry()` + `_get_option_chain_tradier()` from `strike_selector`, extends `symbols` list with up to 200 SPXW option symbols before opening SSE stream; falls back gracefully to SPX-only if chain fetch fails; removed unused `from datetime import date` local import
  - `backend/gex_engine.py` — `compute_gex` inner loop: on cache miss, performs synchronous `httpx.get /v1/markets/quotes` with 3s timeout, caches result in `quote_cache` and Redis (60s TTL); skips symbol with `gex_quote_missing_after_rest` warning only if REST also fails
  - `backend/prediction_engine.py` — `run_cycle`: (a) Redis availability guard via `self.redis_client.ping()` — returns `{no_trade_signal: True, no_trade_reason: "redis_unavailable"}` immediately if ping fails; (b) reads `vvix_z_raw` and `gex_conf_raw` from Redis before session fetch; if both are None returns `{no_trade_signal: True, no_trade_reason: "feed_data_unavailable"}`
  - `backend/trading_cycle.py` — added `from db import get_client`; D-005 block replaced with `realized_pnl + unrealized_pnl` where `unrealized_pnl` sums `current_pnl` from all open positions via `trading_positions` table query; falls back to realized only on DB error
  - `backend/session_manager.py` — `close_today_session`: inserts `trading.session_error_snapshot` audit log entry (total_errors + per-service breakdown) immediately before the `trading.session_closed` entry; provides EOD snapshot for GLC-006 evaluation
  - `backend/criteria_evaluator.py` — `evaluate_glc006_zero_exceptions` rewritten: (a) queries last 20 closed sessions; (b) reads `trading.session_error_snapshot` audit entries from last 30 days; (c) sums `total_errors` from snapshots; (d) falls back to live `trading_system_health` if no snapshots exist yet
  - `backend/tests/test_fix_group10.py` (new) — 6 tests: GEX REST fallback source check, Redis unavailable no-trade, no-feed-data no-trade (with session mock), D-005 unrealized source check, GLC-006 snapshot source check, close_today_session snapshot source check
- **docs_updated:**
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** NONE — no frontend, migration, or out-of-scope backend files modified
- **verification:** 100 passed, 1 skipped (scipy pre-existing), 0 failed. All 4 modules import cleanly. `git diff --name-only origin/main` limited to 6 allowed backend files only.
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ No frontend or migration files modified
  - T-Rule 5 (Paper Phase Integrity): ✅ D-005 now catches unrealized losses from open positions; GLC-006 is properly session-scoped; prediction engine refuses to trade on stale/absent feed data
  - T-Rule 10 (No Silent Failures): ✅ GEX REST fallback logs `gex_quote_missing_after_rest` on both Redis and REST failure; Redis guard logs `prediction_cycle_skipped_redis_unavailable`

---

### T-ACT-023 — GEX/ZG Regime + Direction Classifier

- **id:** T-ACT-023
- **date:** 2026-04-17
- **action:** GEX/ZG regime + direction classifier. prediction_engine.py:
  _compute_regime now has two genuinely independent inputs — regime_hmm
  (VVIX Z-score) and regime_lgbm (GEX zero-gamma distance). D-021
  disagreement now fires legitimately when feeds disagree. _compute_direction
  now uses tanh(SPX-ZG/ZG × 50) × 0.15 probability tilt from zero-gamma level.
  signal_weak gate added: no trade when |p_bull - p_bear| < 0.10.
  GEX confidence < 0.3 falls back to VVIX-only (data quality gate).
  Expected lift: +5 to +8pp on GLC-001 direction accuracy.
- **phase:** phase_4
- **impact:** HIGH — core prediction quality
- **t_rules_checked:** T-Rule 1 ✅, T-Rule 4 ✅ (D-021 now active)

---

### T-ACT-024 — Phase 0 Session 1: Four Profit Suppressors

- **id:** T-ACT-024
- **date:** 2026-04-17
- **action:** Phase 0 Session 1 — four profit suppressors removed.
  P0.1: commission 0.65→0.35 per leg (Tradier actual rate).
  P0.2: entry gate 10:00AM→9:35AM (GEX/ZG valid at open, 5min buffer for tape).
  P0.3: signal_weak threshold 0.10→0.05 (0.10 was blocking trades at normal
  0.5-0.8% ZG distance; 0.05 blocks only genuinely ambiguous <0.3% ZG).
  P0.5: event-day 40% size multiplier on day_type="event" sessions.
- **phase:** phase_4
- **impact:** HIGH — combined +6-9pp annual return expected
- **t_rules_checked:** T-Rule 1 ✅, T-Rule 5 ✅ (D-005 still absolute)

---

### T-ACT-025 — Phase 0 Session 2: IV/RV Filter + Partial Exit

- **id:** T-ACT-025
- **date:** 2026-04-17
- **action:** Phase 0 Session 2 — IV/RV filter and partial exit at 25%.
  P0.4: polygon_feed.py now fetches VIX (I:VIX) and SPX daily close
  (I:SPX) every 5 minutes; computes 20-day annualized realized vol from
  rolling SPX close history; stores polygon:vix:current and
  polygon:spx:realized_vol_20d to Redis. prediction_engine._evaluate_no_trade
  gates on VIX < realized_vol × 1.10 (iv_rv_cheap_premium no-trade).
  P0.6: new migration adds partial_exit_done to trading_positions.
  position_monitor closes 30% of contracts at 25% of max profit, marks
  partial_exit_done=True, writes audit log. Full 50% exit still fires on
  remaining contracts.
- **phase:** phase_4
- **impact:** HIGH — IV/RV prevents selling cheap premium; partial exit
  reduces variance and captures early reversals
- **t_rules_checked:** T-Rule 1 ✅, T-Rule 5 ✅

---

### T-ACT-026 — Phase A1: Outcome Labels + Real GLC-001/002 Accuracy

- **id:** T-ACT-026
- **date:** 2026-04-17
- **action:** Phase A1 — prediction outcome labels + real GLC-001/002 accuracy.
  New migration adds outcome_direction, outcome_correct, spx_return_30min to
  trading_prediction_outputs. label_prediction_outcomes() in model_retraining.py
  runs daily at EOD: fetches SPX price 30min after each prediction via Polygon
  aggregate API, writes real direction outcome and correct/incorrect flag.
  evaluate_glc001 now computes accuracy = outcome_correct/total_labeled (was
  win_rate proxy). evaluate_glc002 now groups outcome_correct by regime (was
  observation count). run_eod_criteria_evaluation calls labeling before
  criteria evaluation so GLC-001/002 always have fresh labels. GLC-001 and
  GLC-002 can now pass paper phase graduation criteria.
  Also documented 4 deferred items from Phase 0 Session 2 review (D-017 to D-020).
- **phase:** phase_4
- **impact:** CRITICAL — unblocks all ML training and paper phase graduation
- **t_rules_checked:** T-Rule 1 ✅, T-Rule 5 ✅ (D-005 unchanged)

---

### T-ACT-027 — Phase A2: Historical Data Download Script

- **id:** T-ACT-027
- **date:** 2026-04-17
- **action:** Phase A2 — historical data download script.
  backend/scripts/download_historical_data.py: downloads SPX 5-min OHLCV
  2020-2026 from Polygon (I:SPX aggregate API, paginated), SPX daily 2010-2026
  from Polygon, VIX/VVIX/VIX9D daily from CBOE free CSVs. Handles rate limits
  (429 retry with backoff), 403 plan errors (clear message), CBOE CSV parsing.
  Outputs parquet files to backend/data/historical/ (gitignored). Writes
  download_manifest.json with row counts and date ranges for A3 to validate.
  backend/scripts/README.md: documents how to run scripts.
  backend/data/historical/ added to .gitignore.
- **phase:** phase_a
- **impact:** HIGH — enables all ML model training (A3, A4)
- **t_rules_checked:** T-Rule 1 ✅ (no production files modified)

---

### T-ACT-028 — Phase A3: LightGBM Direction Model Training + Wiring

- **id:** T-ACT-028
- **date:** 2026-04-17
- **action:** Phase A3 — LightGBM direction model training script + wiring.
  backend/scripts/train_direction_model.py: engineers 47 features from
  SPX 5-min + VIX/VVIX/VIX9D daily parquet files, trains LightGBM classifier
  (3-class: bull/bear/neutral at ±0.1% threshold, 30min forward horizon) with
  2025+ holdout validation, requires >=72% directional win rate gate before
  saving model. Saves direction_lgbm_v1.pkl + model_metadata.json to
  backend/models/. Script is standalone (not wired into scheduler).
  backend/prediction_engine.py: __init__ loads direction_lgbm_v1.pkl when
  present; _compute_direction uses LightGBM inference as priority 1, falls
  back to GEX/ZG rule-based (priority 2) on model error or when model is not
  loaded. Uses getattr for defensive attribute access so legacy test fixtures
  using __new__ continue to pass. Emits model_source="lgbm_v1" in output when
  model is used.
  backend/polygon_feed.py: _compute_spx_features writes live SPX technical
  features (return_5m/30m/1h/4h, prior_day_return, rsi_14) to Redis every
  5 minutes inside _poll_loop for inference. Failures logged as
  spx_features_update_failed and swallowed (inference falls back to defaults).
  backend/tests/test_phase_a3.py: 4 unit tests covering feature engineering
  column coverage, model loading, GEX/ZG fallback when model=None, and
  metadata writing.
- **phase:** phase_a
- **impact:** CRITICAL — replaces hardcoded probability tables with trained
  ML once model is committed; expected win-rate lift 65% -> 74-78%
- **t_rules_checked:** T-Rule 1 ✅ (no foundation files touched), T-Rule 5 ✅
  (capital preservation gates unchanged), T-Rule 8 ✅ (A3 follows A1+A2 in
  phase A sequence)

---

### T-ACT-029 — Phase B1: Dynamic Spread Width Optimizer

- **id:** T-ACT-029
- **date:** 2026-04-17
- **action:** Phase B1 — dynamic spread width optimizer.
  backend/strike_selector.py: added VIX_SPREAD_WIDTH_TABLE and
  get_dynamic_spread_width(vix_level). get_strikes() reads
  polygon:vix:current from Redis and selects width:
  $2.50 (VIX<15), $5.00 (15-20), $7.50 (20-30), $10.00 (>30).
  Both the Tradier-chain happy path and the _fallback_strikes path
  use the dynamic width, so long_strike geometry matches the declared
  spread_width field in all branches (consistency fix beyond literal
  task to avoid risk_engine under-sizing positions).
  _fallback_strikes() now accepts spread_width parameter (default =
  DEFAULT_SPREAD_WIDTH) instead of hardcoding the module constant.
  result dict gains vix_level_used for observability.
  backend/risk_engine.py: added position_sized structured log after
  contracts computation in compute_position_size for width monitoring.
  backend/tests/test_phase_b1.py: 9 unit tests — 5 cover VIX buckets
  (low, normal, elevated, high-stress, invalid), 2 cover get_strikes
  Redis read paths (VIX present / VIX absent), 1 covers
  _fallback_strikes parameter threading, 1 covers the Tradier-chain
  happy path with VIX=25 returning $7.50 width and correct long_strike
  geometry.
- **phase:** phase_b
- **impact:** HIGH — +1-3pp expected annual return from better premium
  capture in elevated-VIX regimes; also unblocks B4 width-aware stop-loss
- **t_rules_checked:** T-Rule 1 ✅ (no foundation files touched),
  T-Rule 5 ✅ (capital preservation gates unchanged; risk_engine sizing
  math unchanged, only an info log added), T-Rule 8 ✅ (Phase B follows
  Phase A in build order)

---

### T-ACT-030 — Phase B2: Asymmetric Iron Condor + OptionsDX Processor

- **id:** T-ACT-030
- **date:** 2026-04-17
- **action:** Phase B2 + OptionsDX processor.
  backend/strike_selector.py: _get_gex_asymmetry() reads
  gex:nearest_wall and gex:confidence from Redis and returns
  put_width_mult/call_width_mult multipliers (1.5x on the strong
  side, 0.75x on the weak side). Applied only when confidence >= 0.3
  and nearest wall is within 0.1%-2% of SPX. Both the iron_condor /
  iron_butterfly Tradier-chain happy path and the _fallback_strikes
  path use the asymmetry; widths are snapped to $2.50 increments and
  floored at $2.50. Result dict gains put_spread_width and
  call_spread_width fields. _fallback_strikes() gained a
  redis_client=None keyword arg; all three call sites in get_strikes()
  forward redis_client so asymmetry flows into fallback too.
  backend/scripts/process_options_data.py: reads 24 monthly
  OptionsDX SPX EOD chain files from backend/data/historical/options/,
  groups by QUOTE_DATE, filters DTE==0, computes ATM IV, put/call
  volume ratio, zero-gamma level (linear interpolation of C_GAMMA -
  P_GAMMA sign change across strikes), 25-delta IV skew. Adds 252-day
  rolling IV rank and IV percentile. Saves options_features.parquet
  plus options_features_manifest.json.
  backend/tests/test_phase_b2_optionsdx.py: 6 unit tests — 4 cover
  _get_gex_asymmetry cases (wall below SPX, wall above SPX, low
  confidence symmetric, no-Redis symmetric), 2 cover the processor
  (zero-gamma crossover detection, monotonic IV rank).
- **phase:** phase_b
- **impact:** HIGH — asymmetric wings: +1-2pp expected annual return
  from directional premium capture; OptionsDX features unblock future
  GEX/ZG backtest and enable true meta-label training for A3 rework
- **t_rules_checked:** T-Rule 1 ✅ (no foundation files touched),
  T-Rule 5 ✅ (capital preservation gates unchanged; no risk_engine
  changes), T-Rule 8 ✅ (Phase B follows Phase A in build order)

---

### T-ACT-031 — GEX/ZG Backtest Script

- **id:** T-ACT-031
- **date:** 2026-04-17
- **action:** GEX/ZG backtest script.
  backend/scripts/backtest_gex_zg.py: standalone backtest that
  reconstructs the production prediction_engine GEX/ZG classifier
  (classify_regime + regime_to_strategy) against 2022-2023
  options_features.parquet. Simulates 16-delta credit spread entries
  at 9:35 AM SPX open, exits at EOD with proportional breach loss,
  50% profit target, and 2x stop-loss. Costs: $0.35/leg/contract x 4
  legs commission + $0.10 slippage per trade. IV-rank is used as a
  VVIX z-score proxy until real VVIX historical data is wired in.
  Outputs win rate, profit factor, Sharpe (annualized), max drawdown,
  per-strategy breakdown, and a text verdict (STRONG / MODERATE /
  WEAK / NO edge). Saves to data/historical/backtest_results.json.
  backend/tests/test_backtest_gex_zg.py: 9 unit tests covering
  classify_regime (pin_range, quiet_bullish, volatile_bearish, crisis),
  regime_to_strategy (sit-out and tradeable sets), simulate_trade
  (win and loss paths), and estimate_credit (positivity + iron-condor
  > single spread).
- **phase:** phase_b
- **impact:** CRITICAL — validates whether the rule-based GEX/ZG
  signal has real edge before we trust it with live capital. Result
  drives the A3 meta-labeling vs keep-GEX-ZG decision.
- **t_rules_checked:** T-Rule 1 ✅ (no production files modified;
  script is standalone under backend/scripts/), T-Rule 5 ✅ (capital
  preservation gates untouched), T-Rule 8 ✅ (Phase B task; unblocks
  later A3 rework)

---

### T-ACT-032 — Phase B3: Tighter Exit Parameters

- **id:** T-ACT-032
- **date:** 2026-04-17
- **action:** Phase B3 — tighter exit parameters. position_monitor.py:
  take_profit threshold 50% -> 40% of max_profit (exit_reason updated
  to take_profit_40pct). stop_loss threshold 200% -> 150% of credit
  (exit_reason updated to stop_loss_150pct_credit). CV_Stress exit
  guard updated to match new 40% take-profit threshold.
  Backtest justification: avg loss $296 at 200% stop; at 150% reduces
  to ~$222. Combined with 81% win rate from GEX/ZG signal, improves
  profit factor from ~1.13 to ~1.4. Expected annual lift: +1.5-2.5pp.
  Partial exit at 25% (P0.6) is unchanged.
- **phase:** phase_b
- **impact:** HIGH
- **t_rules_checked:** T-Rule 1 ✅, T-Rule 5 ✅ (tighter stops = more
  capital preserved, consistent with D-005 daily loss limit)

---

### T-ACT-033 — Phase B4: Kelly-Adjusted Position Sizing

- **id:** T-ACT-033
- **date:** 2026-04-17
- **action:** Phase B4 — Kelly-adjusted position sizing. risk_engine.py:
  new compute_kelly_multiplier(win_rate, avg_win, avg_loss) computes
  quarter-Kelly fraction normalized to a multiplier (0.5x to 2.0x).
  compute_position_size() accepts optional kelly_multiplier parameter
  (default 1.0 = no change to existing behavior). At backtest stats
  (72.5% WR, $70 avg win, $143 avg loss) produces multiplier ~1.12.
  Infrastructure only — wiring into strategy_selector in follow-up.
  Expected lift when wired: +1-3pp annual from better capital deployment.
- **phase:** phase_b
- **impact:** HIGH
- **t_rules_checked:** T-Rule 1 ✅, T-Rule 5 ✅ (Kelly floored at 0.5x
  and capped at 2.0x; stacks multiplicatively with existing D-021 /
  D-022 / allocation_tier reductions so it cannot undo safety-driven
  size cuts; daily -3% drawdown halt in check_daily_drawdown is
  unchanged and remains absolute)

### T-ACT-034 — Phase B4 Wiring: Kelly Multiplier from Live Win Rate

- **id:** T-ACT-034
- **date:** 2026-04-17
- **action:** Phase B4 wiring — connects compute_kelly_multiplier
  (T-ACT-033) to the live execution path. model_retraining.py:
  get_kelly_multiplier_from_db(days=20) queries trading_positions
  (closed, virtual) to compute win_rate / avg_win / avg_loss and
  returns the Kelly multiplier; enforces the 20-trade minimum
  (returns 1.0 below that) and returns 1.0 on any DB error.
  strategy_selector.py: select_strategy() now reads kelly:multiplier
  from Redis (TTL 3600s), falls back to the DB helper on cache miss,
  and passes the result to compute_position_size(kelly_multiplier=).
  Exceptions in the fetch path default to 1.0 so sizing is never
  blocked by Redis/DB issues.
- **phase:** phase_b
- **impact:** HIGH
- **t_rules_checked:** T-Rule 1 ✅, T-Rule 5 ✅ (safe fallback to
  1.0x on any failure; D-021 / D-022 / allocation_tier / event-day
  reductions still apply; -3% daily drawdown halt unchanged)
- **files_touched:** backend/model_retraining.py,
  backend/strategy_selector.py, backend/tests/test_phase_b4_wiring.py
- **tests:** tests/test_phase_b4_wiring.py — 5 tests
  (insufficient-trades, high-WR multiplier, DB-error fallback, Redis
  cache hit, DB fallback on cache miss); full suite 180 passed

### T-ACT-035 — Fix Databento Parser: Zero-Record Flooding + False-Positive Health

- **id:** T-ACT-035
- **date:** 2026-04-17
- **action:** Rewrite backend/databento_feed.py. Production diagnostic
  revealed databento:opra:trades contained 473,035 zero-filled records
  per 5-minute window (all with symbol="", price=0.0, strike=0.0) while
  databento_feed reported "healthy" every 10s. Root cause: old code used
  getattr(record, "symbol", "") but databento.TradeMsg (v0.35.0) has no
  .symbol attribute — the default "" was returned for every record and
  the OCC regex never matched. No record-type filter meant SystemMsg /
  ErrorMsg / SymbolMappingMsg were all processed as trades with default
  zero fields. Subscribe also defaulted to symbols=ALL_SYMBOLS (full
  OPRA firehose) instead of SPX/SPXW only. Heartbeat updated
  last_data_at on every rpush, so 473k garbage writes kept the health
  probe green. Rewrite: (1) databento.InstrumentMap with
  insert_symbol_mapping_msg() + resolve(instrument_id, event_date) for
  symbol resolution; (2) isinstance dispatch splits SymbolMappingMsg,
  TradeMsg, and everything-else paths; (3) subscribe narrowed to
  symbols=["SPX.OPT","SPXW.OPT"], stype_in=SType.PARENT; (4)
  record.pretty_price replaces manual /1e9; (5) rename last_data_at ->
  last_valid_trade_at, updated only on fully-resolved non-zero trades;
  heartbeat now reports "degraded" when no valid trade within 30s;
  (6) imap.clear() called in outer retry loop on reconnect. __init__
  also deletes databento:opra:trades on startup to flush stale
  placeholders from previous runs. process_trade() kept as back-compat
  wrapper around _push_trade for test_fix_group7a compatibility.
- **phase:** phase_b
- **impact:** CRITICAL
- **t_rules_checked:** T-Rule 1 ✅, T-Rule 5 ✅ (fix is strictly more
  conservative than before — drops records instead of writing zero
  placeholders; D-021 / D-022 / drawdown halts unchanged; outside
  market hours status now correctly reports "degraded" reflecting no
  flow, replacing the old false-positive "healthy")
- **files_touched:** backend/databento_feed.py,
  backend/tests/test_databento_feed.py
- **tests:** tests/test_databento_feed.py — 5 tests (SymbolMappingMsg
  feeds InstrumentMap, known-id TradeMsg writes full trade,
  unknown-id TradeMsg skipped with no placeholder, SystemMsg+ErrorMsg
  ignored, unparseable OCC symbol dropped without raising). Tests use
  pytest.importorskip("databento") so they skip cleanly locally and
  run on Railway/CI. Local full suite: 180 passed, 1 skipped (new
  test, databento not installed locally).
- **post_deploy_validation:** After deploy, verify via `railway ssh`:
  (a) `tests/test_databento_feed.py` reports 5 passed, (b)
  `LRANGE databento:opra:trades 0 5` shows real symbols/prices (not
  zeros), (c) `trading_system_health` shows databento_feed=degraded
  outside market hours, healthy during RTH once trades flow.

### T-ACT-036 — B2 Backtest Fix: Asymmetric Iron Condor Wings

- **id:** T-ACT-036
- **date:** 2026-04-18
- **action:** B2 backtest fix — asymmetric iron condor wings in
  simulation. backtest_gex_zg.py: new get_backtest_asymmetry(dist_pct,
  spread_width) replicates _get_gex_asymmetry() from strike_selector.py
  using dist_pct as GEX wall proxy. simulate_trade() iron_condor branch
  now uses asymmetric put/call widths and computes credit per side
  separately. Makes backtest more faithful to Phase B2 production
  behavior. 6 new unit tests.
- **phase:** phase_b
- **impact:** MEDIUM — improves backtest accuracy, no production change
- **t_rules_checked:** T-Rule 1 ✅ (no production files modified;
  strictly backend/scripts/backtest_gex_zg.py + new test file +
  trading-docs)
- **files_touched:** backend/scripts/backtest_gex_zg.py,
  backend/tests/test_b2_backtest.py
- **tests:** tests/test_b2_backtest.py — 6 tests (wall below widens
  put, wall above widens call, symmetric near zero, symmetric too far,
  floor at $2.50, iron_condor with asymmetric credit). Full suite:
  186 passed, 1 skipped.
- **implementation_note:** Helper uses int() (truncation) rather than
  the round() shown in the original task spec. This was an approved
  deviation after a pre-write ambiguity check: spec's round() formula
  produces call_w=5.0 for (0.005, 5.0), but the spec's own test
  asserts call_w=2.5. int() truncation reconciles both — matches the
  "floor at $2.50" comment intent and passes all 6 tests as written.

