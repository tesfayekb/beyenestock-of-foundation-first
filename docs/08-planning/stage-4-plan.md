# Phase 4 — Admin & User Interfaces Plan (v2)

> **Status:** PROPOSED — awaiting approval  
> **Owner:** AI  
> **Created:** 2026-04-10  
> **Revised:** 2026-04-10 (v2 — SSOT reconciliation + design governance)  
> **Scope:** PLAN-ADMIN-001 (Admin Panel) + PLAN-USRPNL-001 (User Panel)  
> **Baseline:** Executes against approved plan baseline v9  
> **Design Reference:** TailAdmin-class enterprise dashboard — sidebar + top nav + content area layout, professional bold aesthetic  
> **Supersedes:** Stage 4 Plan v1

---

## Objective

Build the admin and user interface panels that consume all Phase 1–3.5 backend infrastructure. Admin panel first (higher complexity, leverages full backend), user panel second.

---

## SSOT Reconciliation Record

This plan was reconciled against the following authoritative indexes on 2026-04-10:

| Index | Version | Reconciliation Result |
|-------|---------|----------------------|
| `route-index.md` | route-v1.5 | v1 plan proposed conflicting paths (`/account/*`, `/admin/access/*`). v2 conforms to route-index paths. New routes added via change control. |
| `permission-index.md` | perm-v1.1 | v1 plan used non-existent `roles.manage_permissions`. v2 uses governed `permissions.assign` / `permissions.revoke`. |
| Route lifecycle | — | Unimplemented frontend routes reclassified from `active` to `planned` in route-index. |

---

## Prerequisites (MUST complete before Stage 4A code)

### Governance Docs Required

| Doc | Path | Purpose |
|-----|------|---------|
| UI Architecture | `docs/01-architecture/ui-architecture.md` | Shell structure, scroll ownership, responsive behavior |
| UI Design System | `docs/07-reference/ui-design-system.md` | Token map, typography, spacing, component patterns |
| Component Inventory | `docs/07-reference/component-inventory.md` | Governed shared component list |

**Rule:** These 3 docs must exist and be approved before any Stage 4A code is written.

---

## Design System Foundation

### Layout Architecture

- **Shell pattern:** Sidebar (fixed/sticky, collapsible to icon strip) + top header (fixed/sticky) + content area (independent scroll)
- **Sidebar:** Dark chrome (`bg-sidebar`), collapsible to icon strip, section headers, permission-filtered navigation, sign-out in footer
- **Header:** Fixed top bar with sidebar trigger, search (desktop), theme toggle, notifications badge, user menu avatar
- **Content area:** Light/dark adaptive background (`bg-background`), consistent padding, breadcrumbs, nested `<Suspense>` for lazy route loading
- **Scroll ownership:** Content area only — sidebar and header never scroll
- **Mobile:** Sidebar via sheet overlay, responsive content padding

### Visual Direction: Professional Bold

One governed visual language across all pages:

- **Typography:** One display font for headings, Inter for body, JetBrains Mono for code/IDs. Font choice documented in `ui-design-system.md`.
- **Color:** Extend existing semantic tokens (background, foreground, card, primary, secondary, destructive, muted, accent, sidebar). Add brand accent scale and status tokens (success, warning, info). All HSL. No raw arbitrary colors in components.
- **Depth:** Content shadow, card elevation. NO glass effects. NO text-gradient utilities.
- **Motion:** Subtle fade-in transitions, collapsible animations, skeleton loading states. `prefers-reduced-motion` respected. NO decorative motion.
- **Dark mode:** Full dark mode support with proper token switching — required from day one, not deferred.
- **Uniformity rule:** One card style, one table style, one dialog style, one form field style, one toast/alert style, one empty/loading/error state family. No page-local variants.

### Component Architecture

| Component | Purpose | Reused Across |
|-----------|---------|---------------|
| `DashboardLayout` | Shell wrapper (sidebar + header + outlet) | Admin, User panels |
| `DashboardSidebar` | Permission-filtered nav with sections | Admin, User panels |
| `DashboardHeader` | Top bar (trigger, search, theme, user menu) | Admin, User panels |
| `DashboardBreadcrumbs` | Route-aware breadcrumb trail | All dashboard pages |
| `PageHeader` | Consistent page title + action buttons zone | All dashboard pages |
| `StatCard` | Metric display card | Dashboard home pages |
| `DataTable` | Sortable, filterable table with pagination | Users, Roles, Audit |
| `UserMenu` | Avatar dropdown with profile/settings/sign-out | All authenticated pages |
| `ConfirmActionDialog` | Standard destructive action confirmation | All destructive flows |
| `EmptyState` | Standard icon + message for no-data | All list/table pages |
| `ErrorState` | Standard error + retry button | All async operations |
| `LoadingSkeleton` | Standard skeleton for async loading | All async operations |
| `StatusBadge` | Color-coded status indicator | Users, Roles |

**Rule:** Pages assemble from this component inventory. No page-local component variants permitted.

---

## Execution Stages

### Stage 4A — Design System Governance + Dashboard Shell

**Scope:** Governance docs, design tokens, layout infrastructure, shared components

**Prerequisites (governance — must complete first):**
1. Create and approve `docs/01-architecture/ui-architecture.md`
2. Create and approve `docs/07-reference/ui-design-system.md`
3. Create and approve `docs/07-reference/component-inventory.md`

**Deliverables (implementation — after governance docs approved):**
1. Design system extension in `index.css`:
   - Font imports (display + body + mono — as specified in ui-design-system.md)
   - Brand accent scale tokens
   - Status semantic tokens: `--success`, `--warning`, `--info`
   - Dark mode tokens (parity with light)
   - Utility classes: `.font-display`, `.font-mono`
   - NO `.text-gradient`, `.glass`, or decorative utilities
2. `tailwind.config.ts` updates for new tokens
3. Navigation type system: `NavItem` interface with permission gating
4. `DashboardLayout` component (SidebarProvider + Sidebar + Header + Outlet)
5. `DashboardSidebar` — permission-filtered, section headers, collapsible groups, active state
6. `DashboardHeader` — sidebar trigger, user menu, theme toggle (fixed/sticky)
7. `UserMenu` component — avatar, display name, sign-out
8. `PageHeader` component — consistent page title zone
9. `ConfirmActionDialog` — standard destructive confirmation pattern
10. `EmptyState`, `ErrorState`, `LoadingSkeleton` — standard async state components
11. Admin navigation config (`admin-navigation.ts`)
12. User navigation config (`user-navigation.ts`)
13. Route setup: `/admin/*` and `/dashboard`, `/settings/*` with lazy loading
14. `AdminLayout` and `UserLayout` wrappers (both using shared DashboardLayout)
15. `RequireAuth` + `RequirePermission` route guards integrated
16. Theme toggle (light/dark) with `next-themes`

**Files Created/Modified:**

| File | Action |
|------|--------|
| `docs/01-architecture/ui-architecture.md` | New — shell contract |
| `docs/07-reference/ui-design-system.md` | New — token map + component patterns |
| `docs/07-reference/component-inventory.md` | New — governed component list |
| `src/index.css` | Extend — add brand/status tokens, fonts |
| `tailwind.config.ts` | Extend — add new token mappings |
| `src/config/navigation.types.ts` | New — NavItem interface |
| `src/config/admin-navigation.ts` | New — admin nav config |
| `src/config/user-navigation.ts` | New — user nav config |
| `src/layouts/DashboardLayout.tsx` | New — shell component |
| `src/layouts/AdminLayout.tsx` | New — admin wrapper |
| `src/layouts/UserLayout.tsx` | New — user wrapper |
| `src/components/dashboard/DashboardSidebar.tsx` | New |
| `src/components/dashboard/DashboardHeader.tsx` | New |
| `src/components/dashboard/UserMenu.tsx` | New |
| `src/components/dashboard/DashboardBreadcrumbs.tsx` | New |
| `src/components/dashboard/PageHeader.tsx` | New |
| `src/components/dashboard/StatCard.tsx` | New |
| `src/components/dashboard/ConfirmActionDialog.tsx` | New |
| `src/components/dashboard/EmptyState.tsx` | New |
| `src/components/dashboard/ErrorState.tsx` | New |
| `src/components/dashboard/LoadingSkeleton.tsx` | New |
| `src/components/dashboard/index.ts` | New — barrel export |
| `src/App.tsx` | Add admin/user route trees |

**Success Criteria:**
- [ ] Governance docs created and approved before code
- [ ] Admin and user shells render with correct layout
- [ ] Sidebar collapses to icon mode and expands
- [ ] Sidebar is fixed/sticky — does not scroll with content
- [ ] Header is fixed/sticky — does not scroll with content
- [ ] Content area scrolls independently
- [ ] Navigation items filtered by user permissions
- [ ] Active route highlighted in sidebar
- [ ] User menu shows display name + sign-out
- [ ] Dark mode toggle works — light and dark themes visually consistent
- [ ] Mobile responsive (sidebar as sheet)
- [ ] Lazy-loaded routes with skeleton fallback
- [ ] No permission-filtered routes accessible via direct URL without permission
- [ ] No raw colors outside semantic tokens in any component
- [ ] No page-local modal/table/form variants
- [ ] WCAG AA contrast in both themes
- [ ] Focus states visible on all interactive controls
- [ ] `text-gradient`, `glass` utilities do NOT exist in codebase

---

### Stage 4B — Admin: User Management

**Scope:** User list, user detail, deactivate/reactivate actions

**Deliverables:**
1. `AdminDashboard` page — overview stats (total users, active, deactivated, roles breakdown)
2. `UserListPage` — DataTable with:
   - Columns: display name, email, status, roles, created date
   - Search/filter by name, email, status
   - Pagination (server-side via `list-users` edge function)
   - Row click → user detail
3. `UserDetailPage` — single user view:
   - Profile info (display name, avatar, email verified status, created/updated)
   - Current roles (with StatusBadge)
   - Action buttons: deactivate/reactivate (with ConfirmActionDialog)
   - Audit trail for this user (filtered)
4. Deactivate/Reactivate flows:
   - ConfirmActionDialog with reason input
   - Calls `deactivate-user` / `reactivate-user` edge functions
   - Toast feedback on success/failure
   - Optimistic UI update

**API Integration:**

| UI Action | Edge Function | Permission Required |
|-----------|--------------|-------------------|
| List users | `list-users` | `users.view_all` |
| View user detail | `get-profile` | `users.view_all` |
| Deactivate user | `deactivate-user` | `users.deactivate` |
| Reactivate user | `reactivate-user` | `users.reactivate` |

**Route Conformance (per route-index.md):**

| Route | Route Index Entry | Lifecycle |
|-------|------------------|-----------|
| `/admin` | ✅ exists | planned → active |
| `/admin/users` | ✅ exists | planned → active |
| `/admin/users/:id` | ✅ exists | planned → active |

**Files Created:**

| File | Action |
|------|--------|
| `src/pages/admin/AdminDashboard.tsx` | New |
| `src/pages/admin/users/UserListPage.tsx` | New |
| `src/pages/admin/users/UserDetailPage.tsx` | New |
| `src/pages/admin/users/index.ts` | New |
| `src/hooks/useUsers.ts` | New — React Query hooks for user API |
| `src/hooks/useUserActions.ts` | New — deactivate/reactivate mutations |

**Success Criteria:**
- [ ] User list loads with pagination using DataTable
- [ ] Search and filter work correctly
- [ ] User detail shows complete profile + roles
- [ ] Deactivate/reactivate flows work with ConfirmActionDialog
- [ ] Unauthorized users see "Access Denied" page
- [ ] Loading → LoadingSkeleton, error → ErrorState, empty → EmptyState
- [ ] All components from governed inventory — no page-local variants

---

### Stage 4C — Admin: Role & Permission Management

**Scope:** Role list, role detail with permissions, assign/revoke role from user

**Deliverables:**
1. `RoleListPage` — DataTable of all roles:
   - Columns: name, key, is_base, is_immutable, permission count, user count
   - Click → role detail
2. `RoleDetailPage` — single role view:
   - Role info (name, key, description, immutability status)
   - Assigned permissions list (with add/remove for non-immutable)
   - Users with this role
3. `PermissionListPage` — read-only DataTable of all permissions:
   - Columns: key, description, roles that have it
4. User role assignment (from UserDetailPage):
   - Assign role dialog (select from available roles)
   - Revoke role (with ConfirmActionDialog)
   - Both call `assign-role` / `revoke-role` edge functions

**API Integration:**

| UI Action | Edge Function / RPC | Permission Required |
|-----------|-------------------|-------------------|
| List roles | Supabase client (RLS: `roles.view`) | `roles.view` |
| View role detail | Supabase client | `roles.view` |
| Assign role to user | `assign-role` | `roles.assign` |
| Revoke role from user | `revoke-role` | `roles.revoke` |
| Assign permission to role | `assign-permission-to-role` | `permissions.assign` |
| Revoke permission from role | `revoke-permission-from-role` | `permissions.revoke` |
| List permissions | Supabase client (RLS: `roles.view`) | `roles.view` |

**Route Conformance (per route-index.md):**

| Route | Route Index Entry | Lifecycle | Notes |
|-------|------------------|-----------|-------|
| `/admin/roles` | ✅ exists | planned → active | |
| `/admin/roles/:id` | ❌ missing | — | Add to route-index |
| `/admin/permissions` | ❌ missing | — | Add to route-index |

**Files Created:**

| File | Action |
|------|--------|
| `src/pages/admin/access/RoleListPage.tsx` | New |
| `src/pages/admin/access/RoleDetailPage.tsx` | New |
| `src/pages/admin/access/PermissionListPage.tsx` | New |
| `src/pages/admin/access/index.ts` | New |
| `src/hooks/useRoles.ts` | New — React Query hooks |
| `src/hooks/useRoleActions.ts` | New — assign/revoke mutations |
| `src/components/admin/AssignRoleDialog.tsx` | New |
| `src/components/admin/ManagePermissionsDialog.tsx` | New |

**Success Criteria:**
- [ ] Role list displays with correct counts using DataTable
- [ ] Role detail shows permissions and users
- [ ] Assign/revoke role works with audit logging
- [ ] Assign/revoke permission on role works
- [ ] Immutable roles cannot have key/base/immutable fields changed
- [ ] Self-superadmin-revocation blocked (409 from backend, friendly error in UI)
- [ ] requireRecentAuth triggers re-authentication when needed
- [ ] All dialogs use governed ConfirmActionDialog pattern

---

### Stage 4D — Admin: Audit Log Viewer

**Scope:** Searchable, filterable audit log viewer

**Deliverables:**
1. `AuditLogPage` — DataTable with:
   - Columns: timestamp, action, actor (display name), target type, target ID
   - Expandable row → full metadata JSON viewer
   - Filters: action type, actor, date range, target type
   - Server-side pagination via `query-audit-logs` edge function
2. Export button → calls `export-audit-logs` edge function
3. Denial events highlighted (action = `auth.permission_denied`)

**API Integration:**

| UI Action | Edge Function | Permission Required |
|-----------|--------------|-------------------|
| Query audit logs | `query-audit-logs` | `audit.view` |
| Export audit logs | `export-audit-logs` | `audit.export` |

**Route Conformance (per route-index.md):**

| Route | Route Index Entry | Lifecycle |
|-------|------------------|-----------|
| `/admin/audit` | ✅ exists | planned → active |

**Files Created:**

| File | Action |
|------|--------|
| `src/pages/admin/audit/AuditLogPage.tsx` | New |
| `src/pages/admin/audit/index.ts` | New |
| `src/hooks/useAuditLogs.ts` | New — React Query hooks |
| `src/components/admin/AuditMetadataViewer.tsx` | New — JSON tree viewer |
| `src/components/admin/AuditActionBadge.tsx` | New — color-coded action badges |

**Success Criteria:**
- [ ] Audit logs load with pagination using DataTable
- [ ] Filters work (action, actor, date range)
- [ ] Metadata expandable and readable
- [ ] Export downloads CSV
- [ ] Denial events visually distinct
- [ ] No sensitive data displayed (metadata sanitization verified)
- [ ] All async states use governed LoadingSkeleton/ErrorState/EmptyState

---

### Stage 4E — User Panel

**Scope:** Profile management, MFA configuration, session info

**Deliverables:**
1. `UserDashboard` page (at `/dashboard`) — welcome + quick links
2. `ProfilePage` (at `/settings`) — view/edit own profile:
   - Display name (editable)
   - Avatar (display, future: upload)
   - Email (read-only)
   - Email verification status
   - Calls `update-profile` edge function
3. `SecurityPage` (at `/settings/security`) — MFA + sessions:
   - Current MFA status
   - Link to enroll/unenroll TOTP
   - Session info (last sign-in, session metadata)
   - Recovery codes placeholder (when DW-008 is implemented)

**API Integration:**

| UI Action | Edge Function / RPC | Permission Required |
|-----------|-------------------|-------------------|
| View own profile | `get-profile` | `users.view_self` |
| Update own profile | `update-profile` | `users.edit_self` |
| MFA enroll | Supabase Auth MFA API | authenticated |
| MFA unenroll | Supabase Auth MFA API | authenticated |

**Route Conformance (per route-index.md):**

| Route | Route Index Entry | Lifecycle |
|-------|------------------|-----------|
| `/dashboard` | ✅ exists | planned → active |
| `/settings` | ✅ exists | planned → active |
| `/settings/security` | ✅ exists | planned → active |

**Files Created:**

| File | Action |
|------|--------|
| `src/pages/user/UserDashboard.tsx` | New |
| `src/pages/user/ProfilePage.tsx` | New |
| `src/pages/user/SecurityPage.tsx` | New |
| `src/pages/user/index.ts` | New |
| `src/hooks/useProfile.ts` | New — React Query hooks |
| `src/hooks/useProfileMutations.ts` | New — update profile mutation |

**Success Criteria:**
- [ ] User can view and edit own profile
- [ ] MFA status displayed correctly
- [ ] Profile update calls edge function with audit logging
- [ ] Self-scope enforced (cannot edit other users' profiles)
- [ ] Loading/error states use governed components
- [ ] Toast feedback on save
- [ ] Same shell, dialog, form, card components as admin pages

---

### Stage 4F — Deferred Admin Surfaces (EXPLICITLY DEFERRED)

**Status:** Deferred to Phase 5/6 — backend infrastructure not yet built

The following admin-panel.md scope items have NO backend implementation yet and are **explicitly excluded** from Phase 4:

| Surface | admin-panel.md Scope | Why Deferred | Deferred To |
|---------|---------------------|--------------|-------------|
| Health Dashboard | `monitoring.view` | No health-check endpoint or monitoring backend exists | Phase 5 (Health & Monitoring) |
| Alert Configuration | `monitoring.configure` | No alert system backend exists | Phase 5 |
| System Config UI | `admin.config` | No config management backend exists | Phase 5 |
| Jobs Dashboard | `jobs.view` | No job/scheduler backend exists | Phase 5 (Jobs & Scheduler) |
| Job Trigger | `jobs.trigger` | No job trigger backend exists | Phase 5 |
| Dead-Letter Management | `jobs.deadletter.manage` | No dead-letter backend exists | Phase 5 |
| Emergency Kill Switch | `jobs.emergency` | No kill switch backend exists | Phase 5 |

**Rule:** These routes remain `planned` in route-index.md. They will be implemented when their backend modules (health-monitoring, jobs-and-scheduler) are built. Corresponding deferred work entries: DW-016, DW-017.

### Stage 4G — Deferred User Panel Features (EXPLICITLY DEFERRED)

**Status:** Deferred — requires backend work or Supabase features not yet integrated

| Feature | user-panel.md Scope | Why Deferred | Deferred To |
|---------|---------------------|--------------|-------------|
| Password Change | Password change flow | Requires Supabase `updateUser()` integration + re-auth flow | Phase 4 follow-up or Phase 5 |
| Session Revocation | Session visibility + revoke | Supabase session revocation API not yet integrated | Phase 4 follow-up or Phase 5 |
| Notification Preferences | Notification/preferences management | No notification system backend exists | Phase 5+ |

**Rule:** Stage 4E delivers profile editing, MFA status/enrollment, and session info (read-only). The deferred features above require dedicated backend work first. Corresponding deferred work entries: DW-018, DW-019, DW-020.

---

## Cross-Stage Requirements

### Shell Uniformity Rule

Admin and user panels share the same:
- `DashboardLayout` shell
- `DashboardSidebar` component (different nav config)
- `DashboardHeader` component
- `ConfirmActionDialog` for destructive actions
- `DataTable` for all tabular data
- `EmptyState` / `ErrorState` / `LoadingSkeleton` for async states
- Form field styles, card styles, badge styles

User pages may simplify **content** (fewer fields, fewer actions), but NOT **shell language**.

### Accessibility Baseline
- All interactive elements keyboard navigable
- Focus visible indicators
- ARIA labels on icon-only buttons
- Color contrast meets WCAG AA in both themes
- `prefers-reduced-motion` respected

### Error Handling Pattern
- API errors → toast with user-friendly message
- Permission denied → `AccessDenied` page within shell (not blank/hidden)
- Network failure → ErrorState with retry button
- Loading → LoadingSkeleton (not spinner)

### Auth Guard Loading
- `RequireAuth` loading state should use LoadingSkeleton pattern (not spinner) — update when Stage 4A components are available

### Deferred Work Integration
- **DW-008 (MFA Recovery Codes):** Stage 4E SecurityPage will include placeholder for recovery codes.
- **DW-016/DW-017:** Admin monitoring/jobs/config UI deferred to Phase 5.
- **DW-018/DW-019/DW-020:** User password change, session revocation, notification preferences deferred.

---

## Route Plan (Reconciled with route-index.md)

| Route | Page | Permission | Stage | Route Index |
|-------|------|-----------|-------|-------------|
| `/admin` | AdminDashboard | `admin.access` + `users.view_all` | 4B | ✅ exists |
| `/admin/users` | UserListPage | `admin.access` + `users.view_all` | 4B | ✅ exists |
| `/admin/users/:id` | UserDetailPage | `admin.access` + `users.view_all` | 4B | ✅ exists |
| `/admin/roles` | RoleListPage | `admin.access` + `roles.view` | 4C | ✅ exists |
| `/admin/roles/:id` | RoleDetailPage | `admin.access` + `roles.view` | 4C | ➕ add |
| `/admin/permissions` | PermissionListPage | `admin.access` + `roles.view` | 4C | ➕ add |
| `/admin/audit` | AuditLogPage | `admin.access` + `audit.view` | 4D | ✅ exists |
| `/dashboard` | UserDashboard | authenticated | 4E | ✅ exists |
| `/settings` | ProfilePage | `profile.self_manage` | 4E | ✅ exists |
| `/settings/security` | SecurityPage | `mfa.self_manage` + `session.self_manage` | 4E | ✅ exists |

---

## Regression Protection

**Explicitly preserved (no changes permitted):**
- All edge function behavior and response shapes
- SQL functions: `has_permission()`, `has_role()`, `is_superadmin()`
- RLS policies
- Audit event schemas
- Existing auth flows (sign-in, sign-up, forgot-password, MFA)

**New frontend code must NOT:**
- Bypass server-side authorization (UI hiding is supplementary, not enforcement)
- Store roles/permissions in localStorage
- Hardcode role names for access decisions (use permission checks)
- Modify edge functions or database schema
- Introduce components not in governed component inventory
- Use raw colors outside semantic token system
- Create page-local dialog/table/form/card variants

---

## Closure Outputs (post-execution)

After all stages executed and verified:
- `docs/07-reference/route-index.md` — update lifecycle of new routes to `active`
- `docs/07-reference/component-inventory.md` — reconcile with actual components
- `docs/00-governance/system-state.md` — update module statuses
- `docs/08-planning/master-plan.md` — update Phase 4 gate checkboxes with evidence
- `docs/08-planning/deferred-work-register.md` — update DW-008 status if applicable
