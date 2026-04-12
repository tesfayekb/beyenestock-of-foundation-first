# Event Index

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-10 | **Status:** Living Document | **Event Schema Version:** `evt-v1.2`

## Purpose

Central registry and **event contract system** for all events emitted and consumed across modules. This document is the single source of truth for event definitions — it governs schemas, delivery guarantees, versioning, security, and observability for every event in the system.

## Scope

All application events across all modules, including domain, audit, security, system, and infrastructure events.

---

## Enforcement Rule (CRITICAL)

| Rule | Description |
|------|-------------|
| **Completeness** | No event may exist outside this index. Undocumented event = unauthorized event. |
| **Contract governance** | No module may emit or consume an undocumented event. Event contract changes require change control. |
| **Breaking changes** | Breaking event changes (payload removal, type change, semantic change) must follow versioning rules. |
| **Name reuse prohibition** | Event name reuse for different semantics is **prohibited**. |
| **Schema enforcement** | Every event must have a defined payload schema. Unschemaed events are invalid. |
| **Security** | No secrets in event payloads. PII must be minimized or masked. Sensitive events must be access-controlled. |

---

## Event Classification Model

| Classification | Description | Governance Level |
|---------------|-------------|-----------------|
| **security** | Authentication, authorization, access events | Highest — audit mandatory, retention enforced |
| **audit** | State changes requiring audit trail | High — must be logged and retained |
| **system** | Infrastructure, health, lifecycle events | High — must be observable |
| **domain** | Business logic events (user actions, profile changes) | Standard — logged |
| **infrastructure** | Platform, deployment, config events | Medium — tracked |
| **monitoring** | Metrics, health checks, telemetry | Standard — observable |

---

## Event Entry Schema

Every event in the registry must include:

| Field | Description | Required |
|-------|-------------|----------|
| `name` | Fully qualified event name (e.g., `auth.signed_in`) | Yes |
| `version` | Schema version (e.g., `v1`) | Yes |
| `classification` | From classification model above | Yes |
| `severity` | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` | Yes |
| `owner_module` | Module responsible for emitting this event | Yes |
| `consumers` | Modules that consume this event | Yes |
| `description` | What this event represents | Yes |
| `payload_schema` | Required and optional fields with types | Yes |
| `delivery_guarantee` | `at-most-once`, `at-least-once`, `exactly-once` | Yes |
| `ordering` | `strict`, `best-effort`, `none` | Yes |
| `idempotency` | Whether consumers must handle duplicates; idempotency key if applicable | Yes |
| `retry_policy` | Retry behavior on emission failure | Yes |
| `failure_handling` | Fallback, dead-letter, or alert behavior | Yes |
| `observability` | Logging, tracing, monitoring requirements | Yes |
| `related_risks` | Risk register items | If applicable |
| `related_tests` | Tests validating this event | If applicable |
| `action_tracker` | Whether event must create action tracker entry | If applicable |
| `lifecycle` | `active`, `deprecated`, `pending-removal` | Yes |

---

## Event Versioning Strategy

| Rule | Description |
|------|-------------|
| **Version format** | Events are versioned: `event_name.v1`, `event_name.v2` |
| **Non-breaking changes** | Adding optional fields = same version (backward compatible) |
| **Breaking changes** | Removing fields, changing types, or altering semantics = new version |
| **Deprecation** | Old versions must be marked `deprecated` with sunset date |
| **Parallel support** | During transition, both versions must be supported until all consumers migrate |
| **Sunset rule** | Deprecated versions removed after all consumers confirmed migrated |

---

## Delivery Guarantees

| Guarantee | When Used | Example Events |
|-----------|-----------|----------------|
| **At-least-once** | Default for all audit, security, and system events | `auth.signed_in`, `job.failed`, `health.alert_triggered` |
| **At-most-once** | Acceptable for low-severity monitoring/metrics | `audit.logged`, `job.queued` |
| **Exactly-once** | Critical state changes where duplication causes harm | `job.kill_switch_activated` |

**Rule:** All `CRITICAL` and `HIGH` severity events must be `at-least-once` minimum.

---

## Ordering and Idempotency Rules

### Ordering

| Requirement | Applies To | Description |
|------------|-----------|-------------|
| **Strict** | Auth flows, job lifecycle | Events must be processed in emission order |
| **Best-effort** | Audit, admin events | Order preserved where possible |
| **None** | Monitoring, metrics | No ordering dependency |

### Idempotency

| Rule | Description |
|------|-------------|
| **Consumer responsibility** | All consumers must handle duplicate delivery gracefully |
| **Idempotency key** | Critical events must include `event_id` (UUID) for deduplication |
| **Payload stability** | Re-delivery of same event must produce same payload |

---

## Event Failure Handling

| Scenario | Behavior |
|----------|----------|
| **Emission failure (critical)** | Retry up to 3× with exponential backoff → alert if still failing |
| **Emission failure (non-critical)** | Log warning, continue operation |
| **Consumer failure** | Retry per consumer policy → dead-letter after max retries |
| **Dead-letter** | Dead-lettered events must be visible in admin panel and generate alert |
| **Critical event loss** | Must trigger `health.alert_triggered` and action tracker entry |

---

## Event Replay / Reprocessing Governance

| Rule | Description |
|------|-------------|
| **Replayable events** | Job lifecycle events and domain state-change events must support replay from dead-letter or archive |
| **Idempotency** | Replayed events must produce the same outcome as original — consumers must be idempotent |
| **Audit** | Every replay must generate `job.replayed` event and action tracker entry with: who replayed, reason, original event timestamp |
| **Authorization** | Replay requires operator or admin role — no automated replay without explicit approval |
| **Scope control** | Replay must target specific events — bulk replay requires Lead approval |
| **Non-replayable** | Security events (`auth.*`, `rbac.*`) are **not replayable** — they are historical records only |

---

## Event Sampling Strategy

| Rule | Description |
|------|-------------|
| **Never sample** | `security`, `audit`, and `CRITICAL`/`HIGH` severity events must **never** be sampled — 100% capture required |
| **Sampling allowed** | `monitoring` and `infrastructure` classified events with `LOW` severity may be sampled under load |
| **Sample rate** | Default sample rate: 10% for eligible events; adjustable per event type |
| **Metadata preservation** | Sampled events must still contribute to aggregate counters (total emitted vs. sampled stored) |
| **Config** | Sampling rates are config-governed — changes follow Config Index rules |

---

## Event Backpressure Handling

| Scenario | Behavior |
|----------|----------|
| **System overloaded** | Non-critical events (`LOW` severity, `monitoring` class) are buffered or dropped first |
| **Critical preservation** | `security`, `audit`, and `CRITICAL` severity events are **never** dropped — they use reserved capacity |
| **Backpressure signal** | When buffer exceeds 80% capacity, emit `health.alert_triggered` with `alert_type: event_backpressure` |
| **Degradation order** | Drop order: `monitoring` → `infrastructure` → `domain` → `system` → never: `audit`/`security` |
| **Recovery** | After pressure clears, resume normal processing; log gap period for audit |

---

## Event Contract Compatibility Testing

| Rule | Description |
|------|-------------|
| **Version compatibility** | New event versions must be tested against all existing consumers before deployment |
| **Backward compatibility** | New versions adding optional fields must not break consumers expecting the previous schema |
| **Breaking change gate** | Breaking changes (field removal, type change) must: pass consumer migration tests, have all consumers updated, be approved via change control |
| **CI integration** | Event contract tests must run in CI pipeline — contract violation blocks deployment |
| **Test coverage** | Every versioned event must have a contract compatibility test |

---

## Event Dependency Visualization

| Rule | Description |
|------|-------------|
| **Event flow graph** | System must maintain a visual dependency graph showing: emitters → events → consumers → downstream effects |
| **Update requirement** | Graph must be updated when events are added, modified, or deprecated |
| **Debugging utility** | Graph must be usable for: root cause analysis, impact assessment of event changes, onboarding |
| **Format** | Maintained as Mermaid diagram or equivalent machine-readable format |
| **Review** | Graph reviewed quarterly alongside event registry review |

---

## Event Security Rules

| Rule | Description |
|------|-------------|
| **No secrets** | Event payloads must NEVER contain secrets, tokens, or credentials |
| **PII minimization** | Include only necessary PII; use user_id references over personal data |
| **Masking** | IP addresses and device info may be included but must be masked in logs |
| **Access control** | Security-classified events must be access-controlled — only authorized consumers |
| **Payload sanitization** | All event payloads must be sanitized before emission |

---

## Observability Requirements

| Requirement | Description |
|-------------|-------------|
| **Logging** | Every event emission must be logged with timestamp, event name, and correlation_id |
| **Tracing** | Events must carry `correlation_id` for end-to-end request tracing |
| **Monitoring** | Event emission rates, failure rates, and latency must be observable in dashboards |
| **Alerting** | Anomalous patterns (spike, drop-off, failure burst) must trigger alerts |
| **Metrics** | Per-event counters: emitted, consumed, failed, dead-lettered |

---

## Action Tracker Integration

Events that must automatically create action tracker entries:

| Event | Reason |
|-------|--------|
| `job.dead_lettered` | Requires operator investigation |
| `job.poison_detected` | Systematic failure requiring fix |
| `job.kill_switch_activated` | Emergency action requiring follow-up |
| `job.slo_breach` | SLO violation requiring review |
| `health.alert_triggered` | System health event requiring response |
| `health.monitoring_failed` | Monitoring blind spot requiring immediate fix |
| `admin.config_changed` | Config change requiring audit trail |
| `audit.write_failed` | Audit integrity failure requiring investigation |

---

## Risk Register Mapping

| Event Pattern | Risk | Description |
|--------------|------|-------------|
| `auth.failed_attempt` spike | RISK-001 (credential compromise) | Brute-force indicator |
| `auth.permission_denied` spike | RISK-002 (privilege escalation) | Unauthorized access attempts |
| `job.failed` / `job.dead_lettered` | RISK-007 (job failure cascade) | System reliability risk |
| `health.alert_triggered` | RISK-004 (infrastructure failure) | System health degradation |
| `api.rate_limited` spike | RISK-005 (DoS) | Potential attack |

---

## Event Lifecycle

| State | Description | Action Required |
|-------|-------------|-----------------|
| **Active** | In use, governed by this index | Standard governance |
| **Deprecated** | Scheduled for removal; consumers must migrate | Sunset date + migration path documented |
| **Pending removal** | Will be removed in next release | All consumers confirmed migrated |

---

## Testing Requirements

| Test Type | Applies To | Description |
|-----------|-----------|-------------|
| **Emission tests** | All events | Verify event is emitted with correct payload on trigger |
| **Payload validation tests** | All events | Verify payload matches schema, types, required fields |
| **Consumer tests** | All consumed events | Verify each consumer handles event correctly |
| **Idempotency tests** | Critical events | Verify duplicate delivery is handled gracefully |
| **Failure tests** | Critical events | Verify retry and dead-letter behavior |
| **Security tests** | Security-classified events | Verify no secrets/PII leakage in payloads |

**Rule:** Every `CRITICAL` or `HIGH` severity event must have emission, payload, and consumer tests.

---

## Event Flow Mapping

Key event chains showing upstream triggers and downstream effects:

| Flow | Chain | Ordering |
|------|-------|----------|
| **Login** | `auth.signed_in` → `audit.logged` → monitoring metrics | Strict |
| **Failed login** | `auth.failed_attempt` → `audit.logged` → `health.alert_triggered` (if threshold) | Strict |
| **MFA recovery** | `auth.mfa_recovered` → `audit.logged` → admin notification (security review) | Strict |
| **Session revoke** | `auth.session_revoked` → `audit.logged` → session cleanup | Strict |
| **Role change** | `rbac.role_assigned` / `rbac.role_revoked` → `audit.logged` → admin notification | Best-effort |
| **Role lifecycle** | `rbac.role_created` / `rbac.role_deleted` → `audit.logged` → admin notification | Strict |
| **Permission change** | `rbac.permission_assigned` / `rbac.permission_revoked` → `audit.logged` | Best-effort |
| **Job failure** | `job.failed` → `job.retry_scheduled` → `job.dead_lettered` (if exhausted) → `health.alert_triggered` | Strict |
| **Kill switch** | `job.kill_switch_activated` → `audit.logged` → `health.alert_triggered` → admin notification | Strict |
| **Config change** | `admin.config_changed` → `audit.logged` → `health.status_changed` (if applicable) | Best-effort |
| **Audit failure** | `audit.write_failed` → `health.alert_triggered` → admin notification | Strict |
| **Monitor failure** | `health.monitoring_failed` → independent alert channel → admin notification | Strict |

---

## Event Registry

### Authentication Events

#### `auth.signed_up` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | HIGH |
| **Owner module** | auth |
| **Consumers** | audit-logging, user-management |
| **Description** | New user account created |
| **Payload schema** | `{ user_id: uuid, email: string (masked), timestamp: datetime, ip_address: string, method: enum[email, oauth] }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id (UUID) |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert on failure; must not be lost |
| **Observability** | Logged, traced (correlation_id), counted |
| **Related risks** | RISK-001 |
| **Related tests** | Signup emission test, payload validation test |
| **Lifecycle** | active |

#### `auth.signed_in` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | MEDIUM |
| **Owner module** | auth |
| **Consumers** | audit-logging |
| **Description** | User successfully authenticated |
| **Payload schema** | `{ user_id: uuid, timestamp: datetime, ip_address: string, device: string, method: enum[password, oauth, mfa] }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id (UUID) |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Log warning on failure |
| **Observability** | Logged, traced, counted |
| **Related tests** | Login emission test, audit consumer test |
| **Lifecycle** | active |

#### `auth.signed_out` — v1

| Field | Value |
|-------|-------|
| **Classification** | audit |
| **Severity** | LOW |
| **Owner module** | auth |
| **Consumers** | audit-logging |
| **Description** | User signed out |
| **Payload schema** | `{ user_id: uuid, timestamp: datetime, session_id: string }` |
| **Delivery guarantee** | at-most-once |
| **Ordering** | none |
| **Idempotency** | event_id |
| **Retry policy** | No retry |
| **Failure handling** | Log only |
| **Observability** | Logged |
| **Lifecycle** | active |

#### `auth.password_reset` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | MEDIUM |
| **Owner module** | auth |
| **Consumers** | audit-logging |
| **Description** | Password reset requested or completed |
| **Payload schema** | `{ user_id: uuid, timestamp: datetime, ip_address: string, stage: enum[requested, completed] }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert on failure |
| **Observability** | Logged, traced |
| **Related risks** | RISK-001 |
| **Lifecycle** | active |

#### `auth.mfa_enrolled` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | MEDIUM |
| **Owner module** | auth |
| **Consumers** | audit-logging |
| **Description** | MFA enrolled for user |
| **Payload schema** | `{ user_id: uuid, timestamp: datetime, mfa_type: enum[totp, sms] }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | best-effort |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Log warning |
| **Observability** | Logged, traced |
| **Lifecycle** | active |

#### `auth.failed_attempt` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | HIGH |
| **Owner module** | auth |
| **Consumers** | audit-logging, health-monitoring |
| **Description** | Failed authentication attempt |
| **Payload schema** | `{ user_id: uuid | null, timestamp: datetime, ip_address: string, reason: enum[invalid_password, account_locked, mfa_failed, unknown_user] }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert — must not be lost (security signal) |
| **Observability** | Logged, traced, rate-monitored, anomaly detection |
| **Related risks** | RISK-001 (credential compromise) |
| **Related tests** | Failed attempt emission, threshold alerting test |
| **Lifecycle** | active |

#### `auth.permission_denied` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | HIGH |
| **Owner module** | api (handler.ts) |
| **Consumers** | audit-logging, health-monitoring |
| **Description** | Authorization denial — any PermissionDeniedError intercepted by handler |
| **Payload schema** | `{ actor_id: uuid | null, action: "auth.permission_denied", target_type: "permission", metadata: { permission_key: string, reason: enum[missing_permission, self_scope_violation, recent_auth_required], endpoint: string, correlation_id: string, actor_known: boolean } }` |
| **Delivery guarantee** | at-most-once (fire-and-forget — must not block 403 response) |
| **Ordering** | none |
| **Idempotency** | correlation_id |
| **Retry policy** | No retry — fire-and-forget |
| **Failure handling** | Console error only; 403 response always returned regardless of audit outcome |
| **Observability** | Logged, traced (correlation_id), spike detection recommended |
| **Related risks** | RISK-002 (privilege escalation), RISK-001 (credential compromise) |
| **Related tests** | Denial audit emission test, payload validation test |
| **Lifecycle** | active |

#### `auth.mfa_recovered` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | HIGH |
| **Owner module** | auth |
| **Consumers** | audit-logging, health-monitoring |
| **Description** | MFA recovered via backup method after primary MFA unavailable |
| **Payload schema** | `{ user_id: uuid, timestamp: datetime, recovery_method: enum[backup_code, admin_override, support_reset], ip_address: string }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id (UUID) |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert on failure — security event must not be lost |
| **Observability** | Logged, traced, rate-monitored, anomaly detection |
| **Related risks** | RISK-001 (credential compromise) |
| **Related tests** | MFA recovery emission test, payload validation test |
| **Lifecycle** | active |

#### `auth.session_revoked` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | HIGH |
| **Owner module** | auth |
| **Consumers** | audit-logging, health-monitoring |
| **Description** | User session forcibly revoked (by user, admin, or system) |
| **Payload schema** | `{ user_id: uuid, session_id: string, revoked_by: uuid, timestamp: datetime, reason: enum[user_request, admin_action, security_policy, timeout] }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id (UUID) |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert on failure — session revocation is security-critical |
| **Observability** | Logged, traced |
| **Related tests** | Session revocation emission test, audit consumer test |
| **Lifecycle** | active |

### RBAC Events

#### `rbac.role_assigned` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | HIGH |
| **Owner module** | rbac |
| **Consumers** | audit-logging |
| **Description** | Role assigned to user |
| **Payload schema** | `{ user_id: uuid, role_key: string, role_id: uuid, assigned_by: uuid, timestamp: datetime }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert on failure |
| **Observability** | Logged, traced |
| **Related risks** | RISK-002 (privilege escalation) |
| **Related tests** | Role assignment emission, audit consumer test |
| **Lifecycle** | active |

#### `rbac.role_revoked` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | HIGH |
| **Owner module** | rbac |
| **Consumers** | audit-logging |
| **Description** | Role revoked from user |
| **Payload schema** | `{ user_id: uuid, role_key: string, role_id: uuid, revoked_by: uuid, timestamp: datetime, reason: string }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert on failure |
| **Observability** | Logged, traced |
| **Related risks** | RISK-002 |
| **Lifecycle** | active |

#### `rbac.role_created` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | HIGH |
| **Owner module** | rbac |
| **Consumers** | audit-logging |
| **Description** | New dynamic role created in the RBAC system |
| **Payload schema** | `{ role_name: string, created_by: uuid, timestamp: datetime, permissions: string[] }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert on failure |
| **Observability** | Logged, traced |
| **Related permissions** | `roles.create` |
| **Related risks** | RISK-002 (privilege escalation via new role) |
| **Related tests** | Role creation event emission test |
| **Lifecycle** | active |

#### `rbac.role_updated` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | HIGH |
| **Owner module** | rbac |
| **Consumers** | audit-logging |
| **Description** | Role name or description updated. Key is immutable and cannot be changed. |
| **Payload schema** | `{ role_key: string, changes: { name?: string, description?: string }, previous: { name?: string, description?: string }, updated_by: uuid, timestamp: datetime }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert on failure |
| **Observability** | Logged, traced |
| **Related permissions** | `roles.edit` |
| **Related risks** | RISK-002 |
| **Related tests** | Role update event emission test |
| **Lifecycle** | active |

#### `rbac.role_deleted` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | HIGH |
| **Owner module** | rbac |
| **Consumers** | audit-logging |
| **Description** | Dynamic role deleted from the RBAC system. Base roles cannot be deleted. |
| **Payload schema** | `{ role_name: string, deleted_by: uuid, timestamp: datetime, affected_users: integer }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert on failure |
| **Observability** | Logged, traced |
| **Related permissions** | `roles.delete` |
| **Related risks** | RISK-002 (orphaned users after role deletion) |
| **Related tests** | Role deletion event emission test, base role protection test |
| **Lifecycle** | active |

#### `rbac.permission_denied` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | MEDIUM |
| **Owner module** | rbac |
| **Consumers** | audit-logging, health-monitoring |
| **Description** | Permission check failed |
| **Payload schema** | `{ user_id: uuid, permission: string, resource: string, timestamp: datetime, ip_address: string }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | best-effort |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Log warning; alert on spike |
| **Observability** | Logged, traced, rate-monitored |
| **Related risks** | RISK-002 (privilege escalation) |
| **Lifecycle** | active |

#### `rbac.permission_assigned` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | HIGH |
| **Owner module** | rbac |
| **Consumers** | audit-logging |
| **Description** | Permission granted to user |
| **Payload schema** | `{ role_id: uuid, permission_key: string, permission_id: uuid, assigned_by: uuid, timestamp: datetime }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert on failure |
| **Observability** | Logged, traced |
| **Related risks** | RISK-002 (privilege escalation) |
| **Related tests** | Permission assignment emission, audit consumer test |
| **Lifecycle** | active |

#### `rbac.permission_revoked` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | HIGH |
| **Owner module** | rbac |
| **Consumers** | audit-logging |
| **Description** | Permission revoked from user |
| **Payload schema** | `{ role_id: uuid, permission_key: string, permission_id: uuid, revoked_by: uuid, timestamp: datetime, reason: string }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert on failure |
| **Observability** | Logged, traced |
| **Related risks** | RISK-002 (privilege escalation) |
| **Related tests** | Permission revocation emission, audit consumer test |
| **Lifecycle** | active |

### User Management Events

#### `user.profile_updated` — v1

| Field | Value |
|-------|-------|
| **Classification** | domain |
| **Severity** | LOW |
| **Owner module** | user-management |
| **Consumers** | audit-logging |
| **Description** | User profile data changed |
| **Payload schema** | `{ user_id: uuid, timestamp: datetime, fields_changed: string[] }` |
| **Delivery guarantee** | at-most-once |
| **Ordering** | none |
| **Idempotency** | event_id |
| **Retry policy** | No retry |
| **Failure handling** | Log only |
| **Observability** | Logged |
| **Lifecycle** | active |

#### `user.account_deactivated` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | MEDIUM |
| **Owner module** | user-management |
| **Consumers** | audit-logging, admin-panel |
| **Description** | User account deactivated |
| **Payload schema** | `{ user_id: uuid, timestamp: datetime, deactivated_by: uuid, reason: string }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert on failure |
| **Observability** | Logged, traced |
| **Lifecycle** | active |

#### `user.account_reactivated` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | MEDIUM |
| **Owner module** | user-management |
| **Consumers** | audit-logging, admin-panel |
| **Description** | User account reactivated |
| **Payload schema** | `{ user_id: uuid, timestamp: datetime, reactivated_by: uuid, reason: string }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert on failure |
| **Observability** | Logged, traced |
| **Lifecycle** | active |

#### `user.deactivation_rolled_back` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | MEDIUM |
| **Owner module** | user-management |
| **Consumers** | audit-logging, admin-panel |
| **Description** | User deactivation rolled back after downstream failure (e.g., session revocation failed) |
| **Payload schema** | `{ user_id: uuid, timestamp: datetime, reason: string, rollback_success: boolean, original_reason: string }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert on failure — rollback events are safety-critical |
| **Observability** | Logged, traced |
| **Related risks** | RISK-004 (infrastructure failure) |
| **Lifecycle** | active |

### Admin Events

#### `admin.config_changed` — v1

| Field | Value |
|-------|-------|
| **Classification** | audit |
| **Severity** | HIGH |
| **Owner module** | admin-panel |
| **Consumers** | audit-logging, health-monitoring |
| **Description** | System configuration changed via admin panel |
| **Payload schema** | `{ config_name: string, before_value: string, after_value: string, changed_by: uuid, timestamp: datetime, change_id: string }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert — config changes must be audited |
| **Observability** | Logged, traced |
| **Action tracker** | Yes — creates entry |
| **Lifecycle** | active |

#### `admin.user_action` — v1

| Field | Value |
|-------|-------|
| **Classification** | audit |
| **Severity** | MEDIUM |
| **Owner module** | admin-panel |
| **Consumers** | audit-logging |
| **Description** | Admin performed action on user account |
| **Payload schema** | `{ admin_id: uuid, target_user_id: uuid, action: string, timestamp: datetime, details: string }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | best-effort |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Log warning |
| **Observability** | Logged, traced |
| **Lifecycle** | active |

### User Panel Events

#### `user_panel.settings_changed` — v1

| Field | Value |
|-------|-------|
| **Classification** | domain |
| **Severity** | LOW |
| **Owner module** | user-panel |
| **Consumers** | audit-logging |
| **Description** | User changed their settings |
| **Payload schema** | `{ user_id: uuid, timestamp: datetime, settings_changed: string[] }` |
| **Delivery guarantee** | at-most-once |
| **Ordering** | none |
| **Idempotency** | event_id |
| **Retry policy** | No retry |
| **Failure handling** | Log only |
| **Observability** | Logged |
| **Lifecycle** | active |

> **Note:** Session revocation events are emitted as `auth.session_revoked` (auth module owns session lifecycle). User panel triggers the action but does not own the event.

#### `user_panel.mfa_updated` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | MEDIUM |
| **Owner module** | user-panel |
| **Consumers** | audit-logging |
| **Description** | User changed their own MFA settings (enable, disable, reconfigure) |
| **Payload schema** | `{ user_id: uuid, timestamp: datetime, action: enum[enabled, disabled, reconfigured], mfa_type: enum[totp, sms] }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert on failure — MFA changes are security-relevant |
| **Observability** | Logged, traced |
| **Related risks** | RISK-001 (credential compromise — MFA downgrade) |
| **Related tests** | MFA update emission test, payload validation test |
| **Lifecycle** | active |

### Audit Events

#### `audit.logged` — v1

| Field | Value |
|-------|-------|
| **Classification** | infrastructure |
| **Severity** | LOW |
| **Owner module** | audit-logging |
| **Consumers** | health-monitoring |
| **Description** | Audit entry recorded (meta-event) |
| **Payload schema** | `{ audit_id: uuid, source_event: string, timestamp: datetime }` |
| **Delivery guarantee** | at-most-once |
| **Ordering** | none |
| **Idempotency** | audit_id |
| **Retry policy** | No retry |
| **Failure handling** | Log only |
| **Observability** | Counted (metrics) |
| **Lifecycle** | active |

#### `audit.write_failed` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | HIGH |
| **Owner module** | audit-logging |
| **Consumers** | health-monitoring, admin-panel |
| **Description** | Audit log write operation failed — critical integrity risk |
| **Payload schema** | `{ source_event: string, timestamp: datetime, error: string, retry_count: integer, correlation_id: string }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Must not be lost — multi-channel alert; fallback to secondary log store |
| **Observability** | Logged, traced, alerted |
| **Action tracker** | Yes — creates entry (audit integrity failure) |
| **Related risks** | RISK-004 (infrastructure failure) |
| **Related tests** | Audit write failure emission, fallback store test |
| **Lifecycle** | active |

#### `audit.exported` — v1

| Field | Value |
|-------|-------|
| **Classification** | audit |
| **Severity** | MEDIUM |
| **Owner module** | audit-logging |
| **Consumers** | audit-logging (self-audit), admin-panel |
| **Description** | Audit logs exported by authorized user — records who exported what filters |
| **Payload schema** | `{ actor_id: uuid, timestamp: datetime, filters: { action?: string, actor_id?: string, target_type?: string, date_from?: string, date_to?: string }, max_rows: integer }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | best-effort |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Log warning — export itself succeeds regardless |
| **Observability** | Logged, traced |
| **Lifecycle** | active |

### Health Monitoring Events

#### `health.alert_triggered` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | CRITICAL |
| **Owner module** | health-monitoring |
| **Consumers** | admin notification |
| **Description** | Health alert threshold breached |
| **Payload schema** | `{ alert_type: string, metric: string, threshold: number, actual_value: number, timestamp: datetime, severity: enum[warning, critical] }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Must not be lost — fallback to secondary notification channel |
| **Observability** | Logged, traced, alerted |
| **Action tracker** | Yes — creates entry |
| **Related risks** | RISK-004 (infrastructure failure) |
| **Lifecycle** | active |

#### `health.status_changed` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | MEDIUM |
| **Owner module** | health-monitoring |
| **Consumers** | audit-logging |
| **Description** | System health status changed |
| **Payload schema** | `{ component: string, previous_status: enum[healthy, degraded, unhealthy], new_status: enum[healthy, degraded, unhealthy], timestamp: datetime }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert on failure |
| **Observability** | Logged, traced |
| **Lifecycle** | active |

#### `health.monitoring_failed` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | HIGH |
| **Owner module** | health-monitoring |
| **Consumers** | admin-panel |
| **Description** | Health monitoring system itself failed — creates observability blind spot |
| **Payload schema** | `{ component: string, timestamp: datetime, error: string, last_successful_check: datetime, affected_monitors: string[] }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff + fallback notification |
| **Failure handling** | Must not be lost — multi-channel alert (monitoring the monitor) |
| **Observability** | Logged, alerted via independent channel |
| **Action tracker** | Yes — creates entry (monitoring blind spot) |
| **Related risks** | RISK-004 (infrastructure failure) |
| **Related tests** | Monitor failure emission, independent alert channel test |
| **Lifecycle** | active |

### API Events

#### `api.error` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | MEDIUM |
| **Owner module** | api |
| **Consumers** | health-monitoring |
| **Description** | API error occurred |
| **Payload schema** | `{ route: string, method: string, status_code: integer, error_type: string, timestamp: datetime, correlation_id: string }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | best-effort |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Log warning |
| **Observability** | Logged, traced, rate-monitored |
| **Lifecycle** | active |

#### `api.rate_limited` — v1

| Field | Value |
|-------|-------|
| **Classification** | security |
| **Severity** | LOW |
| **Owner module** | api |
| **Consumers** | audit-logging |
| **Description** | Request rate-limited |
| **Payload schema** | `{ ip_address: string, route: string, timestamp: datetime, limit: integer, window: string }` |
| **Delivery guarantee** | at-most-once |
| **Ordering** | none |
| **Idempotency** | event_id |
| **Retry policy** | No retry |
| **Failure handling** | Log only |
| **Observability** | Logged, rate-monitored |
| **Related risks** | RISK-005 (DoS) |
| **Lifecycle** | active |

### Job Events

#### `job.started` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | LOW |
| **Owner module** | jobs-and-scheduler |
| **Consumers** | audit-logging |
| **Description** | Job execution started |
| **Payload schema** | `{ job_id: uuid, job_type: string, timestamp: datetime, attempt: integer }` |
| **Delivery guarantee** | at-most-once |
| **Ordering** | strict |
| **Idempotency** | job_id + attempt |
| **Retry policy** | No retry |
| **Failure handling** | Log only |
| **Observability** | Logged, traced |
| **Lifecycle** | active |

#### `job.completed` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | LOW |
| **Owner module** | jobs-and-scheduler |
| **Consumers** | audit-logging |
| **Description** | Job completed successfully |
| **Payload schema** | `{ job_id: uuid, job_type: string, timestamp: datetime, duration_ms: integer, attempt: integer }` |
| **Delivery guarantee** | at-most-once |
| **Ordering** | strict |
| **Idempotency** | job_id + attempt |
| **Retry policy** | No retry |
| **Failure handling** | Log only |
| **Observability** | Logged, traced, duration-monitored |
| **Lifecycle** | active |

#### `job.failed` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | HIGH |
| **Owner module** | jobs-and-scheduler |
| **Consumers** | audit-logging, health-monitoring |
| **Description** | Job execution failed |
| **Payload schema** | `{ job_id: uuid, job_type: string, timestamp: datetime, attempt: integer, error: string, will_retry: boolean }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert; escalate if repeated |
| **Observability** | Logged, traced, alerted |
| **Related risks** | RISK-007 (job failure cascade) |
| **Lifecycle** | active |

#### `job.queued` — v1

| Field | Value |
|-------|-------|
| **Classification** | monitoring |
| **Severity** | LOW |
| **Owner module** | jobs-and-scheduler |
| **Consumers** | health-monitoring |
| **Description** | Job added to queue |
| **Payload schema** | `{ job_id: uuid, job_type: string, timestamp: datetime, priority: integer }` |
| **Delivery guarantee** | at-most-once |
| **Ordering** | none |
| **Idempotency** | job_id |
| **Retry policy** | No retry |
| **Failure handling** | Log only |
| **Observability** | Counted (queue depth metric) |
| **Lifecycle** | active |

#### `job.retry_scheduled` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | MEDIUM |
| **Owner module** | jobs-and-scheduler |
| **Consumers** | audit-logging, health-monitoring |
| **Description** | Job retry scheduled after failure |
| **Payload schema** | `{ job_id: uuid, job_type: string, timestamp: datetime, attempt: integer, next_retry_at: datetime, backoff_seconds: integer }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Log warning |
| **Observability** | Logged, traced |
| **Lifecycle** | active |

#### `job.dead_lettered` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | CRITICAL |
| **Owner module** | jobs-and-scheduler |
| **Consumers** | audit-logging, health-monitoring, admin-panel |
| **Description** | Job moved to dead-letter queue after exhausting retries |
| **Payload schema** | `{ job_id: uuid, job_type: string, timestamp: datetime, total_attempts: integer, last_error: string, original_payload: object }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Must not be lost — alert + action tracker entry |
| **Observability** | Logged, traced, alerted |
| **Action tracker** | Yes — creates entry |
| **Related risks** | RISK-007 |
| **Lifecycle** | active |

#### `job.paused` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | MEDIUM |
| **Owner module** | jobs-and-scheduler |
| **Consumers** | audit-logging |
| **Description** | Job execution paused |
| **Payload schema** | `{ job_id: uuid, job_type: string, timestamp: datetime, paused_by: uuid, reason: string }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Log warning |
| **Observability** | Logged, traced |
| **Lifecycle** | active |

#### `job.cancelled` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | MEDIUM |
| **Owner module** | jobs-and-scheduler |
| **Consumers** | audit-logging |
| **Description** | Job execution cancelled |
| **Payload schema** | `{ job_id: uuid, job_type: string, timestamp: datetime, cancelled_by: uuid, reason: string }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Log warning |
| **Observability** | Logged, traced |
| **Lifecycle** | active |

#### `job.poison_detected` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | CRITICAL |
| **Owner module** | jobs-and-scheduler |
| **Consumers** | audit-logging, health-monitoring, admin-panel |
| **Description** | Poison message detected — systematic failure pattern |
| **Payload schema** | `{ job_id: uuid, job_type: string, timestamp: datetime, failure_count: integer, pattern: string, quarantined: boolean }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Must not be lost — alert + action tracker entry |
| **Observability** | Logged, traced, alerted |
| **Action tracker** | Yes — creates entry |
| **Related risks** | RISK-007 |
| **Lifecycle** | active |

#### `job.replayed` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | MEDIUM |
| **Owner module** | jobs-and-scheduler |
| **Consumers** | audit-logging |
| **Description** | Job replayed from dead-letter queue |
| **Payload schema** | `{ job_id: uuid, job_type: string, timestamp: datetime, replayed_by: uuid, original_dead_letter_at: datetime }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Log warning |
| **Observability** | Logged, traced |
| **Lifecycle** | active |

#### `job.slo_breach` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | HIGH |
| **Owner module** | jobs-and-scheduler |
| **Consumers** | health-monitoring, admin-panel |
| **Description** | Job SLO target breached |
| **Payload schema** | `{ job_id: uuid, job_type: string, timestamp: datetime, slo_target_ms: integer, actual_ms: integer, breach_ratio: float }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | best-effort |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert |
| **Observability** | Logged, traced, alerted |
| **Action tracker** | Yes — creates entry |
| **Related risks** | RISK-007 |
| **Lifecycle** | active |

#### `job.kill_switch_activated` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | CRITICAL |
| **Owner module** | jobs-and-scheduler |
| **Consumers** | audit-logging, health-monitoring, admin-panel |
| **Description** | Emergency kill switch activated — all jobs halted |
| **Payload schema** | `{ timestamp: datetime, activated_by: uuid, reason: string, scope: enum[all, job_type, specific_job], affected_jobs: string[] }` |
| **Delivery guarantee** | exactly-once |
| **Ordering** | strict |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff + fallback notification |
| **Failure handling** | Must not be lost — multi-channel alert |
| **Observability** | Logged, traced, alerted, dashboard-visible |
| **Action tracker** | Yes — creates entry |
| **Related risks** | RISK-007 |
| **Lifecycle** | active |

#### `job.schedule_missed` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | MEDIUM |
| **Owner module** | jobs-and-scheduler |
| **Consumers** | health-monitoring |
| **Description** | Scheduled job missed its execution window |
| **Payload schema** | `{ job_type: string, scheduled_at: datetime, detected_at: datetime, delay_seconds: integer }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | best-effort |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Alert |
| **Observability** | Logged, alerted |
| **Lifecycle** | active |

#### `job.resource_budget_exceeded` — v1

| Field | Value |
|-------|-------|
| **Classification** | system |
| **Severity** | MEDIUM |
| **Owner module** | jobs-and-scheduler |
| **Consumers** | health-monitoring |
| **Description** | Job exceeded allocated resource budget |
| **Payload schema** | `{ job_id: uuid, job_type: string, timestamp: datetime, resource: enum[cpu, memory, time], budget: number, actual: number }` |
| **Delivery guarantee** | at-least-once |
| **Ordering** | best-effort |
| **Idempotency** | event_id |
| **Retry policy** | 3× exponential backoff |
| **Failure handling** | Log warning |
| **Observability** | Logged, monitored |
| **Lifecycle** | active |

---

## Dependencies

- [Dependency Map](../01-architecture/dependency-map.md)
- [Action Tracker](../06-tracking/action-tracker.md) — critical events create entries
- [Risk Register](../06-tracking/risk-register.md) — event patterns linked to risks
- [Change Control Policy](../00-governance/change-control-policy.md) — event contract changes follow change control

## Related Documents

- Module docs in `docs/04-modules/`
- [Config Index](config-index.md)
- [Function Index](function-index.md)
- [Route Index](route-index.md)
- [Permission Index](permission-index.md)
