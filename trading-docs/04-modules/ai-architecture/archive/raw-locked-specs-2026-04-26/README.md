# Raw Locked AI Architecture Specs — Archive (2026-04-26)

**Status:** Immutable. DO NOT MODIFY.

**Created:** 2026-04-26 (Phase 1 P1.3.0b of CONSOLIDATED_PLAN_v1.2_APPROVED.md)
**Purpose:** Archive the 13 locked AI architecture specs (plus their umbrella registry) at the moment they were locked, BEFORE any audit-driven corrections were applied.

---

## Why This Archive Exists

The 13 AI architecture specs were produced through multi-AI collaboration (Claude + GPT-5.5 Pro, April 2026) and locked at the dates documented inside each file. Each spec is the binding architectural intent for its respective item; corrections during Phase 2 are factual fixes only, not architectural changes.

This archive preserves the exact byte-content of each spec at the moment of lock, with SHA-256 checksums proving no silent modification.

Validated module documentation under `trading-docs/04-modules/ai-architecture/<item>.md` may include factual corrections (Class A) and content omissions (Class B) per Phase 2 corrections, but the original architectural decisions are preserved here unchanged.

---

## Immutability Rule

**Files in this directory MUST NOT be modified after the initial archive commit.**

Any change requires:
1. A new D-XXX entry in `trading-docs/08-planning/approved-decisions.md` explicitly authorizing the archive amendment
2. Operator approval of the amendment
3. A new archive subdirectory (e.g., `raw-locked-specs-2026-04-27/`) — the original `raw-locked-specs-2026-04-26/` directory remains untouched
4. Both the original and amended versions accessible for traceability

---

## Files In This Archive

13 locked AI architecture specs (one per item) plus 1 umbrella registry:

| File | Item | Tier | Cluster |
|------|------|------|---------|
| `ITEM_1_AI_RISK_GOVERNOR_LOCKED.md` | AI-SPEC-001 | V0.1 | A (foundational) |
| `ITEM_2_STRATEGY_AWARE_ATTRIBUTION_LOCKED.md` | AI-SPEC-002 | V0.1 | A (foundational) |
| `ITEM_3_SYNTHETIC_COUNTERFACTUAL_LOCKED.md` | AI-SPEC-003 | V0.4 | C (governance/maturation) |
| `ITEM_4_REPLAY_HARNESS_LOCKED.md` | AI-SPEC-004 | V0.1 | A (foundational) |
| `ITEM_5_VOLATILITY_FAIR_VALUE_ENGINE_LOCKED.md` | AI-SPEC-005 | V0.2 | B (alpha-generation) |
| `ITEM_6_META_LABELER_LOCKED.md` | AI-SPEC-006 | V0.2 | B (alpha-generation) |
| `ITEM_7_ADVERSARIAL_REVIEW_LOCKED.md` | AI-SPEC-007 | V0.4 | C (governance/maturation) |
| `ITEM_8_OPRA_FLOW_ALPHA_LOCKED.md` | AI-SPEC-008 | V0.2 | B (alpha-generation) |
| `ITEM_9_EXIT_OPTIMIZER_LOCKED.md` | AI-SPEC-009 | V0.2 | B (alpha-generation) |
| `ITEM_10_COUNTERFACTUAL_PNL_LOCKED.md` | AI-SPEC-010 | V0.1 | A (foundational) |
| `ITEM_11_EVENT_DAY_PLAYBOOKS_LOCKED.md` | AI-SPEC-011 | V0.3 | C (governance/maturation) |
| `ITEM_12_DYNAMIC_CAPITAL_ALLOCATION_LOCKED.md` | AI-SPEC-012 | V0.3 | C (governance/maturation) |
| `ITEM_13_DRIFT_DETECTION_LOCKED.md` | AI-SPEC-013 | V0.3 | C (governance/maturation) |
| `AI_ARCHITECTURE_IMPROVEMENT_REGISTRY.md` | (umbrella) | n/a | n/a |

---

## SHA-256 Checksums

Checksums for each file in this archive are stored in `checksums.txt` (this directory). Verify with:

```bash
cd trading-docs/04-modules/ai-architecture/archive/raw-locked-specs-2026-04-26/
sha256sum -c checksums.txt
```

If any line returns "FAILED", a file has been modified — investigate immediately.

---

## How To Use This Archive

Per-item audits (P1.3.1 through P1.3.13) read the relevant `ITEM_N_*_LOCKED.md` file as the source-of-truth spec. Auditors compare it against the codebase using the audit template at `trading-docs/08-planning/ai-architecture-audits/_template.md` and produce a redline at `trading-docs/08-planning/ai-architecture-audits/AI-SPEC-NNN.md`.

Phase 2 produces corrected drafts at `trading-docs/08-planning/ai-architecture-drafts/` (separate path; preserves originals here).

Phase 4 places validated module documentation at `trading-docs/04-modules/ai-architecture/<item>.md` (sibling of this `archive/` directory).

---

## Reference Documents

- [Consolidated Plan (operator-side)] CONSOLIDATED_PLAN_v1.2_APPROVED.md §7 P2.0
- [Evidence Pack] `../../../../08-planning/ai-architecture-audits/AI_ARCH_EVIDENCE_PACK.md`
- [Cross-Cutting Matrix] `../../../../08-planning/ai-architecture-audits/CROSS_CUTTING_EVIDENCE_MATRIX.md`
- [Audit Template] `../../../../08-planning/ai-architecture-audits/_template.md`
- [Approved Decisions] `../../../../08-planning/approved-decisions.md`
