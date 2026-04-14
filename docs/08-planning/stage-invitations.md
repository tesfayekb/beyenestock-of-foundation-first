# Stage Plan: User Onboarding & Invitations

> **Plan ID:** PLAN-INVITE-001  
> **DW Reference:** DW-035  
> **Status:** approved  
> **Created:** 2026-04-13  
> **Baseline:** v11.0  

---

## Overview

Implements a complete user onboarding system with three modes:

1. **Open Signup** — anyone with the URL can register (current behavior)
2. **Invite Only** — accounts created only via admin-sent invitations
3. **Both Enabled** — self-signup and invite coexist (default)

### Security Model

- **Enforcement point:** Supabase Auth Pre-Signup Hook (edge function). Cannot be bypassed by direct API calls.
- **Invite tokens:** 32-byte cryptographically random, bcrypt-hashed at rest, single-use, 72-hour TTL.
- **Permission gate:** `admin.config` (existing, SUPERADMIN_ONLY) controls onboarding mode. `users.invite` / `users.invite.manage` control invitation operations.

### Key Architecture Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Reuse `admin.config` instead of new `system.config` | Already seeded, already SUPERADMIN_ONLY in all 3 locations, no existing UI conflict. Audit granularity provided by event payload, not permission key. |
| 2 | Pre-signup hook manual registration | One-time Dashboard step (Auth → Hooks). Same pattern as CRON_SECRET setup. |
| 3 | Supabase built-in email for dev; custom SMTP before production | `inviteUserByEmail()` works out of the box. Configure Resend/custom SMTP pre-launch. |
| 4 | Textarea bulk invite (defer CSV upload → DW-038) | Textarea handles 50 emails. CSV adds Papa Parse dep + mapping UI for marginal benefit. |
| 5 | Lazy expiry check (defer cleanup cron → DW-039) | Validation checks `expires_at < now()`. UI computes virtual expired status. No DB writes needed. |
| 6 | No `accept-invitation` endpoint | `inviteUserByEmail()` creates user → `handle_new_user_role` trigger reads `invitation_id` from metadata → assigns role + marks accepted atomically. |
| 7 | Pre-signup hook has no token validation | `inviteUserByEmail()` bypasses the hook (service-role). Hook only checks `signup_enabled`. |
| 8 | Existing-user invite returns 409 | `invite-user` detects existing auth account → returns `user_already_exists: true` so admin can assign role directly. |

---

## Phase 1: Schema & Permissions (Session 1)

### 1A — Database Migration

**`system_config` table:**

```sql
CREATE TABLE public.system_config (
  key         TEXT PRIMARY KEY,
  value       JSONB NOT NULL,
  description TEXT,
  updated_by  UUID,
  updated_at  TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.system_config ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Authenticated users can read system config"
  ON public.system_config FOR SELECT TO authenticated USING (true);
INSERT INTO public.system_config (key, value, description) VALUES
  ('onboarding_mode', '{"signup_enabled": true, "invite_enabled": true}',
   'Controls user onboarding pathways. At least one must be true.');
```

**`invitations` table:**

```sql
CREATE TABLE public.invitations (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           TEXT NOT NULL,
  token_hash      TEXT NOT NULL UNIQUE,
  role_id         UUID REFERENCES public.roles(id) ON DELETE SET NULL,
  invited_by      UUID NOT NULL,
  status          TEXT NOT NULL DEFAULT 'pending',
  expires_at      TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '72 hours'),
  accepted_at     TIMESTAMPTZ,
  accepted_by     UUID,
  created_at      TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.invitations ENABLE ROW LEVEL SECURITY;
-- No direct client access — all operations via edge functions
CREATE UNIQUE INDEX idx_invitations_email_pending
  ON public.invitations(email) WHERE status = 'pending';
CREATE INDEX idx_invitations_token_hash ON public.invitations(token_hash);
CREATE INDEX idx_invitations_status ON public.invitations(status);
CREATE INDEX idx_invitations_expires_at ON public.invitations(expires_at);
```

**Validation trigger** (not CHECK constraint):

```sql
CREATE OR REPLACE FUNCTION public.validate_invitation_status()
  RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public' AS $$
BEGIN
  IF NEW.status NOT IN ('pending', 'accepted', 'expired', 'revoked') THEN
    RAISE EXCEPTION 'Invalid invitation status: %. Must be pending, accepted, expired, or revoked.', NEW.status;
  END IF;
  RETURN NEW;
END; $$;
CREATE TRIGGER validate_invitation_status_trigger
  BEFORE INSERT OR UPDATE ON public.invitations
  FOR EACH ROW EXECUTE FUNCTION public.validate_invitation_status();
```

### 1B — Permissions

Add to seed SQL + `permission-deps.json` + `supabase/functions/_shared/permission-deps.ts`:

```
"users.invite":        ["users.view_all", "admin.access"]
"users.invite.manage": ["users.invite", "users.view_all", "admin.access"]
```

- `admin.config` already exists and is SUPERADMIN_ONLY — no changes needed.
- Assign `users.invite` + `users.invite.manage` to admin role in seed.

### 1C — Trigger Update

Update `handle_new_user_role` to:
1. Check `NEW.raw_user_meta_data->>'invitation_id'`
2. If present: look up invitation, assign `role_id` from invitation, mark invitation `accepted`, set `accepted_by` and `accepted_at`
3. All within the same transaction (atomic with user creation)

### Deliverables

- 1 migration (2 tables + trigger + validation function)
- Updated `permission-deps.json` + `_shared/permission-deps.ts`
- Updated `handle_new_user_role` trigger
- Updated permission seed SQL

---

## Phase 2: Pre-Signup Hook & Core Edge Functions (Session 2)

### 2A — Pre-Signup Auth Hook

`supabase/functions/auth-hook-pre-signup/index.ts`

Logic (simplified per architecture decision #7):
1. Read `system_config` → `onboarding_mode`
2. If `signup_enabled = false` → return 400 with "Registration is by invitation only"
3. If `signup_enabled = true` → return 200

No token validation — invited users bypass the hook entirely via `inviteUserByEmail()`.

**Manual deployment step:** Register in Supabase Dashboard → Auth → Hooks → "Before user is created" → point to edge function URL.

### 2B — Core Edge Functions

| Function | Method | Auth | Permission |
|----------|--------|------|------------|
| `get-system-config` | GET | None (public) | — |
| `update-system-config` | PATCH | JWT + reauth | `admin.config` (SUPERADMIN_ONLY) |

**`get-system-config`:** Returns `{ signup_enabled, invite_enabled }` only. No sensitive data.

**`update-system-config`:** Validates at least one mode is true. Emits `system.config_changed` audit event with `{ before, after }`.

### Deliverables

- 3 edge functions (hook + get + update)
- Audit events: `system.config_changed`
- Manual step documented: hook registration

---

## Phase 3: Invitation Management Edge Functions (Session 3)

| Function | Method | Permission | Notes |
|----------|--------|------------|-------|
| `invite-user` | POST | `users.invite` | Single invite. Checks `invite_enabled`. Detects existing accounts → 409. |
| `invite-users-bulk` | POST | `users.invite` | Max 50/call. Sequential. Returns `{ succeeded, failed, skipped_existing }`. |
| `list-invitations` | GET | `users.invite.manage` | Paginated. Status filter. Computes virtual `expired` status for pending + past-TTL. |
| `revoke-invitation` | POST | `users.invite.manage` | Marks revoked. Optionally deletes pending auth user. |
| `resend-invitation` | POST | `users.invite.manage` | Revokes old token, generates new, resets TTL. Rate limit: 3/email/24h. |

### Token Generation (invite-user)

```
1. Generate 32-byte random: crypto.getRandomValues(new Uint8Array(32))
2. Base64url encode → raw token (sent in email)
3. Bcrypt hash (cost 10) → stored as token_hash
4. Call supabase.auth.admin.inviteUserByEmail(email, { data: { invitation_id: uuid } })
5. Emit user.invited audit event
```

### Existing-User Detection (invite-user)

```
1. Check supabase.auth.admin.listUsers({ filter: email })
2. If user exists → return 409 { error: 'user_already_exists', user_id }
3. Admin can then assign role directly via existing assign-role endpoint
```

### Audit Events

- `user.invited` — single invite sent
- `user.bulk_invited` — bulk invite with count
- `user.invitation_revoked` — invitation revoked
- `user.invitation_resent` — invitation resent
- `user.invitation_accepted` — invitation consumed during signup (emitted by `handle_new_user_role` trigger in Phase 1, not an edge function)

### Deliverables

- 5 edge functions
- 4 audit events

---

## Phase 4: Admin UI (Sessions 4–5)

### 4A — Admin Onboarding Page

**Route:** `/admin/onboarding` (add `ADMIN_ONBOARDING` to `routes.ts`)

**Navigation:** Add under "User Management" in `admin-navigation.ts`:
```ts
{ title: 'Invitations', url: ROUTES.ADMIN_ONBOARDING, icon: UserPlus, permission: 'users.invite' }
```

**Page sections:**
1. **Onboarding Mode Card** — Two switches (signup enabled, invite enabled). Mutual-exclusion prevention (cannot disable both). Requires reauth confirmation for changes.
2. **Send Invitation** — Form: email + optional role dropdown + optional display name. Calls `invite-user`.
3. **Bulk Invite** — Textarea (one email per line, max 50). Calls `invite-users-bulk`. Shows results summary.
4. **Invitations Table** — Status filter tabs (all/pending/accepted/expired/revoked). Columns: email, status, invited by, created, expires. Actions: revoke, resend.

### 4B — Components

| Component | Purpose |
|-----------|---------|
| `OnboardingModeCard` | Two switches + confirmation dialog |
| `InviteUserDialog` | Single invite form modal |
| `BulkInviteDialog` | Textarea bulk invite modal |
| `InvitationStatusBadge` | Reusable status badge (pending/accepted/expired/revoked) |
| `InvitationsTable` | Data table with status filters and actions |

### 4C — Hooks

| Hook | Purpose |
|------|---------|
| `useSystemConfig()` | Fetch + mutate onboarding mode via get/update-system-config |
| `useInvitations()` | List, revoke, resend via list/revoke/resend-invitation |
| `useInviteUser()` | Send single/bulk invites via invite-user/invite-users-bulk |

### Deliverables

- 1 page, 5 components, 3 hooks
- Route + navigation updates
- App.tsx route addition

---

## Phase 5: SignUp Page Update (Session 5)

### 5A — Mode Check

On mount: call `get-system-config` (public, no auth).
- If `signup_enabled = false` → render `InviteOnlyMessage` component (no form)
- If `signup_enabled = true` → render existing signup form

### 5B — Invite Link Flow (Not Applicable)

Phase 5B is not applicable. `inviteUserByEmail()` handles the full invite-to-account flow: admin sends invite → user receives magic link email from Supabase → user clicks link → Supabase hosted page to set password → redirected to app callback (`emailRedirectTo`) → `handle_new_user_role` trigger has already fired and assigned the role. The SignUp page (`/sign-up`) is not involved in the invite flow at all. Phase 5 scope is limited to: (A) checking signup mode on mount, (B) rendering `InviteOnlyMessage` when `signup_enabled = false`.

### 5C — Edge Cases

| Case | Behavior |
|------|----------|
| Signup disabled, no invite | Show "Invitation Only" message with "Contact your administrator" |
| Expired invite link | Show clear error: "This invitation has expired" |
| Used invite link | Show: "This invitation has already been used. Sign in instead." |
| User already has account | Show: "You already have an account. Sign in instead." |

### 5D — Refactoring

Refactor `SignUp.tsx` (currently 216 lines) into:
- `SignUpForm` — the actual form
- `InviteOnlyMessage` — displayed when signup disabled
- `SignUp` — orchestrator that checks mode and renders appropriate component

### Deliverables

- Refactored `SignUp.tsx` → 2 components (`SignUp` orchestrator + `InviteOnlyMessage`)
- `InviteOnlyMessage` component

---

## Phase 6: Testing, Documentation & Reconciliation (Session 6)

### 6A — Regression Tests

| Test ID | Coverage |
|---------|----------|
| RW-011 | Invite token: hash verification, expiry check, single-use enforcement |
| RW-012 | Pre-signup hook: signup disabled → reject, signup enabled → allow |
| RW-013 | Permission dependency drift for `users.invite`, `users.invite.manage` |

### 6B — Documentation Updates

| Document | Action |
|----------|--------|
| `docs/04-modules/user-onboarding.md` | **Create** — module doc: 3 modes, schema, edge functions, permissions |
| `docs/07-reference/route-index.md` | **Update** — add `/admin/onboarding` + 7 edge function routes |
| `docs/07-reference/event-index.md` | **Update** — add 5 audit events |
| `docs/07-reference/function-index.md` | **Update** — add 8 edge functions + 1 hook |
| `docs/07-reference/permission-index.md` | **Update** — add `users.invite`, `users.invite.manage` |
| `docs/08-planning/deferred-work-register.md` | **Update** — DW-035 → `implemented` |
| `docs/00-governance/system-state.md` | **Update** — add `user-onboarding` module |

### 6C — Phase Gate

- Update `master-plan.md` with PLAN-INVITE-001 evidence references
- Reference index reconciliation (all new routes/functions/events/permissions in indexes)
- Phase gate closure document

### Deliverables

- 3 regression test files
- 1 new module doc, 6 updated reference docs
- Phase gate closure

---

## Manual Deployment Actions (Post-Implementation)

These are one-time manual steps required after code is deployed:

1. **Pre-signup hook registration:** Supabase Dashboard → Auth → Hooks → "Before user is created" → select `auth-hook-pre-signup` edge function
2. **Custom SMTP configuration** (before production): Supabase Dashboard → Auth → Settings → SMTP → configure Resend or equivalent provider
3. **Permission seed execution:** Run updated permission seed SQL to add `users.invite` and `users.invite.manage`

---

## Deferred Items Created by This Plan

| ID | Title | Reason |
|----|-------|--------|
| DW-038 | Bulk invite CSV upload | Textarea sufficient for v1. CSV adds dep + mapping UI. |
| DW-039 | Invitation expiry cleanup cron | Lazy check sufficient at expected scale. Add when >1,000 expired rows accumulate. |

---

## Estimated Effort

| Phase | Scope | Sessions |
|-------|-------|----------|
| 1 | Schema + Permissions + Trigger | 1 |
| 2 | Pre-signup Hook + Config Functions | 1 |
| 3 | Invitation Management Functions | 1 |
| 4 | Admin UI | 1–2 |
| 5 | SignUp Page Update | 1 |
| 6 | Tests + Docs + Reconciliation | 1 |
| **Total** | | **6–7** |
