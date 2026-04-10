# Phase 3C Closure Record — User Management Schema & Lifecycle

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-10

## Status

| Field | Value |
|-------|-------|
| **Phase** | Phase 3C — User Management Schema & Lifecycle |
| **Plan Section** | PLAN-USRMGMT-001 |
| **Status** | **CLOSED — A+ Institutional Grade** |
| **Closed Date** | 2026-04-10 |
| **Approved Baseline** | v7 |
| **Authoritative Evidence Actions** | ACT-027, ACT-028, ACT-029, ACT-030, ACT-031, ACT-032, ACT-033, ACT-034 |
| **Supersedes** | ACT-027, ACT-028 (superseded by ACT-029 verified lifecycle proof) |

---

## Architecture Summary

### Edge Functions (4 deployed)

| Function | Method | Permission | Rate Limit | Audit |
|----------|--------|-----------|------------|-------|
| `get-profile` | GET | `users.view_self` (self) / `users.view_all` (admin) | standard | No |
| `update-profile` | POST | `users.edit_self` (self) / `users.edit_any` (admin) | standard | Yes |
| `list-users` | GET | `users.view_all` | standard | No |
| `deactivate-user` | POST | `users.deactivate` + `requireRecentAuth` | strict | Yes (fail-closed) |
| `reactivate-user` | POST | `users.reactivate` + `requireRecentAuth` | strict | Yes (fail-closed) |

All functions use the shared handler (`createHandler`) with: JWT validation, permission checks via `checkPermissionOrThrow`, Zod input validation, correlation IDs, structured error responses.

### Lifecycle State Machine

```
active ──[deactivate]──► deactivated
  ▲                          │
  └──────[reactivate]────────┘
```

**Two stable states:** `active`, `deactivated`
**Validation trigger:** `validate_profile_status()` enforces allowed values at DB level.
**Login block trigger:** `check_user_active_on_login()` prevents deactivated users from authenticating.

### Transaction Sequencing (Fail-Closed)

| Step | Deactivation | Reactivation |
|------|-------------|-------------|
| 1 | Audit write (abort if fails) | Audit write (abort if fails) |
| 2 | Set profile status to `deactivated` | Clear auth ban (`ban_duration: 'none'`) |
| 3 | Ban auth user (`ban_duration: '876000h'`) | Set profile status to `active` |
| **Rollback** | If step 3 fails → restore status to `active` + audit rollback event | If step 3 fails → re-ban auth user |

### Self-Scope Enforcement

- `get-profile` and `update-profile` enforce self-scope: callers without `users.view_all` / `users.edit_any` may only access their own profile (UUID comparison against `ctx.user.id`).
- Self-deactivation is explicitly blocked in `deactivate-user`.

### Security Controls

| Control | Implementation |
|---------|---------------|
| Authentication | JWT validation via `authenticateRequest()` |
| Authorization | `checkPermissionOrThrow()` + self-scope guards |
| Re-authentication | `requireRecentAuth()` for destructive actions |
| Input validation | Zod schemas with UUID regex, string length limits |
| Rate limiting | `createHandler({ rateLimit: 'strict' })` for destructive endpoints |
| Audit trail | `logAuditEvent()` with fail-closed semantics |
| Auth ban | `supabaseAdmin.auth.admin.updateUserById()` for session invalidation |

---

## Gate Closure Evidence

| # | Gate Item | Evidence | Action |
|---|-----------|----------|--------|
| 1 | Profile CRUD operational | `get-profile` (self + admin), `update-profile` tested via curl with real JWTs | ACT-027, ACT-029 |
| 2 | User listing with pagination | `list-users` tested with offset/limit | ACT-027, ACT-029 |
| 3 | Self-scope enforcement | Self-only access verified; admin cross-user access verified | ACT-027, ACT-029 |
| 4 | Deactivation sets profile status + auth ban | Profile → `deactivated`, auth → `banned_until: 2126-*` | ACT-029, ACT-032 |
| 5 | Deactivation blocks login | Sign-in returns "User is banned" | ACT-029, ACT-032 |
| 6 | Deactivation compensating rollback | If ban fails → status restored to `active` + audit event | ACT-029 (code review) |
| 7 | Reactivation clears auth ban first | `ban_duration: 'none'` applied before profile flip | ACT-029, ACT-032 |
| 8 | Reactivation restores login | Session obtained after reactivation | ACT-032 |
| 9 | Reactivation compensating rollback | If profile update fails → re-ban applied | ACT-029 (code review) |
| 10 | Fail-closed audit | Audit write failure → mutation aborted | ACT-029 (code review) |
| 11 | Self-deactivation blocked | `user_id === ctx.user.id` → 400 | ACT-029 |
| 12 | Regression tests passing | 6/6 Deno tests: unauth denial, method denial, CORS (both endpoints) | ACT-030 |

---

## Behavioral Runtime Evidence (ACT-032)

Server-side lifecycle test via temporary `lifecycle-test` edge function. **7/7 passed + cleanup.**

| Test | Result | Details |
|------|--------|---------|
| 0. User created with `active` status | ✅ | `status=active` |
| 1. Deactivation: profile → `deactivated` | ✅ | `error=none, status=deactivated` |
| 2. Deactivation: auth user banned | ✅ | `banned_until=2126-03-17T09:29:44.387018Z` |
| 3. Login blocked for banned user | ✅ | `login_error=User is banned` |
| 4. Reactivation: auth ban cleared | ✅ | `banned_until=null` |
| 5. Reactivation: profile → `active` | ✅ | `error=none, status=active` |
| 6. Login restored after reactivation | ✅ | `has_session=true` |
| CLEANUP | ✅ | Test user deleted, no orphan |

**Execution ID:** `59607b5a-f033-40cb-a780-419ec8e331d6`
**Request ID:** `019d76b9-d167-74f6-a378-0f90caf0b0a4`

---

## Known Limitations

| Limitation | Impact | Workaround | Reference |
|-----------|--------|-----------|-----------|
| `auth.admin.deleteUser()` may fail due to FK constraints (`user_roles.assigned_by`) | Test-user cleanup requires manual intervention | Nullify FK references first, then use SQL migration `DELETE FROM auth.users` | RISK-011, ACT-034 |
| In-memory per-isolate rate limiting | Cold starts reset counters; no cross-isolate coordination | Acceptable for development; distributed rate limiting deferred | DW-011 |
| Authenticated 409/400 tests not yet automated | Require test harness for admin token provisioning | Deferred to Phase 6 hardening | DW-012 |
| Rollback-path tests require failure injection | Cannot simulate `auth.admin` failures without mocks | Deferred to Phase 6 hardening | DW-012 |

---

## Deferred Items Carried Forward

| DW ID | Title | Target Phase | Status |
|-------|-------|-------------|--------|
| DW-011 | Distributed/shared rate limiting | Phase 6 | `assigned` |
| DW-012 | Authenticated lifecycle test infrastructure (409, rollback-path) | Phase 6 | `assigned` |
| DW-013 | Orphaned test-user cleanup automation | Phase 6 | `assigned` |

---

## Risk & Watchlist Items Created

| ID | Title | Status |
|----|-------|--------|
| RW-007 | User Lifecycle Regression | Active — watching |
| RISK-010 | Auth/Profile State Desynchronization | Open |
| RISK-011 | Supabase Auth User Deletion Fragility | Open |

---

## Governance Quality Indicators

| Indicator | Status |
|-----------|--------|
| ACT-030 evidence matches actual tests | ✅ Corrected (ACT-031) |
| Action tracker summary internally consistent | ✅ Fixed (ACT-031) |
| Last Reviewed dates current | ✅ All updated to 2026-04-10 |
| Orphaned test users cleaned | ✅ All 3 deleted (ACT-033, ACT-034) |
| Known limitations documented in module doc | ✅ Added to user-management.md |
| SSOT docs aligned with code behavior | ✅ user-management.md, function-index.md, route-index.md |

---

## Next Phase Constraints

Phase 3D (next stage within Phase 3) must:
1. Not modify user lifecycle semantics without HIGH-impact change control
2. Ensure any new edge functions follow the same shared handler + rate limit + audit pattern
3. Reference DW-012 if building authenticated test infrastructure

---

## Dependencies

- [Master Plan](../master-plan.md)
- [Action Tracker](../../06-tracking/action-tracker.md)
- [Deferred Work Register](../deferred-work-register.md)
- [User Management Module](../../04-modules/user-management.md)

## Related Documents

- [Phase 2 Closure (RBAC)](phase-02-rbac-closure.md)
- [Function Index](../../07-reference/function-index.md)
- [Route Index](../../07-reference/route-index.md)
- [Risk Register](../../06-tracking/risk-register.md)
- [Regression Watchlist](../../06-tracking/regression-watchlist.md)
