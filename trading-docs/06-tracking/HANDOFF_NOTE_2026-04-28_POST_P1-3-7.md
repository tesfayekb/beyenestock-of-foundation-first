# HANDOFF NOTE — Post-P1.3.7 Session Close (2026-04-28, 22:10 UTC-4)

> **Purpose:** Comprehensive continuity document for the next agent. Covers project context, governance discipline, workflow patterns, work completed in this session, current state, operator-pending decisions, and recommended next actions. Read this file END-TO-END before taking ANY action on this codebase.
>
> **Author of session:** Cursor (Claude Opus 4.7) under Operator (`tesfayekb`) direction.
>
> **Session window:** ~2026-04-26 → 2026-04-28 (3 days; multiple back-to-back action-cycles).
>
> **Recommended reading time:** 25–35 minutes for full read; 10 minutes for "minimum viable handoff" (sections 1, 3, 7, 8, 11, 13).

---

## TABLE OF CONTENTS

1. [Project Context — What This Codebase Is](#1-project-context)
2. [Where to Find Authoritative Sources (File Map)](#2-file-map)
3. [Current Repository State at Handoff](#3-current-state)
4. [The β-lite Multi-Document Governance Structure](#4-beta-lite-governance)
5. [The 5 Prevention Mechanisms (Mandatory Audit Discipline)](#5-prevention-mechanisms)
6. [Workflow Patterns — DIAGNOSE-FIRST vs EXECUTE-FIRST](#6-workflow-patterns)
7. [STOP Conditions (1–7) — When to Halt and Ask](#7-stop-conditions)
8. [Audit Finding Taxonomy — Class A / B / C](#8-finding-taxonomy)
9. [Path Y Activation Gates (A, B, C, D, E, F, ...)](#9-path-y-gates)
10. [What Was Done in This Session (Chronological)](#10-session-chronology)
11. [Operator-Pending Decisions (BLOCKING for Next Steps)](#11-operator-pending-decisions)
12. [Recommended Next Actions (Priority-Ordered)](#12-next-actions)
13. [Critical Guardrails — Things That Will Break the Project](#13-critical-guardrails)
14. [ROI Preservation Discipline](#14-roi-preservation)
15. [Code Execution Discipline (Test Isolation, .venv, Baseline)](#15-code-execution-discipline)
16. [Communication Discipline — How to Report](#16-communication-discipline)
17. [Citation Discipline — Lessons Learned About Prompt-Side Errors](#17-citation-discipline)
18. [Useful Commands and Patterns](#18-useful-commands)
19. [Prior Audit Precedents to Consult](#19-precedents)
20. [Glossary of Project-Specific Terms](#20-glossary)

---

## 1. PROJECT CONTEXT — WHAT THIS CODEBASE IS

This is **Beyene Stock — Foundation First**, a **paper-trading SPX options system** under construction with strict architectural governance. The codebase is *NOT* in production trading. It is in a multi-month documentation + scaffolding + paper-validation phase before any real-capital deployment.

### 1.1 Core architectural principle

> **AI controls admissibility and size ceilings, NOT trade execution. Constitutional gates remain non-overridable. Caps compose by minimum.**

This means: AI components (Items 1–13) propose, filter, and inform — they never directly halt trades, modify sizing, or veto execution. Capital preservation invariants (`risk_engine.py`, `position_monitor.py`) are immutable to AI components.

### 1.2 The 13 AI architecture items (Cluster A / B / C)

The `MASTER_ROI_PLAN.md` and `AI_BUILD_ROADMAP.md` enumerate 13 AI architecture items, organized into 3 clusters:

| Cluster | Tier | Items | Purpose |
|---|---|---|---|
| **A** | V0.1 (foundational) | 1 (AI Risk Governor), 2 (Strategy Attribution), 4 (Replay Harness), 10 (Counterfactual P&L) | Must exist before B/C have data to learn from. **Critical-path for V0.1 deployment.** |
| **B** | V0.2 / V0.3 (alpha-generation) | 5 (Vol Fair-Value HAR-RV), 6 (Meta-Labeler), 8 (OPRA Flow Alpha), 9 (Exit Optimizer) | Generates alpha hypotheses; requires Cluster A as substrate. |
| **C** | V0.3 / V0.4 (governance/maturation) | 3 (Synthetic Counterfactual Cases), 7 (Adversarial Pre-Trade Review), 11 (Event-Day Playbooks), 12 (Dynamic Capital Allocation), 13 (Realized-vs-Modeled Drift Detection) | Promotion governance, edge maintenance, drift detection. |

**Where to find each item's locked spec:** `trading-docs/04-modules/ai-architecture/archive/raw-locked-specs-2026-04-26/ITEM_<N>_<NAME>_LOCKED.md`. These specs are **immutable** (locked 2026-04-25). Every AI-spec audit (P1.3.x) produces a redline in `trading-docs/08-planning/ai-architecture-audits/AI-SPEC-<NNN>.md` against its locked spec.

### 1.3 Phase structure (per `MASTER_PLAN.md`)

- **Phase 0** — bootstrap (governance, decisions, plan baseline) ✓ complete
- **Phase 1** — audits + ROI gap scan (P1.0 → P1.3.x ongoing)
  - **P1.3.5** — AI-SPEC-005 (Vol Fair-Value HAR-RV) ✓ merged (PR #65)
  - **P1.3.6** — AI-SPEC-006 (Meta-Labeler) ✓ merged
  - **P1.3.7** — AI-SPEC-008 (OPRA Flow Alpha) ✓ committed + pushed (this session); **NOT yet merged**
  - **P1.3.8** — AI-SPEC-009 (Exit Optimizer) — next
- **Phase 2+** — implementation per audit dispositions

### 1.4 Operator and AI roles

- **Operator (`tesfayekb`)**: owns all D-XXX (decision) records, all spec amendments, all governance changes, all merges to `main`. The agent NEVER auto-merges, NEVER edits locked specs, NEVER adds D-XXX.
- **Cursor (this agent)**: produces code, audit redlines, governance proposals, and detailed reports. Stops at every Class C escalation, every STOP condition, every ambiguity.
- **Claude (cross-check)** + **GPT-5.5 Pro (validator)**: secondary auditors per `_template.md`. Cursor is the **primary auditor** for all P1.3.x work in this stream.

---

## 2. FILE MAP — WHERE TO FIND AUTHORITATIVE SOURCES

### 2.1 Governance (read EVERY task before doing anything)

| File | Purpose | Notes |
|---|---|---|
| `.cursorrules` | Cursor's binding contract — bootstrap rules, mandatory readings, output formats, gates | Read on every cold start |
| `trading-docs/00-governance/constitution.md` | 11 T-Rules (T1–T11). T-Rule 4 = governance docs are authoritative; T-Rule 5 = capital preservation; T-Rule 10 = no silent failures | 59 lines; read every task |
| `trading-docs/00-governance/system-state.md` | Current operational state: `current_sizing_phase`, `core_risk_pct`, `meta_labeler.phase`, `replay_harness.chain_archive_status`, etc. | 49 lines; **NOTE: stale `core_risk_pct: 0.005` — needs sync to 0.010 post-Action 7b; tracked as informational** |
| `trading-docs/00-governance/change-control-policy.md` | The 9-step workflow for change tasks | Authoritative for any code change |
| `trading-docs/08-planning/approved-decisions.md` | Binding D-XXX decisions (D-001 through D-024 currently). D-008 = Databento budget; D-013 = paper phase; D-016 = volatility blending; D-022 = capital preservation halts; D-023 = AI authority boundary (under enrichment) | 125 lines |
| `trading-docs/08-planning/MASTER_PLAN.md` | Approved execution plan v3.2 with stable PLAN-XXX IDs | 443 lines; **Phase 4C name discrepancy with Build Roadmap — operator-pending side-finding** |

### 2.2 The β-lite multi-plan trio (THIS SESSION'S CENTRAL ARTIFACTS)

| File | Version | Purpose | Cross-references |
|---|---|---|---|
| `trading-docs/08-planning/MASTER_ROI_PLAN.md` | **v2.0.3** | The "spine" — master ROI improvement plan organizing all Actions 1–N | Authority for every Action prompt this session |
| `trading-docs/08-planning/AI_BUILD_ROADMAP.md` | **v1.8** (last touched this session) | Per-item AI build phases + commitments | §3.9 = Item 8 OPRA Flow (updated this session per P1.3.7) |
| `trading-docs/08-planning/AUDIT_DISPOSITION_PLAN.md` | **v1.9** | Operator-decision and audit-disposition register | Updated in Phase 1 EXECUTE this session |
| `trading-docs/08-planning/ROI_LOG_BASELINE_2026-04-28.md` | **NEW (Action 2)** | Pre-activation empirical baseline (100% skip rate; `direction_signal_weak` dominant) | Created this session; closes Gate B provisionally |

### 2.3 Audit infrastructure (THIRD-MOST IMPORTANT location)

| File | Purpose | Status |
|---|---|---|
| `trading-docs/08-planning/ai-architecture-audits/_template.md` | Audit redline template (P1.3.0); 14 sections + §0 Pre-Audit Verification | Authoritative format |
| `trading-docs/08-planning/ai-architecture-audits/AUDIT_FINDINGS_REGISTER.md` | THE consolidated audit finding register. All Class A / B / C findings across all P1.3.x audits | **365 lines after this session**; THE source of truth for finding-IDs |
| `trading-docs/08-planning/ai-architecture-audits/CROSS_CUTTING_EVIDENCE_MATRIX.md` | Cross-spec evidence matrix (`CCEM`) — per-item blocks + cross-cutting themes + dependency graph | **717 lines after this session**; updated for Item 8 (lines 50, 254–276) |
| `trading-docs/08-planning/ai-architecture-audits/AI_ARCH_EVIDENCE_PACK.md` | The immutable P1.1 evidence pack (all repo state captured at one moment). Referenced by every audit | Immutable since P1.1 |
| `trading-docs/08-planning/ai-architecture-audits/AI-SPEC-005.md` | Cluster B audit 1/4 (Vol Fair-Value HAR-RV) | 533 lines; **READ END-TO-END** when Item 5 is in scope (we did this in P1.3.7 EXECUTE) |
| `trading-docs/08-planning/ai-architecture-audits/AI-SPEC-006.md` | Cluster B audit 2/4 (Meta-Labeler) | 603 lines; precedent for cross-spec FK cascade theme |
| `trading-docs/08-planning/ai-architecture-audits/AI-SPEC-008.md` | **Cluster B audit 3/4 (OPRA Flow Alpha) — CREATED THIS SESSION** | 583 lines; on `feature/PLAN-AIARCH-000-phase-1-p1-3-7-audit-spec-008-opra-flow-alpha` branch |

### 2.4 Locked specs (immutable, read-only)

`trading-docs/04-modules/ai-architecture/archive/raw-locked-specs-2026-04-26/`:

- `ITEM_1_AI_RISK_GOVERNOR_LOCKED.md`
- `ITEM_2_STRATEGY_ATTRIBUTION_LOCKED.md`
- `ITEM_3_SYNTHETIC_COUNTERFACTUAL_CASES_LOCKED.md`
- `ITEM_4_REPLAY_HARNESS_LOCKED.md`
- `ITEM_5_VOLATILITY_FAIR_VALUE_ENGINE_LOCKED.md` (533 lines after pre-EXECUTE read this session)
- `ITEM_6_META_LABELER_LOCKED.md`
- `ITEM_7_ADVERSARIAL_PRE_TRADE_REVIEW_LOCKED.md`
- `ITEM_8_OPRA_FLOW_ALPHA_LOCKED.md` (585 lines, 13 sections — audited this session)
- `ITEM_9_EXIT_OPTIMIZER_LOCKED.md` (783 lines — **next audit target**)
- `ITEM_10_COUNTERFACTUAL_PNL_LOCKED.md`
- `ITEM_11_EVENT_DAY_PLAYBOOKS_LOCKED.md`
- `ITEM_12_DYNAMIC_CAPITAL_ALLOCATION_LOCKED.md`
- `ITEM_13_DRIFT_DETECTION_LOCKED.md`

**Never edit these.** They are the immutable source of truth. All amendments happen via Phase 2 corrections to *audit redlines*, then operator-mediated re-lock.

### 2.5 Code (target of audits)

`backend/`:
- `risk_engine.py` — capital preservation; `_RISK_PCT` ladder fixed in Action 7b (this session)
- `strategy_selector.py` — `STATIC_SLIPPAGE_BY_STRATEGY` (canonical 10 strategies); modified in Phase 2 / Action 1 v1.1
- `databento_feed.py` — Layer 0 OPRA stream consumer (452 lines at HEAD; +5 line drift since evidence pack)
- `polygon_feed.py` — realized-vol producer; bilateral with Item 5
- `prediction_engine.py` — `_safe_redis()` defined at line 100, dead-code (carry-forward #4)
- `gex_engine.py` — sole consumer of `databento:opra:trades`
- `position_monitor.py` — exit-reason taxonomy (12 reasons; immutable to AI)
- `main.py` — Railway entry point; `flow_agent` consumer at line 1917
- `tests/` — pytest suite

`backend_agents/`:
- `synthesis_agent.py` — modified in Phase 2 (canonical strategy enums + `_synthesis_schema` validator)
- `surprise_detector.py` — modified in Phase 2 (canonical strategy enums + validator)
- `flow_agent.py` — 343 lines at HEAD; brief generator pending migration per Item 8 spec §8 (`C-AI-008-2`)
- `_synthesis_schema.py` — **NEW FILE** created this session (Phase 2 / Action 1 v1.1)

`supabase/migrations/`:
- 68 migrations at HEAD (verified V3 in P1.3.7)
- Latest material: `2026MMDD_*` patterns; no `opra_flow_*` migrations exist

### 2.6 Tracking & meta-files

| File | Purpose |
|---|---|
| `trading-docs/06-tracking/action-tracker.md` | Logs each ACT-NNN action with evidence; updated Phase 2 (canonical strategy fix) |
| `trading-docs/06-tracking/risk-register.md` | Risk register |
| `trading-docs/06-tracking/HANDOFF_NOTE_2026-04-28_POST_P1-3-7.md` | **THIS FILE** |
| `trading-docs/08-planning/feature-proposals.md` | If you identify ANY unplanned feature, log here, do NOT implement (per `.cursorrules`) |

---

## 3. CURRENT REPOSITORY STATE AT HANDOFF

### 3.1 Git state

```
Repo HEAD on main: 13d2b18  (PR #74 merged: Action 7b — _RISK_PCT ladder monotonicity)
Current branch:    feature/PLAN-AIARCH-000-phase-1-p1-3-7-audit-spec-008-opra-flow-alpha
Branch HEAD:       e7baed7  (P1.3.7 audit committed; pushed to origin; NOT merged)
Working tree:      clean (modulo backend/.venv/ untracked, normal)
```

### 3.2 Recent merged work (sequence on `main`)

| PR | SHA | Action | Description |
|---|---|---|---|
| #65 | (earlier) | P1.3.5 audit | AI-SPEC-005 Vol Fair-Value Engine audit (Cluster B 1/4) |
| (merged earlier) | (earlier) | P1.3.6 audit | AI-SPEC-006 Meta-Labeler audit (Cluster B 2/4) |
| (merged this session) | (earlier) | Phase 2 governance trio | Master ROI Plan v2.0.3, AI Build Roadmap v1.7, Audit Disposition Plan v1.8 committed |
| (merged this session) | (earlier) | Phase 1 / 1B | Trio + AFR + AI-SPEC-006 canonical-list factual corrections (drift literals replaced with canonical) |
| #72 | (merged this session) | Action 1 v1.1 | Strategy enum string-drift fix in 4 code + 2 test files; new `_synthesis_schema.py` validator; warning in `strategy_selector.py`; 3 regression tests |
| #74 | `13d2b18` | Action 7b | `_RISK_PCT` ladder monotonicity fix (Phase 2-4 scaled 2× to preserve dollar-equivalent ladder); test added |

### 3.3 Pushed-but-NOT-merged branches (operator-pending)

| Branch | Commit | What it contains |
|---|---|---|
| `feature/PLAN-AIARCH-000-phase-1-p1-3-7-audit-spec-008-opra-flow-alpha` | `e7baed7` | **THIS SESSION'S P1.3.7 AUDIT** — 4 files (3 modified + 1 new); +668 / -38 lines. Recommended status: `spec_has_semantic_drift_from_locked_intent` (RATIFY-WITH-AMENDMENTS) |
| (Action 2 branch — created earlier this session) | (its SHA) | `ROI_LOG_BASELINE_2026-04-28.md` (162 lines verbatim baseline). Provisionally closes Gate B |

> Both branches await operator review/merge. **Do NOT merge them autonomously.**

### 3.4 Path Y activation gate status

| Gate | Closed by | Status |
|---|---|---|
| **Gate A** | Action 1 v1.1 (strategy enum drift) | ✓ Closed (PR #72 merged) |
| **Gate B** | Action 2 (ROI log baseline) | △ Provisionally closed (branch pushed; not merged) |
| **Gate C** | Action 3 / P1.3.7 (AI-SPEC-008 audit) | ✓ Closed (this session; branch pushed; not merged) |
| **Gate D** | (TBD per Master Plan §3) | ⏸ Not yet sequenced |
| **Gate E** | (TBD per Master Plan §3) | ⏸ Not yet sequenced |
| **Gate F** | Action 7b (`_RISK_PCT` ladder monotonicity) | ✓ Closed (PR #74 merged; SHA `13d2b18`) |

> Path Y activation = future feature activation gate. Closing all required gates is a prerequisite for Path Y operator approval.

### 3.5 AI-spec audit progress

| Audit | Spec | Status |
|---|---|---|
| P1.3.0 | template + scaffolding | ✓ |
| P1.3.0b | template revisions | ✓ |
| P1.3.1 | AI-SPEC-001 (AI Risk Governor) | ✓ merged |
| P1.3.2 | AI-SPEC-002 (Strategy Attribution) | ✓ merged |
| P1.3.3 | AI-SPEC-004 (Replay Harness) | ✓ merged |
| P1.3.4 | AI-SPEC-010 (Counterfactual P&L) | ✓ merged |
| **P1.3.5** | **AI-SPEC-005 (Vol Fair-Value HAR-RV)** | ✓ merged (PR #65); **Cluster B 1/4** |
| **P1.3.6** | **AI-SPEC-006 (Meta-Labeler)** | ✓ merged; **Cluster B 2/4** |
| **P1.3.7** | **AI-SPEC-008 (OPRA Flow Alpha)** | ⚠ committed + pushed THIS SESSION; **NOT merged**; **Cluster B 3/4** |
| **P1.3.8** | **AI-SPEC-009 (Exit Optimizer)** | ⏸ NEXT TARGET (Master ROI Plan §3 Action 4); **closes Cluster B (4/4)** |
| P1.3.9+ | Cluster C audits (AI-SPEC-003, 007, 011, 012, 013) | ⏸ Future |

---

## 4. THE β-lite MULTI-DOCUMENT GOVERNANCE STRUCTURE

This was a **major architectural decision** in this session. Read carefully.

### 4.1 The problem it solves

Earlier in the conversation, an audit revealed "silent drops" — ROI-relevant items being lost because tables and lists were treated as authoritative when they were actually just summaries of source registers. The fix: adopt a **3-document trio** with **strict source-fidelity discipline** + a **fix-now-over-defer-to-later** rule.

### 4.2 The trio

1. **`MASTER_ROI_PLAN.md`** (the "spine") — central ROI improvement plan; enumerates all Actions 1–N; binding authority for action prompts
2. **`AI_BUILD_ROADMAP.md`** (the "build companion") — per-AI-item build phases (3.1 through 3.13 for Items 1–13); commitment lists per V0.x phase; ROI vectors
3. **`AUDIT_DISPOSITION_PLAN.md`** (the "register companion") — operator-decision register with disposition status; D-023 enrichment items tracked here

### 4.3 Source-fidelity discipline (CRITICAL)

> **Companion documents MUST faithfully reflect content from source registers. Whenever you update one of the trio, check whether the other two need synchronized patches. Tables and lists in companion docs are NOT authoritative — they are summaries. The actual source register (`AUDIT_FINDINGS_REGISTER.md`, `CROSS_CUTTING_EVIDENCE_MATRIX.md`, locked specs) is the source of truth.**

### 4.4 Fix-now over defer-to-later

When you discover an issue during review, prefer to **fix it immediately** rather than queue it. This emerged after multiple cycles of "deferred items get silently dropped." The rule applies to:

- Cosmetic fixes (apply now; don't list and defer)
- Documentation drift (fix now; don't note-and-leave)
- Cross-doc inconsistencies (sync now in same PR)

### 4.5 Converged-state cleanup

When trio updates land in the same PR, do a final synchronized patch cycle to ensure all three are converged on the same state.

---

## 5. THE 5 PREVENTION MECHANISMS (MANDATORY AUDIT DISCIPLINE)

These mechanisms emerged from post-P1.3.5 issues and are mandatory for every audit. Apply ALL FIVE on every Class B finding (especially) and every Class C escalation.

### Mechanism 1 — Inline-citation discipline

Every concrete claim in an audit MUST cite its evidence inline:
- Spec citations: `Spec §<N> line <NN>` or `Spec lines <NN>–<MM>`
- Code citations: `<file>:<NN>` (line number) or `grep -rn "<pattern>" <dir>` (verification command)
- Cross-spec citations: `<other-finding-id>` (e.g., `B-AI-005-1`, `C-AI-004-4`)
- Verification commands: documented in §0.4 "Verification commands run" table

### Mechanism 2 — Quote vs paraphrase distinction

When citing spec text:
- **Quote verbatim** if the exact wording matters (use backticks around the quoted phrase)
- **Paraphrase clearly** when summarizing — use phrases like "spec states that" or "per spec"
- Never blur the line. Quotes are evidence; paraphrases are interpretation.

### Mechanism 3 — Class B sanity-check (triple-check before commit)

For every Class B finding, before commit:
1. **Spec quote** — what does the spec actually say? (Re-read the cited line)
2. **HEAD reality** — what does the code/repo actually show at HEAD? (Re-run the grep)
3. **Proposed correction** — does it match the spec intent + repo gap?

This is a **self-review pass** that runs after the redline is drafted but before `git commit`. We performed it this session for P1.3.7 (verified A-AI-008-2 quality-flag count via spec §1 line 59 + line 146 lookup).

### Mechanism 4 — Verification language discipline

Use precise verification verbs:
- "**verified** by `grep ... returning zero matches`" — strong claim; falsifiable
- "**confirmed** by `wc -l <file>` = 343" — strong claim; falsifiable
- "**bilateral with `<other-finding>`**" — cross-spec dependency; not solo claim
- "**TBD pending P1.3.X**" — explicit defer, not silent drop

Avoid:
- "appears to" (weak)
- "likely" (weak unless you've enumerated alternatives)
- "should be" (prescriptive without authority)

### Mechanism 5 — Amendment-round verification

When operator authorizes an EXECUTE phase that modifies the audit plan (e.g., extends scope, accepts a new finding, adds a mandatory pre-EXECUTE reading), Cursor MUST:
1. Update the audit's §0 (Pre-Audit Verification) to document the amendment
2. Re-run any verification commands affected by the new scope
3. Document the amendment in the audit's Update Log section

**Reference for these mechanisms:** they are referenced throughout `AUDIT_FINDINGS_REGISTER.md` history log entries (look for "post-P1.3.5 prevention discipline").

---

## 6. WORKFLOW PATTERNS — DIAGNOSE-FIRST vs EXECUTE-FIRST

### 6.1 DIAGNOSE-FIRST (the default for AI-spec audits + complex code fixes)

When the operator sends a prompt with explicit "(DIAGNOSE-FIRST)" tag OR when a task involves multiple files / cross-spec impact / non-trivial decisions:

1. **Read all mandatory sources** (locked spec + AFR + CCEM + Evidence Pack chunks + dependency files)
2. **Run verification commands** (grep, wc, ls, git log) and document results
3. **Pre-classify findings** (Class A / B / C with finding-ID stubs)
4. **Identify ambiguities, scope conflicts, contradictions** — surface them as numbered "Ambiguities" requiring operator decision
5. **Identify any STOP conditions** triggered (see §7) — surface them with context
6. **Produce a structured DIAGNOSE report** with:
   - Files read (line counts)
   - Verification commands run + results
   - Pre-classified findings
   - Ambiguities (numbered)
   - STOP conditions (if any)
   - Recommended EXECUTE plan (with dependencies)
7. **STOP and await operator authorization** before EXECUTE

### 6.2 EXECUTE-FIRST (when operator pre-authorizes; rare)

When operator says "proceed with EXECUTE" or sends a fully-specified single-file change:
1. Skip DIAGNOSE → directly produce the change
2. But still apply Mechanisms 1-5
3. Still STOP if any condition in §7 triggers mid-EXECUTE

### 6.3 EXECUTE Authorization (operator response to DIAGNOSE)

The operator's authorization message typically contains:
- Approval / rejection of DIAGNOSE report
- Resolutions for each surfaced ambiguity (e.g., "Ambiguity 1 → option a")
- Any additional pre-EXECUTE prerequisites (e.g., "AI-SPEC-005 standalone end-to-end read REQUIRED")
- Side-findings noted for later (e.g., "Phase 4C name discrepancy — surface but don't auto-resolve")
- The greenlight phrase ("Proceed with EXECUTE", "GO with execution Steps 1-N")

After EXECUTE Authorization, Cursor:
1. Completes any pre-EXECUTE prerequisites
2. Executes the work per the resolved plan
3. Self-applies Mechanism 3 (triple-check) before commit
4. Verifies `git diff --stat` matches expected file count
5. Commits with PR-quality body (HEREDOC format)
6. Pushes branch (do NOT merge unless explicitly authorized)
7. Produces a structured EXECUTE summary report (the format is part of the prompt)

### 6.4 Mid-EXECUTE STOP (Phase 1B Site 4 pattern)

If during EXECUTE you discover the prompt contains a transcription error (e.g., target text doesn't exist), STOP IMMEDIATELY:
1. Document what was found vs what the prompt said
2. Surface as "Mid-EXECUTE Decision Point" with options A/B/C
3. Wait for operator response

This pattern occurred in Phase 1B (Site 4 was a duplicate of Site 1; operator chose Option A: continue with remaining edits).

---

## 7. STOP CONDITIONS (1–7) — WHEN TO HALT AND ASK

These are the canonical conditions that trigger a STOP. Some are HARD STOPS (must halt); some are BORDERLINE (Cursor's judgment + operator notification).

| # | Condition | Type | Example from this session |
|---|---|---|---|
| **1** | Required mandatory document is missing or unclear | HARD | (none triggered this session) |
| **2** | Prompt-specified line numbers don't match actual code | BORDERLINE | Phase 2 — `strategy_selector.py` line numbers drifted; operator said "USE STRUCTURAL PLACEMENT, not prompt's line numbers" |
| **3** | Spec / code fundamentally disagrees with prompt's premise | HARD | (none triggered this session at HARD severity) |
| **4** | Prompt cites a finding-ID whose actual content differs from the prompt's description | BORDERLINE | Phase 1B Site 4 (duplicate of Site 1 — transcription error); P1.3.7 `B-AI-006-3` citation drift; operator chose option 1a |
| **5** | Existing scaffold drifts significantly from evidence pack snapshot | INFORMATIONAL | `databento_feed.py` 447→452 lines; operator accepted as informational |
| **6** | The fix would create stale documentation (e.g., comment block becoming false) | BORDERLINE | Action 7b — comment block in `risk_engine.py` would become stale; operator chose Option B (expand scope to update comment block) |
| **7** | Audit scope or output count doesn't match spec count | BORDERLINE | P1.3.7 — prompt said §1-§10, spec had §1-§13; operator chose option 3a (extend coverage) |
| **9** | Same as Stop 4 but operator notes it's the Nth occurrence of same drafting failure | BORDERLINE | P1.3.7 — operator added discipline note: "grep AFR for actual finding text before citing in prompts" |

**Rule of thumb:** If you find yourself thinking "the prompt says X but the reality is Y, what should I do?" — STOP and ask. The operator strongly prefers Cursor to surface ambiguity early rather than make assumptions and produce drift later.

**Borderline Stop reporting format:**
```markdown
## Borderline STOP CONDITION <N>

**Trigger:** [exact issue]
**What I found:** [verified facts]
**What the prompt assumed:** [paraphrase]
**Options:**
- (a) [option a — usually conservative]
- (b) [option b — usually expanded scope]
- (c) [option c — operator override]
**Recommended default:** [your judgment + rationale]
**Awaiting operator decision before proceeding.**
```

---

## 8. AUDIT FINDING TAXONOMY — CLASS A / B / C

Per `CONSOLIDATED_PLAN_v1.2_APPROVED.md` §3, every audit finding falls into one of three classes:

### Class A — Mechanical Errors

- **Examples**: wrong line numbers, mistyped names, wrong counts (e.g., "8 fields" when actually 7), wrong file paths, stale tier labels
- **Authority**: Any AI corrects; Cursor verifies; operator rubber-stamps at end
- **Format**: Each row has `Spec Says` + `Correct Value` + `Source of Truth` (must be falsifiable)
- **Naming convention**: `A-AI-<NNN>-<N>` (e.g., `A-AI-008-1`)
- **This session**: 2 added (`A-AI-008-1` tier label; `A-AI-008-2` quality-flag count)

### Class B — Implementation Status / Content Omissions

- **Examples**: spec says "exists" but code shows "planned"; spec assumes data captured that isn't; spec says "live" but reality is "observability-only"
- **Authority**: GPT or Claude proposes; Cursor verifies; operator approves consolidated list
- **Format**: Each row has `Spec Says` + `Reality` + `Proposed Correction` (the **triple-check** of Mechanism 3)
- **Naming convention**: `B-AI-<NNN>-<N>` (e.g., `B-AI-008-3`)
- **This session**: 18 added for AI-SPEC-008 (B-AI-008-1 through B-AI-008-18)

### Class C — Architectural Intent Corrections

- **Examples**: Spec violates an existing D-XXX; spec proposes new authority that conflicts with constitutional rules; cross-spec contract gap
- **Authority**: **OPERATOR-ONLY**. Default = reject unless clear reason. Resolution requires NEW D-XXX or spec revision to comply with existing D-XXX.
- **Format**: Each row has `Issue` + `Conflicting D-XXX or Rule` + `Resolution Required` (with 3+ enumerated options + explicit default)
- **Naming convention**: `C-AI-<NNN>-<N>` (e.g., `C-AI-008-1`)
- **This session**: 4 added for AI-SPEC-008 (C-AI-008-1 through C-AI-008-4)
- **Operator-pending**: All 4 fold into D-023 enrichment items (u)/(v)/(w); operator must decide each before P1.3.7 can be considered "closed"

### Cross-spec themes (recorded in `AUDIT_FINDINGS_REGISTER.md` §5)

When 2+ audits surface the same pattern, a "cross-spec theme" is established. Themes are tracked with:
- Theme name
- Number of audits confirming
- Active vs ruled-out items
- Severity (e.g., "open governance debt" vs "load-bearing safety substrate")

**Active themes after P1.3.7:**
- `_safe_redis()` dead code (carry-forward #4) — 4 audits; safety-critical for Cluster B
- Layer 1 / Layer 2 architectural pattern — 4 adoptions (Items 5, 6, 8, 10); Item 8 introduces "Layer 0 + Layer 2 coexistence" variant
- Cross-spec FK / producer-surface cascade — 6 audits
- `calibration_eligible` flag — 5 confirmed surfaces; potential 6th (Item 8 scheduled buildout)
- Decision-card definition — 4 audits
- Archived option-chain substrate — 4 audits (transitive)
- Abstract Commit-N anchor — 3 audits
- **NEW** OPRA-stream substrate dependency — introduced P1.3.7
- **NEW** Cross-spec producer→consumer contract ratification — introduced P1.3.7
- **NEW** Z-score producer authority expansion — confirmed in 3 audits with new scope

---

## 9. PATH Y ACTIVATION GATES

"Path Y" is shorthand for a future feature/capability activation that requires multiple prerequisite gates to close. The operator-defined gates are:

| Gate | Topic | Closure mechanism | Status |
|---|---|---|---|
| A | Strategy enum string-drift fix (canonical 10) | Action 1 v1.1 (PR #72) | ✓ Closed |
| B | ROI log baseline (empirical pre-activation skip distribution) | Action 2 (`ROI_LOG_BASELINE_2026-04-28.md`) | △ Provisionally closed (branch pushed) |
| C | AI-SPEC-008 audit (OPRA Flow Alpha) | Action 3 / P1.3.7 (this session) | ✓ Closed (branch pushed) |
| D | (TBD per Master Plan) | (TBD) | ⏸ Not yet sequenced |
| E | (TBD per Master Plan) | (TBD) | ⏸ Not yet sequenced |
| F | `_RISK_PCT` ladder monotonicity (Phase 2-4 risk-pct restored) | Action 7b (PR #74; SHA `13d2b18`) | ✓ Closed |

> **The gates A-F are not necessarily sequential.** They can close in any order. Path Y activation requires ALL gates to be closed (operator-defined).

---

## 10. WHAT WAS DONE IN THIS SESSION (Chronological)

### 10.1 Phase 0 — β-lite trio review cycle (multiple iterations)

Reviewed and refined the 3 governance documents through ~10 versions each:
- `MASTER_ROI_PLAN.md` v2.0.1 → v2.0.3
- `AI_BUILD_ROADMAP.md` v1.0 → v1.7
- `AUDIT_DISPOSITION_PLAN.md` v1.0 → v1.8

Adopted "fix-now over defer-to-later" rule + "tables are silent-drop surfaces" structural lesson + version-agnostic invariant citations (e.g., "PRE-P11-3" instead of "Bug B1-3 v1.4").

### 10.2 Phase 2 governance trio commit

Branch: `docs/phase-2-governance-trio` (since deleted post-merge). Committed all 3 governance docs to `trading-docs/08-planning/`. Updated `system-state.md` (scope: documentation-track changes only). Added `ADDITIONAL VERIFICATION STEP` for line counts. Merged after operator review.

### 10.3 Post-merge verification

Verified trio landed cleanly on `main` after merge. Cleaned up local stale branches per operator (`option a`).

### 10.4 Action 1 Pre-Deployment Audit (READ-ONLY)

Audited the existing `CURSOR_PROMPT_ACTION_1_STRING_DRIFT.md` against `MASTER_ROI_PLAN.md` v2.0.3 Action 1. Identified the "canonical 8" error (should be 10) — propagated widely. Surfaced 3 flagged defects + uncovered more. Operator chose `ship all 4` for the §(r) forward-pointer default.

### 10.5 Phase 1 — Trio Canonical-List Correction (DIAGNOSE → EXECUTE)

DIAGNOSE surfaced 6 clarification needs (math error, out-of-scope claims, wording mismatches, line drifts). Operator authorized EXECUTE with 6 clarifications. EXECUTE applied factual corrections to:
- `MASTER_ROI_PLAN.md`
- `AI_BUILD_ROADMAP.md`
- `AUDIT_DISPOSITION_PLAN.md`

Replaced "canonical 8" → "canonical 10" at all ASSERTING sites; preserved REPORTING/HISTORICAL sites for audit-trail clarity.

### 10.6 Phase 1B — AFR + AI-SPEC-006 Canonical-List Correction (DIAGNOSE → EXECUTE)

DIAGNOSE identified 4 sites for correction. Mid-EXECUTE: Site 4 was a duplicate of Site 1 (prompt-side transcription error). Surfaced as Mid-EXECUTE Decision; operator chose **Option A**: continue with remaining edits. Completed 3 corrections to:
- `AUDIT_FINDINGS_REGISTER.md`
- `AI-SPEC-006.md`

### 10.7 Phase 2 / Action 1 v1.1 — Strategy Enum String-Drift Fix (DIAGNOSE → EXECUTE)

DIAGNOSE surfaced borderline STOP CONDITION 2 (line numbers drifted). Operator clarified: USE STRUCTURAL PLACEMENT. EXECUTE applied:
- 4 code files modified (`backend_agents/synthesis_agent.py`, `backend_agents/surprise_detector.py`, `backend/strategy_selector.py`, `backend_agents/_synthesis_schema.py` NEW)
- 2 test files modified (`backend/tests/test_phase_2a_agents.py`, `backend/tests/test_consolidation_s5.py`)
- 1 tracking file modified (`trading-docs/06-tracking/action-tracker.md`)
- 3 new regression tests (`test_validator_returns_none_on_invalid_strategy`, `test_validator_returns_payload_unchanged_on_canonical_strategy`, `test_strategy_selector_logs_warning_on_invalid_hint`)

Pytest baseline preservation pattern: used `git stash push -m "phase2-tracked-only"` (without `-u` flag) to preserve `.venv` for baseline testing on `main`. Confirmed no new regressions vs baseline. **Closed Gate A.**

### 10.8 Action 2 — Commit ROI Log Baseline (Gate B)

Single new file `ROI_LOG_BASELINE_2026-04-28.md` (162 lines verbatim content provided by operator). Committed to new branch; pushed; **NOT merged** per instructions. **Provisionally closed Gate B.**

### 10.9 Action 7b — `_RISK_PCT` Ladder Monotonicity Fix (DIAGNOSE → EXECUTE)

DIAGNOSE identified non-monotonic ladder (Phase 1 was 2× post-2026-04-20 width widening but Phases 2-4 retained pre-widening values). Surfaced borderline STOP CONDITION 6 (comment block in `risk_engine.py` would become stale). Operator chose **Option B**: expand scope to update comment block. EXECUTE applied:
- `backend/risk_engine.py` — `_RISK_PCT` Phase 2-4 scaled 2× to restore monotonicity; comment block updated
- `backend/tests/test_risk_engine.py` — new `test_risk_pct_ladder_monotonic()` regression test
- `AUDIT_FINDINGS_REGISTER.md` — `PRE-P11-3` status updated

Merged as PR #74 to `main` at SHA `13d2b18`. **Closed Gate F.**

### 10.10 Action 3 / P1.3.7 — AI-SPEC-008 OPRA Flow Alpha Audit (DIAGNOSE → EXECUTE)

**This was the largest single task this session.**

**DIAGNOSE phase** surfaced 4 ambiguities + 3 informational side-findings:
- **Ambiguity 1**: Prompt's `B-AI-006-3` citation didn't match AFR (transcription error). Operator chose 1a (Class C finding).
- **Ambiguity 2**: `flow_agent` migration policy contradiction (spec §8 coexistence vs Build Roadmap §3.9 line 372 successor-replace). Operator chose 2a (Class C escalation; default option 1 = coexistence).
- **Ambiguity 3**: Audit scope §1-§10 vs §1-§13. Operator chose 3a (extend to §1-§13).
- **Ambiguity 4**: Mandatory readings — partial reads disclosed. Operator required end-to-end read of `AI-SPEC-005.md` before EXECUTE.

**EXECUTE phase** completed 4 outputs after AI-SPEC-005 standalone read:
- **Output 1**: NEW `AI-SPEC-008.md` redline (583 lines, 14 sections + §0 Pre-Audit Verification)
- **Output 2**: `AUDIT_FINDINGS_REGISTER.md` updated (2 Class A + 18 Class B + 4 Class C; cross-spec themes; D-023 enrichment items u/v/w; new phase entry; new TASK_REGISTER section; new system-state field; constitution.md pointer note; P1.3.7 history log entry)
- **Output 3**: `CROSS_CUTTING_EVIDENCE_MATRIX.md` updated (line 50 tier V0.2→V0.3; lines 254-276 Item 8 block populated)
- **Output 4**: `AI_BUILD_ROADMAP.md` §3.9 updated (audit-validated 13-item enumeration + 14th cross-spec hygiene addendum + flow_agent migration options + V0.3 pre-implementation gate)

Mechanism 3 self-review pass completed; `git diff --stat` verified 4 files (3 modified + 1 new); committed with PR-quality HEREDOC body; pushed; **NOT merged**. **Closed Gate C.**

### 10.11 Mandatory structured EXECUTE summary report

Produced 11-section report documenting branch/commit/push status, pre-EXECUTE prerequisites, findings tally, Class C operator decisions, cross-spec themes, governance updates queued, STOP conditions tripped + resolved, side-findings, Mechanism 3 self-review results, Path Y gate status, and next recommended action.

---

## 11. OPERATOR-PENDING DECISIONS (BLOCKING for Next Steps)

These items require `tesfayekb` decisions before further progress on related work streams. **Do NOT make any of these decisions autonomously.**

### 11.1 P1.3.7 Class C operator decisions (4 items)

| ID | Issue | Default | Operator action required |
|---|---|---|---|
| `C-AI-008-1` | Cross-spec producer→consumer contract gap (Item 8 §5 unilateral 8-feature contract with Item 5; 20-feature with Item 6; both consumer specs silent at field-name level) | Option 3 (forward-looking unilateral; bilateral confirmation deferred to next P1.3.5/P1.3.6 amendment cycle) | Choose option 1 (ratify via amendment), 2 (revoke claims), or 3 (default — accept unilateral) |
| `C-AI-008-2` | `flow_agent` migration policy contradiction (locked spec §8 coexistence vs Build Roadmap §3.9 line 372 successor-replace) | Option 1 (coexistence with role-narrowing) | Choose option 1 (default), 2 (full replacement), or 3 (hybrid with new file) |
| `C-AI-008-3` | Databento subscription scope (sub-second NBBO + sweep tape granularity may exceed current tier) | Option 4 (pre-implementation operator gate — V0.3 cannot begin until subscription verification completes) | Verify subscription tier vs spec §1 requirements; choose 1 (within budget), 2 (D-008 budget revision via D-025), 3 (spec amendment to relax), or 4 (default — pre-implementation gate) |
| `C-AI-008-4` | V0.3 advisory-only acceptance (calendar-blocked on Item 6 V0.2 + chain-archive substrate; bilateral with `C-AI-004-4`) | Option 3 (explicit V0.3 advisory-only acceptance; logged in `system-state.md`) | Choose option 1 (forward archival), 2 (paid historical archive), or 3 (default — advisory-only) |

### 11.2 D-023 enrichment items (encoded for batch operator approval)

D-023 = "AI Authority Boundary" decision record (proposed in AI-SPEC-001 §11; addended by AI-SPEC-002, AI-SPEC-004, AI-SPEC-010, AI-SPEC-005, AI-SPEC-006). After P1.3.7 it accumulates these enrichment items pending operator wording approval:

- (a)–(t) — accumulated from prior audits (see AFR §6)
- **(u)** — Item 8 (OPRA Flow Alpha) authority boundary: feature-producer-only; no admissibility/sizing/veto authority
- **(v)** — `flow_agent` cutover policy for Item 8 (per `C-AI-008-2`)
- **(w)** — Cross-spec producer→consumer contract ratification process (per `C-AI-008-1`)

### 11.3 Side-findings surfaced (NOT auto-resolved per authorization)

| # | Finding | Required action |
|---|---|---|
| 1 | `system-state.md` `current_sizing_phase: 1` shows `core_risk_pct: 0.005` — stale vs `risk_engine.py` post-Action 7b 0.010 | Tracked as informational; operator may issue docs PR to sync after a couple more gate closures land |
| 2 | `MASTER_PLAN.md` Phase 4C = "Trading Console — Options Module" vs `AI_BUILD_ROADMAP.md` §3.9 = "Item 8 OPRA Flow Alpha" | Pre-existing governance debt; operator decides whether to (a) rename MASTER_PLAN, (b) renumber Build Roadmap to Phase 4D, or (c) document explicit cross-reference |
| 3 | `databento_feed.py` 447→452 line drift since evidence pack snapshot | Informational; not blocking |

### 11.4 Open branches requiring operator action

| Branch | Purpose | Operator decision |
|---|---|---|
| Action 2 branch (ROI_LOG_BASELINE) | Provisional Gate B closure | Merge or hold |
| `feature/PLAN-AIARCH-000-phase-1-p1-3-7-audit-spec-008-opra-flow-alpha` | P1.3.7 audit; Gate C closure | Review the 4 Class C decisions; merge after disposition |

---

## 12. RECOMMENDED NEXT ACTIONS (Priority-Ordered)

### Priority 1 (NEXT TASK — P1.3.8 audit)

**Action 4 / P1.3.8: AI-SPEC-009 Exit Optimizer audit** per `MASTER_ROI_PLAN.md` v2.0.3 §3 Action 4.

- **Spec**: `trading-docs/04-modules/ai-architecture/archive/raw-locked-specs-2026-04-26/ITEM_9_EXIT_OPTIMIZER_LOCKED.md` (783 lines per Build Roadmap §3.10)
- **Purpose**: Closes Cluster B (audit 4 of 4)
- **Pattern**: DIAGNOSE-FIRST per the Cluster B audit template; mandatory readings include constitution + system-state + approved-decisions + MASTER_PLAN + Evidence Pack + AFR + CCEM + AI-SPEC-005 + AI-SPEC-006 + AI-SPEC-008 (now)
- **Prior precedents**: `AI-SPEC-005.md` (533 lines), `AI-SPEC-006.md` (603 lines), `AI-SPEC-008.md` (583 lines)
- **Expected output**: 4 files (1 new redline + 3 updates to AFR/CCEM/Build Roadmap §3.10)
- **Will likely confirm**: OPRA-stream substrate dependency (P1.3.7's new theme) if Item 9 V0.x reads OPRA flow inputs for exit-trigger evaluation

### Priority 2 (operator review window)

Operator review of P1.3.7 audit + 4 Class C decisions + D-023 enrichment items u/v/w. This is **operator work**, not Cursor work. Cursor stays available for clarification questions.

### Priority 3 (post-Cluster-B closure)

After P1.3.8 closes Cluster B:
- **Phase 2 spec corrections** for Cluster B (apply Class A/B corrections to locked spec amendments in next P1.3 amendment cycle; fold in operator-approved Class C resolutions)
- **D-023 wording finalization** (combined operator review of all enrichment items a-w)
- **Cluster C audit sequence**: AI-SPEC-003 / 007 / 011 / 012 / 013 (P1.3.9 onward)

### Priority 4 (longer-horizon)

- Path Y activation prerequisite review (gates A/B/C/F closed; D/E pending)
- Phase 4C/4D reconciliation (MASTER_PLAN.md vs AI_BUILD_ROADMAP.md naming)
- `system-state.md` sync for `core_risk_pct` (post-multiple-gate-closures)

---

## 13. CRITICAL GUARDRAILS — THINGS THAT WILL BREAK THE PROJECT

These are absolute don'ts. Violating any will produce invalid work product per `.cursorrules` final warning.

### 13.1 NEVER (without explicit operator approval)

- **NEVER edit a locked spec** (`trading-docs/04-modules/ai-architecture/archive/raw-locked-specs-2026-04-26/ITEM_*_LOCKED.md`)
- **NEVER add a D-XXX** to `approved-decisions.md` autonomously
- **NEVER merge a branch** to `main` autonomously (operator owns all merges)
- **NEVER force-push to main**
- **NEVER skip pre-commit hooks** (`--no-verify`)
- **NEVER bypass `.cursorrules` mandatory readings** for a fresh task
- **NEVER auto-resolve a Class C escalation** (operator-only authority)
- **NEVER invent a new shared function/route/event/permission/config-key without indexing per `.cursorrules`**
- **NEVER update `git config`**
- **NEVER commit `.env` or anything containing secrets**
- **NEVER drop a plan section** (per Constitution T-Rule 8)
- **NEVER change a stable PLAN-XXX ID** (immutable per change-control-policy)

### 13.2 ALWAYS (without exception)

- **ALWAYS read** `.cursorrules` + constitution + system-state + approved-decisions + MASTER_PLAN at task start
- **ALWAYS check** `system-state.md` execution gates before generating ANY code (`code_generation: blocked`?)
- **ALWAYS preserve** `.venv` when running `git stash` (use `-m "tracked-only"` without `-u`, OR pop after baseline)
- **ALWAYS run** `git diff --stat` before commit to verify file count matches expected
- **ALWAYS use HEREDOC** for commit messages (per `committing-changes-with-git` pattern)
- **ALWAYS push** new branches with `-u` flag for tracking
- **ALWAYS document** the §0.4 verification commands run + their results in audit redlines
- **ALWAYS apply Mechanism 3** (triple-check) before commit on every Class B finding
- **ALWAYS surface Class C escalations** with 3+ enumerated options + explicit default
- **ALWAYS produce structured EXECUTE summary report** when prompt requires it

### 13.3 If you find yourself doing X, STOP

- "I'll just go ahead and..." — STOP, ask first
- "The prompt probably means..." — STOP, surface ambiguity
- "This small fix won't matter..." — STOP, "fix-now over defer-to-later" applies but the operator still needs to approve scope expansion
- "I'll merge this since it's safe..." — STOP, never auto-merge
- "I'll just edit the locked spec..." — STOP, immutable
- "I'll add a new D-XXX..." — STOP, operator-only

---

## 14. ROI PRESERVATION DISCIPLINE

**ROI = Return on Investment** in this project means: every action either (a) directly enables a future trading edge, (b) removes a known risk to capital, or (c) closes a governance gap that blocks a/b. Actions that don't fit one of these shouldn't ship.

### 14.1 Where ROI is enumerated

- `MASTER_ROI_PLAN.md` (v2.0.3) — central ROI improvement plan; each Action has explicit ROI vector
- `AI_BUILD_ROADMAP.md` (v1.8) — per-AI-item "Expected ROI per registry" entries (e.g., "0% months 1-3 (collect/replay), +0% to +2% months 4-6 (advisory), +4% to +8% base / +8% to +12% bull months 7-12")
- `AUDIT_FINDINGS_REGISTER.md` Update Log — each P1.3.x history log entry summarizes findings impact

### 14.2 ROI-protective rules

- **Never silently drop an item.** If a finding/decision/spec line surfaces in source registers, it MUST appear in companion documents. Lists/tables in companion docs are summaries; the source register is authoritative.
- **Never re-classify Class A as Class B without operator notice.** Class A = mechanical/falsifiable; Class B = meaning change. Reclassification has policy implications.
- **Never re-classify Class B as Class A.** Class B requires `Spec Says + Reality + Proposed Correction` triple; Class A is single-correction. Reclassifying loses the triple.
- **Never re-classify Class C as Class B.** Class C is operator-only authority; Class B is consolidated-list approval. Reclassifying bypasses operator authority.
- **Track ROI vector per Action.** Every Action prompt has an implicit or explicit ROI claim. Verify it against the Master ROI Plan before EXECUTE.
- **Preserve audit-trail clarity.** REPORTING/HISTORICAL sites in audits must NOT be retroactively rewritten — they document past decisions. Only ASSERTING/forward-pointing sites get factual corrections.
- **Bilateral confirmation discipline.** When Spec X claims producer→consumer contract with Spec Y, verify Spec Y actually accepts that contract. If Y is silent/contradictory, surface as Class C — never assume bilateral.

### 14.3 Anti-pattern: silent-drop sites

Tables and lists in companion docs are silent-drop surfaces. When updating:
1. Cross-reference the source register (`AUDIT_FINDINGS_REGISTER.md`)
2. If a finding-ID is removed/changed in the table, verify it's also removed/changed in source
3. Never leave a finding-ID in source but absent from companion (or vice versa)
4. Use grep to verify: `rg "B-AI-008-3" trading-docs/` should show consistent count across all documents

---

## 15. CODE EXECUTION DISCIPLINE (Test Isolation, .venv, Baseline)

### 15.1 Pytest baseline preservation pattern

When testing a code fix, you need to compare PASS/FAIL counts on `main` (baseline) vs your feature branch. The trick is preserving the working `.venv`.

**WRONG** (loses `.venv`):
```bash
git stash push -u  # -u includes untracked → stashes .venv
git checkout main
.venv/bin/pytest backend/tests/  # FAILS — .venv gone
```

**RIGHT** (preserves `.venv`):
```bash
git stash push -m "phase2-tracked-only"  # no -u flag, .venv stays
git checkout main
.venv/bin/pytest backend/tests/ -v 2>&1 | tail -20  # baseline
git checkout <feature-branch>
git stash pop  # restore tracked changes
.venv/bin/pytest backend/tests/ -v 2>&1 | tail -20  # post-fix
# Compare PASS/FAIL counts; verify no NEW regressions
```

### 15.2 Path-mangling for test imports

When tests need to import from `backend/` and `backend_agents/`, the test file needs:
```python
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
_BACKEND_AGENTS_DIR = Path(__file__).resolve().parents[2] / "backend_agents"
sys.path.insert(0, str(_BACKEND_DIR))
sys.path.insert(0, str(_BACKEND_AGENTS_DIR))
```

(See `backend/tests/test_phase_2a_agents.py` for the canonical pattern.)

### 15.3 Test naming + placement

- All tests in `backend/tests/test_*.py`
- Test functions prefixed with `test_`
- One assertion concept per test where practical
- Use `pytest.raises(ExpectedException)` for negative tests
- Mock external dependencies (Redis, Supabase, network) via `unittest.mock`

### 15.4 Pre-existing test failures

The codebase has some pre-existing test failures that are NOT caused by current work. The discipline:
1. Establish baseline PASS/FAIL count on `main` BEFORE making changes
2. Apply changes
3. Verify NEW test count == baseline new tests + your additions; FAILS count <= baseline
4. If FAILS increases by N, your N tests are regressions — investigate

### 15.5 Code style alignment

Per user rules (in `<user_rules>`):
- 4 spaces indentation
- 80-char line limit (soft; existing code may exceed)
- snake_case variables
- camelCase functions (NOTE: existing Python code uses snake_case for functions; align to existing style)
- PascalCase classes
- Concise comments for complex blocks ONLY (no narration of obvious code)

> **Style ambiguity:** The user rules conflict with PEP 8 (Python uses snake_case for functions, not camelCase). For Python files, **align to existing project style (snake_case functions)**. For new TypeScript / JavaScript files, follow user rules.

---

## 16. COMMUNICATION DISCIPLINE — HOW TO REPORT

### 16.1 DIAGNOSE report format

```markdown
# DIAGNOSE Report — <Task Name>

## 1. Files Read (with line counts)
[List]

## 2. Verification Commands Run (with results)
[Numbered V1, V2, V3, ...]

## 3. Pre-Classified Findings
- Class A (Mechanical): N items — [stub IDs]
- Class B (Implementation Status): N items — [stub IDs]
- Class C (Architectural Intent): N items — [stub IDs]

## 4. Ambiguities Surfaced (numbered)
- **Ambiguity 1:** [exact issue]
  - Option a: [conservative]
  - Option b: [expanded]
  - Option c: [override]
  - Recommended default: [judgment + rationale]

## 5. STOP Conditions Triggered (if any)
[Per format in §7]

## 6. Recommended EXECUTE Plan
[Step-by-step with dependencies + estimated file count]

## 7. Awaiting Operator Authorization
```

### 16.2 EXECUTE summary report format

```markdown
# <Task Name> EXECUTE Summary Report

## 1. Branch / Commit / Push Status
[Table: branch, base SHA, commit SHA, push status, PR URL]

## 2. Pre-EXECUTE Prerequisites Completed
[Table: prerequisite, status, notes]

## 3. Findings Tally
[Class A / B / C counts + IDs]

## 4. Class C Findings — Operator Decision Required
[Table: ID, issue, default, folds into]

## 5. Cross-Spec Themes — Confirmation / New
[Table]

## 6. Governance Updates Queued (Operator-Pending)
[Table: document, update, status]

## 7. STOP Conditions Tripped + Resolved
[Table]

## 8. Side-Findings Per EXECUTE Authorization
[Table: finding, action]

## 9. Mechanism 3 Self-Review Pass Results
[Confirmation that all Class A/B/C have triple-check]

## 10. Path Y Activation Gate Status
[Table]

## 11. Next Recommended Action
[Per Master ROI Plan]
```

### 16.3 Mid-EXECUTE Decision format (when STOP triggers mid-EXECUTE)

```markdown
## Mid-EXECUTE Decision Point

**Trigger:** [exact issue mid-execute]
**What I found:** [evidence]
**What was already done:** [completed steps]
**What remains:** [pending steps]
**Options:**
- (a) Continue with remaining edits per default
- (b) Halt + revert + regenerate plan
- (c) [other operator override]
**Recommended default:** [judgment + rationale]
**Awaiting operator decision before proceeding.**
```

### 16.4 Final report format

ALWAYS produce a structured final report after EXECUTE. The operator depends on this for decision-making. Format depends on the prompt's structure but should at minimum include:
- What was committed (file list)
- What is open/pending operator action
- What the next recommended action is

### 16.5 Tone and style

- **No emojis** unless explicitly requested
- **Concise but complete** — every claim cited, no filler
- **Tables for structured data** (DON'T use Cursor canvas for these per the canvas skill — markdown tables are fine here)
- **Backticks for file/function/class names**
- **Code blocks with language tags** for new code; **CODE REFERENCE format `startLine:endLine:filepath`** for existing code citations
- **Never narrate tool use** ("Let me read X" before tool call) — just call the tool

---

## 17. CITATION DISCIPLINE — LESSONS LEARNED ABOUT PROMPT-SIDE ERRORS

This is a **major lesson from this session** that the next agent MUST internalize.

### 17.1 The pattern (4 occurrences this session)

| Occurrence | Location | Error |
|---|---|---|
| 1 | Phase 1B Site 4 | Site 4 was a duplicate of Site 1 (transcription error in prompt) |
| 2 | Phase 2 Site D | Line numbers drifted from actual code |
| 3 | Action 7b comment block | Comment block staleness not anticipated in prompt |
| 4 | P1.3.7 `B-AI-006-3` citation | Prompt cited `B-AI-006-3` for "5 of Item 6's 47 features come from Item 8" but `B-AI-006-3` actually refers to 5 Rules Engine fields |

### 17.2 The discipline (operator-added in P1.3.7 EXECUTE Authorization)

> "Before drafting any prompt that cites a prior-audit finding ID (e.g., `B-AI-006-3`, `C-AI-005-2`), grep AFR for the actual finding text and re-verify the claim being attributed. Do not transcribe finding-ID claims from memory or summaries."

### 17.3 What this means for the next agent (during DIAGNOSE)

If the prompt cites a finding-ID, **immediately verify it**:
```bash
rg "B-AI-006-3" trading-docs/08-planning/ai-architecture-audits/AUDIT_FINDINGS_REGISTER.md
```
If the actual content differs from the prompt's description, this is a **borderline STOP CONDITION 4** — surface it before proceeding.

The operator generally appreciates this discipline and may restructure the EXECUTE plan based on the surfaced error (e.g., promote the actual cross-spec issue to a new Class C finding while documenting the prompt-side transcription error).

### 17.4 What this means for the next agent (during EXECUTE)

If you draft any new finding-ID citations in your audit redline:
1. Re-grep AFR to confirm the cited finding-ID exists with the right content
2. Cite it inline with `[finding-ID]` syntax (matches AFR pattern)
3. If your audit introduces a new ID (e.g., `B-AI-008-N`), verify the next available ordinal number isn't already taken

---

## 18. USEFUL COMMANDS AND PATTERNS

### 18.1 Branch creation pattern

```bash
git fetch origin main
git checkout -b feature/PLAN-AIARCH-000-phase-1-p1-3-X-audit-spec-NNN-<short> origin/main
```

> Use `feature/PLAN-AIARCH-000-phase-1-p1-3-<X>-audit-spec-<NNN>-<descriptor>` for AI-spec audits.
> Use `feature/<id>-<descriptor>` for non-audit features.

### 18.2 Git stash baseline pattern (preserves .venv)

```bash
git stash push -m "<descriptor>-tracked-only"  # no -u
# do baseline work
git stash pop
```

### 18.3 Verification command patterns (audit redline §0.4 substance)

```bash
# Verify a module's existence
rg -ln "<module_pattern>" backend/ backend_agents/

# Verify Redis key consumption
rg -n "<redis_key_pattern>" backend/ backend_agents/

# Verify Supabase migrations
ls supabase/migrations/ | wc -l
rg -ln "<table_or_column_name>" supabase/

# Verify line count drift
wc -l backend/<file>.py backend_agents/<file>.py

# Verify cross-spec contract claims
rg -n "<feature_or_field_name>" trading-docs/04-modules/ai-architecture/archive/raw-locked-specs-2026-04-26/ITEM_<N>_*.md

# Verify HEAD SHA + log message
git fetch origin main && git log -1 origin/main --format="%H %s"

# Spec section count
rg -nE "^## [0-9]+\." trading-docs/04-modules/ai-architecture/archive/raw-locked-specs-2026-04-26/ITEM_<N>_*.md | wc -l
```

### 18.4 Commit pattern (HEREDOC for safe formatting)

```bash
git add <files>
git commit -m "$(cat <<'EOF'
docs(audit): <one-line summary>

<paragraph 1: what was done>

<paragraph 2: findings tally / themes>

<paragraph 3: governance / D-XXX impact>

Files:
- NEW: <path>
- M: <path>
...

Branch: <feature-branch>
Base SHA: <SHA> (<context>)
Per <Action authorization>: do NOT merge.
EOF
)"
```

### 18.5 Push pattern

```bash
git push -u origin <branch-name>
```

(With `required_permissions: ["all"]` in Shell call.)

### 18.6 Reading large files efficiently

For files >500 lines:
- Use `Grep` first to find relevant sections
- Use `Read` with `offset` + `limit` to read targeted ranges
- Reserve full reads for files where end-to-end reading is operator-required (e.g., `AI-SPEC-005.md` in P1.3.7 per Ambiguity 4)

### 18.7 Status check

```bash
git status --short
git branch --show-current
git diff --stat HEAD
git log --oneline -10
```

---

## 19. PRIOR AUDIT PRECEDENTS TO CONSULT

When auditing any new spec, these are the **canonical Cluster B audits** to use as templates and cross-references:

### 19.1 P1.3.5 — AI-SPEC-005 (Vol Fair-Value HAR-RV)

`trading-docs/08-planning/ai-architecture-audits/AI-SPEC-005.md` (533 lines)

**Patterns established:**
- Layer 1 / Layer 2 architectural pattern (introduced)
- `vol_fair_value_engine.py` canonical-name recommendation pattern (`B-AI-005-1`)
- Layer 1/Layer 2 cutover policy framework (`C-AI-005-2`)
- V0.x advisory-only acceptance (`C-AI-005-3`)
- Cross-spec FK / producer-surface cascade (introduced)

### 19.2 P1.3.6 — AI-SPEC-006 (Meta-Labeler)

`trading-docs/08-planning/ai-architecture-audits/AI-SPEC-006.md` (603 lines)

**Patterns established/extended:**
- 5 producer surfaces enumeration (`B-AI-006-2` through `B-AI-006-6`)
- `meta_labeler_engine.py` canonical-name recommendation pattern (`B-AI-006-1`)
- `dormant_legacy_observability` cutover variant (`C-AI-006-2`)
- Bayesian prior parameter governance (`C-AI-006-3`)
- LightGBM Direction Model spec ownership (`C-AI-006-4`)
- 47-named-feature-fields surface area
- Layer 1/Layer 2 architectural pattern (3rd adoption)

### 19.3 P1.3.7 — AI-SPEC-008 (OPRA Flow Alpha) [THIS SESSION]

`trading-docs/08-planning/ai-architecture-audits/AI-SPEC-008.md` (583 lines)

**Patterns established/extended:**
- `flow_alpha_engine.py` canonical-name recommendation pattern (`B-AI-008-1`)
- Layer 0 + Layer 2 coexistence variant (4th Layer 1/2 adoption; degraded form)
- Cross-spec producer→consumer contract gap pattern (`C-AI-008-1`) — NEW
- OPRA-stream substrate dependency theme — NEW
- Databento subscription scope governance (`C-AI-008-3`) — NEW
- `_safe_redis()` dead code escalation to safety-critical for Cluster B
- 4 Class C escalations folded into D-023 enrichment (u/v/w)

### 19.4 Earlier audits (Cluster A — context only)

- AI-SPEC-001 (AI Risk Governor) — D-023 introduced; Card schema framework
- AI-SPEC-002 (Strategy Attribution) — `C-AI-002-1` writer/consumer-coordination pattern (mirror for `C-AI-008-1`)
- AI-SPEC-004 (Replay Harness) — `C-AI-004-2` decision-card definition; `C-AI-004-4` chain-archive substrate
- AI-SPEC-010 (Counterfactual P&L) — `C-AI-010-3` Z-score producer authority; `C-AI-010-5` abstract Commit-N anchor

---

## 20. GLOSSARY OF PROJECT-SPECIFIC TERMS

| Term | Definition |
|---|---|
| **AFR** | `AUDIT_FINDINGS_REGISTER.md` — the central register of all audit findings |
| **CCEM** | `CROSS_CUTTING_EVIDENCE_MATRIX.md` — cross-spec evidence matrix |
| **β-lite trio** | The 3-document governance structure: Master ROI Plan + AI Build Roadmap + Audit Disposition Plan |
| **Class A/B/C** | Audit finding taxonomy (mechanical / implementation / architectural) — see §8 |
| **Cluster A/B/C** | AI item grouping by tier (foundational / alpha-generation / governance) — see §1.2 |
| **D-XXX** | Decision record (e.g., D-008 = Databento budget). Operator-only authority. |
| **DIAGNOSE-FIRST** | Workflow pattern: read + verify + classify + ask before any change — see §6 |
| **EXECUTE Authorization** | Operator response to DIAGNOSE report, greenlight + ambiguity resolutions |
| **Gate A/B/C/D/E/F** | Path Y activation prerequisites — see §9 |
| **Layer 0 / 1 / 2** | Architectural tier within an AI item: 0 = raw feed, 1 = observability, 2 = decision/feature engine |
| **Locked spec** | Immutable AI item spec under `trading-docs/04-modules/ai-architecture/archive/raw-locked-specs-2026-04-26/` |
| **Master ROI Plan** | `trading-docs/08-planning/MASTER_ROI_PLAN.md` (v2.0.3 currently) — the spine document |
| **Mechanism 1-5** | Post-P1.3.5 prevention discipline for audit rigor — see §5 |
| **Path Y** | Future feature activation gated on multiple prerequisites |
| **PRE-P11-N** | Version-agnostic invariant citation (e.g., PRE-P11-3 for `_RISK_PCT` ladder) |
| **REPORTING / HISTORICAL site** | Audit-trail record; preserve verbatim, do NOT retroactively rewrite |
| **ASSERTING site** | Forward-pointing claim; subject to factual correction |
| **Silent drop site** | A code path / table cell where an item could be lost without trace; high vigilance required |
| **STOP CONDITION 1-9** | Explicit triggers for halting and asking — see §7 |
| **T-Rule N** | Constitutional rule (T1-T11). T-Rule 4 = governance docs are authoritative; T-Rule 5 = capital preservation; T-Rule 10 = no silent failures |
| **Tier V0.1 / V0.2 / V0.3 / V0.4** | AI item readiness tier (matches deployment phase, not version number) |

---

## CLOSING NOTES FOR THE NEXT AGENT

1. **Start fresh from `.cursorrules`** — even if you've read this handoff, the `.cursorrules` mandatory readings are non-negotiable.

2. **Re-read this file at task start** — it's long but each section has a purpose. Sections 3 (current state), 7 (STOP conditions), 8 (finding taxonomy), 11 (operator-pending), 13 (guardrails), and 17 (citation discipline) are most critical.

3. **The P1.3.7 branch is open and unmerged** — don't merge it autonomously; the operator owns that decision after reviewing the 4 Class C escalations.

4. **The next natural task is P1.3.8 (AI-SPEC-009 Exit Optimizer audit)** — but wait for operator instruction. Don't preemptively start.

5. **Operator (`tesfayekb`) is highly engaged and detail-oriented** — they expect:
   - DIAGNOSE-FIRST discipline on all non-trivial work
   - Clear surfacing of ambiguities with options + defaults
   - Honest disclosure of partial reads / drifts / uncertainties
   - Mechanism 3 self-review before commit
   - Structured EXECUTE summary reports
   - Never auto-merging, never auto-resolving Class C, never editing locked specs

6. **The agent transcripts folder** (`/Users/tesfayemackbookpro/.cursor/projects/Users-tesfayemackbookpro-CascadeProjects-Lovable-beyenestock-of-foundation-first/agent-transcripts/`) contains the full JSONL transcript at `28a7b316-10dc-412a-b6bd-3bd49ad04170/28a7b316-10dc-412a-b6bd-3bd49ad04170.jsonl` — consult for any unclear context. Cite as `[<title for chat>](28a7b316-10dc-412a-b6bd-3bd49ad04170)` if needed.

7. **When in doubt, STOP and ask.** This is the operator's strongest preference and the project's strongest guardrail.

---

## Appendix A — DIAGNOSE Discipline Additions (cumulative, governance-grade)

These checklist additions are mandatory for the corresponding DIAGNOSE round in any future PR. Each was extracted from a real defect that escaped earlier DIAGNOSE rounds, cost a deploy cycle, and would have been caught had the discipline been in place. Order is chronological.

### A.1 Health-probe `service_name` (added 2026-04-30 from T-ACT-042 / Fix PR 3)

For any new health-probe `service_name` introduced via `db.write_health_status()` or equivalent, the DIAGNOSE round MUST validate against migration files defining CHECK constraints, NOT just runtime call sites. "No collision with existing names" in the codebase is necessary but not sufficient. Concretely:

- Locate the migration that defines `trading_system_health_service_name_check` (or the equivalent CHECK constraint for any other `_service_name_check` table).
- Confirm the new `service_name` is in the IN list of the most-recent migration that touched that constraint.
- If absent, add a DROP IF EXISTS + ADD migration in the same PR that introduces the new probe.

**Defect that triggered this:** PR 2 (T-ACT-041) DIAGNOSE Q-D6 verified `direction_model` didn't collide with the 23 existing service names in call sites, but missed the CHECK constraint allowlist. Result: `health_write_failed error={'code': '23514', ...}` log spam at deploy `a77195a` until PR 3 fixed it.

### A.2 Deploy-config edits — validate the meta-config (added 2026-04-30 from T-ACT-043 / Fix PR 4)

For any change to `nixpacks.toml`, `railpack.json`, `Dockerfile`, `Procfile`, `.platform.yaml`, `fly.toml`, `app.json`, or any builder-specific config file, the DIAGNOSE round MUST:

1. **Identify the AUTHORITATIVE builder** via `railway.json` `build.builder` field (or equivalent meta-config for other PaaS). The presence of a config file at repo root is **necessary but NOT sufficient** evidence that the builder consumes it. This project pins `RAILPACK` in `railway.json:4` and ignores `nixpacks.toml` entirely — but PR 3 missed this and edited the inert file.
2. **List ALL deploy-config files at repo root** via a single inventory command:
   ```bash
   ls -1a | grep -iE "^(nixpacks|railpack|dockerfile|procfile|railway|fly|app\.json|\.platform|render\.yaml|heroku|buildpacks|\.buildpacks)"
   ```
3. **If multiple deploy-config files exist**, document in the DIAGNOSE report which is active and which is inert. Cite the meta-config that determines this.
4. **For inert configs, propose deletion in the same PR** to prevent the recurrence pattern. Keeping inert deploy configs is exactly the misleading-context surface that wastes deploy cycles.

**Defect that triggered this:** PR 3 (T-ACT-042) edited `nixpacks.toml` to add `aptPkgs = ["libgomp1"]`. Empirically inert — Railway uses Railpack per `railway.json:4`. Same `libgomp.so.1` error appeared in deploy `eaa7aa8` post-PR-3-merge, costing a deploy cycle and forcing T-ACT-043 + Fix PR 4.

### A.3 Future additions

Append future discipline additions here as A.3, A.4, ... Each addition must include: (a) the rule text, (b) the defect that triggered it, (c) the action-tracker entry that documents the discovery.

---

*Handoff note authored 2026-04-28 22:10 UTC-4 by Cursor (Claude Opus 4.7) at end of P1.3.7 EXECUTE session. Owner: tesfayekb. File location: `trading-docs/06-tracking/HANDOFF_NOTE_2026-04-28_POST_P1-3-7.md`. End of handoff.*

*Appendix A added 2026-04-30 (T-ACT-042 + T-ACT-043 lessons-learned consolidation; per operator decision D5 in Fix PR 4 DIAGNOSE round).*
