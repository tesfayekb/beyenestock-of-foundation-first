# UI Architecture

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-10

## Purpose

Defines the structural shell contract for all authenticated UI surfaces (admin panel and user panel). This document is the SSOT for layout behavior, scroll ownership, responsive rules, and page structure.

## Scope

All frontend pages that use the dashboard shell (admin and user panels).

## Enforcement Rule (CRITICAL)

- All authenticated pages MUST use the governed `DashboardLayout` shell
- No page may define its own shell structure, sidebar, or header
- Deviations require change control (HIGH impact)

---

## App Shell Structure

### Desktop Layout (≥ 1024px)

```
┌──────────────────────────────────────────────────┐
│ Sidebar (fixed)    │  Header (fixed/sticky)       │
│                    │─────────────────────────────── │
│ - Logo             │  Content Area (scrolls)       │
│ - Nav sections     │                               │
│ - Nav items        │  ┌─ PageHeader ─────────────┐ │
│ - Collapse toggle  │  │ Title + Actions          │ │
│                    │  └──────────────────────────┘ │
│                    │  ┌─ Page Content ───────────┐ │
│                    │  │ (cards, tables, forms)    │ │
│ - Sign-out (footer)│  └──────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Position | Behavior |
|-----------|----------|----------|
| `DashboardSidebar` | Left, fixed | Does NOT scroll. Collapsible to icon strip (64px → icon-only). Contains nav sections, items, sign-out. |
| `DashboardHeader` | Top, fixed/sticky | Does NOT scroll. Contains sidebar trigger, search (desktop), theme toggle, user menu. Height: 56px. |
| Content Area | Right of sidebar, below header | ONLY element that scrolls. Contains PageHeader + page content. |

### Scroll Ownership

| Element | Scrolls? | Rule |
|---------|----------|------|
| Sidebar | No | Fixed position. If nav items overflow, internal scroll within sidebar only. |
| Header | No | Fixed/sticky at top of content area. |
| Content Area | Yes | Only scrollable region. `overflow-y: auto`. |
| Modals/Dialogs | Yes (internal) | Modal body scrolls internally if content exceeds viewport. |

---

## Sidebar Specification

### States

| State | Width | Content |
|-------|-------|---------|
| Expanded | 256px (16rem) | Icon + label + section headers |
| Collapsed (icon mode) | 56px (3.5rem) | Icon only, tooltips on hover |

### Structure

```
Logo / App Name
────────────────
Section: Main
  - Dashboard
  - Users (admin only)
  - Roles (admin only)
  - Permissions (admin only)
Section: System
  - Audit Logs (admin only)
  - Monitoring (admin only, future)
  - Jobs (admin only, future)
Section: Account
  - Profile
  - Security
────────────────
Sign Out (footer, always visible)
```

### Permission Filtering

- Nav items declare required permission(s) in config
- Items without user's permission are NOT rendered (not just hidden via CSS)
- Section headers hidden if all items in section are filtered out

### Active State

- Current route highlighted with `bg-sidebar-accent` + `text-sidebar-accent-foreground`
- Parent group expanded if child is active

---

## Header Specification

### Layout

```
┌─────────────────────────────────────────────────┐
│ [☰ Trigger] [Search...          ] [🌙] [👤 Menu]│
└─────────────────────────────────────────────────┘
```

| Element | Desktop | Mobile |
|---------|---------|--------|
| Sidebar trigger | Visible (collapses sidebar) | Visible (opens sheet) |
| Search | Visible | Hidden (future: icon trigger) |
| Theme toggle | Visible | Visible |
| User menu | Avatar + name | Avatar only |

### User Menu Dropdown

- Display name
- Email (muted)
- Separator
- Profile link
- Security link
- Separator
- Sign out

---

## Page Structure

### PageHeader Component

Every page has a consistent header zone:

```
┌─────────────────────────────────────────────────┐
│ Breadcrumbs: Admin > Users > John Doe           │
│                                                 │
│ Page Title                         [Action Btn] │
│ Optional subtitle/description                   │
└─────────────────────────────────────────────────┘
```

| Element | Required | Notes |
|---------|----------|-------|
| Breadcrumbs | Yes | Auto-generated from route path |
| Title | Yes | h1, display font |
| Subtitle | Optional | Muted text |
| Actions | Optional | Right-aligned buttons |

### Content Padding

| Breakpoint | Padding |
|------------|---------|
| Mobile (< 768px) | 16px (1rem) |
| Tablet (768–1023px) | 24px (1.5rem) |
| Desktop (≥ 1024px) | 32px (2rem) |

### Max Content Width

- Default: no max-width (fills available space)
- Form pages: max-width 768px, centered
- Dashboard pages: full width

---

## Responsive Behavior

### Breakpoints

| Breakpoint | Sidebar | Header | Content |
|------------|---------|--------|---------|
| Desktop (≥ 1024px) | Fixed, expanded or collapsed | Fixed | Full width minus sidebar |
| Tablet (768–1023px) | Collapsed (icon mode) | Fixed | Full width minus icon sidebar |
| Mobile (< 768px) | Hidden (sheet overlay on trigger) | Fixed, compact | Full width |

### Mobile Sidebar

- Rendered as `Sheet` (slide-in overlay from left)
- Triggered by hamburger icon in header
- Closes on nav item click or outside tap
- Full nav content (not icon-only)

---

## Route Guard Integration

### Loading State

- While auth state is resolving: full-page LoadingSkeleton (shell outline)
- After auth confirmed: render shell with content

### Permission Denied

- If user lacks required permission: render `AccessDenied` page within the shell
- Do NOT redirect away — show "You don't have permission to access this page" with a back button
- Shell remains visible (user can navigate to permitted pages)

### Unauthenticated

- Redirect to `/sign-in`

---

## Theme Integration

- Theme toggle in header
- Theme preference persisted (localStorage via `next-themes`)
- System preference respected as default
- All shell components support both themes via semantic tokens
- No raw color values in shell components

---

## Shell Uniformity Rule

Admin and user panels use the **same shell** (`DashboardLayout`):
- Same sidebar component (different nav config)
- Same header component
- Same page structure (PageHeader + content)
- Same async state components (LoadingSkeleton, ErrorState, EmptyState)

User pages may have fewer nav items and simpler content, but the shell language is identical.

---

## Dependencies

- [UI Design System](../07-reference/ui-design-system.md) — visual tokens
- [Component Inventory](../07-reference/component-inventory.md) — governed components
- [Route Index](../07-reference/route-index.md) — route definitions

## Used By / Affects

All Phase 4 frontend implementation.

## Risks If Modified

HIGH — shell changes affect every authenticated page.

## Related Documents

- [Admin Panel Module](../04-modules/admin-panel.md)
- [User Panel Module](../04-modules/user-panel.md)
- [Architecture Overview](architecture-overview.md)
