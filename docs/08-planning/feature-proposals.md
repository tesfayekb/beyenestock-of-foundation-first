# Feature Proposals

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-09

## Purpose

Structured intake for unplanned features. Any feature not already in `master-plan.md` MUST be proposed here before any implementation or plan modification occurs.

This document prevents scope creep, unauthorized feature additions, and AI drift.

## Scope

All new feature ideas, enhancements, and capability requests that are NOT currently tracked in the approved master plan.

## Enforcement Rule (CRITICAL)

- **NO** unplanned feature may be implemented without a proposal in this document
- **NO** proposal may be executed until it reaches `approved` status
- **NO** proposal may bypass the master plan — approved proposals MUST be added to `master-plan.md` before implementation begins
- If an AI agent identifies a useful feature during any task → it MUST log a proposal here and **STOP** — it must NOT implement it
- Violations = **INVALID** change subject to revert

## Feature Proposal Protocol

When an AI agent (or any contributor) wants to add a feature not in the master plan:

### Step 1 — STOP

Do NOT implement. Do NOT modify the master plan. Do NOT create code or schema.

### Step 2 — Create Proposal Entry

Add an entry to the Proposal Register below using the mandatory schema.

### Step 3 — Notify

Inform the user/project lead that a feature proposal has been logged and requires review.

### Step 4 — Wait for Approval

The proposal must be reviewed and explicitly approved by the project lead. No assumptions.

### Step 5 — Integrate into Master Plan

Once approved:
1. Add a new `PLAN-{MODULE}-NNN` section to `master-plan.md` with a stable ID
2. Create a `DEC-NNN` entry in `approved-decisions.md`
3. Log the change in `plan-changelog.md`
4. Update `system-state.md` if the plan version changes
5. Follow all Constitution rules (especially Rules 8, 9, 10)

### Step 6 — Implement via Normal Workflow

Only after the feature exists in the approved master plan may implementation begin, following the full 9-step change control workflow.

## Proposal Entry Schema (MANDATORY)

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Stable identifier (FP-NNN) |
| `date_proposed` | Yes | Date the proposal was created |
| `proposed_by` | Yes | Who proposed it (AI agent name / human) |
| `title` | Yes | Short descriptive title |
| `description` | Yes | What the feature does and why it is needed |
| `justification` | Yes | Why this was not in the original plan |
| `affected_modules` | Yes | Which existing modules are impacted |
| `new_modules_required` | If applicable | Any new modules this would create |
| `dependencies` | Yes | What must exist before this can be built |
| `estimated_impact` | Yes | LOW / MEDIUM / HIGH |
| `risk_assessment` | Yes | What risks does this introduce |
| `status` | Yes | proposed / under-review / approved / rejected / deferred |
| `reviewed_by` | When reviewed | Who reviewed the proposal |
| `review_date` | When reviewed | Date of review |
| `decision_id` | When approved | Reference to DEC-NNN in approved-decisions.md |
| `plan_section_id` | When approved | Reference to PLAN-XXX-NNN in master-plan.md |
| `rejection_reason` | If rejected | Why it was not accepted |

## Proposal Register

_No proposals yet._

---

## Status Definitions

| Status | Meaning |
|--------|---------|
| `proposed` | Logged, awaiting review |
| `under-review` | Being evaluated by project lead |
| `approved` | Accepted — must be added to master plan before implementation |
| `rejected` | Not accepted — must not be implemented |
| `deferred` | Postponed to a future version |

## Escalation Rule

- Proposals that remain in `proposed` status for more than 2 plan revisions must be escalated or explicitly deferred
- Rejected proposals must NOT be re-proposed without new justification

## Dependencies

- [Master Plan](master-plan.md)
- [Approved Decisions](approved-decisions.md)
- [Constitution](../00-governance/constitution.md)

## Used By / Affects

- All new feature requests
- Master plan revisions
- AI agent behavior (scope enforcement)

## Risks If Changed

HIGH — weakening this document allows scope creep and unauthorized feature additions.

## Related Documents

- [Master Plan](master-plan.md)
- [Approved Decisions](approved-decisions.md)
- [Plan Changelog](plan-changelog.md)
- [Open Questions](open-questions.md)
- [Change Control Policy](../00-governance/change-control-policy.md)
