# Trading System — Regression Strategy

> **Owner:** tesfayekb | **Version:** 1.0

## Purpose

Define how trading work avoids breaking the foundation. Every trading change must preserve foundation behavior exactly — there is zero tolerance for foundation regression.

---

## 1. Foundation Isolation Rule (T-Rule 1)

**Trading changes must NEVER break foundation behavior.**

- All trading code lives in dedicated paths: `src/pages/admin/trading/`, `src/components/trading/`, `src/hooks/trading/`, `backend/`, `trading-docs/`
- All trading database objects use the `trading_` prefix
- The ONLY approved foundation modification is the `profiles` ALTER (Part 4.1)
- Inserts into existing foundation tables (`permissions`, `role_permissions`, `job_registry`, `alert_configs`) must use `ON CONFLICT DO NOTHING`

---

## 2. Trading Change Impact Classification

| Change Type | Impact | Requires |
|-------------|--------|----------|
| New `trading_*` table | LOW | Migration ledger entry, RLS policies |
| Insert into `permissions` / `role_permissions` | MEDIUM | Permission index update, ON CONFLICT DO NOTHING |
| Insert into `job_registry` / `alert_configs` | MEDIUM | ON CONFLICT DO NOTHING, owner_module='trading' |
| ALTER on `profiles` (approved columns only) | HIGH | Pre/post snapshot of profile reads, regression tests |
| New trading frontend page | LOW | Permission gate, lazy import, route index entry |
| New shared component in `src/components/trading/` | LOW | Component inventory entry |
| New trading hook | LOW | Component inventory entry |
| Modification to existing foundation file | **FORBIDDEN** | Refuse and request scope review |
| New edge function for trading | MEDIUM | Authorization check using `has_permission()` |
| New backend Python module | MEDIUM | Heartbeat to `trading_system_health` mandatory |

---

## 3. Foundation Modules at Risk

These foundation modules could be affected by trading work and must be verified after every change:

| Foundation Module | Risk From Trading | How to Verify |
|-------------------|-------------------|---------------|
| **Auth** | Profile schema change could break `handle_new_user` trigger | Sign up new user → verify profile row created with all expected columns |
| **RBAC** | New permissions could collide with existing keys | Visit `/admin/permissions` → confirm no duplicate keys |
| **Profile** | New columns could break `get-profile` edge function | Sign in → visit `/profile` → verify name/email/avatar still load |
| **Admin Users** | Profile reads in `list-users` could return new columns unexpectedly | Visit `/admin/users` → verify table loads, no console errors |
| **Audit** | New actions must follow existing structured logging format | Visit `/admin/audit` → filter by `action LIKE 'trading.%'` |
| **Health** | Trading health must NOT pollute `system_health_snapshots` | Visit `/admin/health` → confirm only foundation services listed |
| **Jobs** | New jobs must coexist with foundation jobs in `job_registry` | Visit `/admin/jobs` → confirm trading and foundation jobs both visible |
| **Alerts** | New alert configs must coexist with foundation alerts | Visit `/admin/alerts` → confirm trading thresholds visible |

---

## 4. Critical Foundation Queries That Must Keep Working

After every trading migration, these queries must return correct results without errors:

```sql
-- Q1: Profile reads (all columns)
SELECT id, display_name, last_name, email, email_verified, avatar_url, status
FROM public.profiles WHERE id = auth.uid();

-- Q2: User role lookup
SELECT r.key, r.name FROM public.user_roles ur
JOIN public.roles r ON r.id = ur.role_id
WHERE ur.user_id = auth.uid();

-- Q3: Permission check (foundation permissions)
SELECT public.has_permission(auth.uid(), 'users.view_all');
SELECT public.has_permission(auth.uid(), 'audit.view');
SELECT public.has_permission(auth.uid(), 'monitoring.view');

-- Q4: Audit log read
SELECT id, action, actor_id, target_type, created_at
FROM public.audit_logs ORDER BY created_at DESC LIMIT 10;

-- Q5: Foundation health snapshot
SELECT id, status, checks, created_at
FROM public.system_health_snapshots ORDER BY created_at DESC LIMIT 1;

-- Q6: Foundation job registry (excluding trading jobs)
SELECT id, owner_module, schedule, enabled
FROM public.job_registry WHERE owner_module != 'trading';
```

---

## 5. Post-Migration Verification Checklist

After every trading migration is applied, run this checklist manually before marking the migration `verified`:

- [ ] **Sign in** — `/sign-in` works, MFA challenge appears, session created
- [ ] **Visit `/admin/health`** — page loads, foundation services healthy, no trading services polluting the list
- [ ] **Visit `/admin/jobs`** — page loads, both foundation and trading jobs visible, no errors
- [ ] **Visit `/admin/audit`** — page loads, audit log displays recent foundation events
- [ ] **Visit `/admin/permissions`** — page loads, all permissions visible (foundation + trading), no duplicates
- [ ] **Visit `/profile`** — own profile loads with display name, email, avatar
- [ ] **Visit `/admin/users`** — user list loads with profile data intact
- [ ] **Browser console** — no errors referencing trading_* tables on non-trading pages
- [ ] **Network tab** — no failed requests on foundation pages

If ANY checkbox fails → revert the migration, fix the regression, retest from scratch.

---

## 6. Regression Watchlist Items

| Watch Item | Trigger | Mitigation |
|-----------|---------|-----------|
| Profile column count drift | Adding columns beyond approved 3 | Schema audit at every migration |
| Permission key collision | Trading permission accidentally uses foundation key | Permission index reconciliation |
| Job registry pollution | Trading job missing `owner_module='trading'` | INSERT must include owner_module |
| RLS policy gaps | New trading table without RLS | Linter check after every migration |
| Audit log format drift | Trading actions not following `module.action` format | Audit reconciliation script |
