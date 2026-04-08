# Documentation Standard

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines the mandatory structure and metadata for every document in this SSOT system.

## Scope

All files under `/docs`.

## Mandatory Document Structure

Every document MUST include:

### Header Metadata

```
> **Owner:** [Role/Person] | **Last Reviewed:** [YYYY-MM-DD]
```

### Required Sections

1. **Purpose** — What this document defines
2. **Scope** — What it covers
3. **Key Rules / Principles** — Core content (varies by document type)
4. **Dependencies** — What this document relies on
5. **Used By / Affects** — What depends on this document
6. **Risks If Changed** — Impact classification (LOW / MEDIUM / HIGH)
7. **Related Documents** — Cross-references

### Additional Sections for Module Documents

Module files (under `docs/04-modules/`) must also include:

8. **Shared Functions** — Functions used by or shared with other modules
9. **Events** — Events emitted and consumed
10. **Jobs** — Background jobs owned by this module
11. **Permissions** — Permissions defined by this module
12. **Risks If Modified** — Specific behavioral risks

## Naming Conventions

- Files: `kebab-case.md`
- Section IDs in plans: `PLAN-{MODULE}-{NNN}` (e.g., `PLAN-AUTH-001`)
- Decision IDs: `DEC-{NNN}` (e.g., `DEC-001`)
- IDs are permanent and never reassigned

## Cross-Reference Rules

- Never copy content between documents; always link
- Use relative paths for links within `/docs`
- Every cross-reference must point to an existing document

## Dependencies

- [Constitution](constitution.md) — Rule 5 (no duplicates)

## Used By / Affects

Every document in this system must follow this standard.

## Risks If Changed

MEDIUM — affects document consistency across the entire project.

## Related Documents

- [Constitution](constitution.md)
