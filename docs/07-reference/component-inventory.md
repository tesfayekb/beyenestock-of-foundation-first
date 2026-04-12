# Component Inventory

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-12 | **Status:** Living Document

## Purpose

Governed registry of all shared Phase 4 components. Pages must assemble from this inventory. No page-local component variants are permitted.

## Enforcement Rule (CRITICAL)

- Every shared UI component used across pages MUST be listed here
- No page may create a local variant of a governed component
- Adding a new shared component requires updating this document first
- Component behavior must conform to patterns defined in [UI Design System](ui-design-system.md)

---

## Shell Components

| Component | Path | Purpose | Used By |
|-----------|------|---------|---------|
| `DashboardLayout` | `src/layouts/DashboardLayout.tsx` | Shell wrapper: SidebarProvider + Sidebar + Header + Outlet | Admin, User panels |
| `AdminLayout` | `src/layouts/AdminLayout.tsx` | Admin route wrapper: DashboardLayout + admin nav config + RequirePermission(`admin.access`) | Admin pages |
| `UserLayout` | `src/layouts/UserLayout.tsx` | User route wrapper: DashboardLayout + user nav config + RequireAuth | User pages |
| `DashboardSidebar` | `src/components/dashboard/DashboardSidebar.tsx` | Permission-filtered navigation sidebar with nested collapsible groups, badge support, mobile isMobile awareness, and active parent highlighting | Shell |
| `DashboardHeader` | `src/components/dashboard/DashboardHeader.tsx` | Fixed top bar: trigger, search, theme, user menu | Shell |
| `DashboardBreadcrumbs` | `src/components/dashboard/DashboardBreadcrumbs.tsx` | Route-aware breadcrumb trail with dynamic entity name resolution from React Query cache | All pages |
| `PageHeader` | `src/components/dashboard/PageHeader.tsx` | Page title + subtitle + action buttons zone | All pages |
| `DashboardNotFound` | `src/components/dashboard/DashboardNotFound.tsx` | In-shell 404: icon + message + go-back button, rendered within shell | Invalid routes under /admin/*, /dashboard/*, /settings/* |
| `UserMenu` | `src/components/dashboard/UserMenu.tsx` | Avatar dropdown: profile, security, cross-panel navigation (Admin Console / My Dashboard), sign-out | Header |
| `ThemeToggle` | `src/components/dashboard/ThemeToggle.tsx` | Light/dark theme toggle button | Header |

## Data Display Components

| Component | Path | Purpose | Used By |
|-----------|------|---------|---------|
| `DataTable` | `src/components/dashboard/DataTable.tsx` | Sortable, filterable table with pagination | Users, Roles, Permissions, Audit |
| `StatCard` | `src/components/dashboard/StatCard.tsx` | Metric card: icon + label + value + trend | Dashboards |
| `StatusBadge` | `src/components/dashboard/StatusBadge.tsx` | Color-coded status indicator (active/deactivated/pending) | Users, Roles |
| `AuditActionBadge` | `src/components/admin/AuditActionBadge.tsx` | Color-coded audit action label | Audit log |
| `AuditMetadataViewer` | `src/components/admin/AuditMetadataViewer.tsx` | Expandable JSON tree for audit metadata | Audit log |

## State Components

| Component | Path | Purpose | Used By |
|-----------|------|---------|---------|
| `LoadingSkeleton` | `src/components/dashboard/LoadingSkeleton.tsx` | Skeleton placeholder matching content shape | All async loads |
| `EmptyState` | `src/components/dashboard/EmptyState.tsx` | Icon + heading + description + optional action | All empty lists/tables |
| `ErrorState` | `src/components/dashboard/ErrorState.tsx` | Error icon + message + retry button | All failed operations |
| `AccessDenied` | `src/components/dashboard/AccessDenied.tsx` | Permission-denied page: lock icon + message + back/home link, rendered within shell | Permission-denied routes |

## Dialog Components

| Component | Path | Purpose | Used By |
|-----------|------|---------|---------|
| `ConfirmActionDialog` | `src/components/dashboard/ConfirmActionDialog.tsx` | Standard destructive confirmation: title + description + reason input + confirm/cancel | Deactivate, revoke, delete actions |
| `AssignRoleDialog` | `src/components/admin/AssignRoleDialog.tsx` | Role selection dialog for user role assignment | User detail page |
| `ReauthDialog` | `src/components/auth/ReauthDialog.tsx` | Email OTP identity verification dialog for sensitive actions | Security, PasswordChange |

| `AdminEditProfileCard` | `src/components/admin/AdminEditProfileCard.tsx` | Inline admin edit form for user profile (display name, avatar) with permission gate | UserDetailPage |
| `PasswordChangeCard` | `src/components/user/PasswordChangeCard.tsx` | In-panel password change form with email OTP re-auth, 12-char min, confirm match | SecurityPage |

## Configuration

| Component | Path | Purpose | Used By |
|-----------|------|---------|---------|
| `NavItem` (type) | `src/config/navigation.types.ts` | Navigation item interface with permission gating | Sidebar |
| Admin nav config | `src/config/admin-navigation.ts` | Admin sidebar navigation structure | AdminLayout |
| User nav config | `src/config/user-navigation.ts` | User sidebar navigation structure | UserLayout |

---

## Component Rules

### No Page-Local Variants

❌ **Forbidden:**
```tsx
// In UserListPage.tsx
const UserTable = () => <table>...</table>  // Page-local table
const UserStatusChip = () => ...            // Page-local badge
const UserDeleteModal = () => ...           // Page-local dialog
```

✅ **Required:**
```tsx
// In UserListPage.tsx
import { DataTable, StatusBadge, ConfirmActionDialog } from '@/components/dashboard'
```

### Extension Pattern

If a page needs unique data columns or filters, it configures the governed component — it does not replace it:

```tsx
<DataTable
  columns={userColumns}        // Page defines columns
  data={users}                 // Page provides data
  filters={userFilters}        // Page defines filter options
  onRowClick={handleRowClick}  // Page handles interaction
/>
```

---

## Reconciliation

At Phase 4 closure, this inventory must match:
- Actual components in `src/components/dashboard/` and `src/components/admin/`
- Imports used across all Phase 4 pages
- Any mismatch is a governance violation

---

## Dependencies

- [UI Design System](ui-design-system.md) — visual patterns
- [UI Architecture](../01-architecture/ui-architecture.md) — shell structure

## Used By / Affects

All Phase 4 page implementation.

## Related Documents

- [Stage 4 Plan](../08-planning/stage-4-plan.md)
