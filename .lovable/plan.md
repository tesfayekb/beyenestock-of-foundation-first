

## Audit: Change Control Step Count Mismatch

### The Problem
`change-control-policy.md` says **"9-Step Workflow"** in two places (heading + enforcement rule), but the numbered list contains **10 steps**. This contradiction exists in 3 locations total:

| Location | Current Text | Issue |
|----------|-------------|-------|
| `change-control-policy.md` line 15 | "All 9 steps MUST be executed" | Says 9, actually 10 |
| `change-control-policy.md` line 20 | "Mandatory 9-Step Workflow" | Says 9, actually 10 |
| `ai-operating-model.md` line 29 | "Must follow the 9-step change-control workflow" | Says 9 |
| `mem://governance/change-control` line 5-6 | "9-Step Workflow" | Says 9 (but content is correctly condensed to 9) |

### Two Options

**Option A — Rename to 10-Step (straightforward)**
- Change all references from "9" to "10"
- No structural change to the steps
- Simple, honest, minimal risk

**Option B — Merge back to 9 steps (cleaner architecture)**
- Step 10 ("Update system-state.md if system state changed") is conditional and logically part of finalization
- Merge it into Step 9 (Verify) as a sub-bullet, making the list genuinely 9 steps
- The memory file already models it this way — so this aligns doc with existing memory
- No external reference updates needed since the count stays at 9

### Recommendation: Option B

Rationale:
1. The memory file (`mem://governance/change-control`) already correctly condensed this to 9 steps — proving the 9-step model is natural
2. Step 10 is conditional ("if system state changed") — it's a finalization sub-action, not a standalone workflow step
3. Avoids updating references across multiple files
4. Keeps the established "9-step" identity stable

### Implementation (Option B)

**File 1: `docs/00-governance/change-control-policy.md`**
- Keep "9-Step" in heading and enforcement rule (no change needed)
- Restructure steps 9-10 into a single Step 9 with sub-bullets:
  ```
  9. **Verify and finalize:**
     - Dependencies intact
     - Reference indexes accurate
     - No unintended behavior changes
     - Required regression checks completed
     - Update `system-state.md` if system state changed
  ```

No changes needed in `ai-operating-model.md` or `mem://governance/change-control` — they already say 9.

**Total files changed: 1**

