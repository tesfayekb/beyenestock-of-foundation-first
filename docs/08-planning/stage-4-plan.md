# Phase 4 — Admin & User Interfaces Plan (v1)

> **Status:** PROPOSED — awaiting approval  
> **Owner:** AI  
> **Created:** 2026-04-10  
> **Scope:** PLAN-ADMIN-001 (Admin Panel) + PLAN-USRPNL-001 (User Panel)  
> **Baseline:** Executes against approved plan baseline v9  
> **Design Reference:** [Apex Marketplace](/projects/7feff7b5-c4c9-4ec9-8b62-41d2f462aa64) — sidebar + top nav + content area layout, TailAdmin-inspired dark chrome, bold & modern aesthetic

---

## Objective

Build the admin and user interface panels that consume all Phase 1–3.5 backend infrastructure. Admin panel first (higher complexity, leverages full backend), user panel second.

---

## Design System Foundation

### Layout Architecture (from Apex Marketplace reference)

- **Shell pattern:** Sidebar (collapsible icon mode) + top header + content area
- **Sidebar:** Dark chrome (`bg-sidebar`), collapsible to icon strip, section headers, permission-filtered navigation, sign-out in footer
- **Header:** Sticky top bar with sidebar trigger, search (desktop), theme toggle, notifications badge, user menu avatar
- **Content area:** Light/dark adaptive background (`bg-content`), rounded top-left corner, breadcrumbs, nested `<Suspense>` for lazy route loading
- **Mobile:** Bottom navigation bar, sidebar via sheet, responsive content padding

### Visual Direction: Bold & Modern

- **Typography:** Display font (Bricolage Grotesque or similar) for headings, Inter for body, JetBrains Mono for code/IDs
- **Color:** Brand color scale (10 shades), semantic tokens for success/warning/destructive/info
- **Depth:** Content shadow (`--content-shadow`), card elevation, glass effects
- **Motion:** `animate-in fade-in` transitions, collapsible animations, skeleton loading states
- **Dark mode:** Full dark mode support with proper token switching

### Component Architecture

| Component | Purpose | Reused Across |
|-----------|---------|---------------|
| `DashboardLayout` | Shell wrapper (sidebar + header + outlet) | Admin, User panels |
| `DashboardSidebar` | Permission-filtered nav with sections | Admin, User panels |
| `DashboardHeader` | Top bar (trigger, search, theme, user menu) | Admin, User panels |
| `DashboardBreadcrumbs` | Route-aware breadcrumb trail | All dashboard pages |
| `StatCard` | Metric display card | Dashboard home pages |
| `DataTable` | Sortable, filterable table with pagination | Users, Roles, Audit |
| `UserMenu` | Avatar dropdown with profile/settings/sign-out | All authenticated pages |
| `NavItem` type | Navigation config with permission gating | Admin, User configs |

---

## Execution Stages

### Stage 4A — Dashboard Shell & Design System

**Scope:** Layout infrastructure, design tokens, shared components

**Deliverables:**
1. Design system overhaul in `index.css`:
   - Font imports (display + body + mono)
   - Brand color scale (10 shades via `--brand-50` through `--brand-950`)
   - Semantic tokens: `--header-*`, `--content-*`, `--shadow-*` variants
   - Dark mode tokens
   - Utility classes: `.font-display`, `.text-gradient`, `.glass`
2. `tailwind.config.ts` updates for new tokens
3. Navigation type system: `NavItem` interface with permission gating
4. `DashboardLayout` component (SidebarProvider + Sidebar + Header + Outlet)
5. `DashboardSidebar` — permission-filtered, section headers, collapsible groups, active state
6. `DashboardHeader` — sidebar trigger, user menu, theme toggle
7. `UserMenu` component — avatar, display name, sign-out
8. Admin navigation config (`admin-navigation.ts`)
9. User navigation config (`user-navigation.ts`)
10. Route setup: `/admin/*` and `/account/*` with lazy loading
11. `AdminLayout` and `AccountLayout` wrappers
12. `RequireAuth` + `RequirePermission` route guards integrated

**Files Created/Modified:**

| File | Action |
|------|--------|
| `src/index.css` | Major overhaul — design system tokens |
| `tailwind.config.ts` | Add brand/header/content/shadow tokens |
| `src/config/navigation.types.ts` | New — NavItem interface |
| `src/config/admin-navigation.ts` | New — admin nav config |
| `src/config/user-navigation.ts` | New — user nav config |
| `src/layouts/DashboardLayout.tsx` | New — shell component |
| `src/layouts/AdminLayout.tsx` | New — admin wrapper |
| `src/layouts/AccountLayout.tsx` | New — user wrapper |
| `src/components/dashboard/DashboardSidebar.tsx` | New |
| `src/components/dashboard/DashboardHeader.tsx` | New |
| `src/components/dashboard/UserMenu.tsx` | New |
| `src/components/dashboard/DashboardBreadcrumbs.tsx` | New |
| `src/components/dashboard/StatCard.tsx` | New |
| `src/components/dashboard/index.ts` | New — barrel export |
| `src/App.tsx` | Add admin/account route trees |

**Success Criteria:**
- [ ] Admin and user shells render with correct layout
- [ ] Sidebar collapses to icon mode and expands
- [ ] Navigation items filtered by user permissions
- [ ] Active route highlighted in sidebar
- [ ] User menu shows display name + sign-out
- [ ] Dark mode toggle works
- [ ] Mobile responsive (sidebar as sheet, bottom nav)
- [ ] Lazy-loaded routes with skeleton fallback
- [ ] No permission-filtered routes accessible via direct URL without permission

---

### Stage 4B — Admin: User Management

**Scope:** User list, user detail, deactivate/reactivate actions

**Deliverables:**
1. `AdminDashboard` page — overview stats (total users, active, deactivated, roles breakdown)
2. `UserListPage` — data table with:
   - Columns: display name, email, status, roles, created date
   - Search/filter by name, email, status
   - Pagination (server-side via `list-users` edge function)
   - Row click → user detail
3. `UserDetailPage` — single user view:
   - Profile info (display name, avatar, email verified status, created/updated)
   - Current roles (with role badges)
   - Action buttons: deactivate/reactivate (with confirmation dialog)
   - Audit trail for this user (filtered by `actor_id` or `target_id`)
4. Deactivate/Reactivate flows:
   - Confirmation dialog with reason input
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

**Files Created:**

| File | Action |
|------|--------|
| `src/pages/admin/AdminDashboard.tsx` | New |
| `src/pages/admin/users/UserListPage.tsx` | New |
| `src/pages/admin/users/UserDetailPage.tsx` | New |
| `src/pages/admin/users/index.ts` | New |
| `src/hooks/useUsers.ts` | New — React Query hooks for user API |
| `src/hooks/useUserActions.ts` | New — deactivate/reactivate mutations |
| `src/components/admin/UserStatusBadge.tsx` | New |
| `src/components/admin/ConfirmActionDialog.tsx` | New |

**Success Criteria:**
- [ ] User list loads with pagination
- [ ] Search and filter work correctly
- [ ] User detail shows complete profile + roles
- [ ] Deactivate/reactivate flows work with confirmation
- [ ] Unauthorized users see "Access Denied" (not hidden routes)
- [ ] Loading and error states for all async operations
- [ ] Actions audit-logged (verified via audit log viewer later)

---

### Stage 4C — Admin: Role & Permission Management

**Scope:** Role list, role detail with permissions, assign/revoke role from user

**Deliverables:**
1. `RoleListPage` — table of all roles:
   - Columns: name, key, is_base, is_immutable, permission count, user count
   - Click → role detail
2. `RoleDetailPage` — single role view:
   - Role info (name, key, description, immutability status)
   - Assigned permissions list (with add/remove for non-immutable)
   - Users with this role
3. `PermissionListPage` — read-only table of all permissions:
   - Columns: key, description, roles that have it
4. User role assignment (from UserDetailPage):
   - Assign role dialog (select from available roles)
   - Revoke role (with confirmation)
   - Both call `assign-role` / `revoke-role` edge functions

**API Integration:**

| UI Action | Edge Function / RPC | Permission Required |
|-----------|-------------------|-------------------|
| List roles | Supabase client (RLS: `roles.view`) | `roles.view` |
| View role detail | Supabase client | `roles.view` |
| Assign role to user | `assign-role` | `roles.assign` |
| Revoke role from user | `revoke-role` | `roles.revoke` |
| Assign permission to role | `assign-permission-to-role` | `roles.manage_permissions` |
| Revoke permission from role | `revoke-permission-from-role` | `roles.manage_permissions` |
| List permissions | Supabase client (RLS: `roles.view`) | `roles.view` |

**Files Created:**

| File | Action |
|------|--------|
| `src/pages/admin/access/RoleListPage.tsx` | New |
| `src/pages/admin/access/RoleDetailPage.tsx` | New |
| `src/pages/admin/access/PermissionListPage.tsx` | New |
| `src/pages/admin/access/index.ts` | New |
| `src/hooks/useRoles.ts` | New — React Query hooks |
| `src/hooks/useRoleActions.ts` | New — assign/revoke mutations |
| `src/components/admin/RoleBadge.tsx` | New |
| `src/components/admin/AssignRoleDialog.tsx` | New |
| `src/components/admin/ManagePermissionsDialog.tsx` | New |

**Success Criteria:**
- [ ] Role list displays with correct counts
- [ ] Role detail shows permissions and users
- [ ] Assign/revoke role works with audit logging
- [ ] Assign/revoke permission on role works
- [ ] Immutable roles cannot have key/base/immutable fields changed
- [ ] Self-superadmin-revocation blocked (409 from backend, friendly error in UI)
- [ ] requireRecentAuth triggers re-authentication when needed

---

### Stage 4D — Admin: Audit Log Viewer

**Scope:** Searchable, filterable audit log viewer

**Deliverables:**
1. `AuditLogPage` — data table with:
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

**Files Created:**

| File | Action |
|------|--------|
| `src/pages/admin/audit/AuditLogPage.tsx` | New |
| `src/pages/admin/audit/index.ts` | New |
| `src/hooks/useAuditLogs.ts` | New — React Query hooks |
| `src/components/admin/AuditMetadataViewer.tsx` | New — JSON tree viewer |
| `src/components/admin/AuditActionBadge.tsx` | New — color-coded action badges |

**Success Criteria:**
- [ ] Audit logs load with pagination
- [ ] Filters work (action, actor, date range)
- [ ] Metadata expandable and readable
- [ ] Export downloads CSV/JSON
- [ ] Denial events visually distinct
- [ ] No sensitive data displayed (metadata sanitization verified)

---

### Stage 4E — User Panel

**Scope:** Profile management, MFA configuration, session info

**Deliverables:**
1. `AccountDashboard` — welcome + quick links
2. `ProfilePage` — view/edit own profile:
   - Display name (editable)
   - Avatar (display, future: upload)
   - Email (read-only)
   - Email verification status
   - Calls `update-profile` edge function
3. `SecurityPage` — MFA configuration:
   - Current MFA status
   - Link to enroll/unenroll TOTP
   - Recovery codes display (when DW-008 is implemented)
4. `SessionPage` — current session info:
   - Last sign-in time
   - Session metadata

**API Integration:**

| UI Action | Edge Function / RPC | Permission Required |
|-----------|-------------------|-------------------|
| View own profile | `get-profile` | `users.view_self` |
| Update own profile | `update-profile` | `users.edit_self` |
| MFA enroll | Supabase Auth MFA API | authenticated |
| MFA unenroll | Supabase Auth MFA API | authenticated |

**Files Created:**

| File | Action |
|------|--------|
| `src/pages/account/AccountDashboard.tsx` | New |
| `src/pages/account/ProfilePage.tsx` | New |
| `src/pages/account/SecurityPage.tsx` | New |
| `src/pages/account/SessionPage.tsx` | New |
| `src/pages/account/index.ts` | New |
| `src/hooks/useProfile.ts` | New — React Query hooks |
| `src/hooks/useProfileMutations.ts` | New — update profile mutation |

**Success Criteria:**
- [ ] User can view and edit own profile
- [ ] MFA status displayed correctly
- [ ] Profile update calls edge function with audit logging
- [ ] Self-scope enforced (cannot edit other users' profiles)
- [ ] Loading/error states for all operations
- [ ] Toast feedback on save

---

## Cross-Stage Requirements

### Accessibility Baseline
- All interactive elements keyboard navigable
- Focus visible indicators
- ARIA labels on icon-only buttons
- Color contrast meets WCAG AA
- `prefers-reduced-motion` respected

### Error Handling Pattern
- API errors → toast with user-friendly message
- Permission denied → "Access Denied" page (not blank/hidden)
- Network failure → retry button with error state
- Loading → skeleton UI (not spinner)

### Deferred Work Integration
- **DW-008 (MFA Recovery Codes):** Stage 4E SecurityPage will include placeholder/section for recovery codes. Actual implementation depends on DW-008 being completed.

---

## Route Plan

| Route | Page | Permission | Stage |
|-------|------|-----------|-------|
| `/admin` | AdminDashboard | `users.view_all` | 4B |
| `/admin/users` | UserListPage | `users.view_all` | 4B |
| `/admin/users/:id` | UserDetailPage | `users.view_all` | 4B |
| `/admin/access/roles` | RoleListPage | `roles.view` | 4C |
| `/admin/access/roles/:id` | RoleDetailPage | `roles.view` | 4C |
| `/admin/access/permissions` | PermissionListPage | `roles.view` | 4C |
| `/admin/audit` | AuditLogPage | `audit.view` | 4D |
| `/account` | AccountDashboard | authenticated | 4E |
| `/account/profile` | ProfilePage | `users.view_self` | 4E |
| `/account/security` | SecurityPage | authenticated | 4E |
| `/account/sessions` | SessionPage | authenticated | 4E |

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

---

## Closure Outputs (post-execution)

After all stages executed and verified:
- `docs/07-reference/route-index.md` — add all new frontend routes
- `docs/00-governance/system-state.md` — update module statuses
- `docs/08-planning/master-plan.md` — update Phase 4 gate checkboxes
- `docs/08-planning/deferred-work-register.md` — update DW-008 status if applicable
