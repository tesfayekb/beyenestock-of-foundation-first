# Stage 3D — Phase 3 Integration Verification & Gate Closure

> **Status:** APPROVED — Executing  
> **Owner:** Developer AI
> **Created:** 2026-04-10  
> **Depends on:** Stages 3A (API Infra), 3B (Audit), 3C (User Mgmt) — all CLOSED  

---

## 1. Purpose

Stage 3D is a **verification-only** stage. Its sole purpose is to close the 6 remaining Phase 3 gate items by producing verifiable evidence that each gate criterion is satisfied.

**This is NOT an implementation stage.** No new features, no refactors, no enhancements.

---

## 2. Scope & Allowed Fix Boundary

### Primary Goal
Verification and gate closure — confirm that all Phase 3 gate requirements are met with evidence.

### Allowed Fixes
Only **minimal gate-closing fixes** directly required by verification findings:
- Missing Zod schema on an endpoint → add schema (Gate 4)
- Inconsistent error response shape → align to shared helper (Gate 5)
- Missing route-index entry → add entry (Gate 6)
- Missing audit call on a mutation → add `logAuditEvent` (Gate 2)

### NOT Allowed
- Feature expansion of any kind
- Refactors beyond what is strictly needed for closure
- Performance optimization
- New shared utilities unless required by a gate fix
- Any work not directly traceable to a gate pass/fail criterion

---

## 3. Execution Order

| Step | Gate | Description |
|------|------|-------------|
| 1 | Gate 6 | Route inventory and reconciliation |
| 2 | Gate 4 + Gate 5 | Input validation coverage + error response standardization |
| 3 | Gate 3 | Sensitive-data audit review |
| 4 | Gate 2 | Audit coverage reconciliation + representative runtime proof |
| 5 | Gate 1 | RBAC / user-management E2E verification |
| 6 | — | Final closure artifacts and tracker/doc updates |

---

## 4. Gate Pass/Fail Contracts

### Gate 6: Route Index Matches Implemented Routes

**Pass only if ALL of:**
- [ ] Every deployed edge function has exactly one route-index entry
- [ ] No route-index entry points to a non-existent endpoint
- [ ] HTTP methods match exactly
- [ ] Classification matches approved tokens only
- [ ] Permission requirements match actual enforcement in code
- [ ] Related docs updated if any mismatch was found and corrected

**Fail if:** Any deployed function lacks a route entry, or any entry describes behavior that does not match the code.

---

### Gate 4: Input Validation Covers All Endpoints

**Pass only if ALL of:**
- [ ] Every endpoint has schema-backed validation (Zod) for query/body/path inputs where applicable
- [ ] Invalid UUID, missing required field, bad enum value, and malformed pagination tested where relevant
- [ ] Validation failures return standardized 400 shape: `{ error, code: "VALIDATION_ERROR", field?, correlation_id }`
- [ ] No endpoint relies on ad hoc parsing without schema or explicit validation helper

**Fail if:** Any endpoint accepts unvalidated user input, or validation errors produce non-standard responses.

---

### Gate 5: Error Responses Standardized

**Pass only if ALL of:**
- [ ] All endpoints use shared response helpers (`apiError` / `apiSuccess` / `createHandler`)
- [ ] All denial/error paths preserve CORS headers
- [ ] Error codes and HTTP statuses are consistent across all endpoints
- [ ] Correlation ID behavior is consistent (present in all error responses)
- [ ] No raw thrown error leaks internal details to the client

**Fail if:** Any endpoint returns an error response that bypasses shared helpers or omits CORS/correlation ID.

---

### Gate 3: No Sensitive Data in Audit Logs

**Pass only if ALL of:**
- [ ] All `logAuditEvent()` call sites reviewed and listed
- [ ] Audit metadata allowlist/denylist rules applied consistently (no passwords, tokens, secrets, session data)
- [ ] DB sample confirms no secrets/passwords/tokens/PII overexposure in `audit_logs.metadata`
- [ ] Any exceptions documented with justification

**Fail if:** Any audit log call passes sensitive data into metadata, or DB sample reveals leaked secrets/PII.

---

### Gate 2: Audit Entries Verified for All Auditable Actions

**Pass only if ALL of:**
- [ ] Every auditable route/function (mutations, auth events, permission changes) cross-referenced against audit expectations in docs AND runtime evidence
- [ ] Representative runtime evidence exists for each class of auditable action
- [ ] Export and query paths (`export-audit-logs`, `query-audit-logs`) are confirmed to work
- [ ] No critical mutation (user lifecycle, role assignment, permission change) lacks audit coverage

**Fail if:** Any mutation that should be audited has no `logAuditEvent` call, or runtime evidence is missing for any action class.

---

### Gate 1: User Management Flows Pass E2E with RBAC

**Pass only if ALL of:**
- [ ] Superadmin allowed on all user-management endpoints (list-users, deactivate, reactivate, get-profile, update-profile)
- [ ] Self-scope user allowed only on own-profile endpoints (get-profile, update-profile with own ID)
- [ ] Regular user denied elevated routes (list-users, deactivate, reactivate on others)
- [ ] No-auth requests denied on all protected endpoints
- [ ] Deactivation → reactivation → profile-update → list flows all tested end-to-end

**Fail if:** Any RBAC check is missing, any unauthorized request succeeds, or any authorized request is incorrectly denied.

---

## 5. Evidence Standard

For **every gate**, the verification report MUST include:

| Evidence Item | Required |
|---------------|----------|
| Files reviewed (with paths) | ✅ |
| Commands/tests/curls run | ✅ |
| Exact results (pass/fail per criterion) | ✅ |
| Mismatches found | ✅ |
| Fixes applied (with file paths and diff summary) | ✅ |
| Residual deferred items, if any | ✅ |

**No gate may be closed on narrative alone.** Every pass claim must have code evidence and, where applicable, runtime/test evidence.

---

## 6. Stop-and-Record Rule

If any gate verification uncovers a non-trivial issue:

1. **Create or update** an action-tracker entry in `docs/06-tracking/action-tracker.md`
2. **Update** `docs/06-tracking/regression-watchlist.md` or `docs/06-tracking/risk-register.md` if warranted
3. **Do NOT** silently patch and continue as if nothing happened
4. **If the issue is too large for Stage 3D** (i.e., requires feature work, schema changes, or multi-file refactoring beyond gate-closing scope):
   - Defer formally in `docs/08-planning/deferred-work-register.md`
   - Document the gate as conditionally passed with the deferral reference
   - Do NOT attempt the fix within Stage 3D

---

## 7. Required Closure Outputs

Stage 3D is NOT complete until all of these artifacts are produced:

- [ ] **Updated `docs/08-planning/master-plan.md`** — all 6 Phase 3 gate checkboxes checked with evidence references (ACT-NNN)
- [ ] **Updated `docs/00-governance/system-state.md`** — Phase 3 marked CLOSED, Stage 3D status updated
- [ ] **Phase 3 closure document** — `docs/08-planning/phase-closures/phase-03-closure.md`
- [ ] **Action-tracker entry** for Stage 3D in `docs/06-tracking/action-tracker.md`
- [ ] **Any risk/watchlist/deferred updates** triggered by gate findings
- [ ] **Updated route-index, event-index, function-index** if any mismatches were corrected

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| Verification reveals unfixable gap | Defer formally per Stop-and-Record Rule (§6) |
| Stage drifts into feature work | Allowed-fix boundary (§2) is a hard constraint |
| Narrative-only closure | Evidence Standard (§5) prevents this |
| Gate criteria ambiguity | Pass/fail contracts (§4) are explicit and checkable |

---

## 9. Approval

This plan requires explicit approval before execution begins.

**Approval status:** PENDING
