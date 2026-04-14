# Phase Closure: PLAN-INVITE-001 — User Onboarding & Invitations

> **Plan ID:** PLAN-INVITE-001  
> **DW Reference:** DW-035  
> **Closure Date:** 2026-04-14  
> **Plan Baseline:** v11.0  

---

## Summary

Implemented a complete user onboarding system with three modes: open signup, invite-only, and hybrid (both enabled). All 6 phases completed across schema, permissions, pre-signup hook, invitation management edge functions, admin UI, signup page update, regression tests, and documentation.

---

## Phase Completion Evidence

### Phase 1: Schema & Permissions
- `system_config` table created with RLS (authenticated read)
- `invitations` table created with validation trigger, indexes, and partial unique index on pending email
- `users.invite` and `users.invite.manage` permissions added to seed, `permission-deps.json`, and `_shared/permission-deps.ts`
- `accept_invitation_on_confirm` trigger: marks invitation accepted, assigns role, emits audit event — all atomic with user confirmation

### Phase 2: Pre-Signup Hook & Config Functions
- `auth-hook-pre-signup`: Reads `onboarding_mode` from `system_config`. Rejects signup when disabled. Fails open on error.
- `get-system-config`: Public endpoint returning `{ signup_enabled, invite_enabled, followup_days, max_followups }`
- `update-system-config`: SUPERADMIN_ONLY. Validates at least one mode is true. Emits `system.config_changed` audit event.
- Manual deployment step documented: hook registration in Supabase Dashboard

### Phase 3: Invitation Management Edge Functions
- `invite-user`: Single invite with existing-user detection (409), SHA-256 token hashing, dynamic expiry from followup config
- `invite-users-bulk`: Up to 50 invitations, sequential processing, per-entry error isolation
- `list-invitations`: Paginated with status filter, resolves `invited_by` → display name, `role_id` → role name
- `revoke-invitation`: Marks revoked with audit trail
- `resend-invitation`: New token, reset TTL, rate limited 3/email/24h
- `send-signup-nudge`: Signup reminder when invite system disabled, rate limited 3/email/24h

### Phase 4: Admin UI
- `AdminOnboardingPage` with 4 sections: onboarding mode switches, single invite, bulk invite, invitations table
- 5 components: `OnboardingModeCard`, `InviteUserDialog`, `BulkInviteDialog`, `InvitationStatusBadge`, `InvitationsTable`
- 3 hooks: `useSystemConfig`, `useInvitations`, `useInviteUser`
- Route `/admin/onboarding` added with navigation entry

### Phase 5: SignUp Page Update
- Mode check on mount via `get-system-config`
- `InviteOnlyMessage` component rendered when `signup_enabled = false`

### Phase 6: Tests, Documentation & Reconciliation
- 3 regression test files: RW-011 (token contract), RW-012 (pre-signup hook), RW-013 (permission deps) — 31 tests, all passing
- 4 reference indexes updated: route-index (9 new routes), event-index (7 new events), function-index (9 new functions), permission-index (2 new permissions)
- DW-035 → `implemented`
- System state and master plan updated
- This closure document created

---

## Audit Events Added

| Event | Source |
|-------|--------|
| `user.invited` | `invite-user` edge function |
| `user.bulk_invited` | `invite-users-bulk` edge function |
| `user.invitation_accepted` | `accept_invitation_on_confirm` DB trigger |
| `user.invitation_revoked` | `revoke-invitation` edge function |
| `user.invitation_resent` | `resend-invitation` edge function |
| `user.signup_nudge_sent` | `send-signup-nudge` edge function |
| `system.config_changed` | `update-system-config` edge function |

---

## Permissions Added

| Permission | Dependencies | Default Roles |
|------------|-------------|---------------|
| `users.invite` | `users.view_all`, `admin.access` | admin, superadmin |
| `users.invite.manage` | `users.invite`, `users.view_all`, `admin.access` | admin, superadmin |

---

## Deferred Items Created

| ID | Title | Status |
|----|-------|--------|
| DW-038 | Bulk invite CSV upload | `deferred (v2)` |
| DW-039 | Invitation expiry cleanup cron | `deferred (v2)` |
| DW-040 | Automated invitation follow-up cron job | `deferred (v2)` |

---

## Manual Deployment Actions Required

1. **Pre-signup hook registration:** Supabase Dashboard → Auth → Hooks → "Before user is created" → select `auth-hook-pre-signup`
2. **Custom SMTP configuration** (before production): Supabase Dashboard → Auth → Settings → SMTP
3. **Permission seed execution:** Run updated permission seed SQL to add `users.invite` and `users.invite.manage`

---

## Security Notes

- Pre-signup hook is the sole enforcement point for signup gating — cannot be bypassed by direct API calls
- Invite tokens: 32-byte cryptographically random, SHA-256 hashed at rest, single-use
- All invitation management requires `requireRecentAuth(30min)`
- Superadmin-only protection on `admin.config` for onboarding mode changes
- Rate limiting: 3 resends per email per 24 hours

---

## Regression Coverage

| Test ID | File | Tests | Coverage |
|---------|------|-------|----------|
| RW-011 | `src/test/rw011-invitation-token.test.ts` | 9 | Token generation: 32 bytes, base64url, SHA-256, hex encoding |
| RW-012 | `src/test/rw012-pre-signup-hook.test.ts` | 9 | Pre-signup hook: exists, reads config, continue/reject/fail-open |
| RW-013 | `src/test/rw013-invite-permission-deps.test.ts` | 13 | Permission deps sync: JSON ↔ TS, edge function permission checks |
