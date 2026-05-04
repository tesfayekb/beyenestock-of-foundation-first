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

### A.3 Pickled ML artifacts — pin every contributing library (added 2026-04-30 from T-ACT-044 / Fix PR 5)

For any pickled ML model artifact (e.g. `direction_lgbm_v1.pkl`), the pickle's deserialization at production load time depends on EVERY library whose objects are reachable from the pickled object graph, not just the headline ML library. Concretely, an `LGBMClassifier` pickle includes:

- `lightgbm.Booster` state (lightgbm)
- `sklearn.preprocessing.LabelEncoder` (auto-created by `LGBMClassifier` when fit on string labels — see `backend/scripts/train_direction_model.py:394-396`) — sklearn
- `numpy.ndarray` for `classes_`, `feature_importances_`, internal feature buffers — numpy
- Various scipy-derived utilities (scipy, transitively via sklearn)

Discipline:

1. **Identify the full set of pickle-critical libraries** for any new ML artifact format. For sklearn-flavored estimators: at minimum `{scikit-learn, numpy, pandas, scipy, lightgbm}` plus the headline ML library. The canonical list is maintained in `backend/scripts/preflight_training_env.py` `PICKLE_CRITICAL` tuple — update there whenever a new pickle-critical library is added.
2. **Pin EVERY pickle-critical library to an exact version** (`==X.Y.Z`) in `backend/requirements.txt`. NO range pins (`>=`, `<`, `~=`) on pickle-critical libraries. A range pin is itself a defect surfaced by `preflight_training_env.py`.
3. **Capture training-environment versions** of all pickle-critical libraries in `model_metadata.json` at training time. The `_capture_training_environment()` helper in `train_direction_model.py` writes a `training_environment` dict that records python, sklearn, numpy, pandas, scipy, lightgbm versions plus platform + hostname. This enables forensic reconstruction of any artifact's training context AND enables future runtime version-skew detection at model load (deferred to follow-up PR per T-ACT-044 D5).
4. **Always install training venvs via `pip install -r backend/requirements.txt`** OR via the `preflight_training_env.py` cycle that validates versions against `requirements.txt`. NEVER freelance `pip install <pkg>` without version pins for pickle-critical libraries — this is exactly how T-ACT-044 was triggered.

Operator-runnable preflight (run BEFORE every training session):

```bash
cd backend
python -m scripts.preflight_training_env
# Exit 0: safe to train. Exit 1: fix the venv first (script prints copy-paste pip command).
```

**Defect that triggered this lesson:** PR 2 Stage 0 instructed `pip install lightgbm pandas pyarrow` in a fresh Python 3.11 venv WITHOUT version pins. Pip resolved latest available wheels — sklearn 1.8.0, numpy 2.4.4 (MAJOR version skew vs prod's 1.26.4), pandas 3.0.2 (MAJOR), scipy 1.17.1. The resulting model loaded successfully in production but emitted `InconsistentVersionWarning: Trying to unpickle estimator LabelEncoder from version 1.8.0 when using version 1.5.2`, costing 1 deploy cycle to diagnose + retrain. Defense-in-depth at `prediction_engine.py:861-865` (string-name lookup via `direction_model.classes_` rather than integer-index from internal LabelEncoder mapping) silently absorbed the warning for an unknown number of prediction cycles — informational evidence that defensive coding patterns matter even when version pins fail.

**Tracker entry:** [T-ACT-044](#t-act-044--sklearn-version-pin--training-env-capture--preflight-script-post-t-act-043-deploy-validation) (Fix PR 5).

### A.4 DIAGNOSE-FIRST cumulative-pattern discipline — explicitly check the meta-config that determines what your config does (added 2026-04-30 from T-ACT-040 through T-ACT-044 saga, ratified via Master Forward Plan v1.2 reconciliation PR)

**Rule:** Before authorizing a fix proposed by a `DIAGNOSE-FIRST` round, the round MUST explicitly enumerate and verify the **meta-config layer that determines what the config layer actually does** — not just the config layer itself. If the fix touches a config file (`nixpacks.toml`, `requirements.txt`, schema migration, env var, etc.), the DIAGNOSE round MUST surface and verify:

1. **What selects this config?** — e.g., `railway.json` `builder` field selects between Nixpacks and Railpack; `pyproject.toml` `[tool.poetry]` vs `requirements.txt` selects between pip and poetry; database constraint `CHECK` clauses determine which `INSERT` values are valid even when the column type would otherwise admit them; library version pins in `requirements.txt` determine which `.pkl` artifacts unpickle correctly even when the model class library is itself pinned.
2. **Is the config layer being edited the one that's actually consulted at runtime?** — verify by reading the meta-config file at HEAD, not by assumption based on filename conventions.
3. **What adjacent surfaces does this config layer participate in?** — e.g., a Python library version pin participates in the entire pickle-graph contributing-library set, not just the directly-imported library; a Postgres CHECK constraint participates in the entire `INSERT`/`UPDATE` validation surface, not just the column-name-matching set.

**Defect pattern that triggered this lesson:** During the 5-PR LightGBM activation saga (T-ACT-040 through T-ACT-044, 2026-04-30), 3 of 5 PRs surfaced adjacent meta-discipline gaps that earlier `DIAGNOSE-FIRST` rounds had failed to enumerate:

- **Fix PR 2 (T-ACT-041) DIAGNOSE missed CHECK constraint allowlist** — the three-tier model loader's health probe wrote `service_name='direction_model'` to `trading_system_health`. The Postgres CHECK constraint `trading_system_health_service_name_check` was an enumerated allowlist, NOT just a NOT NULL / type validator. The DIAGNOSE round verified the column existed and its type but did not verify the CHECK constraint membership. Production hit `psycopg2.errors.CheckViolation` on first probe call, requiring Fix PR 3 migration to expand the allowlist. **Lesson source for A.1.**
- **Fix PR 3 (T-ACT-042) DIAGNOSE missed Railway builder-pin meta-config** — the fix added `aptPkgs = ["libgomp1"]` to `nixpacks.toml` to provide the OpenMP runtime library `libgomp.so.1` required by the LightGBM Cython binary. The DIAGNOSE round verified `nixpacks.toml` exists in the repo and the syntax for `aptPkgs` was correct. It did NOT verify `railway.json`'s `builder` field — which pins Railway to use **Railpack**, not Nixpacks, making `nixpacks.toml` an inert config. The deploy succeeded (no errors), production logs still showed `OSError: libgomp.so.1: cannot open shared object file`. Required Fix PR 4 to redirect the apt package addition to `railpack.json`'s `deploy.aptPackages` field. **Lesson source for A.2.**
- **Fix PR 5 (T-ACT-044) DIAGNOSE missed numpy/pandas/scipy 3-library skew via Fix PR 2 Stage 0 freelance pip install** — the operator's local training environment was bootstrapped via Fix PR 2 Stage 0 instructions: `pip install lightgbm pandas pyarrow` with NO version pins. Pip resolved latest wheels (sklearn 1.8.0, numpy 2.4.4, pandas 3.0.2, scipy 1.17.1) — all incompatible with prod's pinned versions. The Fix PR 5 DIAGNOSE initially scoped only sklearn (the library that emitted the visible `InconsistentVersionWarning`). Diagnostic-deepening surfaced that the `.pkl` pickle graph contained references to numpy and scipy types from the LabelEncoder + transformers, AND pandas DataFrame dtypes from feature-engineering caches — making all 4 libraries pickle-critical, not just sklearn. **Lesson source for A.3 (broader scope) + A.4 (this entry, the meta-pattern).**

**The cumulative pattern (this lesson, A.4):** Each `DIAGNOSE-FIRST` round verified its in-scope config layer, but missed an adjacent meta-layer that determined whether the in-scope layer would actually be honored at runtime. The fix is not "do more DIAGNOSE" — DIAGNOSE rounds were rigorous. The fix is "explicitly enumerate the meta-config decision tree before each fix" as a checklist item, not as an emergent insight that surfaces only after deploy validation fails.

**Tracker entries:** Cumulative — T-ACT-041 (Fix PR 2), T-ACT-042 (Fix PR 3), T-ACT-043 (Fix PR 4), T-ACT-044 (Fix PR 5). See [`trading-docs/06-tracking/action-tracker.md`](../../trading-docs/06-tracking/action-tracker.md) for full per-PR audit trail.

**Cross-reference:** `MASTER_ROI_PLAN.md` §1.8 (LightGBM v1 activation chain narrative — full PR sequence + commit SHAs) + §7 F-38 (findings register milestone). Master Forward Plan v1.2 reconciliation PR (`docs/master-forward-plan-v1-2-reconciliation`, 2026-04-30) ratifies this Appendix A.4 entry as part of the governance-doc reconciliation per Task 1 of the v1.2 forward plan.

### A.5 Schema migrations must ship with the code that depends on them — and integration tests must validate persistence (added 2026-05-01 from incident: model_source PGRST204 silent-failure since LightGBM v1 activation)

**Lesson:** When a code change introduces a new column write to a database table, the migration adding that column MUST ship in the same PR. PR-level review must cross-check that every new column referenced in code has a corresponding `ADD COLUMN` in a migration file in the same merge. Unit tests that check dict-level outputs are NOT sufficient; integration tests that exercise the actual database insert path must be present (or, at minimum, a post-merge smoke check that runs one end-to-end cycle against a real database before declaring the PR validated).

**Defect that triggered this lesson:**

- PR #82 (T-ACT-040, 94edb9a, 2026-04-30) shipped migration `20260430_add_ai_synthesis_columns.sql` adding columns `strategy_hint`, `sizing_modifier`, `source` to `trading_prediction_outputs`.
- PR #83 (T-ACT-041, a77195a, 2026-04-30) added code at `backend/prediction_engine.py:883` writing `"model_source": "lgbm_v1"` — referring to a column with a name that did NOT exist in PR #82's migration. The names `source` and `model_source` are NOT the same column (different semantic scope: `source` = broader pipeline provenance; `model_source` = direction-model-specific).
- Neither PR's tests caught the gap. Unit tests at `backend/tests/test_phase_a3.py:95-96` validated `result.get("model_source") != "lgbm_v1"` at the dict level, never exercising the database insert.
- Outer `try/except` in `prediction_engine.py:run_cycle()` swallowed the resulting PGRST204 error.
- Symptom only surfaced on 2026-05-01 13:30 UTC (~16+ hours post-LightGBM-v1-activation) when operator ran empirical validation queries against `trading_prediction_outputs` and got "column does not exist" errors. Railway logs showed `prediction_cycle_failed` every cycle since 2026-04-30 21:33 UTC, but the failures were not surfaced as alerts because the try/except masked them at the application layer.

**Net runtime impact:** ~16+ hours of zero-row persistence post-LightGBM-v1-activation. Model compute pipeline worked correctly throughout (verified empirically from traceback `locals` dump showing `p_bull: 0.4905, p_bear: 0.5095, model_source: 'lgbm_v1'` — model-derived, NOT placeholder). Persistence layer was the silent-failure surface.

**Mitigations going forward:**

1. **Schema-code coupling check at PR review:** Reviewer must run `git diff main..HEAD --name-only | grep -E "supabase/migrations|backend/.*\.py$"` and cross-check that every new column written in code has a corresponding `ADD COLUMN` in the migrations diff. If the PR touches `backend/` and writes a new dict key that maps to a database insert, AND the PR does NOT touch `supabase/migrations/`, that is a flag for explicit reviewer confirmation.

2. **Integration smoke-test after schema-touching PRs:** Operator runs one end-to-end cycle against a real Supabase instance (production paper-trading, dev mirror, or test schema) before marking the PR as validated. Acceptance: at least one row written to the affected table in the post-merge cycle. Record the row count in HANDOFF NOTE follow-up.

3. **Try/except discipline:** The outer `try/except` in `prediction_engine.py:run_cycle()` should re-raise PostgrestAPIError and similar schema errors at WARN level (or higher). Schema errors are fundamentally different from transient DB connectivity failures and should not be silenced by the same handler. (Tracked as a separate follow-up; not part of this fix's scope.)

4. **Empirical validation BEFORE declaring activation success:** The 5-PR LightGBM activation chain declared success at PR-merge time without an end-to-end persistence check. Future activation milestones must include a "post-merge ≥1 row persisted to target table" smoke check before being marked done.

**Tracker entries:** T-ACT-NNN (to be assigned post-validation) for the column-consolidation between `source` and `model_source`. Migration sync to repo: this PR (`fix/migration-model_source-repo-sync`).

Ratified 2026-05-01 via this PR.

### A.6 Validate upstream feed freshness against an independent source BEFORE declaring activation success — paper-trading P&L is meaningless if the inputs are stale (added 2026-05-01 from incident: 15-min Tradier sandbox SPX delay surfaced via empirical Polygon comparison)

**Lesson:** When declaring an activation milestone "validated," operator MUST empirically compare the system's recorded inputs against an independent real-time source. Validation queries that confirm only "the model is producing varying outputs" are insufficient — they confirm the model is responsive to its inputs without confirming those inputs reflect real market state. A model fed 15-min-stale data will produce varying outputs that look healthy but represent decisions based on a market that no longer exists.

**Defect that triggered this lesson:**

- 2026-04-30 21:33 UTC — LightGBM v1 activated (T-ACT-044, commit 5162020). Activation declared successful at PR-merge time.
- 2026-05-01 ~13:35 UTC — Operator empirical validation queries against `trading_prediction_outputs` confirmed the model was emitting model-derived (non-placeholder) probabilities and varying outputs across cycles.
- 2026-05-01 ~13:45 UTC — System entered paper trade `033f55dc-e44c-4cd6-a694-13452f5cd3c4` (long_straddle, strike 7210). System-recorded `entry_spx_price = 7209.01`.
- 2026-05-01 ~13:46 UTC — Position exited at `take_profit_debit_100pct` with simulated +$3,493.70 net P&L in 54 seconds (entry $4.15 debit → exit $39.25, ~9.5x return).
- 2026-05-01 ~14:00 UTC — Operator flagged: "I don't think markets move that fast" — surfaced suspicion that the speed/magnitude was inconsistent with real-market dynamics.
- 2026-05-01 ~17:00 UTC — Empirical Polygon comparison confirmed: at 13:45 UTC, Polygon's actual SPX 1-min bar was 7244.80–7249.24 (~$37 above the system's recorded 7209.01). System was reading 15-min-delayed Tradier sandbox SPX data; the 9.5x return was the option-chain feed (real-time per Tradier OPRA exception) catching up to a real underlying move that had already happened ~15 min earlier.
- The +$3,493.70 was **phantom alpha** — paper-trading artifact from a feed-recency mismatch. In real markets with real-time SPX, the system would have seen SPX at ~7245 and would NOT have entered an at-the-money straddle at strike 7210 (already deep ITM on one leg).

**Net runtime impact:** Every prediction cycle from LightGBM v1 activation (2026-04-30 21:33 UTC) through PR #90 deploy (2026-05-01 ~end of day UTC) was made on 15-min-stale SPX inputs. **Pre-merge validation queries that declared "LightGBM v1 empirically validated" were operating on stale data and need to be re-validated post-PR-#90 deploy.**

**Mitigations going forward:**

1. **Activation milestones require independent-source feed comparison:** Before declaring any data-driven feature activated (LightGBM, AI synthesis, new feed integration), operator runs a comparison query against an independent real-time source (Polygon for equities/indices; Databento for OPRA; etc.) to confirm the system's recorded inputs match contemporaneous real-time prints within tolerance (e.g., ±$5 for SPX). Document the comparison output in the activation's PR or HANDOFF NOTE.

2. **Subscription-vs-runtime audit:** Periodically (e.g., quarterly) verify that real-time data subscriptions documented in `SUBSCRIPTION_REGISTRY.md` are actually consumed by the live decision path. PR #90 surfaced that Polygon Stocks Advanced ($199/mo) and Databento OPRA Standard ($199/mo) were paid for but only feeding auxiliary signals; the primary SPX feed was still Tradier sandbox. This kind of "paying for it but not using it" gap should be caught by audit, not by an empirical surprise.

3. **Freshness guards on critical feeds:** Every Redis-cached feed key consumed by the live decision path should have a freshness check at the consumer side (PR #90's `prediction_engine.run_cycle` model). If the upstream timestamp is older than a documented threshold, log a WARN and either skip the cycle or fall back to a known-real-time source. Default behavior on stale primary should be "no decision" rather than "wrong decision."

4. **Sandbox semantics must be explicitly verified, not inferred:** Tradier sandbox's "real-time for SPX/VIX index options" exception (per Tradier policy) was inferred to apply to SPX index *underlying* quotes too — it did not. Future sub onboarding must confirm sandbox-vs-production data semantics for every endpoint the system reads, with empirical timestamp comparison as the verification method.

**Empirical-validation update (2026-05-03):** T-ACT-045 was attempted on 2026-05-03 using `trading_prediction_outputs` data from 2026-05-01 13:35-19:55 UTC compared against Polygon's real-time 1-min SPX bars for the same window. Independent review (Cursor session 2026-05-03) determined the data set is structurally pre-PR-#90-merge: PR #90 squash-merged at 2026-05-01 19:59:22 UTC, but the last cycle in the validation data was 2026-05-01 19:55 UTC — entirely before the merge, well before Railway deploy completion. The 13:50 UTC inflection from 7209.01 to 7247.42 is Tradier sandbox catching up through its own 15-min delay cycle as it transitioned from pre-market to post-open data, NOT PR #90 working. Post-13:50 system values systematically match Tradier 15-min-delayed values across 7 of 11 testable cycles, confirming continued 15-min delay throughout the May 1 session. **T-ACT-045 status: PENDING-RE-RUN against post-deploy data, target Monday 2026-05-04 ≥10 minutes after Railway deploy is confirmed stable.** This update is itself an example of the A.6 lesson: empirical validation can produce false-positive verdicts if the timestamp boundary of the data isn't independently checked. Going forward, T-ACT-045 acceptance criteria require an explicit cross-check that all rows in the SQL output have `predicted_at >= PR #90 Railway deploy timestamp + 10 min` (per N-1 finding from this session); see TASK_REGISTER §14 T-ACT-045 acceptance criteria.

**Validation-artifact protocol (2026-05-03, per N-2 finding):** When T-ACT-045 is properly re-run, the operator commits the validation artifact (SQL output + Polygon bars + gap analysis + verdict reasoning) to a new file at `trading-docs/06-tracking/T-ACT-045-validation-artifact-2026-05-XX.md`. Action 6 prerequisite is updated to require both "T-ACT-045 verdict = VALIDATED" AND "validation artifact exists at the documented path." This makes the verdict independently re-verifiable by future agents in minutes, not opinion-only.

**Tracker entries:**
- T-ACT-045 (post-PR-#90 empirical re-validation — **PENDING-RE-RUN** per 2026-05-03 update above; the May 1 attempt operated on pre-deploy data and did not validate)
- T-ACT-046 (silent-staleness pattern fix — bundles `tradier_feed.py:282-283` AND `polygon_feed.py:174-184`; same root pattern; **DONE** in Track B PR `docs/track-b-silent-staleness-and-governance` 2026-05-03)
- T-ACT-047 (try/except discipline mitigation from A.5 #3 — outer try/except in `prediction_engine.run_cycle` still silences PostgrestAPIError-class errors)
- T-ACT-054 (charm/vanna/cv_stress silent-zero pattern — same silent-failure family as A.5; investigation_complete; design_pending operator decision per Cursor design memo 2026-05-03; remediation in separate follow-up PR after Track B merges)

Ratified 2026-05-01 via this PR. Amended 2026-05-03 via Track B PR (T-ACT-045 status update + validation-artifact protocol + T-ACT-054 entry).

### A.7 Silent-failure-class family — when "valid math, degenerate semantics" produces zero-class outputs that look benign in isolation but break downstream contracts (added 2026-05-03 from cv_stress design memo finding; **family REOPENED 2026-05-02 via T-ACT-055 discovery — convention pointer ≠ exhaustive audit**; original "FULLY CLOSED" claim from T-ACT-047 (5 members) was empirically over-confident and is preserved verbatim below as discipline-meta-lesson; **family expanded to 7 members 2026-05-02 via T-ACT-057 discovery (infrastructure-config silent-failure subclass added — third subclass alongside derived-feature surface and database-persistence surface)**; convention pointer for future agents)

**Lesson:** When data ingestion produces missing or saturated inputs that a derived-feature formula correctly translates into a "neutral" or "zero" output, the resulting persisted value carries the same byte pattern as a real "no signal" reading. Downstream consumers cannot tell them apart. The system "looks like it's computing" — no exception fires, no log warns — but the output is degenerate-but-mathematically-valid, and consumer-side gates that depend on the signal silently lose their semantics.

A second, distinct vector in the same family: when an outer `try/except Exception` catches a *persistent* error (schema/code drift, RLS misconfiguration, unique-constraint violation) at the same priority as a *transient* error (network timeout, momentary connectivity blip), the persistent error is silently retried indefinitely — no alert fires, no operator-actionable signal surfaces, and the system can run for hours writing zero rows. T-ACT-047 closes this vector specifically.

This family includes (2026-05-02 — initially **5 members, FAMILY CLOSED** per T-ACT-047 closure verdict; **2026-05-02 (same day)** REOPENED with **6 members** after T-ACT-055 discovery surfaced a sixth vector that was outside T-ACT-047's audit scope; **2026-05-02 (same day)** further expanded to **7 members** after T-ACT-057 discovery surfaced an infrastructure-config silent-failure vector — new third subclass; T-ACT-059 reserved for exhaustive-config-audit before A.7 may be formally re-closed):

1. **A.5 — `model_source` schema/code drift** (PR #89): Code wrote a column the schema didn't have. Outer try/except silenced PGRST204. Caught only by post-merge empirical validation. Mitigated by schema-code coupling check at PR review + integration smoke-test.

2. **A.6 — 15-min Tradier sandbox SPX delay** (PR #90): System read stale SPX feed; option-chain real-time feed caught up later, producing phantom alpha. Caught by independent-source feed comparison. Mitigated by freshness guards on critical feeds + empirical validation against independent source BEFORE declaring activation success.

3. **T-ACT-046 — write-time wall-clock timestamps in `tradier_feed.py:282-283` AND `polygon_feed.py:174-184`** (Track B PR `docs/track-b-silent-staleness-and-governance`, 2026-05-03): Both feed cache writes stamped `timestamp` / `fetched_at` at write-time, not at upstream-quote-time. Cache always looks fresh because the timestamp is wall-clock-now; consumers cannot distinguish "we just got real-time data" from "the upstream cached us something 15 minutes old." Same root pattern across both feeds; bundled into a single fix per Cursor's recommendation. Both replaced with upstream-supplied timestamps via defensive field-name chains + null-sentinel-on-absent semantics. Track B's prediction_engine freshness guard amendment makes the new contract explicit at the consumer side (distinct WARN log for missing-upstream-timestamp).

4. **T-ACT-054 — cv_stress degenerate-input pattern** (PR `fix/t-act-054-cv-stress-null-on-degenerate`, 2026-05-02; **remediation DONE**): When `vvix_z=0 AND gex_conf=1.0` (both common defaults during warmup, zero-variance, or saturated OPRA flow), the formula at `prediction_engine.py:691-694` correctly produced 0/0/0. ~29.2% of cycles in the last 7 days persisted these silent zeros, neutralizing 2 active downstream consumers (no_trade gate at `prediction_engine.py:1008`, strategy_selector long-gamma override at `strategy_selector.py:176`) PLUS the D-017 cv_stress exit at `position_monitor.py:778` (surfaced during plan review; missed in original investigation). Choice A NULL-on-degenerate-input remediation implemented with **AND-logic degenerate gate** — critical correction during plan review when the original draft used OR-logic that would have NULLed the majority of healthy RTH cycles (gex_conf=1.0 alone is normal RTH steady-state per gex_engine.py:175). All 4 direct consumers + 3 propagation boundaries patched; meta-label model uses Meta-3 NaN sentinel at 3 lockstep sites for native LightGBM missing-value handling. **T-ACT-054 implementation now serves as the canonical example of this discipline applied to a derived-feature surface** — concrete reference template for future agents touching derived-feature compute paths.

5. **T-ACT-047 — try/except discipline at `prediction_engine` persist site** (PR `fix/t-act-047-postgrest-error-classification`, 2026-05-02; **remediation DONE; A.7 FAMILY FULLY CLOSED** [claim subsequently REVERSED same-day by T-ACT-055 — preserved verbatim as discipline-meta-lesson per R6]): The outer `try/except Exception` at `prediction_engine.py:1518` (post-Track B/T-ACT-054 line numbers — shifts forward as the file grows) silently retried `PostgrestAPIError` (the persistent class) at the same priority as `httpx.ConnectError` and other transient classes. This is the precise surface that hid the A.5 `model_source` PGRST204 for ~16+ hours on 2026-04-30 to 2026-05-01 (between PR #82 and PR #89). Choice C remediation: wrap ONLY the supabase insert at L1495-1500 (post-edit) with a narrow `except PostgrestAPIError` block — does NOT refactor the broader run_cycle. Persistent errors now log at WARN with structured `pgrst_code`/`pgrst_details`/`pgrst_hint` fields, write `service_health.status="error"` with a `PERSISTENT[<code>]:` prefix in `last_error_message` (auto-incrementing the `error_count_1h` counter at `db.py:233-249` for sustained-error escalation), AND fire `alerting.send_alert(CRITICAL, ...)` with the hint in the email body for per-cycle operator visibility. Critical discipline: DB `service_health.status` stays in the schema CHECK-constraint allowlist (writing `'critical'` would violate the constraint at `supabase/migrations/20260420_add_idle_health_status.sql:11` per HANDOFF A.1 lesson) — critical severity is expressed via the `alerting.send_alert(CRITICAL, ...)` channel instead. Defensive: alert-pipeline failure does NOT mask the original error (inner try/except around the alerting call). **T-ACT-047 implementation now serves as the canonical example of this discipline applied to a database-persistence surface** — concrete reference template for future agents extending the inner-try pattern to other persist sites or schema-coupled operations.

6. **T-ACT-055 — `paper_phase_criteria` upsert NOT NULL violation regression** (PR `fix/t-act-055-criteria-evaluator-update-revert`, 2026-05-02; **remediation DONE; A.7 REOPENED — pending exhaustive persist-site audit (T-ACT-056 reserved) before formal re-closure**): Regression introduced 2026-04-17 in commit `836a83c` (PR #17) when `_upsert_criterion` body changed from `.update().eq('criterion_id', X)` to `.upsert(..., on_conflict='criterion_id')`. The `paper_phase_criteria` schema requires `criterion_name TEXT NOT NULL` and `target_description TEXT NOT NULL` (`supabase/migrations/20260417000001_paper_phase_criteria.sql:8-9`), neither of which is in the upsert payload. PostgreSQL's INSERT-phase NOT NULL check fires code 23502 BEFORE `ON CONFLICT` engages, the outer `try/except Exception` swallows the failure as `criterion_upsert_failed`, and 8 of 12 GLC rows silently freeze at seed values for ~16 days. Discovery: operator surfaced via Railway log analysis on 2026-05-02; Cursor's verification report pinpointed the regression vintage via `git log --follow` on `criteria_evaluator.py`. Choice B remediation: direct revert to `.update().eq()` form (`fea0ace` PR #6 baseline) + function rename `_upsert_criterion` → `_update_criterion` (semantic correctness — body is `.update()`, not `.upsert()`; 12 production caller sites + 6 test references renamed mechanically) + defensive WARN log on empty `result.data` (surfaces row-deleted edge case that `.update()` silently no-ops on; converts another silent-failure surface into observable signal — `criterion_update_no_match` event with operator-actionable hint citing the seed migration filename). Event name `criterion_upsert_failed` preserved at `logger.error` line for dashboard/log-search continuity (deliberate; see inline code comment in `criteria_evaluator.py`). **Critical discipline meta-lesson: convention pointer ≠ exhaustive audit.** T-ACT-047's family-closure claim earlier on 2026-05-02 was based on remediation of 5 known members (A.5, A.6, T-ACT-046, T-ACT-054, T-ACT-047) but did NOT perform an exhaustive audit of all persist sites in the codebase. T-ACT-055 surfaced a 6th member (`criteria_evaluator` persist site) on the SAME DAY that was OUTSIDE T-ACT-047's audit scope and therefore not caught by the convention pointer. Future "family closed" claims must explicitly distinguish (a) convention-establishment closure (which T-ACT-047 achieved) from (b) exhaustive-audit closure (which is reserved as T-ACT-056 follow-up before A.7 may be formally re-closed). **T-ACT-055 implementation now serves as the canonical example of regression-vintage discipline applied to a database-persistence surface** — git-archaeology pinpointing the exact commit that introduced the regression (`git log --follow backend/criteria_evaluator.py`), distinguishing regression from long-standing bug, and choosing direct-revert-plus-defensive-amendment over redesign as the appropriate remediation path. The original "FULLY CLOSED" claim at member 5 above is preserved verbatim per R6 stop-condition: sanitizing it would lose the discipline-meta-lesson — the over-confident claim IS the lesson.

7. **T-ACT-057 — `ALERT_GMAIL_APP_PASSWORD` whitespace silent-rejection at SMTP layer (infrastructure-config surface — NEW SUBCLASS)** (Operator-discovered + remediated 2026-05-02 21:28 ET; smoke test PASSED 2026-05-02 21:52 ET; CODE-CHANGE-DEFERRED to separate PR for Option B `.replace(" ", "")` defensive strip at `config.py:103`; A.7 EXPANDED — pending exhaustive-config-audit (T-ACT-059 reserved) before formal re-closure): Long-standing infrastructure-config silent-failure introduced when `alerting.py` was added 2026-04-19 (commit `082bdc0`). The Railway env var `ALERT_GMAIL_APP_PASSWORD` was wired with Google's display-format value (`xxxx xxxx xxxx xxxx` = 19 chars including 3 spaces) — Google's UI displays App Passwords as four 4-character groups separated by spaces for readability; the actual 16-char credential is the continuous concatenation. Operators copy-pasting from the UI naturally include the display-format spaces. The `alerting.py:170-172` `srv.login(...)` call passes the env-var value verbatim with NO whitespace stripping; Gmail SMTP rejects with `535 5.7.8 Username and Password not accepted`, raising `smtplib.SMTPAuthenticationError`, caught at `alerting.py:181-188` and logged as `alert_email_auth_failed` with hint "Check ALERT_GMAIL_APP_PASSWORD in Railway env vars. Must be a Gmail App Password, not your account password." The hint TEXT is technically correct but did not help in this case because the operator HAD pasted a Gmail App Password — just with display-format spaces. The L82-88 silent no-op gate did NOT trip because the env var was non-empty. **Effective production state: zero CRITICAL emails delivered for 14 days (2026-04-19 → 2026-05-03 01:28 UTC) — full duration since alerting introduction.** Blast radius: ALL 8 `send_alert(...)` callsites silently rejected; 4 of them are CRITICAL (`prediction_engine_persistent_error`, `emergency_backstop_triggered`, `prediction_watchdog_triggered`, `daily_halt_triggered`). Discovery: operator self-discovered 2026-05-02 21:28 ET while diagnosing why no T-ACT-047 alert validation email arrived. Remediation: env-var stripped to 16-char continuous (DONE 2026-05-02 21:28 ET); Railway redeployed (healthy 2026-05-03 01:28:28 UTC); end-to-end smoke test PASSED 2026-05-02 21:52 ET (`alert_email_sent` log fired + email arrived in operator's inbox); Option B code-change PR DEFERRED to separate PR (1-line `.replace(" ", "")` defensive strip at `config.py:103` — provably safe because App Password format is 16-char alphanumeric continuous per Google's generation grammar, cannot legitimately contain spaces). **Critical discipline meta-lesson (sharpened):** This finding is the canonical instance of "convention pointer ≠ exhaustive audit" predicted at T-ACT-055. T-ACT-047 §R6 asked operator to verify env vars were SET — a convention-pointer-style verification. An exhaustive audit would have asked: SET, of CORRECT FORMAT, AND end-to-end SMTP login validated. The convention pointer caught 1 of 3. Future similar verifications must ask all three. **T-ACT-057 implementation now serves as the canonical example of infrastructure-config-format silent-failure discipline applied to a deploy/secret surface** — concrete reference template for future agents touching env vars, secrets, or deploy configuration. **New subclass: infrastructure-config silent-failure surface** — distinct from derived-feature surface (T-ACT-054 family) and database-persistence surface (T-ACT-047/T-ACT-055 family). Subclass scope: env vars, secrets, deploy config, Railway/Supabase/external-service configuration where format-incorrect input gets accepted at the load layer but rejected at the use layer with the rejection caught/swallowed/logged-only-at-low-priority. T-ACT-059 reserved for exhaustive-config-audit before A.7 may be formally re-closed.

**Convention going forward (sharpened 2026-05-02 via T-ACT-047):** Two distinct disciplines apply to the silent-failure-class family:

- **Derived-feature surface (A.5/A.6/T-ACT-046/T-ACT-054 vector):** Missing or saturated upstream inputs MUST persist as `null` (Python `None` / SQL `NULL`) in derived-feature columns, NOT as zero or any other in-band value. Downstream consumers MUST explicitly handle null with conservative semantics (skip the cycle, fall back to a known-defensive default, log INFO/WARN once-per-process to avoid log noise).
- **Database-persistence surface (T-ACT-047 vector):** Persistent errors (schema cache miss, RLS violation, unique-constraint violation) MUST be classified separately from transient errors (network timeout, connectivity blip) at every persist site. Persistent errors MUST escalate via per-cycle WARN log + `service_health` write with `PERSISTENT[<code>]:` prefix + `alerting.send_alert(CRITICAL, ...)` channel. Transient errors MAY fall through to the existing outer handler unchanged (current ERROR-level behavior preserves accumulated-pattern escalation via `error_count_1h`). DB status MUST stay in the schema CHECK-constraint allowlist per A.1 — express critical severity via the alert channel, not the DB column.

Track B established the first vector for silent-staleness paths (T-ACT-046, both feed paths). T-ACT-054 extended the first vector to derived features (Choice A NULL-on-degenerate-input semantics, implemented 2026-05-02). T-ACT-047 establishes the second vector for the persist-site try/except discipline (Choice C inner-block-specific scoping, implemented 2026-05-02).

**Discipline pointer for future PRs (sharpened 2026-05-02 via T-ACT-054 + T-ACT-047 plan reviews):**

- When a PR introduces or modifies a derived-feature compute path, the reviewer must verify (a) what input combinations could produce degenerate outputs that look like "no signal," and (b) whether downstream consumers have explicit null-handling. If either is missing, the PR is incomplete — same review-discipline class as A.5's schema-code coupling check.
- When a PR introduces or modifies a database persist site, the reviewer must verify (a) whether the catch is narrowly scoped to specific exception classes (NOT a blanket `except Exception` that silences both transient and persistent errors), and (b) whether persistent errors fire an operator-visible alert (email/Slack/etc.) — not just an INFO/DEBUG log that gets buried. If either is missing, the PR is incomplete.

**Plan-review meta-lesson (2026-05-02, from T-ACT-054 + T-ACT-047 implementations):** Independent READ-ONLY plan review is non-optional before EXECUTE on derived-feature changes AND on persist-site discipline changes. Cursor's review of Claude's T-ACT-054 draft plan caught **1 critical defect** (OR-logic vs. AND-logic degenerate gate that would have caused production regression by NULLing healthy cycles), **1 missed active consumer** (D-017 in `position_monitor.py`), and **3 propagation-boundary silent-coercion sites** that would have defeated Choice A's semantic distinction. Cursor's review of Claude's T-ACT-047 draft plan caught **1 schema-constraint violation** (the original framing implied writing `service_health.status="critical"` which violates the CHECK constraint per A.1; resolved by using existing `'error'` allowlist value coupled with `send_alert(CRITICAL, ...)` channel) and **6 implementation refinements** (R1-R7 documented in TASK_REGISTER §14). Single-pass plans would have shipped worse-than-status-quo regressions in both cases. Going forward: any change crossing >2 consumer boundaries OR introducing/modifying error-classification at a persist site MUST go through DIAGNOSE-FIRST + independent plan review before EXECUTE.

**Family REOPEN verdict (2026-05-02, same-day reversal):** T-ACT-047's claim earlier today that all 5 members of A.7 (A.5, A.6, T-ACT-046, T-ACT-054, T-ACT-047) were remediated and the family was FULLY CLOSED was empirically over-confident. T-ACT-055 surfaced a 6th member (`criteria_evaluator` persist site — `paper_phase_criteria` upsert NOT NULL violation regression) on the SAME DAY (2026-05-02), reopening the family. The original "FULLY CLOSED" claim is preserved verbatim above (header L1253, claim L1259, member 5 entry L1269) and below (ratification footer L1287, appendix footer L1297) as the discipline-meta-lesson — sanitizing it would lose the lesson. The over-confident claim IS the lesson: convention pointer ≠ exhaustive audit. **Re-closure of A.7 is now gated on an exhaustive persist-site audit (T-ACT-056 reserved)** to confirm no further hidden vectors exist before the family may be formally re-closed. Future incidents matching any of the three subclass vectors should reference A.7 as the precedent and use the canonical template: **(a) derived-feature surface →** T-ACT-054 (NULL-on-degenerate-input semantics with AND-logic degenerate gates); **(b) database-persistence surface →** T-ACT-047 (try/except classification with PostgrestAPIError narrow scoping) or T-ACT-055 (regression-vintage discipline with git-archaeology pinpointing); **(c) infrastructure-config surface →** T-ACT-057 (defensive format-tolerance at the load layer + exhaustive 3-question audit: SET / CORRECT FORMAT / END-TO-END VALIDATED). **Re-closure of A.7 now gated on TWO exhaustive audits:** T-ACT-056 (exhaustive persist-site audit) AND T-ACT-059 (exhaustive-config-audit) — both must complete before A.7 may be formally re-closed.

Ratified 2026-05-03 via Track B PR `docs/track-b-silent-staleness-and-governance`. Reinforced 2026-05-02 via T-ACT-054 implementation PR `fix/t-act-054-cv-stress-null-on-degenerate` (T-ACT-054 entry status updated from REMEDIATION-PENDING to DONE; plan-review meta-lesson added). **Family fully closed 2026-05-02** via T-ACT-047 implementation PR `fix/t-act-047-postgrest-error-classification` (T-ACT-047 added as 5th and final member; second vector documented; convention split into derived-feature surface and database-persistence surface; T-ACT-047 cited as canonical example for the persist-site discipline).

**A.7 family REOPENED 2026-05-02** (same-day reversal) via T-ACT-055 implementation PR `fix/t-act-055-criteria-evaluator-update-revert`. The "Family fully closed" claim above is preserved verbatim as discipline-meta-lesson — `paper_phase_criteria` upsert NOT NULL violation regression introduced PR #17 commit `836a83c` 2026-04-17, surfaced 2026-05-02 via Railway log analysis, was OUTSIDE T-ACT-047's audit scope (a 6th member of the family). T-ACT-056 reserved for exhaustive persist-site audit before A.7 may be formally re-closed. New discipline-meta-lesson: convention pointer ≠ exhaustive audit.

**A.7 family further expanded 2026-05-02 (same-day, second expansion)** via T-ACT-057 discovery of infrastructure-config silent-failure subclass. The "Family fully closed" claim (preserved verbatim above) is now also preserved as discipline-meta-lesson for the third subclass — `ALERT_GMAIL_APP_PASSWORD` whitespace silent-rejection at SMTP layer was OUTSIDE both T-ACT-047's audit scope AND T-ACT-055's discovery scope (a 7th member, NEW subclass). The pattern of "same-day, multiple expansions" itself reinforces the discipline-meta-lesson: an exhaustive audit of A.7's existing 6 members on 2026-05-02 evening would likely have surfaced T-ACT-057 BEFORE operator hit it empirically while testing T-ACT-047 §R6 path. T-ACT-059 reserved for exhaustive-config-audit; T-ACT-056 still reserved for exhaustive persist-site audit; both must complete before A.7 may be formally re-closed. New discipline-meta-lesson: **3-question exhaustive verification (SET / CORRECT FORMAT / END-TO-END VALIDATED) must be applied to ALL infrastructure-config surfaces**, not just code/data semantics ones.

### A.8 Subscription tier mismatch outage 2026-05-01 → 2026-05-04 (76 hours zero predictions; three discipline lessons — present-day-factual-questions, triage anchoring, external-dashboard-request attribution) (added 2026-05-04 evening from `HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md` post-incident closure; T-ACT-061 PENDING-VERIFICATION on §7.1 probe)

**Summary:** Predictions stopped writing 2026-05-01 15:55 ET (Friday). Diagnosis took 3 days. Root cause: Polygon Indices Starter $49/m provides 15-min delayed indices data; the codebase + 330s freshness guard at `prediction_engine.py:1366/1373` correctly rejected every cycle as `spx_price_stale_or_unavailable`. The triggering change was **PR #92 (T-ACT-046, 2026-05-02 12:00 ET)** flipping `polygon:spx:current.fetched_at` from `datetime.now(utc)` (wall-clock-now) to upstream Polygon timestamp via `_normalize_polygon_timestamp` — **NOT PR #90 (T-ACT-045, 2026-04-30)** as the deploy timing initially suggested. The Friday→Monday silence boundary was governed by the cron schedule (`mon-fri` only), not by deploy timing. Resolved 2026-05-04 evening by operator upgrading to Indices Advanced $99/m (real-time entitlement). T-ACT-061 verification gated on §7.1 manual API probe in `HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md`.

**Three discipline lessons** (sub-lessons L8.1, L8.2, L8.3 — all governance-grade additions to the pre-existing A.1-A.7 lessons):

**L8.1 — Subscription/entitlement claims about external services are present-day factual questions.** Prior Cursor/Claude sessions repeatedly answered "no, you don't need to upgrade" when the operator asked whether the Polygon subscription was sufficient. That advice was incorrect and contributed to the 3-day outage plus loss of training data. The advice was answered from memory/assumption rather than verified against the actual tier-description language on Polygon's pricing page at the time of the question. **Convention going forward:** Whenever a future agent is asked "does subscription X provide entitlement Y?", the answer MUST be derived from one of two sources: (a) the live current tier-description text on the provider's pricing page (which the agent can access via web fetch / browser MCP / explicit operator probe), OR (b) a tier-comparison matrix recorded in `SUBSCRIPTION_REGISTRY.md` (or analogous governance file) with a recent verified-as-of date. The agent MUST NOT answer from prior knowledge, training data, or session memory. **Structural mitigation (this PR):** `SUBSCRIPTION_REGISTRY.md` §1A now contains a tier comparison matrix for Polygon Indices (Basic / Starter / Advanced) so the entitlement question is answerable from this file alone without re-loading Polygon's pricing page. Future tier-comparison matrices should be added to `SUBSCRIPTION_REGISTRY.md` for any subscription where the operator commonly asks "is X tier sufficient?" or where tier-description ambiguity has historically caused friction. **Discipline-meta-lesson:** "Subscription is a present-day factual question" — same class of discipline as "test against the latest deployed code" or "check the running schema, not the migration file." All three are anti-patterns for the same root failure mode: answering from a stale-but-confident reference.

**L8.2 — Time-correlated incident triage must verify the suspected change's actual logic could produce the symptom; do not anchor on deploy timing alone.** Initial outage triage anchored on PR #90 (T-ACT-045, deployed 2026-04-30) because the deploy timing correlated with the last successful prediction (Friday 2026-05-01 15:55 ET ≈ first RTH window post-PR-#90-deploy with PR #92 not yet shipped). PR #90 added the freshness guard, but its `fetched_at = datetime.now(utc)` (wall-clock-now) made the guard's input self-defeating: the guard could not have fired on PR #90's code alone because every poll's `fetched_at` was always within microseconds of `now()`, making `age_seconds ≈ 0`. The actual structural break was **PR #92's flip to upstream timestamp** (T-ACT-046, deployed 2026-05-02 12:00 ET — Saturday), which only manifested at Monday's first RTH cron because cron is `mon-fri 9-15 minute=*/5` and there are no weekend cycles. **Convention going forward:** When triaging a time-correlated incident, the agent MUST trace the precise data flow of the suspected breaking change and verify that the change's logic alone could produce the observed symptom. If the change's logic CANNOT produce the symptom in isolation, the agent MUST search forward and backward in commit history for a complementary change that, combined with the original suspect, produces the symptom. Anchoring on the FIRST plausibly-correlated commit and stopping investigation there is the anti-pattern. **Discipline-meta-lesson:** "Verify the suspected change's actual logic could produce the symptom — don't anchor on deploy timing alone." This is a sharpening of A.6's "validate against an independent source" lesson applied to commit-attribution-during-triage rather than feed-data-validation.

**L8.3 — When an external dashboard shows a request, verify the request originates from our code before reasoning about what our code does.** During diagnosis, the operator's Polygon dashboard screenshot showed `/v3/snapshot/options/I:SPX` (200 OK, 25,275 bytes, 57 ms). This was treated as evidence of what our code was calling. A `grep -rn 'snapshot/options' backend/` returns 0 matches — that endpoint is **not** in our backend. The 25KB body size is consistent with a full options chain payload, not a single index snapshot, further suggesting the request was from a different code path (Polygon's web dashboard's own pre-fetch for billing display, a deleted code path, frontend code, or a CLI tool). Anchoring diagnosis on this misleading evidence would have led toward "fix the wrong-endpoint bug" — a non-existent bug. **Convention going forward:** Before reasoning about what our code does based on an external dashboard's request log, the agent MUST verify the request originates from our codebase via `grep -rn '<endpoint-pattern>' backend/ --include='*.py'` (or equivalent ripgrep for the relevant language). The cost of a 30-second `grep` is lower than the cost of misframed diagnosis. **Discipline-meta-lesson:** "External dashboard requests are not our code unless proven otherwise." The dashboard is a vendor-side observability surface; many requests on it originate from non-product paths (vendor's own billing-display pre-fetches, manual operator probes, deleted code paths). This is a sharpening of A.7's "convention pointer ≠ exhaustive audit" applied to evidence-source attribution rather than family-closure verification.

**What this incident's discipline got right** (preserved as positive precedent for future incident triage):

1. **Three independent evidence streams (SQL, Railway logs, Polygon dashboard) gathered before drafting hypotheses.** No single-source diagnosis. Same discipline as A.6's "validate against an independent source."
2. **Read-only diagnostic path with explicit "do not anchor" framing in the Cursor prompt and STOP-and-disagree section.** Cursor's diagnosis caught two anchoring errors in the prompt's framing (PR #90 vs PR #92 attribution; Polygon-dashboard-screenshot evidence misattribution); both were material. Same discipline as the DIAGNOSE-FIRST workflow.
3. **Refused to ship a code fix or a rollback before diagnosis confirmed root cause.** The "easiest unblock" path (rollback PR #92) would have re-buried the silent staleness without removing it — re-introducing the A.7 silent-failure-class family bug T-ACT-046 was created to fix. Same discipline as A.7's convention-pointer-vs-audit lesson.
4. **Operator's choice to upgrade subscription rather than rollback or threshold-relax.** Path A (upgrade tier) was the correct product decision; Path C (relax 330s threshold) and Path D (rollback PR #92) would have re-buried the underlying issue. Same discipline as "fix the cause, not the symptom."

**Structural changes resulting from A.8 (this PR `docs/post-incident-indices-advanced-2026-05-04`):**

1. **`SUBSCRIPTION_REGISTRY.md`** now records the entitlement matrix for Polygon Indices tiers explicitly (§1A new sub-section), with the "Non-pros only" usage restriction on the Advanced tier called out in row 9 description AND in §5 Forward-looking re-licensing trigger row. Future sessions can verify the entitlement question against this file rather than answering from memory (L8.1 mitigation).
2. **VVIX/VIX/VIX9D freshness guard + 330s constant extraction** queued as **T-ACT-062** — same structural fix as SPX. Will eliminate the silent-staleness class of bug for the remaining three index feeds (currently silently 15-min stale pre-T-ACT-061; will become real-time post-T-ACT-061 + T-ACT-062 rollout). Eliminates inline `330` literal at `prediction_engine.py:1366/1373` to module-level `POLYGON_FRESHNESS_THRESHOLD_SECONDS` constant (drift-between-comparison-and-log-message future-bug-class noted in `HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md` §8.3).
3. **Email egress** queued as **T-ACT-063** — current SMTP path failed during this outage with `[Errno 101] Network is unreachable`; watchdog correctly fired but no alert reached the operator. Switching to webhook-based or HTTP-API-based alerting prevents recurrence of detection-without-notification (a class of failure distinct from the T-ACT-057 alerting blackout — that was config-format silent-rejection; this is transport-layer egress reliability).
4. **Post-upgrade retraining decision tracking** logged as **T-ACT-064** — informational; reactivates at ~50-100 closed paper trades on confirmed-fresh data threshold. Decision deferred to that point.
5. **`HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md`** relocated from repo root to `trading-docs/06-tracking/` (this PR) for filesystem-convention compliance with the existing `HANDOFF_NOTE_<date>_<topic>.md` pattern.

**Cost of the incident:**

- 76 hours of zero predictions during what would have been ~456 cron cycles worth of training data (76 hours × 6 cycles/hour = 456 max; actual closed-trade conversion rate would have been a fraction of that, modulo no-trade signals).
- 3 days of operator + Claude + Cursor cycles diagnosing.
- Loss of confidence in prior subscription guidance — direct-cause of L8.1 discipline addition.
- Indirect: post-incident, VVIX silent-staleness explanation became visible (covered in T-ACT-062 description), partially explaining the Sunday 2026-05-03 accuracy investigation findings (degraded directional accuracy attributable in part to 15-min-delayed VVIX features during much of the LightGBM training window).
- **Net subscription cost change:** +$50/mo from 2026-05-04 evening (Indices Starter $49 cancelled → Indices Advanced $99 subscribed; Stocks Advanced $199 unchanged). Pending T-ACT-050 full-restructure execution would yield -$149/mo from current state (cancel Stocks Advanced once Indices Advanced sufficiency is confirmed).

**Open question (tracked separately as T-ACT-064):** Whether the LightGBM model needs retraining on a known-fresh data window post-T-ACT-061 (Indices Advanced) + post-T-ACT-062 (VVIX/VIX/VIX9D freshness guards). Deferred until ~50-100 closed paper trades on confirmed-fresh data are available. At that point: decide whether to retrain on known-fresh window or accept current model's drift. No action now; tracked.

**Convention going forward (sharpened from A.8 — three discipline pointers for future PRs and future agents):**

- **Subscription/entitlement questions** MUST be answered from live tier-description text or recent governance-file matrices, NOT from prior-session memory or training data. (L8.1)
- **Time-correlated incident triage** MUST verify the suspected change's logic alone could produce the symptom; if not, search forward/backward for complementary changes. (L8.2)
- **External dashboard request logs** MUST be verified to originate from our codebase via grep before being treated as evidence about our code's behavior. (L8.3)

**Discipline pointer for future agents reasoning about subscriptions, scaling, productionization, or commercialization:** Indices Advanced row 9 in `SUBSCRIPTION_REGISTRY.md` carries the **"Non-pros only"** usage restriction (Polygon's professional/non-professional exchange-licensing distinction). Operator currently qualifies as non-professional. **Future state changes** (registering as a professional trader, taking external capital, running on behalf of any entity beyond the individual operator, commercializing in any form including paid SaaS or signal redistribution) **WILL change the entitlement and trigger exchange fees.** Future agents reasoning about scaling/commercialization paths MUST surface this constraint in the reasoning chain without operator re-prompting it. Two "Non-pros only" subscriptions now apply: row 2 Stocks Advanced AND row 9 Indices Advanced; both need re-licensing review under the §5 "MarketMuse goes commercial / takes outside capital" trigger.

Ratified 2026-05-04 evening via PR `docs/post-incident-indices-advanced-2026-05-04`. Predecessor diagnostic: `trading-docs/06-tracking/HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md` (relocated from repo root in this PR). T-ACT-061 closure pending §7.1 manual API probe (operator action; expected `age_seconds < 60s` during RTH). Sibling T-ACTs queued: T-ACT-062 (VVIX/VIX/VIX9D freshness guard), T-ACT-063 (email egress investigation), T-ACT-064 (post-upgrade retraining decision tracking — informational).

### A.9 Future additions

Reserved placeholder for the next governance-discipline lesson surfaced by future incident, audit cycle, or post-mortem. Append future discipline additions here as A.9, A.10, ... rolling forward.

---

*Handoff note authored 2026-04-28 22:10 UTC-4 by Cursor (Claude Opus 4.7) at end of P1.3.7 EXECUTE session. Owner: tesfayekb. File location: `trading-docs/06-tracking/HANDOFF_NOTE_2026-04-28_POST_P1-3-7.md`. End of handoff.*

*Appendix A added 2026-04-30 (T-ACT-042 + T-ACT-043 lessons-learned consolidation; per operator decision D5 in Fix PR 4 DIAGNOSE round). A.3 added 2026-04-30 (T-ACT-044 lessons-learned; per operator decision D1 Scope B in Fix PR 5 DIAGNOSE round). A.4 ratified 2026-04-30 via Master Forward Plan v1.2 reconciliation PR (operator decision F7 → option E-ii: cumulative DIAGNOSE-FIRST meta-pattern lesson, distinct from A.1-A.3 single-PR lessons). A.5 ratified 2026-05-01 via PR `fix/migration-model_source-repo-sync` (model_source schema-code drift silent-failure post-mortem; ~16+ hours of zero-row persistence post-LightGBM-v1-activation surfaced via operator empirical validation). A.6 ratified 2026-05-01 via PR `docs/post-may-1-followups` (15-min Tradier sandbox SPX delay phantom-alpha post-mortem; empirical-validation-against-independent-source discipline lesson). A.6 amended 2026-05-03 via Track B PR `docs/track-b-silent-staleness-and-governance` (T-ACT-045 verdict reversal — pre-deploy data could not validate PR #90; PENDING-RE-RUN against post-deploy data; validation-artifact protocol added per N-2 finding; T-ACT-054 added to tracker entries). A.7 ratified 2026-05-03 via Track B PR `docs/track-b-silent-staleness-and-governance` (silent-failure-class family convention pointer; bundles A.5/A.6/T-ACT-046/T-ACT-054 under a single discipline lens). A.7 reinforced 2026-05-02 via T-ACT-054 PR `fix/t-act-054-cv-stress-null-on-degenerate` (T-ACT-054 entry updated to DONE; plan-review meta-lesson added; T-ACT-054 implementation cited as the canonical example of derived-feature NULL-on-degenerate-input discipline). **A.7 family fully closed 2026-05-02** via T-ACT-047 PR `fix/t-act-047-postgrest-error-classification` (T-ACT-047 added as the 5th and final member — try/except discipline at the prediction_engine persist site; second vector for the database-persistence surface documented; convention now distinguishes derived-feature surface from database-persistence surface; T-ACT-047 cited as canonical example for the persist-site discipline; A.1 schema-constraint lesson reinforced via Cursor's plan-review catch that prevented a `service_health.status="critical"` violation). **A.7 family REOPENED 2026-05-02 (same-day reversal)** via T-ACT-055 PR `fix/t-act-055-criteria-evaluator-update-revert` (T-ACT-055 added as the 6th member — `paper_phase_criteria` upsert NOT NULL violation regression introduced PR #17 commit `836a83c` 2026-04-17, surfaced 2026-05-02 via Railway log analysis; database-persistence vector second instance documented; convention now distinguishes (a) convention-establishment closure from (b) exhaustive-audit closure; new discipline-meta-lesson "convention pointer ≠ exhaustive audit" added; T-ACT-056 reserved for exhaustive persist-site audit before A.7 may be formally re-closed; original T-ACT-047 "FULLY CLOSED" claim preserved verbatim at L1253/L1259/L1269/L1285/L1287/L1297 as discipline-meta-lesson — partial-rewrites that sanitize the over-confident historical claim would lose the lesson per R6 stop-condition; T-ACT-055 cited as canonical example for regression-vintage discipline applied to a database-persistence surface — git-archaeology pinpointing commit 836a83c, distinguishing regression from long-standing bug, choosing direct-revert-plus-defensive-amendment over redesign). **A.7 family expanded to 7 members 2026-05-02 (second same-day expansion)** via T-ACT-057 PR `docs/t-act-057-governance-closure` (`ALERT_GMAIL_APP_PASSWORD` whitespace silent-rejection at SMTP layer); new infrastructure-config silent-failure subclass added (third subclass alongside derived-feature surface and database-persistence surface); 14-day production-alerting blackout 2026-04-19 → 2026-05-03 01:28 UTC; ALL 8 `send_alert(...)` callsites silently rejected including 4 CRITICAL (`prediction_engine_persistent_error`, `emergency_backstop_triggered`, `prediction_watchdog_triggered`, `daily_halt_triggered`); operator self-discovered + env-var-fix-applied 2026-05-02 21:28 ET; smoke test PASSED 2026-05-02 21:52 ET (`alert_email_sent` log fired + email arrived in operator's inbox); code-change PR DEFERRED for Option B `.replace(" ", "")` defensive strip at `config.py:103` (T-ACT-058 reserved); T-ACT-059 reserved for exhaustive-config-audit; discipline-meta-lesson sharpened to "3-question exhaustive verification: SET / CORRECT FORMAT / END-TO-END VALIDATED" applied to ALL infrastructure-config surfaces. **A.8 ratified 2026-05-04 evening via PR `docs/post-incident-indices-advanced-2026-05-04`** (Subscription tier mismatch outage 2026-05-01 → 2026-05-04, 76 hours; three discipline lessons: L8.1 subscription/entitlement claims as present-day factual questions, L8.2 time-correlated triage must verify suspected change's logic alone could produce symptom, L8.3 external dashboard request logs must be verified to originate from our codebase before being treated as evidence; T-ACT-061 PENDING-VERIFICATION on §7.1 probe; T-ACT-062/063/064 sibling tasks queued; predecessor diagnostic `HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md` relocated from repo root to `trading-docs/06-tracking/` in same PR; "Non-pros only" usage restriction surfaced as governance constraint applying to BOTH Stocks Advanced row 2 AND Indices Advanced row 9 in `SUBSCRIPTION_REGISTRY.md`). A.9 reserved as the next "future additions" placeholder slot.*
