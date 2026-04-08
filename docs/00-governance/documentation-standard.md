# Documentation Standard

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines the mandatory structure, format, and enforcement rules for all documentation in the SSOT system.

## Scope

Applies to ALL files under `/docs`.

## Enforcement Rule (CRITICAL)

- All documents MUST follow this structure exactly
- No required section may be omitted
- If any required section is missing → the document is **INVALID**
- Invalid documents must **NOT** be used as a source of truth

## Mandatory Document Structure

Every document MUST include:

### Header Metadata

```
> **Owner:** [Role/Person] | **Last Reviewed:** [YYYY-MM-DD]
```

- `Last Reviewed` MUST be updated whenever the document is modified

### Required Sections

1. **Purpose** — What this document defines
2. **Scope** — What it covers
3. **Key Rules / Principles** — Core content
4. **Dependencies** — What this document relies on
5. **Used By / Affects** — What depends on this document
6. **Risks If Changed** — Impact classification (LOW / MEDIUM / HIGH)
7. **Related Documents** — Cross-references

## Additional Requirements for Module Documents

Module files (`docs/04-modules/`) MUST include:

- **Shared Functions** — Functions used across modules
- **Events** — Events emitted and consumed
- **Jobs** — Background jobs owned by this module
- **Permissions** — Permissions defined by this module
- **Risks If Modified** — Specific behavioral risks

### Module Enforcement

- Dependencies MUST be explicitly listed
- "Used By / Affects" MUST be populated
- If module behavior changes → dependencies and references MUST be updated

## Naming Conventions

- Files: `kebab-case.md`
- Plan section IDs: `PLAN-{MODULE}-{NNN}`
- Decision IDs: `DEC-{NNN}`
- IDs are permanent and never reassigned

## Cross-Reference Rules

- Never duplicate content — always link
- Use relative paths within `/docs`
- Every reference MUST point to an existing document
- Broken references = **INVALID** document

## Document Integrity Rules

- No temporary, ad-hoc, or free-form documents allowed
- No "notes", "draft", or duplicate files allowed as sources of truth
- Each concept must exist in exactly one authoritative document

## Update Requirements

When a document is modified:
- `Last Reviewed` MUST be updated
- Related documents MUST be checked for consistency
- Cross-references MUST be validated

## Dependencies

- [Constitution](constitution.md) — Rule 5 (no duplicates)

## Used By / Affects

All documentation in the SSOT system.

## Risks If Changed

MEDIUM — improper changes lead to inconsistency and breakdown of the SSOT system.

## Related Documents

- [Constitution](constitution.md)
