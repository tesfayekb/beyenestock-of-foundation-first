# Stage 4I — Navigation Enhancements Plan

> **Status:** IMPLEMENTED (ACT-044)  
> **Owner:** AI  
> **Created:** 2026-04-11  
> **Parent:** Phase 4 — Admin & User Interfaces (stage-4-plan.md)  
> **ACT:** ACT-044  

---

## Objective

Enhance the dashboard navigation shell with nested collapsible groups, dynamic breadcrumb entity names, active parent highlighting, mobile sidebar awareness, and nav item badge support.

---

## Items

### Item 23 — Mobile isMobile Awareness

**Problem:** When sidebar is in mobile Sheet mode, `state` may briefly report `collapsed` before the Sheet opens, causing icon-only rendering to flash.

**Fix:** Override collapsed check: `const collapsed = state === 'collapsed' && !isMobile`. One-line change in `DashboardSidebar.tsx`.

**Files:** `src/components/dashboard/DashboardSidebar.tsx`

---

### Item 5 — Nested/Collapsible Nav Groups

**Problem:** `NavItem.children` is typed but not rendered. Sidebar only renders flat items.

**Implementation:**
- When a NavItem has `children`, render a `Collapsible` with `CollapsibleTrigger` (parent row with ChevronRight/Down) and `CollapsibleContent` (indented children)
- In collapsed sidebar mode, children groups cannot expand — show only parent icons with tooltips
- Default open state: open if any child `isActive`, closed otherwise
- Uses existing shadcn Collapsible component

**Files:** `src/components/dashboard/DashboardSidebar.tsx`

---

### Item 11 — Dynamic Breadcrumb Entity Names

**Problem:** UUID segments in breadcrumbs show "Detail" instead of entity display names.

**Implementation:**
- For UUID segments, read display name from React Query cache via `queryClient.getQueryData()`
- Cache keys: `['admin', 'user', uuid]` for user detail, `['roles', 'detail', uuid]` for role detail
- Cache miss → fall back to "Detail" (no new fetches triggered)
- Read-only cache access — no loading states in breadcrumbs

**Files:** `src/components/dashboard/DashboardBreadcrumbs.tsx`

---

### Item 13 — Active Parent Highlighting

**Problem:** When a child route is active, the parent collapsible item should visually indicate activity.

**Implementation:**
- Add `hasActiveChild` check: `children.some(child => isActive(child.url))`
- Apply active visual style to CollapsibleTrigger when `hasActiveChild` is true
- Depends on Item 5 (nested nav)

**Files:** `src/components/dashboard/DashboardSidebar.tsx`

---

### Item 24 — Nav Item Badge Support

**Problem:** No infrastructure for showing counts/labels on nav items (e.g. pending actions).

**Implementation:**
- Add `badge?: string | number` to `NavItem` in `navigation.types.ts`
- Render `Badge` next to nav item title when defined, only in expanded mode
- Badge styling: `variant="secondary"` with `text-xs ml-auto`
- Currently no nav items use badges — infrastructure only

**Files:** `src/config/navigation.types.ts`, `src/components/dashboard/DashboardSidebar.tsx`

---

## Implementation Order

1. Item 23 (mobile fix) — no dependencies
2. Item 24 (badge type) — no dependencies  
3. Item 5 (nested nav) — before Items 11 and 13
4. Item 11 (dynamic breadcrumbs) — independent but benefits from nesting context
5. Item 13 (active parent) — depends on Item 5

---

## Governance

- ACT-044 in action-tracker.md
- Stage 4I section in stage-4-plan.md
- system-state.md active_work updated
- component-inventory.md updated
- ui-architecture.md updated (nested nav behavior)
