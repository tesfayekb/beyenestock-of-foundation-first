# Route Index

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-09 | **Status:** Living Document | **Index Version:** `route-v1.1`

## Purpose

Central registry and **route governance system** for all application routes and API endpoints. This document is the single source of truth for route definitions — it governs access control (permission-based, not role-based), request/response contracts, audit requirements, and testing expectations.

## Scope

All frontend routes and API endpoints across all modules.

---

## Enforcement Rule (CRITICAL)

| Rule | Description |
|------|-------------|
| **Completeness** | No route may exist outside this index. Undocumented route = invalid implementation. |
| **Permission-based access** | Protected routes must use permission-based access control from the Permission Index, not role-based checks. |
| **Server enforcement** | Protected routes must not rely on UI hiding alone — server-side enforcement required. |
| **Traceability** | Every protected route must map to at least one Permission Index entry. |
| **Change control** | Route changes (path, access, contract) require change control. |
| **No hidden routes** | Internal/debug routes in production are prohibited unless documented and governed. |

---

## Route Classification Model

| Classification | Description | Governance Level |
|---------------|-------------|-----------------|
| **public** | No authentication required; accessible to all | Standard |
| **authenticated** | Requires valid session; no specific permission | Medium |
| **privileged** | Requires specific permission(s) from Permission Index | High — permission-linked |
| **destructive** | Enables irreversible or high-impact actions | Highest — re-auth + audit |
| **internal** | System/health endpoints, not user-facing | Medium — access-controlled |

---

## Route Entry Schema

### Frontend Route Fields

| Field | Description | Required |
|-------|-------------|----------|
| `path` | URL path pattern | Yes |
| `page` | Page/component name | Yes |
| `module` | Owning module | Yes |
| `classification` | From classification model | Yes |
| `auth_required` | Whether authentication is required | Yes |
| `permission_required` | Permission key(s) from Permission Index | If protected |
| `scope` | `self`, `tenant`, `system-wide` | If protected |
| `panel` | `public`, `user-panel`, `admin-panel` | Yes |
| `reauth_required` | Whether re-authentication is needed for actions | If destructive |
| `related_functions` | Shared functions used by this route | If applicable |
| `related_events` | Events emitted from this route | If applicable |
| `related_tests` | Tests covering this route | If applicable |
| `related_risks` | Risk register items | If applicable |
| `lifecycle` | `active`, `deprecated`, `pending-removal` | Yes |

### API Route Fields (additional)

| Field | Description | Required |
|-------|-------------|----------|
| `method` | HTTP method (GET, POST, PUT, DELETE, PATCH) | Yes |
| `request_schema` | Expected request body/params (Zod schema reference) | If applicable |
| `response_contract` | Response shape and status codes | Yes |
| `rate_limit_class` | Rate limiting tier (`standard`, `strict`, `relaxed`) | Yes |
| `audit_required` | Whether actions generate audit events | Yes |
| `idempotent` | Whether the endpoint is idempotent | Yes |

---

## Sensitive Route Rules

Routes classified as `destructive` or `privileged` with system-wide scope:

| Rule | Description |
|------|-------------|
| **Re-auth** | May require re-authentication before action |
| **Audit** | All actions must generate audit events |
| **Approval** | Route changes require Lead approval |
| **Double confirmation** | Destructive actions should require user confirmation in UI |

---

## Testing Requirements

| Test Type | Applies To | Description |
|-----------|-----------|-------------|
| **Authenticated allow** | All protected routes | Verify correct permission grants access |
| **Unauthenticated deny** | All protected routes | Verify unauthenticated request returns 401 |
| **Unauthorized deny** | All privileged routes | Verify wrong permission returns 403 |
| **Scope boundary** | Scoped routes | Verify user cannot exceed their scope |
| **Public access** | Public routes | Verify no auth required |
| **E2E coverage** | Critical routes | Full user flow testing |
| **Rate limit** | API routes | Verify rate limiting enforced |

**Rule:** Every protected route must have at minimum an allow test and a deny test.

---

## Route Lifecycle

| State | Description | Action Required |
|-------|-------------|-----------------|
| **Active** | In use, governed by this index | Standard governance |
| **Deprecated** | Scheduled for removal | Redirect plan + sunset date |
| **Pending removal** | Will be removed in next release | All references updated |

---

## API Route Versioning

| Rule | Description |
|------|-------------|
| **Version format** | API routes use path-based versioning: `/v1/...`, `/v2/...` |
| **Default version** | All current endpoints are `v1` (implicit — explicit prefix added when `v2` is introduced) |
| **Breaking changes** | Breaking API changes (request/response schema, auth model, behavior) require new version |
| **Parallel support** | Old versions remain active during transition with documented sunset date |
| **Deprecation** | Deprecated versions return `Sunset` header and are removed after all consumers migrate |

---

## Route Latency Budget

| Route Classification | Max Expected Latency (p95) | Alert Threshold |
|---------------------|---------------------------|-----------------|
| **Public pages** | 200ms | > 500ms |
| **Authenticated pages** | 300ms | > 750ms |
| **Admin pages** | 500ms | > 1000ms |
| **API — read** | 100ms | > 250ms |
| **API — write** | 200ms | > 500ms |
| **Health check** | 50ms | > 100ms |

**Rule:** Routes exceeding their latency budget must be investigated. Sustained breach = action tracker entry.

---

## Route Access Telemetry

| Rule | Description |
|------|-------------|
| **Access frequency** | Track request counts per route (sampled for high-volume) |
| **Permission denial rate** | Track 401/403 rates per route — anomalies trigger alerts |
| **Anomaly detection** | Unusual patterns (traffic spike, off-hours access to admin routes, repeated denials) trigger security review |
| **Dead route detection** | Routes with zero traffic over 90 days flagged for review |
| **Dashboard** | Route telemetry visible in admin monitoring panel |

---

## Route Dependency Graph (Future-Ready)

| Rule | Description |
|------|-------------|
| **Mapping** | Each route's `related_functions`, `related_events`, and downstream job triggers enable automated dependency graphs |
| **Visualization** | System should support: `route → function → event → job` visual mapping |
| **Impact analysis** | Route changes should surface all downstream dependencies automatically |
| **Debugging utility** | Graph usable for root cause analysis and incident response |

---

## Canary / Rollout Control

| Rule | Description |
|------|-------------|
| **Critical routes** | Destructive and system-wide privileged routes should support staged rollout for major changes |
| **Canary phase** | Route changes deployed to small percentage of traffic first; monitored for errors, latency, and denial rates |
| **Monitoring** | During rollout: error rate, latency budget, permission denial anomalies tracked |
| **Rollback** | Automatic rollback if error rate exceeds threshold during canary |
| **Full deploy** | Only after canary phase passes with clean metrics |

---

## Frontend Route Registry

### Public Routes

#### `/` — Home (Authenticated Landing)

| Field | Value |
|-------|-------|
| **Page** | Index (Home) |
| **Module** | auth |
| **Classification** | authenticated |
| **Auth required** | Yes |
| **Permission required** | *(authenticated + verified email — no specific permission)* |
| **Scope** | self |
| **Panel** | user-panel |
| **Related functions** | `requireAuth()`, `requireVerifiedEmail()` |
| **Related tests** | Home page render test, unauthenticated deny test |
| **Lifecycle** | active |

#### `/sign-in` — Sign In

| Field | Value |
|-------|-------|
| **Page** | Sign In |
| **Module** | auth |
| **Classification** | public |
| **Auth required** | No |
| **Panel** | public |
| **Related functions** | `authenticateRequest()` |
| **Related events** | `auth.signed_in`, `auth.failed_attempt` |
| **Related tests** | Login flow tests, failed login tests |
| **Related risks** | RISK-001 (credential compromise) |
| **Lifecycle** | active |

#### `/sign-up` — Sign Up

| Field | Value |
|-------|-------|
| **Page** | Sign Up |
| **Module** | auth |
| **Classification** | public |
| **Auth required** | No |
| **Panel** | public |
| **Related events** | `auth.signed_up` |
| **Related tests** | Signup flow tests, validation tests |
| **Lifecycle** | active |

#### `/forgot-password` — Password Reset

| Field | Value |
|-------|-------|
| **Page** | Password Reset |
| **Module** | auth |
| **Classification** | public |
| **Auth required** | No |
| **Panel** | public |
| **Related events** | `auth.password_reset` |
| **Related tests** | Password reset flow tests |
| **Related risks** | RISK-001 |
| **Lifecycle** | active |

#### `/reset-password` — Password Reset Completion

| Field | Value |
|-------|-------|
| **Page** | Reset Password |
| **Module** | auth |
| **Classification** | public |
| **Auth required** | No (token-based) |
| **Panel** | public |
| **Related events** | `auth.password_reset` |
| **Related tests** | Password reset completion tests |
| **Related risks** | RISK-001 |
| **Lifecycle** | active |

#### `/mfa-challenge` — MFA Verification

| Field | Value |
|-------|-------|
| **Page** | MFA Challenge |
| **Module** | auth |
| **Classification** | public |
| **Auth required** | No (partial session — AAL1 with MFA pending) |
| **Panel** | public |
| **Related functions** | `checkMfaStatus()` |
| **Related events** | `auth.signed_in` (on MFA completion), `auth.failed_attempt` (on MFA failure) |
| **Related tests** | MFA challenge flow tests |
| **Lifecycle** | active |

#### `/mfa-enroll` — MFA Enrollment

| Field | Value |
|-------|-------|
| **Page** | MFA Enroll |
| **Module** | auth |
| **Classification** | authenticated |
| **Auth required** | Yes |
| **Permission required** | *(authenticated + verified email — no specific permission)* |
| **Scope** | self |
| **Panel** | user-panel |
| **Related functions** | `requireAuth()`, `requireVerifiedEmail()`, `checkMfaStatus()` |
| **Related events** | `auth.mfa_enrolled` |
| **Related tests** | MFA enrollment flow tests, unauthenticated deny test |
| **Lifecycle** | active |

### User Panel Routes (Authenticated)

#### `/dashboard` — User Dashboard

| Field | Value |
|-------|-------|
| **Page** | User Dashboard |
| **Module** | user-panel |
| **Classification** | authenticated |
| **Auth required** | Yes |
| **Permission required** | *(authenticated session only — no specific permission)* |
| **Scope** | self |
| **Panel** | user-panel |
| **Related functions** | `getCurrentUser()`, `requireAuth()` |
| **Related tests** | Dashboard render test, unauthenticated deny test |
| **Lifecycle** | active |

#### `/settings` — User Settings

| Field | Value |
|-------|-------|
| **Page** | User Settings |
| **Module** | user-panel |
| **Classification** | authenticated |
| **Auth required** | Yes |
| **Permission required** | `profile.self_manage` |
| **Scope** | self |
| **Panel** | user-panel |
| **Related functions** | `requireAuth()`, `requireSelfScope()`, `getUserProfile()`, `updateUserProfile()` |
| **Related events** | `user_panel.settings_changed` |
| **Related tests** | Settings render test, update flow test, self-scope denial test |
| **Lifecycle** | active |

#### `/settings/security` — MFA Settings

| Field | Value |
|-------|-------|
| **Page** | MFA Settings |
| **Module** | user-panel |
| **Classification** | authenticated |
| **Auth required** | Yes |
| **Permission required** | `mfa.self_manage`, `session.self_manage` |
| **Scope** | self |
| **Panel** | user-panel |
| **Reauth required** | Yes (sensitive security action) |
| **Related functions** | `requireAuth()`, `requireRecentAuth()`, `requireSelfScope()` |
| **Related events** | `auth.mfa_enrolled`, `user_panel.mfa_updated`, `auth.session_revoked` |
| **Lifecycle** | active |

### Admin Panel Routes (Privileged)

#### `/admin` — Admin Dashboard

| Field | Value |
|-------|-------|
| **Page** | Admin Dashboard |
| **Module** | admin-panel |
| **Classification** | privileged |
| **Auth required** | Yes |
| **Permission required** | `admin.access` |
| **Scope** | system-wide |
| **Panel** | admin-panel |
| **Related functions** | `requireAuth()`, `checkPermission()` |
| **Related tests** | Admin access allow/deny suite |
| **Related risks** | RISK-002 (privilege escalation) |
| **Lifecycle** | active |

#### `/admin/users` — User Management

| Field | Value |
|-------|-------|
| **Page** | User Management |
| **Module** | admin-panel |
| **Classification** | privileged |
| **Auth required** | Yes |
| **Permission required** | `admin.access` + `users.view_all` |
| **Scope** | system-wide |
| **Panel** | admin-panel |
| **Related functions** | `listUsers()`, `checkPermission()` |
| **Related tests** | User management allow/deny suite |
| **Lifecycle** | active |

#### `/admin/users/:id/roles` — Role Assignment

| Field | Value |
|-------|-------|
| **Page** | Role Assignment (within User Management) |
| **Module** | admin-panel |
| **Classification** | privileged, destructive |
| **Auth required** | Yes |
| **Permission required** | `admin.access` + `roles.assign` / `roles.revoke` |
| **Scope** | system-wide |
| **Panel** | admin-panel |
| **Reauth required** | Yes |
| **Related functions** | `has_role()`, `checkPermission()` |
| **Related events** | `rbac.role_assigned`, `rbac.role_revoked` |
| **Related risks** | RISK-002 (privilege escalation) |
| **Related watchlist** | RW-001 |
| **Related tests** | Role assign/revoke allow/deny suite |
| **Lifecycle** | active |

#### `/admin/users/:id` — User Detail / Edit

| Field | Value |
|-------|-------|
| **Page** | User Detail and Edit |
| **Module** | admin-panel |
| **Classification** | privileged |
| **Auth required** | Yes |
| **Permission required** | `admin.access` + `users.view_all` / `users.edit_any` |
| **Scope** | system-wide |
| **Panel** | admin-panel |
| **Related functions** | `getUserProfile()`, `updateUserProfile()`, `checkPermission()` |
| **Related events** | `user.profile_updated` |
| **Related tests** | User detail view/edit allow/deny suite |
| **Lifecycle** | active |

#### `/admin/users/:id/deactivate` — User Deactivation

| Field | Value |
|-------|-------|
| **Page** | User Deactivation (action within User Management) |
| **Module** | admin-panel |
| **Classification** | privileged, destructive |
| **Auth required** | Yes |
| **Permission required** | `admin.access` + `users.deactivate` |
| **Scope** | system-wide |
| **Panel** | admin-panel |
| **Reauth required** | Yes |
| **Related functions** | `deactivateUser()`, `checkPermission()`, `requireRecentAuth()` |
| **Related events** | `user.account_deactivated`, `auth.session_revoked` |
| **Related risks** | User access disruption |
| **Related tests** | Deactivation allow/deny suite, post-deactivation lockout test |
| **Lifecycle** | active |

#### `/admin/users/:id/reactivate` — User Reactivation

| Field | Value |
|-------|-------|
| **Page** | User Reactivation (action within User Management) |
| **Module** | admin-panel |
| **Classification** | privileged |
| **Auth required** | Yes |
| **Permission required** | `admin.access` + `users.reactivate` |
| **Scope** | system-wide |
| **Panel** | admin-panel |
| **Reauth required** | Yes |
| **Related functions** | `reactivateUser()`, `checkPermission()`, `requireRecentAuth()` |
| **Related events** | `user.account_reactivated` |
| **Related risks** | Premature access restoration |
| **Related tests** | Reactivation allow/deny suite, post-reactivation access test |
| **Lifecycle** | active |

#### `/admin/roles` — Role Management

| Field | Value |
|-------|-------|
| **Page** | Role Management |
| **Module** | admin-panel |
| **Classification** | privileged |
| **Auth required** | Yes |
| **Permission required** | `admin.access` + `roles.view` |
| **Scope** | system-wide |
| **Panel** | admin-panel |
| **Related tests** | Role listing allow/deny tests |
| **Lifecycle** | active |

#### `/admin/audit` — Audit Logs

| Field | Value |
|-------|-------|
| **Page** | Audit Logs |
| **Module** | admin-panel |
| **Classification** | privileged |
| **Auth required** | Yes |
| **Permission required** | `admin.access` + `audit.view` |
| **Scope** | system-wide |
| **Panel** | admin-panel |
| **Related functions** | `queryAuditLogs()` |
| **Related tests** | Audit view allow/deny tests |
| **Lifecycle** | active |

#### `/admin/audit/export` — Audit Export

| Field | Value |
|-------|-------|
| **Page** | Audit Export (within Audit Logs) |
| **Module** | admin-panel |
| **Classification** | privileged |
| **Auth required** | Yes |
| **Permission required** | `admin.access` + `audit.export` |
| **Scope** | system-wide |
| **Panel** | admin-panel |
| **Audit required** | Yes (compliance-sensitive data export) |
| **Related tests** | Audit export allow/deny suite |
| **Lifecycle** | active |

#### `/admin/monitoring` — Health Dashboard

| Field | Value |
|-------|-------|
| **Page** | Health Dashboard |
| **Module** | admin-panel |
| **Classification** | privileged |
| **Auth required** | Yes |
| **Permission required** | `admin.access` + `monitoring.view` |
| **Scope** | system-wide |
| **Panel** | admin-panel |
| **Related functions** | `getSystemHealth()` |
| **Related tests** | Monitoring view allow/deny tests |
| **Lifecycle** | active |

#### `/admin/monitoring/config` — Alert Configuration

| Field | Value |
|-------|-------|
| **Page** | Alert Configuration (within Health Dashboard) |
| **Module** | admin-panel |
| **Classification** | privileged |
| **Auth required** | Yes |
| **Permission required** | `admin.access` + `monitoring.configure` |
| **Scope** | system-wide |
| **Panel** | admin-panel |
| **Audit required** | Yes |
| **Related tests** | Monitoring config allow/deny tests |
| **Lifecycle** | active |

#### `/admin/config` — System Config

| Field | Value |
|-------|-------|
| **Page** | System Config |
| **Module** | admin-panel |
| **Classification** | privileged, destructive |
| **Auth required** | Yes |
| **Permission required** | `admin.access` + `admin.config` |
| **Scope** | system-wide |
| **Panel** | admin-panel |
| **Reauth required** | Yes |
| **Audit required** | Yes |
| **Related events** | `admin.config_changed` |
| **Related tests** | Config change allow/deny suite |
| **Lifecycle** | active |

#### `/admin/jobs` — Jobs Dashboard

| Field | Value |
|-------|-------|
| **Page** | Jobs Dashboard |
| **Module** | admin-panel |
| **Classification** | privileged |
| **Auth required** | Yes |
| **Permission required** | `admin.access` + `jobs.view` |
| **Scope** | system-wide |
| **Panel** | admin-panel |
| **Related tests** | Jobs view allow/deny tests |
| **Lifecycle** | active |

#### `/admin/jobs/:id/trigger` — Manual Job Trigger

| Field | Value |
|-------|-------|
| **Page** | Job Trigger (within Jobs Dashboard) |
| **Module** | admin-panel |
| **Classification** | privileged |
| **Auth required** | Yes |
| **Permission required** | `admin.access` + `jobs.trigger` |
| **Scope** | system-wide |
| **Panel** | admin-panel |
| **Audit required** | Yes |
| **Related events** | `job.started` |
| **Related tests** | Job trigger allow/deny suite |
| **Lifecycle** | active |

#### `/admin/jobs/deadletter` — Dead-Letter Management

| Field | Value |
|-------|-------|
| **Page** | Dead-Letter Management |
| **Module** | admin-panel |
| **Classification** | privileged, destructive |
| **Auth required** | Yes |
| **Permission required** | `admin.access` + `jobs.deadletter.manage` |
| **Scope** | system-wide |
| **Panel** | admin-panel |
| **Reauth required** | Yes |
| **Audit required** | Yes |
| **Related events** | `job.replayed`, `job.dead_lettered` |
| **Related risks** | RISK-007 (job failure cascade) |
| **Related tests** | Dead-letter management allow/deny suite |
| **Lifecycle** | active |

#### `/admin/jobs/emergency` — Kill Switch

| Field | Value |
|-------|-------|
| **Page** | Kill Switch |
| **Module** | admin-panel |
| **Classification** | privileged, destructive |
| **Auth required** | Yes |
| **Permission required** | `admin.access` + `jobs.emergency` |
| **Scope** | system-wide |
| **Panel** | admin-panel |
| **Reauth required** | Yes |
| **Audit required** | Yes |
| **Related events** | `job.kill_switch_activated` |
| **Related risks** | RISK-007 |
| **Related tests** | Kill switch allow/deny suite, emergency flow E2E |
| **Lifecycle** | active |

---

## API Endpoint Registry

### System Endpoints

#### `GET /health` — Health Check

| Field | Value |
|-------|-------|
| **Module** | health-monitoring |
| **Classification** | internal |
| **Auth required** | No |
| **Purpose** | System health check for monitoring and load balancers |
| **Response contract** | `200: { status: "healthy" | "degraded" | "down", checks: {...} }` |
| **Rate limit class** | relaxed |
| **Audit required** | No |
| **Idempotent** | Yes |
| **Related functions** | `getSystemHealth()` |
| **Related tests** | Health endpoint tests |
| **Lifecycle** | active |

#### `GET /query-audit-logs` — Audit Log Query

| Field | Value |
|-------|-------|
| **Module** | audit-logging |
| **Classification** | privileged |
| **Auth required** | Yes |
| **Permission required** | `audit.view` |
| **Scope** | system-wide |
| **Purpose** | Paginated query of audit log entries with filters |
| **Request schema** | Query params: `limit` (1–100, default 50), `action`, `actor_id` (UUID), `target_type`, `target_id` (UUID), `date_from` (ISO), `date_to` (ISO), `before` (cursor: ISO datetime) |
| **Response contract** | `200: { data: AuditLog[], pagination: { count, limit, next_cursor } }` / `401` / `403` / `400` |
| **Rate limit class** | standard |
| **Audit required** | No (read-only) |
| **Idempotent** | Yes |
| **Related functions** | `authenticateRequest()`, `checkPermissionOrThrow()` |
| **Related permissions** | `audit.view` |
| **Related tests** | Unauth denial, method denial, CORS, pagination |
| **Lifecycle** | active |

#### `GET /export-audit-logs` — Audit Log Export (CSV)

| Field | Value |
|-------|-------|
| **Module** | audit-logging |
| **Classification** | privileged, compliance-sensitive |
| **Auth required** | Yes |
| **Permission required** | `audit.export` |
| **Scope** | system-wide |
| **Purpose** | CSV export of audit logs for compliance |
| **Request schema** | Query params: `action`, `actor_id` (UUID), `target_type`, `date_from` (ISO), `date_to` (ISO) |
| **Response contract** | `200: text/csv` (with Content-Disposition) / `401` / `403` / `400` / `503` (audit integrity failure) |
| **Rate limit class** | strict |
| **Audit required** | Yes — HIGH-RISK (fail-closed: export aborted if audit write fails) |
| **Idempotent** | Yes |
| **Max export size** | 10,000 rows |
| **Related functions** | `authenticateRequest()`, `checkPermissionOrThrow()`, `logAuditEvent()` |
| **Related permissions** | `audit.export` |
| **Related events** | `audit.exported` |
| **Related tests** | Unauth denial, method denial, CORS, fail-closed audit |
| **Lifecycle** | active |

> Additional API endpoints will be added as modules are implemented. Each must follow the full schema above, including method, auth model, permission model, request/response contract, rate limit class, and audit requirements.

### User Management API Endpoints

#### `GET /get-profile`

| Field | Value |
|-------|-------|
| **Path** | `/get-profile` |
| **Method** | `GET` |
| **Classification** | authenticated (self-scope) / privileged (admin) |
| **Auth Model** | Bearer JWT (validated via `authenticateRequest()`) |
| **Permission (self)** | `users.view_self` (self-scope) |
| **Permission (admin)** | `users.view_all` (system-wide) |
| **Query Params** | `user_id` (optional UUID — omit for own profile) |
| **Response (200)** | `{ profile: { id, display_name, avatar_url, email_verified, status, created_at, updated_at } }` |
| **Error (401)** | Missing/invalid token |
| **Error (403)** | Permission denied |
| **Error (404)** | Profile not found |
| **Rate Limit** | standard |
| **Audit Required** | No |
| **Lifecycle** | active |

#### `PATCH /update-profile`

| Field | Value |
|-------|-------|
| **Path** | `/update-profile` |
| **Method** | `PATCH` |
| **Classification** | authenticated (self-scope) / privileged (admin) |
| **Auth Model** | Bearer JWT (validated via `authenticateRequest()`) |
| **Permission (self)** | `users.edit_self` (self-scope) |
| **Permission (admin)** | `users.edit_any` (system-wide) |
| **Request Body** | `{ user_id?: string, display_name?: string, avatar_url?: string \| null }` |
| **Response (200)** | `{ profile: { id, display_name, avatar_url, email_verified, status, created_at, updated_at } }` |
| **Error (401)** | Missing/invalid token |
| **Error (403)** | Permission denied |
| **Error (404)** | Profile not found |
| **Rate Limit** | standard |
| **Audit Required** | Yes — `user.profile_updated` |
| **Lifecycle** | active |

#### `GET /list-users`

| Field | Value |
|-------|-------|
| **Path** | `/list-users` |
| **Method** | `GET` |
| **Classification** | privileged |
| **Auth Model** | Bearer JWT (validated via `authenticateRequest()`) |
| **Permission** | `users.view_all` |
| **Query Params** | `limit` (1-100, default 50), `offset` (default 0), `status` (active\|deactivated), `search` (display name filter) |
| **Response (200)** | `{ users: [...], total: number, limit: number, offset: number }` |
| **Error (401)** | Missing/invalid token |
| **Error (403)** | Permission denied |
| **Rate Limit** | standard |
| **Audit Required** | No |
| **Lifecycle** | active |

#### `POST /deactivate-user`

| Field | Value |
|-------|-------|
| **Path** | `/deactivate-user` |
| **Method** | `POST` |
| **Classification** | privileged, destructive |
| **Auth Model** | Bearer JWT + `requireRecentAuth()` |
| **Permission** | `users.deactivate` |
| **Request Body** | `{ user_id: string, reason?: string }` |
| **Response (200)** | `{ message, user_id, correlationId }` |
| **Error (400)** | Self-deactivation blocked |
| **Error (401)** | Missing/invalid token or session too old |
| **Error (403)** | Permission denied |
| **Error (404)** | User not found |
| **Error (409)** | Already deactivated |
| **Error (500)** | Audit write failed (fail-closed) |
| **Rate Limit** | strict |
| **Audit Required** | Yes — `user.account_deactivated` (HIGH-RISK, fail-closed) |
| **Related events** | `user.account_deactivated`, `auth.session_revoked` |
| **Lifecycle** | active |

#### `POST /reactivate-user`

| Field | Value |
|-------|-------|
| **Path** | `/reactivate-user` |
| **Method** | `POST` |
| **Classification** | privileged |
| **Auth Model** | Bearer JWT + `requireRecentAuth()` |
| **Permission** | `users.reactivate` |
| **Request Body** | `{ user_id: string, reason?: string }` |
| **Response (200)** | `{ message, user_id, correlationId }` |
| **Error (401)** | Missing/invalid token or session too old |
| **Error (403)** | Permission denied |
| **Error (404)** | User not found |
| **Error (409)** | Already active |
| **Error (500)** | Audit write failed (fail-closed) |
| **Rate Limit** | strict |
| **Audit Required** | Yes — `user.account_reactivated` (HIGH-RISK, fail-closed) |
| **Related events** | `user.account_reactivated` |
| **Lifecycle** | active |

---

## Critical Route Summary

### Highest-Risk Routes (Strongest Governance)

| Route | Classification | Permission | Why Critical |
|-------|---------------|------------|--------------|
| `/admin/jobs/emergency` | privileged, destructive | `jobs.emergency` | System-wide job halt |
| `/admin/config` | privileged, destructive | `admin.config` | System behavior changes |
| `/admin/users/:id/roles` | privileged, destructive | `roles.assign` / `roles.revoke` | Privilege escalation risk |
| `/admin/users/:id/deactivate` | privileged, destructive | `users.deactivate` | User access removal |
| `/admin/jobs/deadletter` | privileged, destructive | `jobs.deadletter.manage` | Failure resolution impact |
| `/login` | public | — | Authentication entry point |

### Public Routes

| Route | Purpose |
|-------|---------|
| `/` | Landing page |
| `/login` | Authentication |
| `/signup` | Registration |
| `/forgot-password` | Password recovery |
| `GET /health` | System health |

### Destructive Routes (Require Re-Auth)

| Route | Permission | Re-Auth |
|-------|-----------|---------|
| `/admin/config` | `admin.config` | Yes |
| `/admin/users/:id/roles` | `roles.assign` / `roles.revoke` | Yes |
| `/admin/users/:id/deactivate` | `users.deactivate` | Yes |
| `/admin/users/:id/reactivate` | `users.reactivate` | Yes |
| `/admin/jobs/deadletter` | `jobs.deadletter.manage` | Yes |
| `/admin/jobs/emergency` | `jobs.emergency` | Yes |
| `/settings/security` | `mfa.self_manage`, `session.self_manage` | Yes |

---

## Dependencies

- [Permission Index](permission-index.md) — route access maps to permissions
- [Function Index](function-index.md) — routes use shared functions
- [Event Index](event-index.md) — routes trigger events
- [Change Control Policy](../00-governance/change-control-policy.md) — route changes follow change control
- [Action Tracker](../06-tracking/action-tracker.md) — route changes create entries
- [Risk Register](../06-tracking/risk-register.md) — route-related risks tracked

## Related Documents

- [Auth Module](../04-modules/auth.md)
- [Admin Panel Module](../04-modules/admin-panel.md)
- [User Panel Module](../04-modules/user-panel.md)
- [Architecture Overview](../01-architecture/architecture-overview.md)
