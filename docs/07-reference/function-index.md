# Function Index

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-10 | **Status:** Living Document | **Index Version:** `fn-v1.2`

## Purpose

Central registry and **contract governance system** for all shared functions and services used by 2+ modules. This document is the single source of truth for shared function definitions — it governs signatures, side effects, security behavior, testing requirements, and change impact for every cross-module dependency. Required by Constitution Rule 6.

## Scope

All shared functions, hooks, services, database functions, and utilities used across module boundaries.

---

## Enforcement Rule (CRITICAL)

| Rule | Description |
|------|-------------|
| **Completeness** | No shared function may exist outside this index. Undocumented shared dependency = invalid implementation. |
| **Change governance** | No listed function may be changed without impact review of all consumers. |
| **Contract enforcement** | Breaking signature/behavior changes require change control and regression review. |
| **Verification** | Shared functions on critical paths require explicit verification evidence after changes. |
| **Semantic changes** | Behavior changes without signature changes still count as contract changes if downstream semantics change. |
| **Addition rule** | Any function used by 2+ modules must be added here immediately. |

---

## Function Classification Model

| Classification | Description | Review Rigor |
|---------------|-------------|-------------|
| **security-critical** | Authentication, token validation, session management | Highest — Lead + Security review, fail-secure required |
| **authorization-critical** | Permission checks, role validation, RLS functions | Highest — Lead review, fail-secure required |
| **audit-critical** | Audit logging, compliance recording | High — must not silently fail |
| **api-critical** | Request validation, error handling, API middleware | High — affects all API consumers |
| **job-critical** | Job execution, retry logic, scheduling | Medium-High — affects reliability |
| **data-access** | Profile queries, user listing, data retrieval | Medium — affects data integrity |
| **ui-shared** | Role-based UI hooks, layout utilities | Medium — affects user experience |
| **utility** | General helpers, formatters | Standard |

---

## Function Entry Schema

Every function in the registry must include:

| Field | Description | Required |
|-------|-------------|----------|
| `name` | Function name with parameters | Yes |
| `type` | `function`, `hook`, `service`, `db-function`, `utility` | Yes |
| `classification` | From classification model above | Yes |
| `owner_module` | Module responsible for this function | Yes |
| `signature` | Full type signature (params + return) | Yes |
| `returns` | Return type and semantics | Yes |
| `purity` | `pure` or `impure` | Yes |
| `side_effects` | DB read/write, audit emission, event emission, cache invalidation, external call, none | Yes |
| `transactional` | Whether function participates in DB transactions | Yes |
| `fail_behavior` | `fail-secure`, `fail-fast`, `fail-open`, `async-fallback` | Yes |
| `used_by` | All consuming modules | Yes |
| `blast_radius` | `small`, `medium`, `large`, `system-wide` | Yes |
| `criticality` | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` | Yes |
| `approval_required` | Whether changes require explicit approval | Yes |
| `callable_from` | `request-path`, `job-path`, `ui-only`, `any` | Yes |
| `upstream_deps` | Shared functions this function calls | If applicable |
| `downstream_deps` | Shared functions that call this function | If applicable |
| `related_routes` | Routes that depend on this function | If applicable |
| `related_permissions` | Permissions checked or enforced | If applicable |
| `related_events` | Events emitted or consumed | If applicable |
| `related_tests` | Tests validating this function | If applicable |
| `related_risks` | Risk register items | If applicable |
| `related_watchlist` | Regression watchlist items | If applicable |
| `observability` | Latency/error monitoring requirements | If critical |
| `lifecycle` | `active`, `deprecated`, `pending-removal`, `experimental` | Yes |

---

## Contract and Signature Governance

| Rule | Description |
|------|-------------|
| **Documented contract** | Every indexed function must have a documented signature, return contract, and error behavior |
| **Breaking changes** | Changes to arguments, return shape, thrown errors, side effects, or auth behavior require change control |
| **Semantic changes** | Behavior changes that alter downstream semantics (even without signature change) require the same governance |
| **Versioning** | Breaking changes require new version or successor function with migration path |
| **Consumer notification** | All `used_by` modules must be notified and tested before breaking change deploys |

---

## Side Effects and Dependency Rules

### Purity Declaration

| Type | Description | Refactoring Safety |
|------|-------------|-------------------|
| **Pure** | No side effects — same input always produces same output | Safe to refactor, memoize, parallelize |
| **Impure** | Has side effects (DB, events, audit, external calls) | Requires careful impact analysis |

### Call-Chain Safety

| Rule | Description |
|------|-------------|
| **Request-path functions** | Must complete within request timeout; no unbounded operations |
| **Job-path functions** | May have longer execution; must respect retry/idempotency contracts |
| **UI-only functions** | Client-side only; must not perform authorization decisions for protected behavior |
| **Cross-path** | Functions callable from multiple paths must document behavior differences if any |

---

## Security Rules for Critical Functions

| Rule | Description |
|------|-------------|
| **Fail-secure** | All `security-critical` and `authorization-critical` functions must fail secure — deny access on error |
| **No bypass paths** | No hidden parameters, feature flags, or conditions that bypass security checks |
| **Server-side only** | Authorization decisions must be enforced server-side; client-side checks are UX only |
| **Minimal returns** | Security functions must not return sensitive data beyond what is necessary |
| **Audit on failure** | Security function failures must emit audit events |
| **No client trust** | Functions must not trust client-provided role/permission claims |

---

## Testing and Regression Requirements

| Test Type | Applies To | Description |
|-----------|-----------|-------------|
| **Unit tests** | All indexed functions | Core behavior, edge cases, error handling |
| **Integration tests** | Functions with side effects | DB interactions, event emissions, audit writes |
| **Contract tests** | All critical functions | Verify signature and return shape stability |
| **Regression tests** | Previously broken functions | Prevent recurrence of known issues |
| **Fail-secure tests** | Security/authorization functions | Verify secure behavior on error/invalid input |
| **Snapshot tests** | High-impact pure functions | Golden output verification for critical transforms |

**Rules:**
- Every `CRITICAL` or `HIGH` criticality function must have unit + integration tests
- Changes to indexed functions must run all linked tests from `related_tests`
- Test failures on critical functions block deployment

---

## Lifecycle and Deprecation

| State | Description | Action Required |
|-------|-------------|-----------------|
| **Active** | In use, governed by this index | Standard governance |
| **Deprecated** | Scheduled for removal | Migration plan + successor documented + sunset date |
| **Pending removal** | Will be removed in next release | All consumers confirmed migrated |
| **Experimental** | Under evaluation | May change without full change control |

**Rules:**
- Deprecated functions must reference their successor
- Removal requires all `used_by` consumers migrated and verified
- Renamed/replaced functions must maintain redirect or compatibility shim during transition

---

## Runtime Observability

Critical shared functions must expose observability:

| Function Classification | Monitoring Required |
|------------------------|-------------------|
| **security-critical** | Latency, error rate, failure audit events |
| **authorization-critical** | Denial rate, error rate, anomaly detection |
| **audit-critical** | Write success rate, emission verification |
| **api-critical** | Latency (p50/p95/p99), error rate |
| **job-critical** | Execution duration, retry rate, failure rate |

---

## Function Versioning

| Rule | Description |
|------|-------------|
| **Version tracking** | Critical functions may carry a version (e.g., `v1`, `v2`) when major behavioral changes occur |
| **Successor mapping** | Deprecated or replaced functions must reference their successor: `predecessor → successor` |
| **Parallel support** | During transition, both versions must be available until all consumers migrate |
| **Contract stability** | Same version = same contract. Semantic changes require version bump or new function. |

---

## Function Execution Tracing

| Rule | Description |
|------|-------------|
| **trace_id propagation** | All `security-critical`, `authorization-critical`, and `audit-critical` functions must propagate `trace_id` / `correlation_id` |
| **Cross-function tracing** | When function A calls function B, trace context must be preserved for end-to-end debugging |
| **Log correlation** | Function execution logs must include trace_id for post-incident analysis |
| **Observability link** | Traces must be queryable in monitoring/observability system |

---

## Performance Budget per Function

| Classification | Max Expected Latency (p95) | Alert Threshold |
|---------------|---------------------------|-----------------|
| **security-critical** | 50ms | > 100ms |
| **authorization-critical** | 20ms | > 50ms |
| **audit-critical** | 100ms (async acceptable) | > 500ms |
| **api-critical** | 30ms | > 75ms |
| **job-critical** | Varies by job type | > 2× expected duration |
| **data-access** | 100ms | > 250ms |

**Rule:** Functions exceeding their performance budget must be investigated. Sustained breach = action tracker entry + optimization required.

---

## Automatic Impact Analysis (Future-Ready)

| Rule | Description |
|------|-------------|
| **Mapping** | Each function's `used_by`, `related_routes`, `related_tests`, and `related_permissions` fields enable automated impact graphs |
| **Tooling goal** | System should support: `changed function → affected routes + tests + modules` automated lookup |
| **CI integration** | Future CI pipeline should auto-select tests based on function dependency graph |
| **Review assist** | Change reviews should surface all impacted consumers automatically |

---

## Function Usage Telemetry

| Rule | Description |
|------|-------------|
| **Call tracking** | Critical functions should track invocation counts (sampled, not per-call for performance) |
| **Dead function detection** | Functions with zero invocations over 90 days flagged for review |
| **Hot function identification** | Heavily-used functions (top 10% by call volume) receive priority performance monitoring |
| **Cleanup policy** | Unused functions must be reviewed → confirmed active, deprecated, or removed |
| **Telemetry overhead** | Sampling only — telemetry must not degrade function performance |

---

## Change Workflow for Indexed Functions

When changing any indexed function:

| Step | Requirement |
|------|-------------|
| **1. Impact review** | Review all `used_by` modules and downstream dependencies |
| **2. Route/permission review** | Check `related_routes` and `related_permissions` for impact |
| **3. Run linked tests** | Execute all `related_tests` before and after change |
| **4. Regression check** | Compare behavior against baseline; check `related_watchlist` |
| **5. Action tracker** | Create action tracker entry for the change |
| **6. Update links** | Update watchlist/risk links if new fragility discovered |
| **7. Verification** | For critical functions, provide verification evidence |

---

## Function Registry

### Authentication Functions

#### `getCurrentUser()`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | security-critical |
| **Owner module** | auth |
| **Signature** | `() → User | null` |
| **Returns** | Current authenticated user object or null if unauthenticated |
| **Purity** | impure |
| **Side effects** | DB read (session lookup), token validation |
| **Transactional** | No |
| **Fail behavior** | fail-secure — return null (unauthenticated) |
| **Used by** | All modules |
| **Blast radius** | system-wide |
| **Criticality** | CRITICAL |
| **Approval required** | Yes — Lead |
| **Callable from** | request-path, ui |
| **Related routes** | All authenticated routes |
| **Related risks** | RISK-001 (credential compromise), RISK-003 (session hijacking) |
| **Related tests** | Auth unit tests, session validation tests |
| **Observability** | Latency, error rate |
| **Lifecycle** | active |

#### `requireAuth()`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | security-critical |
| **Owner module** | auth |
| **Signature** | `() → User` (throws if unauthenticated) |
| **Returns** | Authenticated user; throws `401 Unauthorized` if not authenticated |
| **Purity** | impure |
| **Side effects** | DB read, may emit `auth.failed_attempt` on failure |
| **Transactional** | No |
| **Fail behavior** | fail-secure — throw 401 |
| **Used by** | All protected routes |
| **Blast radius** | system-wide |
| **Criticality** | CRITICAL |
| **Approval required** | Yes — Lead |
| **Callable from** | request-path |
| **Upstream deps** | `getCurrentUser()` |
| **Related routes** | All protected routes |
| **Related events** | `auth.failed_attempt` |
| **Related risks** | RISK-001 |
| **Related tests** | Auth guard tests, 401 response tests |
| **Observability** | Denial rate, error rate |
| **Lifecycle** | active |

#### `signOut()`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | security-critical |
| **Owner module** | auth |
| **Signature** | `() → void` |
| **Returns** | void — clears session |
| **Purity** | impure |
| **Side effects** | Session invalidation, emits `auth.signed_out` |
| **Transactional** | No |
| **Fail behavior** | fail-fast — report error |
| **Used by** | layout, user-panel |
| **Blast radius** | medium |
| **Criticality** | MEDIUM |
| **Approval required** | No |
| **Callable from** | ui |
| **Related events** | `auth.signed_out` |
| **Related tests** | Logout flow tests |
| **Lifecycle** | active |

#### `authenticateRequest(req)`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | security-critical |
| **Owner module** | api |
| **Signature** | `(req: Request) → AuthenticatedRequest` (throws on failure) |
| **Returns** | Request enriched with authenticated user context; throws `401` on failure |
| **Purity** | impure |
| **Side effects** | Token validation, DB read, may emit `auth.failed_attempt` |
| **Transactional** | No |
| **Fail behavior** | fail-secure — throw 401 |
| **Used by** | All edge functions |
| **Blast radius** | system-wide |
| **Criticality** | CRITICAL |
| **Approval required** | Yes — Lead + Security |
| **Callable from** | request-path |
| **Upstream deps** | `getCurrentUser()` |
| **Related routes** | All protected API routes |
| **Related events** | `auth.failed_attempt` |
| **Related risks** | RISK-001 (auth bypass), RISK-003 (token misuse) |
| **Related tests** | API auth tests, token validation tests, 401 response tests |
| **Observability** | Latency (p95/p99), error rate, denial rate |
| **Lifecycle** | active |

#### `requireVerifiedEmail()` / `isEmailVerified()`

| Field | Value |
|-------|-------|
| **Type** | function + component guard |
| **Classification** | security-critical |
| **Owner module** | auth |
| **Signature (utility)** | `isEmailVerified(user: User | null) → boolean` |
| **Signature (component)** | `<RequireVerifiedEmail>{children}</RequireVerifiedEmail>` — renders verification prompt if email unverified |
| **Returns** | Utility: `boolean`. Component: renders children if verified, blocks with UI prompt if not. |
| **Purity** | impure |
| **Side effects** | Reads `user.email_confirmed_at` from auth state |
| **Transactional** | No |
| **Fail behavior** | fail-secure — returns `false` / blocks access if unable to determine verification status |
| **Used by** | All protected routes requiring verified email (`/`, `/mfa-enroll`) |
| **Blast radius** | system-wide |
| **Criticality** | CRITICAL |
| **Approval required** | Yes — Lead |
| **Callable from** | ui (component guard), request-path (utility) |
| **Upstream deps** | `requireAuth()` (component is always wrapped inside `<RequireAuth>`) |
| **Related routes** | `/`, `/mfa-enroll`, all future protected routes |
| **Related events** | — |
| **Related risks** | RISK-001 (unverified account abuse) |
| **Related tests** | Email verification enforcement tests, unverified user block test |
| **Observability** | Denial rate |
| **Lifecycle** | active |
| **Implementation** | Utility: `src/lib/auth-guards.ts`. Component: `src/components/auth/RequireVerifiedEmail.tsx` |

#### `requireRecentAuth()` / `isRecentlyAuthenticated()` / `requiresReauthentication()`

| Field | Value |
|-------|-------|
| **Type** | function (utility pair) |
| **Classification** | security-critical |
| **Owner module** | auth |
| **Signature** | `isRecentlyAuthenticated(user: User | null, thresholdMs?: number) → boolean` |
| **Signature (inverse)** | `requiresReauthentication(user: User | null, thresholdMs?: number) → boolean` |
| **Returns** | `isRecentlyAuthenticated`: `true` if last sign-in within threshold (default 5 min). `requiresReauthentication`: inverse. |
| **Purity** | pure (reads user object passed in, no DB call) |
| **Side effects** | None — reads `user.last_sign_in_at` from provided user object |
| **Transactional** | No |
| **Fail behavior** | fail-secure — returns `false` / `true` (requires re-auth) if unable to determine |
| **Used by** | admin-panel, user-panel (sensitive actions: password change, MFA disable, account deletion) |
| **Blast radius** | large |
| **Criticality** | CRITICAL |
| **Approval required** | Yes — Lead |
| **Callable from** | request-path, ui |
| **Upstream deps** | `requireAuth()` |
| **Related routes** | Destructive routes, admin-critical routes |
| **Related permissions** | Admin-critical permissions |
| **Related events** | — (caller responsible for emitting events on denial) |
| **Related risks** | RISK-001 (session hijacking mitigation), RISK-003 |
| **Related tests** | Re-auth enforcement tests, stale session tests |
| **Observability** | Denial rate, re-auth frequency |
| **Lifecycle** | active |
| **Implementation** | `src/lib/auth-guards.ts` |

#### `getSessionContext()`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | security-critical |
| **Owner module** | auth |
| **Signature** | `() → Promise<SessionContext | null>` |
| **Returns** | `{ user: User, session: Session, accessToken: string, expiresAt: number | undefined, isEmailVerified: boolean, lastSignInAt: string | undefined }` or `null` if no valid session |
| **Purity** | impure |
| **Side effects** | DB read (session metadata via Supabase auth) |
| **Transactional** | No |
| **Fail behavior** | fail-secure — return `null` (unauthenticated) |
| **Used by** | All modules (auth context, audit enrichment, rate limiting) |
| **Blast radius** | system-wide |
| **Criticality** | CRITICAL |
| **Approval required** | Yes — Lead |
| **Callable from** | request-path, ui |
| **Related routes** | All authenticated routes |
| **Related risks** | RISK-003 (session hijacking) |
| **Related tests** | Session context tests, metadata accuracy tests |
| **Observability** | Latency, session validity check rate |
| **Lifecycle** | active |
| **Implementation** | `src/lib/auth-guards.ts` |

#### `checkMfaStatus()`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | security-critical |
| **Owner module** | auth |
| **Signature** | `() → Promise<'none' | 'enrolled' | 'challenge_required'>` |
| **Returns** | Current MFA enrollment/challenge state for the authenticated user |
| **Purity** | impure |
| **Side effects** | DB read (MFA authenticator assurance level via Supabase auth) |
| **Transactional** | No |
| **Fail behavior** | fail-secure — return `'none'` on error (no elevated access) |
| **Used by** | auth (AuthContext), MFA pages (MfaEnroll, MfaChallenge) |
| **Blast radius** | large |
| **Criticality** | HIGH |
| **Approval required** | Yes — Lead |
| **Callable from** | ui |
| **Upstream deps** | `getCurrentUser()` |
| **Related routes** | `/mfa-enroll`, `/mfa-challenge` |
| **Related events** | `auth.mfa_enrolled` |
| **Related risks** | RISK-001 (MFA bypass) |
| **Related tests** | MFA status check tests, AAL level tests |
| **Observability** | Error rate |
| **Lifecycle** | active |
| **Implementation** | `src/contexts/AuthContext.tsx` (as `getMfaStatus()` internal + `checkMfaStatus` exposed via context) |

### Authorization Functions

#### `is_superadmin(user_id)`

| Field | Value |
|-------|-------|
| **Type** | db-function |
| **Classification** | authorization-critical |
| **Owner module** | rbac |
| **Signature** | `(user_id: uuid) → boolean` |
| **Returns** | `true` if user has the `superadmin` role |
| **Purity** | impure (DB read) |
| **Side effects** | DB read (user_roles + roles tables) |
| **Transactional** | No |
| **Fail behavior** | fail-secure — return `false` on null/error |
| **Used by** | `has_permission()`, RLS policies |
| **Blast radius** | system-wide |
| **Criticality** | CRITICAL |
| **Approval required** | Yes — Lead |
| **Callable from** | request-path, job-path |
| **Related risks** | RISK-002 (privilege escalation) |
| **Related tests** | Superadmin check tests, null input tests |
| **Observability** | Error rate |
| **Lifecycle** | active |

#### `has_role(user_id, role_key)`

| Field | Value |
|-------|-------|
| **Type** | db-function |
| **Classification** | authorization-critical |
| **Owner module** | rbac |
| **Signature** | `(user_id: uuid, role_key: text) → boolean` |
| **Returns** | `true` if user has the specified role (by key string, not enum) |
| **Purity** | impure (DB read) |
| **Side effects** | DB read (user_roles + roles tables) |
| **Transactional** | No |
| **Fail behavior** | fail-secure — return `false` on null/error |
| **Used by** | All RLS policies |
| **Blast radius** | system-wide |
| **Criticality** | CRITICAL |
| **Approval required** | Yes — Lead |
| **Callable from** | request-path, job-path |
| **Related permissions** | All role-gated permissions |
| **Related risks** | RISK-002 (privilege escalation), RLS bypass |
| **Related watchlist** | RW-001 |
| **Related tests** | RLS policy tests, RBAC unit tests, null input tests |
| **Observability** | Error rate, denial rate anomaly detection |
| **Lifecycle** | active |

#### `has_permission(user_id, permission_key)`

| Field | Value |
|-------|-------|
| **Type** | db-function |
| **Classification** | authorization-critical |
| **Owner module** | rbac |
| **Signature** | `(user_id: uuid, permission_key: text) → boolean` |
| **Returns** | `true` if superadmin (logical inheritance) OR user has explicit permission mapping. `false` on null inputs, nonexistent keys, or errors. |
| **Purity** | impure (DB read) |
| **Side effects** | DB read (user_roles + roles + role_permissions + permissions) |
| **Transactional** | No |
| **Fail behavior** | fail-secure — return `false` on null/error/nonexistent key |
| **Used by** | RLS policies, all edge functions, `get_my_authorization_context()` |
| **Blast radius** | system-wide |
| **Criticality** | CRITICAL |
| **Approval required** | Yes — Lead |
| **Callable from** | request-path, job-path |
| **Upstream deps** | `is_superadmin()` |
| **Related permissions** | All permission index entries |
| **Related risks** | RISK-002 (privilege escalation) |
| **Related watchlist** | RW-001 |
| **Related tests** | Permission check tests, superadmin inheritance tests, null/malformed input tests |
| **Observability** | Denial rate, anomaly detection |
| **Lifecycle** | active |

#### `get_my_authorization_context()`

| Field | Value |
|-------|-------|
| **Type** | db-function |
| **Classification** | authorization-critical |
| **Owner module** | rbac |
| **Signature** | `() → jsonb` |
| **Returns** | `{ roles: text[], permissions: text[], is_superadmin: boolean }` for `auth.uid()` only. Returns null on error. |
| **Purity** | impure (DB read) |
| **Side effects** | DB read (user_roles + roles + role_permissions + permissions) |
| **Transactional** | No |
| **Fail behavior** | fail-secure — return null on error |
| **Used by** | `useUserRoles()` hook (client) |
| **Blast radius** | large |
| **Criticality** | HIGH |
| **Approval required** | Yes — Lead |
| **Callable from** | ui (via RPC) |
| **Upstream deps** | `is_superadmin()` |
| **Related tests** | Authorization context tests, scope limitation tests |
| **Observability** | Latency, error rate |
| **Lifecycle** | active |

#### `useUserRoles()`

| Field | Value |
|-------|-------|
| **Type** | hook |
| **Classification** | ui-shared |
| **Owner module** | rbac |
| **Signature** | `() → { roles: string[], permissions: string[], isSuperadmin: boolean, loading: boolean }` |
| **Returns** | Current user's effective roles, permissions, and superadmin status via `get_my_authorization_context()` RPC — no raw table stitching |
| **Purity** | impure (state + RPC) |
| **Side effects** | RPC call to `get_my_authorization_context()` |
| **Transactional** | No |
| **Fail behavior** | fail-secure — return empty arrays, `isSuperadmin: false` on error |
| **Used by** | admin-panel, user-panel, layout, `RequirePermission` component |
| **Blast radius** | large |
| **Criticality** | HIGH |
| **Approval required** | Yes |
| **Callable from** | ui-only |
| **Upstream deps** | `get_my_authorization_context()` |
| **Related tests** | Role display tests, conditional UI tests, error fallback tests |
| **Lifecycle** | active |

#### `requireRole(userId, roleKey)`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | authorization-critical |
| **Owner module** | rbac |
| **Signature** | `(userId: string, roleKey: string) → Promise<void>` (throws `403` if unauthorized) |
| **Returns** | void; throws `403 Forbidden` if user lacks role |
| **Purity** | impure |
| **Side effects** | DB read, may emit `rbac.permission_denied` |
| **Transactional** | No |
| **Fail behavior** | fail-secure — throw 403 |
| **Used by** | Protected routes |
| **Blast radius** | large |
| **Criticality** | CRITICAL |
| **Approval required** | Yes — Lead |
| **Callable from** | request-path |
| **Upstream deps** | `has_role()`, `authenticateRequest()` |
| **Related permissions** | Role-gated permissions |
| **Related events** | `rbac.permission_denied` |
| **Related risks** | RISK-002 |
| **Related tests** | Role gate tests, 403 response tests |
| **Observability** | Denial rate, error rate |
| **Lifecycle** | active |
| **Usage note** | **Rare infrastructure utility only.** Reserved for coarse administrative gating (e.g., admin panel route access). **MUST NOT** be used as the default authorization primitive for business endpoints — use `checkPermissionOrThrow()` instead. |

#### `checkPermission(context, permission)` *(client-side UX-only)*

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | ui-shared |
| **Owner module** | rbac |
| **Signature** | `(context: AuthorizationContext | null, permission: string) → boolean` |
| **Returns** | `true` if permission exists in cached authorization context. **UX-only — does NOT enforce access.** Server-side `checkPermissionOrThrow()` is authoritative. |
| **Purity** | pure (reads cached context object) |
| **Side effects** | None — reads from pre-fetched authorization context |
| **Transactional** | No |
| **Fail behavior** | fail-secure — return `false` on null context |
| **Used by** | All feature modules (UI element visibility) |
| **Blast radius** | medium |
| **Criticality** | MEDIUM |
| **Approval required** | No |
| **Callable from** | ui-only |
| **Upstream deps** | `useUserRoles()`, `get_my_authorization_context()` |
| **Related permissions** | All permission index entries |
| **Related tests** | Client permission check tests, UI visibility tests |
| **Observability** | — |
| **Lifecycle** | active |
| **Implementation** | `src/lib/rbac.ts` |

#### `checkPermissionOrThrow(userId, permissionKey)`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | authorization-critical |
| **Owner module** | rbac |
| **Signature** | `(userId: string, permissionKey: string) → void` (throws `403` if denied) |
| **Returns** | void; throws `403 Forbidden` if user lacks the specified permission |
| **Purity** | impure |
| **Side effects** | DB read (via `has_permission()`), emits `rbac.permission_denied` on denial |
| **Transactional** | No |
| **Fail behavior** | fail-secure — throw 403 |
| **Used by** | All edge functions (default server-side authorization primitive) |
| **Blast radius** | system-wide |
| **Criticality** | CRITICAL |
| **Approval required** | Yes — Lead |
| **Callable from** | request-path |
| **Upstream deps** | `has_permission()`, `authenticateRequest()` |
| **Related permissions** | All permission index entries |
| **Related events** | `rbac.permission_denied` |
| **Related risks** | RISK-002 (privilege escalation) |
| **Related watchlist** | RW-001 |
| **Related tests** | Permission enforcement tests, 403 response tests, RBAC integration tests |
| **Observability** | Denial rate, anomaly detection |
| **Lifecycle** | active |
| **Usage note** | **Default server-side authorization primitive.** All Phase 3+ business endpoints use this for permission enforcement. Distinct from client-side `checkPermission()` which is UX-only. |

#### `requireSelfScope(ctx, targetUserId)`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | authorization-critical |
| **Owner module** | rbac |
| **Signature** | `(ctx: { user: { id: string } }, targetUserId: string) → void` (throws `403` if mismatch) |
| **Returns** | void; throws `403 Forbidden` if `ctx.user.id` does not match `targetUserId`. Actor is derived from the authenticated context object — callers pass the context returned by `authenticateRequest()`, not a raw user ID. |
| **Purity** | impure |
| **Side effects** | DB read (current user context), emits `rbac.permission_denied` on mismatch |
| **Transactional** | No |
| **Fail behavior** | fail-secure — throw 403 |
| **Used by** | user-panel, user-management |
| **Blast radius** | large |
| **Criticality** | HIGH |
| **Approval required** | Yes — Lead |
| **Callable from** | request-path |
| **Upstream deps** | `authenticateRequest()` |
| **Related permissions** | `users.view_self`, `users.edit_self`, `profile.self_manage` |
| **Related events** | `rbac.permission_denied` |
| **Related risks** | RISK-002 (privilege escalation — cross-user access) |
| **Related tests** | Self-scope enforcement tests, cross-user denial tests |
| **Observability** | Denial rate, anomaly detection |
| **Lifecycle** | active |

### User Management Functions

#### `getUserProfile(userId)`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | data-access |
| **Owner module** | user-management |
| **Signature** | `(userId: uuid) → UserProfile | null` |
| **Returns** | User profile object or null if not found |
| **Purity** | impure |
| **Side effects** | DB read |
| **Transactional** | No |
| **Fail behavior** | fail-fast — throw on DB error |
| **Used by** | admin-panel, user-panel |
| **Blast radius** | medium |
| **Criticality** | MEDIUM |
| **Approval required** | No |
| **Callable from** | any |
| **Related tests** | Profile retrieval tests |
| **Lifecycle** | active |

#### `updateUserProfile(userId, data)`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | data-access |
| **Owner module** | user-management |
| **Signature** | `(userId: uuid, data: ProfileUpdate) → UserProfile` |
| **Returns** | Updated profile object |
| **Purity** | impure |
| **Side effects** | DB write, emits `user.profile_updated` |
| **Transactional** | Yes |
| **Fail behavior** | fail-fast — throw on validation or DB error |
| **Used by** | admin-panel, user-panel |
| **Blast radius** | medium |
| **Criticality** | MEDIUM |
| **Approval required** | No |
| **Callable from** | request-path |
| **Related events** | `user.profile_updated` |
| **Related tests** | Profile update tests, validation tests |
| **Lifecycle** | active |

#### `listUsers(filters, pagination)`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | data-access |
| **Owner module** | user-management |
| **Signature** | `(filters: UserFilters, pagination: PaginationParams) → PaginatedResult<UserSummary>` |
| **Returns** | Paginated list of user summaries |
| **Purity** | impure |
| **Side effects** | DB read |
| **Transactional** | No |
| **Fail behavior** | fail-fast — throw on DB error |
| **Used by** | admin-panel |
| **Blast radius** | small |
| **Criticality** | MEDIUM |
| **Approval required** | No |
| **Callable from** | request-path |
| **Related configs** | `pagination.default_page_size`, `pagination.max_page_size` |
| **Related tests** | User listing tests, pagination tests |
| **Lifecycle** | active |

#### `deactivateUser(userId)`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | data-access |
| **Owner module** | user-management |
| **Signature** | `(userId: uuid) → void` |
| **Returns** | void; sets user lifecycle state to `deactivated` |
| **Purity** | impure |
| **Side effects** | DB write (lifecycle state), emits `user.account_deactivated`, triggers `auth.session_revoked` for active sessions |
| **Transactional** | Yes |
| **Fail behavior** | fail-fast — throw on DB error or invalid state transition |
| **Used by** | admin-panel |
| **Blast radius** | large |
| **Criticality** | HIGH |
| **Approval required** | Yes |
| **Callable from** | request-path |
| **Related permissions** | `users.deactivate` |
| **Related routes** | `/admin/users/:id/deactivate` |
| **Related events** | `user.account_deactivated`, `auth.session_revoked` |
| **Related risks** | User access disruption, session/token invalidation |
| **Related tests** | Deactivation allow/deny suite, post-deactivation lockout test, session revocation test |
| **Observability** | Invocation count, error rate |
| **Lifecycle** | active |

#### `reactivateUser(userId)`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | data-access |
| **Owner module** | user-management |
| **Signature** | `(userId: uuid) → void` |
| **Returns** | void; sets user lifecycle state back to `active` |
| **Purity** | impure |
| **Side effects** | DB write (lifecycle state), emits `user.account_reactivated` |
| **Transactional** | Yes |
| **Fail behavior** | fail-fast — throw on DB error or invalid state transition |
| **Used by** | admin-panel |
| **Blast radius** | large |
| **Criticality** | HIGH |
| **Approval required** | Yes |
| **Callable from** | request-path |
| **Related permissions** | `users.reactivate` |
| **Related routes** | `/admin/users/:id/reactivate` |
| **Related events** | `user.account_reactivated` |
| **Related risks** | Premature access restoration |
| **Related tests** | Reactivation allow/deny suite, post-reactivation access test |
| **Observability** | Invocation count, error rate |
| **Lifecycle** | active |

### Audit Functions

#### `logAuditEvent(params)`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | audit-critical |
| **Owner module** | audit-logging |
| **Signature** | `(params: AuditEventParams) → Promise<AuditWriteResult>` |
| **Returns** | On success: `{ success: true, auditId: string, correlationId: string }`. On failure: `{ success: false, code: string, reason: string, correlationId: string }`. Never throws — callers inspect `success` to decide fail-closed vs log-and-continue behavior. |
| **Purity** | impure |
| **Side effects** | DB write (append-only audit table), emits `audit.logged` on success, emits `audit.write_failed` on failure |
| **Transactional** | Yes (independent transaction — must not fail with parent) |
| **Fail behavior** | Returns structured failure result. Callers enforce policy: high-risk actions abort on `{ success: false }`, standard-risk actions continue and surface alert. |
| **Used by** | All modules |
| **Blast radius** | system-wide |
| **Criticality** | CRITICAL |
| **Approval required** | Yes — Lead |
| **Callable from** | request-path, job-path |
| **Related events** | `audit.logged`, `audit.write_failed` |
| **Related risks** | Audit trail integrity |
| **Related tests** | Audit write tests, append-only integrity tests, failure resilience tests, structured return tests |
| **Observability** | Write success rate, emission verification, latency |
| **Lifecycle** | active |

#### `queryAuditLogs(filters)`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | data-access |
| **Owner module** | audit-logging |
| **Signature** | `(filters: AuditFilters) → PaginatedResult<AuditEntry>` |
| **Returns** | Paginated audit log entries |
| **Purity** | impure |
| **Side effects** | DB read |
| **Transactional** | No |
| **Fail behavior** | fail-fast |
| **Used by** | admin-panel |
| **Blast radius** | small |
| **Criticality** | MEDIUM |
| **Approval required** | No |
| **Callable from** | request-path |
| **Related tests** | Audit query tests, filter tests |
| **Lifecycle** | active |

#### `exportAuditLogs(filters)`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | audit-critical |
| **Owner module** | audit-logging |
| **Signature** | `(filters: AuditExportFilters) → AuditExportResult` |
| **Returns** | Exported audit data in requested format |
| **Purity** | impure |
| **Side effects** | DB read, export generation |
| **Transactional** | No |
| **Fail behavior** | fail-fast — throw on DB error or permission failure |
| **Used by** | admin-panel |
| **Blast radius** | medium |
| **Criticality** | HIGH |
| **Approval required** | No |
| **Callable from** | request-path |
| **Related permissions** | `audit.export` |
| **Related routes** | `/admin/audit/export` |
| **Related risks** | Compliance-sensitive data exposure, large export performance |
| **Related tests** | Export allow/deny suite, export filtering tests, sensitive-field exclusion tests |
| **Observability** | Invocation count, export size, latency |
| **Lifecycle** | active |

### Health Monitoring Functions

#### `getSystemHealth()`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | utility |
| **Owner module** | health-monitoring |
| **Signature** | `() → SystemHealthReport` |
| **Returns** | Current system health status across all components |
| **Purity** | impure |
| **Side effects** | DB read, service health checks |
| **Transactional** | No |
| **Fail behavior** | fail-fast — report degraded if checks fail |
| **Used by** | admin-panel |
| **Blast radius** | small |
| **Criticality** | LOW |
| **Approval required** | No |
| **Callable from** | request-path |
| **Related events** | `health.status_changed` |
| **Related tests** | Health check tests |
| **Lifecycle** | active |

#### `getMetrics(timeRange)`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | data-access |
| **Owner module** | health-monitoring |
| **Signature** | `(timeRange: TimeRange) → MetricsReport` |
| **Returns** | Metrics data for the specified time range |
| **Purity** | impure |
| **Side effects** | DB / metrics-store read |
| **Transactional** | No |
| **Fail behavior** | fail-fast — throw on DB error |
| **Used by** | admin-panel |
| **Blast radius** | small |
| **Criticality** | MEDIUM |
| **Approval required** | No |
| **Callable from** | request-path |
| **Related permissions** | `monitoring.view` |
| **Related routes** | `/admin/monitoring` |
| **Related tests** | Metrics retrieval tests, time-range validation tests, authorized access tests |
| **Observability** | Latency, query performance |
| **Lifecycle** | active |

#### `evaluateAlerts()`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | job-critical |
| **Owner module** | health-monitoring |
| **Signature** | `() → AlertEvaluationResult` |
| **Returns** | Result of threshold evaluations; triggers alerts as needed |
| **Purity** | impure |
| **Side effects** | DB read (metrics + thresholds), may emit `health.alert_triggered`, may update health state via `health.status_changed` |
| **Transactional** | No |
| **Fail behavior** | fail-fast — emit `health.monitoring_failed` on evaluation failure |
| **Used by** | `alert_evaluation` job |
| **Blast radius** | large |
| **Criticality** | HIGH |
| **Approval required** | Yes |
| **Callable from** | job-path |
| **Related permissions** | `monitoring.configure` (for threshold management) |
| **Related events** | `health.alert_triggered`, `health.status_changed`, `health.monitoring_failed` |
| **Related tests** | Threshold evaluation tests, alert grouping/throttling tests, maintenance-mode suppression tests |
| **Observability** | Evaluation latency, alert trigger rate, false-positive rate |
| **Lifecycle** | active |

### API Functions

#### `apiError(code, message)`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | api-critical |
| **Owner module** | api |
| **Signature** | `(code: number, message: string) → Response` |
| **Returns** | Standardized error response |
| **Purity** | pure |
| **Side effects** | none |
| **Transactional** | No |
| **Fail behavior** | N/A (pure formatter) |
| **Used by** | All edge functions |
| **Blast radius** | system-wide |
| **Criticality** | HIGH |
| **Approval required** | No |
| **Callable from** | request-path |
| **Related tests** | Error format tests, status code tests |
| **Lifecycle** | active |

#### `validateRequest(schema, body)`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | api-critical |
| **Owner module** | api |
| **Signature** | `(schema: ZodSchema, body: unknown) → T` (throws `400` on invalid) |
| **Returns** | Validated and typed request body; throws `400 Bad Request` on validation failure |
| **Purity** | pure |
| **Side effects** | none |
| **Transactional** | No |
| **Fail behavior** | fail-fast — throw 400 with validation details |
| **Used by** | All edge functions |
| **Blast radius** | system-wide |
| **Criticality** | HIGH |
| **Approval required** | No |
| **Callable from** | request-path |
| **Related tests** | Input validation tests, boundary tests, injection prevention tests |
| **Lifecycle** | active |

#### `normalizeRequest(input)`

| Field | Value |
|-------|-------|
| **Type** | utility |
| **Classification** | api-critical |
| **Owner module** | api |
| **Signature** | `(input: unknown) → NormalizedInput` |
| **Returns** | Normalized input object (trimmed, lowercased where applicable, sanitized) |
| **Purity** | impure |
| **Side effects** | Input mutation (trim whitespace, normalize casing, sanitize) |
| **Transactional** | No |
| **Fail behavior** | fail-secure — reject malformed input with 400 |
| **Used by** | All edge functions |
| **Blast radius** | system-wide |
| **Criticality** | HIGH |
| **Approval required** | No |
| **Callable from** | request-path |
| **Downstream deps** | `validateRequest()` (called after normalization) |
| **Related tests** | Normalization tests, sanitization tests, encoding tests |
| **Lifecycle** | active |

### Job Functions

#### `executeWithRetry(fn, config)`

| Field | Value |
|-------|-------|
| **Type** | function |
| **Classification** | job-critical |
| **Owner module** | jobs-and-scheduler |
| **Signature** | `(fn: () → Promise<T>, config: RetryConfig) → Promise<T>` |
| **Returns** | Result of successful execution; throws after max retries exhausted |
| **Purity** | impure |
| **Side effects** | Executes wrapped function (inherits side effects), emits `job.retry_scheduled` on retry |
| **Transactional** | Depends on wrapped function |
| **Fail behavior** | fail-fast after max retries — emit `job.failed` |
| **Used by** | All jobs |
| **Blast radius** | medium |
| **Criticality** | HIGH |
| **Approval required** | No |
| **Callable from** | job-path |
| **Related configs** | `jobs.max_retries`, `jobs.retry_backoff_base` |
| **Related events** | `job.retry_scheduled`, `job.failed`, `job.dead_lettered` |
| **Related risks** | RISK-007 (job failure cascade) |
| **Related tests** | Retry behavior tests, backoff tests, max retry tests |
| **Observability** | Retry rate, failure rate, execution duration |
| **Lifecycle** | active |

---

## Critical Shared Functions Summary

### Top Critical Functions (Require Strongest Governance)

| Function | Classification | Blast Radius | Why Critical |
|----------|---------------|--------------|--------------|
| `authenticateRequest()` | security-critical | system-wide | All API auth depends on this |
| `getCurrentUser()` | security-critical | system-wide | All authenticated features depend on this |
| `requireAuth()` | security-critical | system-wide | All route protection depends on this |
| `requireVerifiedEmail()` | security-critical | system-wide | Email verification gate for all protected routes |
| `requireRecentAuth()` | security-critical | large | Re-auth gate for sensitive/destructive actions |
| `getSessionContext()` | security-critical | system-wide | Session metadata for all modules |
| `is_superadmin()` | authorization-critical | system-wide | Superadmin logical inheritance depends on this |
| `has_role()` | authorization-critical | system-wide | All RLS policies depend on this |
| `has_permission()` | authorization-critical | system-wide | All permission checks depend on this |
| `get_my_authorization_context()` | authorization-critical | large | Client authorization context depends on this |
| `checkPermission()` | authorization-critical | system-wide | Client-side permission checks (UX-only) |
| `checkPermissionOrThrow()` | authorization-critical | system-wide | **Default server-side authorization primitive** for all edge functions |
| `requireRole()` | authorization-critical | large | Rare infrastructure gating only — not default auth primitive |
| `requireSelfScope()` | authorization-critical | large | Self-scope enforcement for user-owned resources |
| `logAuditEvent()` | audit-critical | system-wide | Entire audit trail depends on this |
| `validateRequest()` | api-critical | system-wide | All input validation depends on this |
| `normalizeRequest()` | api-critical | system-wide | All input normalization depends on this |

---

## Dependencies

- [Constitution](../00-governance/constitution.md) — Rule 6
- [Dependency Map](../01-architecture/dependency-map.md)
- [Change Control Policy](../00-governance/change-control-policy.md) — function changes follow change control
- [Action Tracker](../06-tracking/action-tracker.md) — critical function changes create entries
- [Risk Register](../06-tracking/risk-register.md) — function-related risks tracked
- [Regression Watchlist](../06-tracking/regression-watchlist.md) — fragile function behavior monitored

## Related Documents

- [Config Index](config-index.md)
- [Event Index](event-index.md)
- [Permission Index](permission-index.md)
- [Route Index](route-index.md)
- [Env Var Index](env-var-index.md)
