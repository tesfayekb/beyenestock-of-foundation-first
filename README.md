# ⛔ AI AGENTS — MANDATORY GOVERNANCE (READ FIRST)

**You MUST read and obey the governance rules before ANY action.**

| Platform | Rules File | Auto-Loaded |
|----------|-----------|-------------|
| **Lovable** | `.lovable/rules.md` | Yes |
| **Cursor** | `.cursorrules` | Yes |
| **Other** | Read `docs/00-governance/constitution.md` + `docs/00-governance/system-state.md` | Manual |

**Current state:** `phase: documentation-only` · `code_generation: blocked` · Baseline: `v4`

- **Do NOT generate code** — phase is documentation-only
- **Do NOT implement unplanned features** — log in `docs/08-planning/feature-proposals.md` and STOP
- **Do NOT skip the 9-step workflow** in `docs/00-governance/change-control-policy.md`
- **Violations = INVALID work product, subject to revert**

---

# Project

## Documentation Structure

```
docs/
├── 00-governance/    — Constitution, change control, system state, AI rules
├── 01-architecture/  — Architecture overview, dependency map, design principles
├── 02-security/      — Auth security, authorization, input validation
├── 03-performance/   — Caching, DB performance, strategy
├── 04-modules/       — Module specs (auth, rbac, admin, user, audit, health, api, jobs)
├── 05-quality/       — Testing strategy, regression strategy
├── 06-tracking/      — Action tracker, risk register, regression watchlist
├── 07-reference/     — Function, permission, route, event, config, env var indexes
└── 08-planning/      — Master plan, approved decisions, changelog, review log, feature proposals
```

## Quick Reference

- **System State**: `docs/00-governance/system-state.md` — current phase and execution gates
- **Constitution**: `docs/00-governance/constitution.md` — 11 non-negotiable rules
- **Master Plan**: `docs/08-planning/master-plan.md` — approved execution plan (baseline v4)
- **Approved Decisions**: `docs/08-planning/approved-decisions.md` — binding decisions (DEC-001+)
- **Feature Proposals**: `docs/08-planning/feature-proposals.md` — intake for unplanned features
