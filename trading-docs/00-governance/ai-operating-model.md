# Trading System — AI Operating Model

> **Owner:** tesfayekb | **Version:** 1.0 | **Status:** ACTIVE

## Purpose

Defines mandatory reading order, output formats, and prohibited actions for any AI agent working on the trading system.

---

## Mandatory Reading Order (Every Trading Task)

1. `MARKETMUSE_MASTER.md` — the single source of truth for the trading system
2. `trading-docs/00-governance/constitution.md` — 10 T-Rules
3. `trading-docs/00-governance/system-state.md` — current trading phase and gates
4. `trading-docs/08-planning/approved-decisions.md` — 22 locked decisions
5. `.lovable/trading-rules.md` (Lovable) or `trading-docs/00-governance/cursorrules-trading.md` (Cursor) — platform-specific constraint rules
6. Relevant module docs from `trading-docs/04-modules/`
7. Relevant reference indexes from `trading-docs/07-reference/`
8. `docs/` (foundation) — read-only reference when needed

**CRITICAL:** Foundation `docs/` is READ-ONLY. Never modify foundation documentation from a trading task.

---

## Prohibited Actions

1. **DO NOT modify any file in `docs/`** — foundation governance is separate and complete.
2. **DO NOT modify existing foundation database tables** — except the approved `profiles` ALTER (Part 4.1).
3. **DO NOT create tables without the `trading_` prefix** — unless inserting into existing foundation tables (`job_registry`, `alert_configs`, `permissions`, `role_permissions`).
4. **DO NOT implement features from Part 14 (V2)** — multi-user mirroring, subscriptions, tiers, etc. are explicitly deferred.
5. **DO NOT override locked decisions (D-001 through D-022)** — they are final.
6. **DO NOT skip the paper phase** — 45 days minimum, all 12 criteria required.
7. **DO NOT mix trading health with system health** — `trading_system_health` is separate from `system_health_snapshots`.
8. **DO NOT expose Tradier API keys in frontend code** — encrypted storage only, last 4 chars for display.
9. **DO NOT implement a phase before its predecessor's Go/No-Go criteria are met.**
10. **DO NOT create silent failure paths** — every error must be logged, detected, and have a defined response.

---

## Output Format (After Every Trading Change Task)

```
## Change Summary
[What was done]

## Trading Phase
[Current phase from system-state.md]

## Modules Impacted
[List of trading modules affected]

## Foundation Impact
[NONE expected — if any foundation file was touched, explain why]

## Docs Updated
[List of trading-docs/ files modified]

## References Updated
[List of trading-docs/07-reference/ files modified]

## Verification Status
[How the change was verified]

## Risks / Follow-up
[Any outstanding risks or required follow-up]
```

---

## Platform Routing

| Task Type | Platform | Constraint File |
|-----------|----------|-----------------|
| Frontend (React/TypeScript) | Lovable | `.lovable/trading-rules.md` |
| Backend (Python) | Cursor | `trading-docs/00-governance/cursorrules-trading.md` |
| Database (SQL migrations) | Lovable (Supabase) | `.lovable/trading-rules.md` |
| Documentation | Either | This file |

---

## Diff Requirements

All changes must be reviewable. When modifying existing files:
- Use search-replace edits, not full rewrites
- Explain what changed and why
- Reference the relevant MARKETMUSE_MASTER.md section
