---
name: Artifact governance system
description: Artifact index, DB migration ledger, phase closure records, and one-current-summary rule for governed implementation artifacts
type: feature
---

## Artifact Governance System (ACT-022)

### New Files
- `docs/07-reference/artifact-index.md` — Catalog of all governed artifacts (ART-NNN IDs)
- `docs/07-reference/database-migration-ledger.md` — Ordered DB migration history (MIG-NNN IDs)
- `docs/08-planning/phase-closures/` — One authoritative closure record per phase

### Rules
- Every migration applied to production MUST have entries in both artifact-index and migration-ledger
- Phase closures: exactly ONE file per phase; old review drafts (v1, v2...) must be deleted
- Broken historical migrations are NEVER deleted — marked `superseded` with pointer to corrective migration
- Artifact index and migration ledger are append-only (status changes forward-only)
- DoD core checklist includes 3 artifact governance items

### Integration Points
- `definition-of-done.md` — 3 new checklist items
- `project-structure.md` — docs/ structure updated
- `action-tracker.md` — ACT-022
- `system-state.md` — `artifact_governance: active`
