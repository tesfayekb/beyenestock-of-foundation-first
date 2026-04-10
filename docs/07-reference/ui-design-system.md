# UI Design System

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-10 | **Status:** Living Document

## Purpose

Governs the visual language for all UI surfaces. This document is the SSOT for colors, typography, spacing, component patterns, and interaction standards. All implementation must conform to this spec.

## Enforcement Rule (CRITICAL)

- No raw/arbitrary colors in components — semantic tokens only
- No page-local component variants — use governed patterns below
- No new visual patterns without adding to this document first
- Light and dark themes must have visual parity
- WCAG AA contrast minimum in both themes

---

## Color System

### Existing Foundation (Preserve)

The project has an established token system in `index.css`. Phase 4 **extends** this — it does not replace it.

**Preserved tokens:**
- `--background`, `--foreground`
- `--card`, `--card-foreground`
- `--popover`, `--popover-foreground`
- `--primary`, `--primary-foreground`
- `--secondary`, `--secondary-foreground`
- `--muted`, `--muted-foreground`
- `--accent`, `--accent-foreground`
- `--destructive`, `--destructive-foreground`
- `--border`, `--input`, `--ring`
- `--sidebar-*` (full sidebar token set)

### New Tokens (Phase 4 Additions)

| Token | Purpose | Light | Dark |
|-------|---------|-------|------|
| `--success` | Positive status/action | Green HSL | Green HSL (adjusted) |
| `--success-foreground` | Text on success | White | White |
| `--warning` | Caution status | Amber HSL | Amber HSL (adjusted) |
| `--warning-foreground` | Text on warning | Dark | Dark |
| `--info` | Informational status | Blue HSL | Blue HSL (adjusted) |
| `--info-foreground` | Text on info | White | White |
| `--content-shadow` | Content area depth | Subtle shadow | Subtle shadow (darker) |

**Rules:**
- All colors MUST be HSL format
- All new tokens must be added to both `:root` and `.dark`
- All new tokens must be mapped in `tailwind.config.ts`
- Exact HSL values chosen during implementation — must pass WCAG AA contrast

### Forbidden Patterns

- ❌ `bg-red-500`, `text-blue-600` — no Tailwind palette colors in components
- ❌ `bg-[#hexcode]` — no arbitrary values
- ❌ `bg-gradient-to-r` on text — no text gradients
- ❌ `backdrop-blur` / glass effects — no frosted glass
- ✅ `bg-destructive`, `text-muted-foreground` — semantic tokens only

---

## Typography

### Font Stack

| Role | Font | Tailwind Class | Usage |
|------|------|---------------|-------|
| Display | *Chosen at implementation* | `.font-display` | Page titles (h1), stat values, hero text |
| Body | Inter | `.font-sans` (default) | All body text, labels, descriptions |
| Mono | JetBrains Mono | `.font-mono` | UUIDs, permission keys, JSON, code |

**Rule:** Display font must be selected and documented here before implementation. Candidates: Bricolage Grotesque, Plus Jakarta Sans, or similar. Must be available via Google Fonts or self-hosted.

### Type Scale

| Level | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| h1 | 1.875rem (30px) | 700 | 1.2 | Page titles |
| h2 | 1.5rem (24px) | 600 | 1.3 | Section headers |
| h3 | 1.25rem (20px) | 600 | 1.4 | Card titles, subsections |
| h4 | 1.125rem (18px) | 500 | 1.4 | Group labels |
| body | 0.875rem (14px) | 400 | 1.5 | Default text |
| body-sm | 0.8125rem (13px) | 400 | 1.5 | Table cells, secondary |
| caption | 0.75rem (12px) | 400 | 1.5 | Timestamps, IDs, hints |

---

## Spacing Scale

Based on 4px grid:

| Name | Value | Usage |
|------|-------|-------|
| `xs` | 4px (0.25rem) | Icon gaps, tight spacing |
| `sm` | 8px (0.5rem) | Inline spacing, badge padding |
| `md` | 16px (1rem) | Card padding, form field gaps |
| `lg` | 24px (1.5rem) | Section spacing |
| `xl` | 32px (2rem) | Page padding, major sections |
| `2xl` | 48px (3rem) | Hero spacing, page separators |

---

## Border & Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius` | 0.5rem (8px) | Default (already defined) |
| `rounded-lg` | var(--radius) | Cards, dialogs, dropdowns |
| `rounded-md` | calc(var(--radius) - 2px) | Buttons, inputs, badges |
| `rounded-sm` | calc(var(--radius) - 4px) | Small elements, tags |

**Border rule:** Always use `border-border`. No arbitrary border colors.

---

## Shadow / Elevation

| Level | CSS | Usage |
|-------|-----|-------|
| None | — | Flat elements (table rows, list items) |
| sm | `0 1px 2px 0 hsl(var(--foreground) / 0.05)` | Subtle lift (cards in light mode) |
| md | `0 4px 6px -1px hsl(var(--foreground) / 0.1)` | Elevated (dropdowns, popovers) |
| lg | `0 10px 15px -3px hsl(var(--foreground) / 0.1)` | Floating (dialogs, sheets) |

**Rule:** No `shadow-2xl` or arbitrary shadows. No glass/blur effects.

---

## Component Patterns

### Card

One card style, used everywhere:

```
┌─────────────────────────────┐
│ Optional header with title  │
│─────────────────────────────│
│ Content                     │
│                             │
│─────────────────────────────│
│ Optional footer / actions   │
└─────────────────────────────┘
```

- Background: `bg-card`
- Border: `border border-border`
- Radius: `rounded-lg`
- Padding: `p-6` (content), `px-6 py-4` (header/footer)
- Shadow: `shadow-sm` (light mode), none (dark mode)

### DataTable

One table pattern:

| Property | Value |
|----------|-------|
| Header bg | `bg-muted/50` |
| Header text | `text-muted-foreground`, `font-medium`, `text-xs uppercase tracking-wider` |
| Row hover | `hover:bg-muted/50` |
| Row border | `border-b border-border` |
| Cell padding | `px-4 py-3` |
| Empty state | `EmptyState` component centered in table body |
| Pagination | Below table, right-aligned, using `Button` variants |

### Form Fields

One form field style:

| Property | Value |
|----------|-------|
| Input height | `h-10` (40px) |
| Label | Above input, `text-sm font-medium` |
| Description | Below label, `text-xs text-muted-foreground` |
| Error | Below input, `text-xs text-destructive` |
| Disabled | `opacity-50 cursor-not-allowed` |
| Focus | `ring-2 ring-ring ring-offset-2` |

### Dialog / Modal

One dialog style:

| Property | Value |
|----------|-------|
| Overlay | `bg-black/80` |
| Max width | `sm:max-w-[425px]` (default), `sm:max-w-[600px]` (wide) |
| Border radius | `rounded-lg` |
| Structure | Header (title + description) → Body (content) → Footer (actions) |
| Destructive variant | Footer has `destructive` button + `outline` cancel |
| Close | X button in top-right corner |

### Toast / Alert

| Type | Border/Accent | Icon |
|------|--------------|------|
| Success | `--success` | CheckCircle |
| Warning | `--warning` | AlertTriangle |
| Error | `--destructive` | XCircle |
| Info | `--info` | Info |

### Badge / Status

| Status | Background | Text |
|--------|-----------|------|
| Active | `bg-success/10` | `text-success` |
| Deactivated | `bg-destructive/10` | `text-destructive` |
| Pending | `bg-warning/10` | `text-warning` |
| Info/Default | `bg-muted` | `text-muted-foreground` |

### Async States

**Loading:** Skeleton with `bg-muted animate-pulse`, matching the shape of the content it replaces.

**Empty:** Centered icon (muted) + heading + description + optional action button.

**Error:** Centered alert icon + error message + "Try Again" button.

**Rule:** All async operations must use these three states. No spinners in page content (spinners only acceptable in buttons during submit).

---

## Motion

| Animation | Duration | Easing | Usage |
|-----------|----------|--------|-------|
| Fade in | 150ms | ease-out | Page transitions, new content |
| Collapse/expand | 200ms | ease-out | Sidebar, accordion |
| Skeleton pulse | 2s | ease-in-out (loop) | Loading states |

**Rules:**
- Respect `prefers-reduced-motion` — disable all non-essential animations
- No decorative animations (bouncing, spinning, sliding text)
- Transitions serve function (showing state change), not decoration

---

## Focus & Accessibility

| Rule | Implementation |
|------|---------------|
| Focus ring | `ring-2 ring-ring ring-offset-2 ring-offset-background` on all interactive elements |
| Focus visible | Use `:focus-visible` (not `:focus`) for keyboard-only indicators |
| Skip links | "Skip to content" link before sidebar (hidden until focused) |
| ARIA labels | Required on icon-only buttons |
| Color contrast | WCAG AA minimum (4.5:1 for text, 3:1 for large text/icons) |
| Screen reader | All status badges include `sr-only` text |

---

## Dark Mode Rules

- Every visual property must work in both themes
- No "light-only" or "dark-only" components
- Card shadows reduce in dark mode (or use border emphasis instead)
- Status colors adjust for dark backgrounds while maintaining contrast
- Images/icons that contain color should work on both backgrounds

---

## Dependencies

- [UI Architecture](../01-architecture/ui-architecture.md) — shell structure
- [Component Inventory](component-inventory.md) — component list

## Used By / Affects

All Phase 4 UI implementation.

## Risks If Modified

MEDIUM — visual changes affect user experience consistency.

## Related Documents

- [Admin Panel Module](../04-modules/admin-panel.md)
- [User Panel Module](../04-modules/user-panel.md)
