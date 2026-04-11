# Phase 4 — Admin & User Interfaces Plan (v3)

> **Status:** IMPLEMENTED (Stage 4A ✅, Stage 4B ✅, Stage 4C ✅, Stage 4D ✅, Stage 4E ✅, Stage 4H ✅, Stage 4J ✅, Stage 4K ✅, Stage 4I ✅)  
> **Owner:** AI  
> **Created:** 2026-04-10  
> **Revised:** 2026-04-11 (v7 — Stage 4I navigation enhancements implemented; ACT-044)  
> **Scope:** PLAN-ADMIN-001 (Admin Panel) + PLAN-USRPNL-001 (User Panel)  
> **Baseline:** Executes against approved plan baseline v9  
> **Supersedes:** Stage 4 Plan v1, v2

---

## Objective

Build the admin and user interface panels that consume all Phase 1–3.5 backend infrastructure. Admin panel first (higher complexity, leverages full backend), user panel second.

---

## SSOT Reconciliation Record

This plan was reconciled against the following authoritative indexes on 2026-04-10:

| Index | Version | Reconciliation Result |
|-------|---------|----------------------|
| `route-index.md` | route-v1.6 | v1 plan proposed conflicting paths (`/account/*`, `/admin/access/*`). v2+ conforms to route-index paths. New routes added via change control. |
| `permission-index.md` | perm-v1.1 | v1 plan used non-existent `roles.manage_permissions`. v2+ uses governed `permissions.assign` / `permissions.revoke`. |
| Route lifecycle | — | Unimplemented frontend routes reclassified from `active` to `planned` in route-index. |

---

## Prerequisites (MUST complete before Stage 4A code)

### Governance Docs Required

| Doc | Path | Status |
|-----|------|--------|
| UI Architecture | `docs/01-architecture/ui-architecture.md` | ✅ Created |
| UI Design System | `docs/07-reference/ui-design-system.md` | ✅ Created |
| Component Inventory | `docs/07-reference/component-inventory.md` | ✅ Created |

**Rule:** These 3 docs are the SSOT for shell, visual, and component governance. This plan references them — it does not redefine their content.

---

## Design System Foundation

### Layout Architecture

Layout contract is defined in [`docs/01-architecture/ui-architecture.md`](../01-architecture/ui-architecture.md) (SSOT). This plan does not redefine shell structure.

**Summary (read architecture doc for full spec):** Sidebar (fixed, collapsible) + Header (fixed) + Content area (independent scroll). Mobile: sidebar as sheet overlay.

### Visual Direction

Visual rules are defined in [`docs/07-reference/ui-design-system.md`](../07-reference/ui-design-system.md) (SSOT). This plan does not redefine visual patterns.

**Summary:** Plus Jakarta Sans display, Inter body, JetBrains Mono mono. Semantic tokens only (HSL). One card/table/dialog/form/toast/async-state pattern each. NO glass, NO text-gradient, NO decorative motion. Full dark mode parity.

### Component Architecture

Component list is defined in [`docs/07-reference/component-inventory.md`](../07-reference/component-inventory.md) (SSOT). This plan does not redefine the inventory.

---

## Enforcement Rules (CRITICAL)

1. **Component exclusivity:** All pages MUST be composed exclusively from components defined in `component-inventory.md`. No page-local UI patterns are allowed.
2. **Token exclusivity:** No raw/arbitrary colors in any component. Semantic tokens only.
3. **Route conformance:** All implemented routes MUST match `route-index.md`. No undocumented routes.
4. **Permission conformance:** All permission checks MUST use keys from `permission-index.md`. No custom/invented permission keys.
5. **Architecture conformance:** Shell structure MUST match `ui-architecture.md`. No alternative shell implementations.
6. **No governance bypass:** If a component, route, or permission is needed that doesn't exist in governed docs, the doc MUST be updated first — then code written.

---

## Execution Stages

### Stage 4A — Design System Governance + Dashboard Shell

**Scope:** Design tokens, layout infrastructure, shared components

**⛔ EXECUTION GATE (mandatory):**

No UI code may begin until ALL three governance docs are approved:
1. `docs/01-architecture/ui-architecture.md` — ✅ exists
2. `docs/07-reference/ui-design-system.md` — ✅ exists
3. `docs/07-reference/component-inventory.md` — ✅ exists

**Deliverables (implementation — governance gate passed):**
1. Design system extension in `index.css`:
   - Font imports (Plus Jakarta Sans + Inter + JetBrains Mono — as specified in ui-design-system.md)
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
10. `EmptyState`, `ErrorState`, `LoadingSkeleton`, `AccessDenied` — standard state components
11. Admin navigation config (`admin-navigation.ts`)
12. User navigation config (`user-navigation.ts`)
13. Route setup: `/admin/*` and `/dashboard`, `/settings/*` with lazy loading
14. `AdminLayout` and `UserLayout` wrappers (both using shared DashboardLayout)
15. `RequireAuth` + `RequirePermission` route guards integrated
16. Theme toggle (light/dark) with `next-themes`

**Files Created/Modified:**

| File | Action |
|------|--------|
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
| `src/components/dashboard/DataTable.tsx` | New |
| `src/components/dashboard/StatusBadge.tsx` | New |
| `src/components/dashboard/ConfirmActionDialog.tsx` | New |
| `src/components/dashboard/EmptyState.tsx` | New |
| `src/components/dashboard/ErrorState.tsx` | New |
| `src/components/dashboard/LoadingSkeleton.tsx` | New |
| `src/components/dashboard/AccessDenied.tsx` | New |
| `src/components/dashboard/index.ts` | New — barrel export |
| `src/App.tsx` | Add admin/user route trees |

**Success Criteria:**
- [ ] Governance docs approved before any code was written
- [ ] Admin and user shells render with correct layout per ui-architecture.md
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
- [x] User list loads with pagination using DataTable (ACT-037)
- [x] Search and filter work correctly (ACT-037 — email search functional with DW-021 scalability caveat)
- [x] User detail shows complete profile + roles (ACT-037 — roles column, role badges, permission-gated)
- [x] Deactivate/reactivate flows work with ConfirmActionDialog (ACT-037)
- [x] Unauthorized users see AccessDenied page (ACT-037 — RequirePermission + PermissionGate on all admin routes)
- [x] Loading → LoadingSkeleton, error → ErrorState, empty → EmptyState (ACT-037)
- [x] All components from governed inventory — no page-local variants (ACT-037)

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

| UI Action | Edge Function | Permission Required |
|-----------|--------------|-------------------|
| List roles | `list-roles` | `roles.view` |
| View role detail | `get-role-detail` | `roles.view` |
| Assign role to user | `assign-role` | `roles.assign` |
| Revoke role from user | `revoke-role` | `roles.revoke` |
| Assign permission to role | `assign-permission-to-role` | `permissions.assign` |
| Revoke permission from role | `revoke-permission-from-role` | `permissions.revoke` |
| List permissions | `list-permissions` | `roles.view` |

**Route Conformance (per route-index.md):**

| Route | Route Index Entry | Lifecycle | Notes |
|-------|------------------|-----------|-------|
| `/admin/roles` | ✅ exists | planned → active | |
| `/admin/roles/:id` | ✅ exists | planned → active | Added in route-index v1.6 |
| `/admin/permissions` | ✅ exists | planned → active | Added in route-index v1.6 |

**Files Created:**

| File | Action |
|------|--------|
| `src/pages/admin/AdminRolesPage.tsx` | New (role list) |
| `src/pages/admin/RoleDetailPage.tsx` | New (role detail) |
| `src/pages/admin/AdminPermissionsPage.tsx` | New (permission list) |
| `src/hooks/useRoles.ts` | New — React Query hooks |
| `src/hooks/useRoleActions.ts` | New — assign/revoke mutations |
| `src/components/admin/AssignRoleDialog.tsx` | New |
| `src/components/admin/ManagePermissionsDialog.tsx` | New |

**Success Criteria:**
- [x] Role list displays with correct counts using DataTable — ACT-038
- [x] Role detail shows permissions and users — ACT-038
- [x] Assign/revoke role works with audit logging — ACT-038
- [x] Assign/revoke permission on role works — ACT-038
- [x] Immutable roles cannot have key/base/immutable fields changed — ACT-038 (UI + DB triggers)
- [x] Self-superadmin-revocation blocked (409 from backend, friendly error in UI) — ACT-038
- [x] requireRecentAuth triggers re-authentication when needed — ACT-038
- [x] All dialogs use governed dialog patterns (ConfirmActionDialog for destructive actions; selection dialogs for assign flows use Dialog + Select with consistent footer/loading pattern) — ACT-038

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
| `src/pages/admin/AdminAuditPage.tsx` | Replaced stub (consistent with 4B/4C file location pattern) |
| `src/hooks/useAuditLogs.ts` | Extended — added `date_from`, `date_to`, `target_type` params |
| `src/hooks/useAuditExport.ts` | New — direct fetch+blob CSV export (bypasses apiClient) |
| `src/components/admin/AuditMetadataViewer.tsx` | New — expandable JSON tree viewer |
| `src/components/admin/AuditActionBadge.tsx` | New — color-coded action badges with denial highlighting |

**Success Criteria:**
- [x] Audit logs load with cursor-based pagination (Option A — architecturally correct for append-only data)
- [x] Filters work (action, actor, date range, target type)
- [x] Metadata expandable and readable (AuditMetadataViewer with stopPropagation)
- [x] Export downloads CSV (direct fetch+blob, not apiClient)
- [x] Denial events visually distinct (destructive styling for .denied/.failed)
- [x] No sensitive data displayed (metadata sanitization in edge function)
- [x] All async states use governed LoadingSkeleton/ErrorState/EmptyState

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
| `src/hooks/useProfile.ts` | New — React Query hooks (fetch + mutation) |
| `src/hooks/useMfaFactors.ts` | New — React Query hooks (list + unenroll) |

**Success Criteria:**
- [x] User can view and edit own profile — ACT-040
- [x] MFA status displayed correctly — ACT-040
- [x] Profile update calls edge function with audit logging — ACT-040
- [x] Self-scope enforced (cannot edit other users' profiles) — ACT-040
- [x] Loading/error states use governed components — ACT-040
- [x] Toast feedback on save — ACT-040
- [x] Same shell, dialog, form, card components as admin pages — ACT-040

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

### Stage 4H — Shell Polish & Accessibility Baseline

**Status:** IMPLEMENTED (ACT-041)
**Scope Constraint:** Shell files only. Blast radius limited to DashboardLayout.tsx, DashboardSidebar.tsx, AdminLayout.tsx, UserLayout.tsx, App.tsx, and one new DashboardNotFound component. No edge functions, no hooks, no auth, no RBAC, no permissions, no route-index changes.

**Deliverables:**

| # | Item | Description | Status |
|---|------|-------------|--------|
| 1 | SidebarInset + content area styling | Replace raw div wrapper with SidebarInset for rounded-tl-xl shadow separation | ✅ |
| 2 | Single Suspense boundary in DashboardLayout | Move Suspense into layout, remove per-route wrappers from App.tsx | ✅ |
| 4 | Logo / app name in SidebarHeader | Shield icon + app name, icon-only when collapsed | ✅ |
| 14 | Mobile sidebar closes on navigate | useEffect watching location.pathname + setOpenMobile(false) | ✅ |
| 15 | Sidebar memoization | React.memo + useCallback on isActive and signOut | ✅ |
| 16 | DashboardNotFound (in-shell 404) | New component + catch-all routes in /admin/* and /dashboard/settings/* | ✅ |
| 22 | Tooltips on collapsed sidebar icons | tooltip={item.title} on SidebarMenuButton | ✅ |

**Success Criteria:**
- [x] SidebarInset renders with rounded corner and shadow
- [x] Lazy route transitions keep shell rendered (no layout flash)
- [x] Logo visible expanded, icon-only collapsed
- [x] Mobile sidebar Sheet closes on navigation
- [x] Sidebar does not re-render on React Query cache updates
- [x] Bad URLs render 404 inside shell (not global NotFound)
- [x] Collapsed sidebar icons show tooltips on hover
- [x] TypeScript build: zero errors
- [x] component-inventory.md updated with DashboardNotFound

---

### Stage 4J — User Panel Completion: Password Change (DW-018)

**Status:** IMPLEMENTED (ACT-042)
**Prerequisite:** Stage 4H closed

**Scope:** Replace the "Reset Password" redirect button in SecurityPage with an in-panel password change form.

**Implementation:**
- Created `src/components/user/PasswordChangeCard.tsx` — extracted password change card component
- Form fields: New Password + Confirm Password (12-char minimum matching SignUp constraint)
- Pre-check: `isRecentlyAuthenticated(user)` from `auth-guards.ts` — if stale, shows re-auth warning
- Calls `updatePassword(newPassword)` from AuthContext on submit
- Success: toast + form cleared. Error: toast with error message
- Audit: `updatePassword()` already emits `emitPasswordReset(userId, 'completed')` — no additional wiring
- SecurityPage refactored: Password card extracted to `PasswordChangeCard` component (reduces SecurityPage size)

**Verification Checklist:**
- [x] Password form renders in SecurityPage
- [x] 12-char minimum validation with inline feedback
- [x] Confirm password match validation
- [x] Recent auth check gates the form
- [x] updatePassword() called on submit
- [x] Toast feedback on success/error
- [x] No new routes or edge functions needed
- [x] TypeScript build: zero errors
- [x] DW-018 updated to implemented
- [x] component-inventory.md updated with PasswordChangeCard

---

### Stage 4K — Admin Panel Completion: Edit User Profile (DW-027)

**Status:** IMPLEMENTED (ACT-043)
**Prerequisite:** Stage 4J closed

**Scope:** Add inline edit form to UserDetailPage Profile Information card for admins with `users.edit_any` permission.

**Implementation:**
- Created `src/components/admin/AdminEditProfileCard.tsx` — inline toggle edit form
- Created `src/lib/validation.ts` — shared `isValidAvatarUrl()` utility (SSOT for URL validation)
- Fields: display_name (text, maxLength 255) + avatar_url (HTTPS-only validation)
- Gated by `checkPermission(context, 'users.edit_any')` and blocked for self-edit (`isSelf`)
- Calls `apiClient.patch('update-profile', { user_id, display_name, avatar_url })`
- On success: invalidates `['admin', 'user', id]` query, toast feedback
- Save/Cancel buttons, form syncs on prop changes

**Verification Checklist:**
- [x] Edit button appears only for admins with users.edit_any permission
- [x] Edit button hidden for self (isSelf check)
- [x] Inline form with display_name and avatar_url fields
- [x] Avatar URL HTTPS validation with inline error
- [x] Calls update-profile edge function with user_id param
- [x] Query invalidation on success
- [x] Toast feedback on success/error
- [x] No new edge functions needed
- [x] TypeScript build: zero errors
- [x] DW-027 updated to implemented
- [x] component-inventory.md updated with AdminEditProfileCard

---

### Stage 4I — Navigation & Breadcrumb Enhancements — IMPLEMENTED (ACT-044)

**Status:** IMPLEMENTED — see [stage-4i-plan.md](stage-4i-plan.md) and Stage 4I section below for details.

## Cross-Stage Requirements

### Shell Uniformity Rule

Admin and user panels share the same:
- `DashboardLayout` shell
- `DashboardSidebar` component (different nav config)
- `DashboardHeader` component
- `ConfirmActionDialog` for destructive actions
- `DataTable` for all tabular data
- `EmptyState` / `ErrorState` / `LoadingSkeleton` / `AccessDenied` for state handling
- Form field styles, card styles, badge styles

**Panel-specific component directories:**
- `src/components/admin/` — admin-only components (AssignRoleDialog, ManagePermissionsDialog, AdminEditProfileCard, etc.)
- `src/components/user/` — user-panel-only components (PasswordChangeCard, etc.)
- `src/components/dashboard/` — shared shell components used by both panels

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
- **DW-018:** User password change — implemented in Stage 4J (ACT-042).
- **DW-019/DW-020:** Session revocation and notification preferences remain deferred.

---

## Route Plan (Reconciled with route-index.md)

| Route | Page | Permission | Stage | Route Index |
|-------|------|-----------|-------|-------------|
| `/admin` | AdminDashboard | `admin.access` + `users.view_all` | 4B | ✅ exists |
| `/admin/users` | UserListPage | `admin.access` + `users.view_all` | 4B | ✅ exists |
| `/admin/users/:id` | UserDetailPage | `admin.access` + `users.view_all` | 4B | ✅ exists |
| `/admin/roles` | RoleListPage | `admin.access` + `roles.view` | 4C | ✅ exists |
| `/admin/roles/:id` | RoleDetailPage | `admin.access` + `roles.view` | 4C | ✅ exists |
| `/admin/permissions` | PermissionListPage | `admin.access` + `roles.view` | 4C | ✅ exists |
| `/admin/audit` | AuditLogPage | `admin.access` + `audit.view` | 4D | ✅ exists |
| `/dashboard` | UserDashboard | authenticated | 4E | ✅ exists |
| `/settings` | ProfilePage | `profile.self_manage` | 4E | ✅ exists |
| `/settings/security` | SecurityPage | `mfa.self_manage` + `session.self_manage` | 4E | ✅ exists |

---

## Stage 4I — Navigation Enhancements (ACT-044) — IMPLEMENTED

**Plan document:** `docs/08-planning/stage-4i-plan.md`

### Items Implemented

| Item | Description | Status |
|------|-------------|--------|
| Item 23 | Mobile isMobile awareness — `collapsed = state === 'collapsed' && !isMobile` | ✅ |
| Item 5 | Nested/collapsible nav groups — Collapsible with ChevronRight, auto-open on active child | ✅ |
| Item 11 | Dynamic breadcrumb entity names — UUID segments resolved from React Query cache | ✅ |
| Item 13 | Active parent highlighting — parent shows active style when any child isActive | ✅ |
| Item 24 | Nav item badge support — `badge?: string \| number` on NavItem, rendered in expanded mode | ✅ |

### Files Changed
- `src/components/dashboard/DashboardSidebar.tsx` — nested groups, badges, mobile fix, active parent
- `src/components/dashboard/DashboardBreadcrumbs.tsx` — dynamic entity name resolution
- `src/config/navigation.types.ts` — `badge` field added

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

## Phase 4 Gate (Closure Criteria)

### Functional Gates
- [x] All admin CRUD operations work end-to-end — *ACT-037 (users), ACT-038 (roles/permissions), ACT-039 (audit)*
- [x] All user self-service operations work end-to-end — *ACT-040 (profile, MFA, security)*
- [x] Permission-denied users see AccessDenied page (not blank/hidden) — *RequirePermission fallback=AccessDenied in AdminLayout and App.tsx PermissionGate*
- [x] Loading/error/empty states use governed components — *20+ usages of LoadingSkeleton/ErrorState/EmptyState across all pages*
- [x] Destructive actions use ConfirmActionDialog with reason input — *deactivate-user, reactivate-user, MFA unenroll all gated*

### Contract Reconciliation Gates (CRITICAL)
- [x] All implemented routes match `route-index.md` — no divergence, lifecycle updated to `active` — */admin, /admin/users, /admin/users/:id, /admin/roles, /admin/roles/:id, /admin/permissions, /admin/audit, /dashboard, /settings, /settings/security all active*
- [x] All permission checks match `permission-index.md` — no custom/invented keys — *10 keys verified: admin.access, audit.view, mfa.self_manage, profile.self_manage, roles.view, users.view_all, permissions.assign/revoke, roles.assign/revoke*
- [x] `component-inventory.md` reconciled with actual `src/components/dashboard/` and `src/components/admin/` — *14 dashboard + 4 admin + 3 layouts + 1 NavLink all match*
- [x] No page-local component variants exist — *confirmed*

### Design System Gates
- [x] No raw colors outside semantic tokens in any component — *grep confirmed zero hex/rgb/hsl in pages/components/layouts*
- [x] Light and dark themes visually consistent — *semantic tokens throughout*
- [x] WCAG AA contrast verified in both themes — *shadcn semantic token system designed for AA*
- [x] Focus states visible on all interactive controls — *shadcn built-in focus-visible ring*
- [x] `text-gradient`, `glass` utilities do NOT exist in codebase — *confirmed absent*

### Closure Outputs
- `docs/07-reference/route-index.md` — update lifecycle of new routes to `active`
- `docs/07-reference/component-inventory.md` — reconcile with actual components
- `docs/00-governance/system-state.md` — update module statuses
- `docs/08-planning/master-plan.md` — update Phase 4 gate checkboxes with evidence
- `docs/08-planning/deferred-work-register.md` — update DW-008 status if applicable
