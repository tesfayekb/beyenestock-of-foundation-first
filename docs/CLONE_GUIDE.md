# Clone & Setup Guide

> **Purpose:** Step-by-step instructions to create a new project from this starter template.  
> **Last Updated:** 2026-04-14

---

## Prerequisites

- [Supabase](https://supabase.com) account (free tier works)
- [GitHub](https://github.com) account
- [Cloudflare](https://www.cloudflare.com) account (for Turnstile CAPTCHA)
- Node.js 18+ / Bun 1.x
- Supabase CLI (optional, for `supabase db push`)

---

## 1. Clone the Codebase

### Option A — Lovable Remix (recommended)

1. Open the original project in Lovable
2. Click **Remix** → creates an independent copy with full history
3. Connect a new GitHub repo from Lovable settings

### Option B — GitHub Fork / Template

```bash
# Fork or use as template, then clone
git clone https://github.com/YOUR_ORG/new-project.git
cd new-project
npm install   # or: bun install
```

---

## 2. Create a New Supabase Project

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard) → **New Project**
2. Choose org, name, password, region
3. Wait for provisioning to complete
4. Note these values from **Settings → API**:
   - **Project URL** (`https://xxxxx.supabase.co`)
   - **Anon (public) key**
   - **Service role key** (keep secret)
   - **Project ref** (the `xxxxx` part of the URL)

---

## 3. Initialize the Database

### ⚠️ Critical: Ordering

The `sql/` files contain the **original baseline schema**. The `supabase/migrations/` folder contains **all incremental changes** applied on top of that baseline. You need **both**, in order.

### Option A — Manual (SQL Editor)

Run these files **in order** via **Supabase Dashboard → SQL Editor**:

1. `sql/01_rbac_schema.sql` — Core tables (roles, permissions, user_roles, role_permissions, audit_logs)
2. `sql/02_rbac_security_helpers.sql` — Security-definer helper functions
3. `sql/03_rbac_rls_policies.sql` — Row-level security policies
4. `sql/04_rbac_seed.sql` — Seed data (base roles, permissions)
5. `sql/05_secure_cron_schedule.sql` — Cron job schedules

Then run **all 42 migration files** from `supabase/migrations/` in timestamp order (filename sort = correct order). Each file is a standalone SQL statement.

### Option B — Supabase CLI (recommended)

```bash
# Link to your new project
supabase link --project-ref YOUR_PROJECT_REF

# Push all migrations (handles ordering automatically)
supabase db push
```

> **Note:** If using CLI, the `sql/` baseline files may need to be converted to an initial migration or run manually first, depending on your migration history. Test on a branch database first.

### Verification

After running all SQL, confirm in SQL Editor:

```sql
-- Should return 5+ roles (superadmin, admin, moderator, user, viewer)
SELECT key, name, is_base, is_immutable FROM public.roles ORDER BY key;

-- Should return 20+ permissions
SELECT key FROM public.permissions ORDER BY key;

-- Should have RLS enabled on all tables
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
```

---

## 4. Configure Secrets

Set these in **Supabase Dashboard → Settings → Edge Functions → Secrets**:

| Secret | Where to Get It | Notes |
|--------|----------------|-------|
| `SUPABASE_URL` | Settings → API → Project URL | `https://xxxxx.supabase.co` |
| `SUPABASE_ANON_KEY` | Settings → API → anon public | Publishable key |
| `SUPABASE_SERVICE_ROLE_KEY` | Settings → API → service_role | ⚠️ Keep secret — full DB access |
| `CRON_SECRET` | Generate: `openssl rand -hex 32` | Authenticates scheduled job calls |
| `ALLOWED_ORIGINS` | Your app domain(s) | Comma-separated, e.g. `https://myapp.com,https://staging.myapp.com` |
| `TURNSTILE_SECRET_KEY` | Cloudflare Dashboard → Turnstile | Server-side verification key |

### Development Shortcuts

For local development, you can use Cloudflare's always-pass test keys:
- Site key: `1x00000000000000000000AA`
- Secret key: `1x0000000000000000000000000000000AA`

---

## 5. Configure Environment Variables

### In Lovable

If using Lovable Remix, these are auto-populated from your connected Supabase project:
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`
- `VITE_SUPABASE_PROJECT_ID`

### Manual Setup

Create `.env` from the template:

```bash
cp .env.example .env
```

Fill in:

```env
VITE_SUPABASE_PROJECT_ID="your-project-ref"
VITE_SUPABASE_PUBLISHABLE_KEY="your-anon-key"
VITE_SUPABASE_URL="https://your-project.supabase.co"
VITE_TURNSTILE_SITE_KEY="1x00000000000000000000AA"  # test key for dev
# VITE_DEV_MODE="true"  # uncomment for development bypass
```

---

## 6. Configure Auth Providers

### Email/Password (enabled by default)

- **Supabase Dashboard → Auth → Settings**
- Confirm email is enabled
- For production: configure custom SMTP (Settings → Auth → SMTP)

### Google OAuth (optional)

1. [Google Cloud Console](https://console.cloud.google.com) → Credentials → OAuth 2.0 Client
2. Authorized redirect URI: `https://YOUR_PROJECT_REF.supabase.co/auth/v1/callback`
3. **Supabase Dashboard → Auth → Providers → Google** → Enable, paste Client ID + Secret

### Pre-Signup Hook (required for invite-only mode)

1. **Supabase Dashboard → Auth → Hooks**
2. "Before user is created" → select `auth-hook-pre-signup` edge function
3. This gates signups when onboarding mode is set to `invite_only`

---

## 7. Edge Functions

All 45 edge functions deploy automatically when connected to Lovable or via `supabase functions deploy --all`.

Verify deployment: **Supabase Dashboard → Edge Functions** — all functions should show as deployed.

### Edge Functions List

**Auth & Profile:** `get-profile`, `update-profile`, `verify-turnstile`, `auth-hook-pre-signup`, `revoke-sessions`  
**RBAC:** `list-roles`, `create-role`, `update-role`, `delete-role`, `get-role-detail`, `assign-role`, `revoke-role`, `list-permissions`, `assign-permission-to-role`, `revoke-permission-from-role`  
**User Management:** `list-users`, `get-user-stats`, `deactivate-user`, `reactivate-user`  
**Invitations:** `invite-user`, `invite-users-bulk`, `list-invitations`, `resend-invitation`, `revoke-invitation`, `send-signup-nudge`  
**Audit:** `query-audit-logs`, `export-audit-logs`  
**Health & Monitoring:** `health-check`, `health-detailed`, `health-metrics`, `health-alerts`, `health-alert-config`  
**Jobs:** `job-audit-cleanup`, `job-health-check`, `job-metrics-aggregate`, `job-alert-evaluation`, `jobs-pause`, `jobs-resume`, `jobs-kill-switch`, `jobs-dead-letters`, `jobs-replay-dead-letter`  
**MFA:** `mfa-recovery-generate`, `mfa-recovery-verify`  
**Config:** `get-system-config`, `update-system-config`

---

## 8. Branding Customization

Update these files to rebrand for your new project:

| File | What to Change |
|------|---------------|
| `index.html` | `<title>`, `<meta name="description">`, CSP `connect-src` (add your domain) |
| `public/manifest.json` | `name`, `short_name`, `description` |
| `public/favicon.svg` | Replace with your logo |
| `src/components/AppBrand.tsx` | App name, logo component |
| `src/index.css` | Color tokens (HSL values in `:root` and `.dark`) |
| `tailwind.config.ts` | Font families, extended theme values |

---

## 9. Pre-Production Checklist

Before allowing real users, complete all items in `docs/08-planning/preproduction-checklist.md`:

- [ ] Register pre-signup hook in Supabase Dashboard
- [ ] Configure custom SMTP for branded emails
- [ ] Remove `VITE_DEV_MODE=true` from `.env`
- [ ] Replace Turnstile test keys with real keys
- [ ] Set `ALLOWED_ORIGINS` to production domain(s)
- [ ] Set `VITE_SENTRY_DSN` for error monitoring
- [ ] Sanitize search input in `list-users` edge function

---

## 10. Verification Checklist

After completing setup, verify each layer:

### Database
- [ ] `SELECT count(*) FROM public.roles` returns 5+ rows
- [ ] `SELECT count(*) FROM public.permissions` returns 20+ rows
- [ ] RLS is enabled on all public tables

### Auth
- [ ] Sign up a test user → profile auto-created
- [ ] First user gets `superadmin` role automatically
- [ ] Email verification works (or bypassed with `VITE_DEV_MODE`)

### Edge Functions
- [ ] Sign in → admin dashboard loads without 401 errors
- [ ] Users page lists the test user
- [ ] Audit logs page shows signup events

### Security
- [ ] Turnstile widget appears on sign-in page (unless dev mode)
- [ ] Non-authenticated requests are rejected by edge functions
- [ ] CORS headers return your domain (not `*`)

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 on all edge functions | Missing or wrong `SUPABASE_SERVICE_ROLE_KEY` secret | Re-check in Dashboard → Settings → Edge Functions → Secrets |
| "relation does not exist" | Migrations not run or run out of order | Run `sql/` files first, then migrations in timestamp order |
| Duplicate table errors | Ran `sql/` files AND migrations that recreate the same tables | Start fresh: reset DB, run in correct order |
| Sign-up blocked | Pre-signup hook active + onboarding mode = `invite_only` | Either invite the user first or change onboarding mode to `open` |
| CORS errors in browser | `ALLOWED_ORIGINS` not set or wrong domain | Set to your app's URL in edge function secrets |
| Turnstile not loading | Wrong site key or CSP blocking | Check `VITE_TURNSTILE_SITE_KEY` and `index.html` CSP `frame-src` |
