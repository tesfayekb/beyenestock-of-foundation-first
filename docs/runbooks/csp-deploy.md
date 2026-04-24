# CSP Fix — Incident Summary & Resolution Runbook

**Date:** 2026-04-19
**Severity:** P2 — Trading console feature toggles and intelligence panels non-functional on Lovable-hosted frontend; trading engine itself unaffected.
**Affected surfaces:** Trading Console (feature flags, AI briefs, activation status, earnings dashboard, subscriptions page)
**Owner:** trading-console module
**Resolution time:** ~3 hours across multiple debugging passes

---

## 1. Background

The Lovable-hosted production frontend enforces a strict Content Security Policy (CSP) that blocks browser `fetch` calls to any origin not on the allow-list. Several React Query hooks in `src/hooks/trading/` were calling the Railway-hosted backend API (`diplomatic-mercy-production-7e61.up.railway.app`) directly from the browser, which silently failed in production.

The fix involved a multi-layer architecture change: mirror the Redis-only data into Supabase tables, route browser writes through Supabase Edge Functions, and read everything client-side via the Supabase JS client (which is on the CSP allow-list).

---

## 2. Root causes encountered (in the order they surfaced)

### 2.1 Browser CSP blocking direct Railway fetches
- **Symptom:** Trading console hooks throwing network errors silently on production but working in local dev.
- **Cause:** Frontend code was calling `fetch('https://diplomatic-mercy-production-7e61.up.railway.app/...')` directly from the browser; Lovable CSP rejected the request before it left the browser.

### 2.2 Edge Functions failing to deploy
- **Symptom:** `supabase functions deploy set-feature-flag` failed with `Module not found: _shared/handler.ts`.
- **Cause:** The first version of the new Edge Functions imported helpers from `supabase/functions/_shared/` (handler, authenticate-request, authorization, validate-request, audit, api-error). Those helpers transitively pulled in modules requiring infrastructure or env vars not provisioned for these new functions.
- **Why we didn't fix the shared library directly:** Those `_shared/` helpers are consumed by ~30 other Edge Functions. Modifying or replacing them would risk widespread regressions.

### 2.3 Edge Functions returning 401 at the gateway (`UNAUTHORIZED_UNSUPPORTED_TOKEN_ALGORITHM`)
- **Symptom:** Every GET to `subscription-key-status` returned 401 with `execution_id: null` (function code never executed). Response header included `sb_error_code: UNAUTHORIZED_UNSUPPORTED_TOKEN_ALGORITHM`.
- **Cause:** The Supabase project had migrated to **asymmetric JWT signing keys (ES256)** for user tokens. The Edge Function deployment was bound to a runtime version whose gateway-level JWT pre-verifier only understood HS256; it rejected ES256 tokens before invoking the function.

### 2.4 Feature-flag toggles returning 200 but UI not updating
- **Symptom:** POST to `set-feature-flag` returned 200, OPTIONS preflight returned 200, Railway logs showed `feature_flag_updated`, the `trading_feature_flags` Supabase table contained the correct rows, but every toggle in the UI stayed in the OFF position.
- **Cause:** RLS policy on `trading_feature_flags` (and the other CSP mirror tables) requires the reading user to hold the `trading.view` permission via `user_roles -> role_permissions -> permissions`. The operator account had only self-management permissions (`mfa.self_manage`, `profile.self_manage`, etc.), so RLS silently filtered every row out of every SELECT — the hook received `{}` and rendered all toggles as default-OFF.
- **Why this was hard to spot:** The data WAS in the table (visible in SQL Editor, which uses `service_role` and bypasses RLS). The bug only manifested under the authenticated user's JWT, which goes through RLS.

---

## 3. Solution architecture

```
+------------------+      +------------------+      +------------------+
| Lovable frontend |----->| Supabase Edge Fn |----->| Railway backend  |
|  (browser, CSP)  |      |  (server-side)   |      |  (Redis primary) |
+------------------+      +------------------+      +--------+---------+
         |                                                   |
         |  direct supabase-js queries                       | mirror upsert
         |  (CSP-allowed origin)                             | (every write)
         v                                                   v
+--------------------------------------------------------------------+
| Supabase Postgres                                                  |
|   trading_feature_flags   (mirror of Redis flag state)             |
|   trading_ai_briefs       (mirror of AI agent briefs)              |
|   earnings_upcoming_scan  (mirror of upcoming earnings scan)       |
|   system_alerts           (existing table, RLS added)              |
|   ab_session_comparison   (already existed)                        |
+--------------------------------------------------------------------+
```

**Authority hierarchy preserved:** Redis is still authoritative for the trading engine. Supabase mirrors are written **after** Redis, inside the same `try/except`, so a Supabase outage cannot prevent a flag from taking effect.

---

## 4. Code changes shipped (chronological)

### 4.1 Backend mirror writes
- `backend/main.py::set_feature_flag()` — added `trading_feature_flags` upsert after Redis write, swallowing Supabase errors.
- `backend/main.py::_backfill_feature_flags_to_supabase()` — startup hook that seeds all 13 flags with their resolved current state (handles signal-flag reverse polarity).
- `backend_agents/{economic_calendar,macro_agent,flow_agent,sentiment_agent,synthesis_agent,surprise_detector}.py` — added `trading_ai_briefs` upsert alongside each `redis.setex`.
- `backend_earnings/earnings_calendar.py` — added `earnings_upcoming_scan` insert alongside Redis writes.

### 4.2 Supabase migrations
Four migrations under `supabase/migrations/20260427_*.sql`:
- `trading_feature_flags.sql` — table + RLS (`service_role` full, `authenticated` read with `trading.view`)
- `trading_ai_briefs.sql` — same pattern
- `earnings_upcoming_scan.sql` — same pattern
- `system_alerts_rls.sql` — RLS only; table already existed in production

### 4.3 Edge Functions
Two new functions, both **fully self-contained** (no `_shared/` imports) so they deploy cleanly:
- `supabase/functions/set-feature-flag/index.ts` — POST proxy that forwards `{flag_key, enabled}` to Railway `/admin/trading/feature-flags`. Validates Bearer JWT via `serviceClient.auth.getUser(token)` and authorizes via `has_permission(_, 'trading.configure')` RPC.
- `supabase/functions/subscription-key-status/index.ts` — GET endpoint that reads Edge Function secrets, masks them, returns the same shape Railway used to return. Validates `trading.view` permission.

### 4.4 Frontend rewrites (`src/hooks/trading/`)
- `useFeatureFlags.ts` — reads `trading_feature_flags` directly; writes via `supabase.functions.invoke('set-feature-flag')`. Applies signal-flag reverse polarity.
- `useTradeIntelligence.ts` — reads `trading_ai_briefs` directly.
- `useActivationStatus.ts` — derives composite status from 4 parallel Supabase queries.
- `useEarningsStatus.ts` — adds `earnings_upcoming_scan` query for upcoming events / last_scan_at.
- `src/pages/trading/SubscriptionsPage.tsx` — invokes `subscription-key-status` Edge Function instead of Railway fetch.

---

## 5. Manual operator steps (one-time, NOT in code)

These were the steps that bit us. They are required for any clean redeploy or new environment, in this order:

### Step 1 — Deploy Edge Functions with gateway JWT verification disabled
Either via CLI:
```bash
supabase functions deploy set-feature-flag --no-verify-jwt
supabase functions deploy subscription-key-status --no-verify-jwt
supabase functions deploy get-learning-stats --no-verify-jwt
```
Or via Dashboard: open each function -> toggle **"Verify JWT with legacy secret"** OFF -> paste code -> Deploy.

**Why:** The project uses ES256-signed user JWTs. The Edge gateway's pre-verifier rejects them. The function code does its own validation via `serviceClient.auth.getUser(token)` (which understands ES256 because it calls the Auth API), so disabling gateway verification is safe — auth still happens, just inside the function.

**Policy:** Any new Edge Function that uses `serviceClient.auth.getUser` for authentication MUST be deployed with `--no-verify-jwt` until the ES256 migration TODO in §8 is closed.

### Step 2 — Set Edge Function secrets
Via Dashboard -> Settings -> Edge Functions -> Secrets, or `supabase secrets set NAME=value`:

| Secret | Purpose |
|---|---|
| `SUPABASE_URL` | Required — both functions |
| `SUPABASE_SERVICE_ROLE_KEY` | Required — auth + has_permission RPC (NOT anon key) |
| `DATABENTO_API_KEY`, `TRADIER_API_KEY`, `TRADIER_SANDBOX`, `POLYGON_API_KEY`, `FINNHUB_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `UNUSUAL_WHALES_API_KEY`, `NEWSAPI_KEY`, `AI_PROVIDER`, `AI_MODEL` | Optional — make subscription-key-status report each key as `configured: true` |

Without `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` the function returns 500 ("Server misconfigured").

### Step 3 — Apply migrations to live Supabase
Via Dashboard -> SQL Editor, paste each file in order:
1. `supabase/migrations/20260427_trading_feature_flags.sql`
2. `supabase/migrations/20260427_trading_ai_briefs.sql`
3. `supabase/migrations/20260427_earnings_upcoming_scan.sql`
4. `supabase/migrations/20260427_system_alerts_rls.sql`

All migrations are idempotent.

### Step 4 — Verify Railway has the service role key
Railway -> Variables must include:
- `SUPABASE_URL=https://hnfvuxcwjferoocvybnf.supabase.co`
- `SUPABASE_SERVICE_ROLE_KEY=<service_role from Supabase Settings -> API>`

Without these, Railway's mirror upserts silently fail (logged as `feature_flag_supabase_mirror_failed`) and the table stays empty.

### Step 5 — Restart Railway (or trigger one toggle per flag)
On startup, `_backfill_feature_flags_to_supabase()` seeds `trading_feature_flags` with all 13 flags' current state. Without this, the table starts empty and only fills as operators toggle flags one-by-one.

### Step 6 — Grant `trading.view` and `trading.configure` to operator users
The CSP mirror tables have RLS gated on `trading.view`. By default a freshly-onboarded user only has self-management permissions and will see empty data everywhere.

In Supabase SQL Editor:
```sql
insert into permissions (key, description)
values
  ('trading.view',      'Read trading console state, flags, briefs, alerts'),
  ('trading.configure', 'Toggle feature flags and configure trading engine')
on conflict (key) do nothing;

with my_roles as (
    select distinct role_id from user_roles where user_id = '<OPERATOR_USER_ID>'
),
target_perms as (
    select id from permissions where key in ('trading.view','trading.configure')
)
insert into role_permissions (role_id, permission_id)
select r.role_id, p.id from my_roles r cross join target_perms p
on conflict do nothing;
```

If `with my_roles` returns nothing, the user has no role — assign one first via `user_roles`.

### Step 7 — Hard-refresh the trading console
React Query caches the empty `{}` response from before the permission grant. Ctrl+Shift+R drops the cache; within 30 seconds (the `useFeatureFlags` refetch interval) toggles reflect reality.

---

## 6. Verification checklist after a clean deploy

| Check | How | Expected |
|---|---|---|
| Edge Functions deployed | Supabase Dashboard -> Functions | Both functions show v >= 14, "Verify JWT" OFF |
| Edge secrets set | Settings -> Edge Functions -> Secrets | `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` present |
| Tables exist | SQL: `select table_name from information_schema.tables where table_name in (...)` | All 4 returned |
| Railway mirror writing | SQL: `select count(*) from trading_feature_flags` | 13 rows after Railway restart |
| Operator has `trading.view` | SQL: 7-permission verification query in section 5 step 6 | `trading.view` + `trading.configure` listed |
| RLS visibility OK | SQL: `set local role authenticated; set local request.jwt.claim.sub = '<id>'; select count(*) from trading_feature_flags;` | 13 |
| Frontend reflects state | Trading console after Ctrl+Shift+R | Toggles match Redis state within 30s |
| Toggle write path | Click any toggle | Row in `trading_feature_flags` updates within 1s; UI reflects within 30s |

---

## 7. Lessons learned

1. **"Code merged" != "infrastructure applied."** Migrations, Edge secrets, RBAC grants, and Edge Function deploy flags are out-of-band. None of them surface in `git log`. They need explicit checklist items in deploy runbooks.

2. **RLS failures are silent — they return zero rows, not errors.** Always test data-access paths under the actual end-user JWT, not just service_role. The Supabase SQL Editor's default mode hides this class of bug.

3. **Don't fight a shared library — bypass it.** When `_shared/handler.ts` failed to deploy, the impulse was to fix the shared module. The right call was to make the two new Edge Functions self-contained, leaving 30+ other functions untouched.

4. **Asymmetric JWT migration is a quiet runtime change.** Edge Function gateway JWT verification can fall behind the project's signing-key algorithm. Keep `--no-verify-jwt` + in-function validation as the safer pattern until Supabase confirms full ES256/RS256 support across every runtime version.

5. **The 200 lied.** A 200 from `set-feature-flag` only proved Railway accepted the call — not that the frontend would see it. End-to-end verification needs `(write succeeds) AND (mirror table updates) AND (RLS allows operator to read it) AND (React Query refetches)`.

---

## 8. Open follow-ups (non-blocking)

- **Re-tighten Edge Function gateway auth** once Supabase confirms ES256 support across all runtime versions. Re-enable `verify-jwt` at the gateway for defense-in-depth.
- **Auto-grant `trading.view` to operator role** on user creation to avoid the manual permission step for new operators.
- **Health-check on the mirror table.** Add a Railway health probe that asserts the upsert path is working (e.g., row in `trading_feature_flags` updated_at < 5 min stale). Catches silent service-role-key drift.
- **Capture this runbook** at `docs/runbooks/csp-deploy.md` (or wherever your ops docs live) and link it from the deploy section of the README.

---

## 9. References

- Repo commits:
  - Mirror writes + migrations + edge functions (PR #49): `0fa85a7`
  - Self-contained Edge Function rewrite (cherry-picked to main): `6dc80f2`
  - Signals D/E/F (unrelated, same session): `3852bf8`
- Affected files: `backend/main.py`, `backend_agents/*.py`, `backend_earnings/earnings_calendar.py`, `supabase/migrations/20260427_*.sql`, `supabase/functions/{set-feature-flag,subscription-key-status}/index.ts`, `src/hooks/trading/{useFeatureFlags,useTradeIntelligence,useActivationStatus,useEarningsStatus}.ts`, `src/pages/trading/SubscriptionsPage.tsx`
