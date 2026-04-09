## Governance Redundancy Fixes

### Fix 1 — Strengthen Memory Index as Backup Governance Layer
Update `mem://index.md` Core section to include binding hard stops (not just notes):
- "STOP: Read docs/00-governance/constitution.md + system-state.md before ANY action"
- "Code generation: blocked. Phase: documentation-only. Violations = INVALID."
- "Unplanned features → docs/08-planning/feature-proposals.md. Do NOT implement."

This ensures that even if `.lovable/rules.md` isn't loaded, the memory (which is ALWAYS in Lovable context) catches the AI.

### Fix 2 — Add governance memory file
Create `mem://governance/bootstrap-backup` with the critical execution gates and reading order — a compressed version of the rules file that memory can reference.

### Fix 3 — Strengthen README as universal fallback
Add a more prominent "STOP" block at the very top of README.md so ANY AI tool (not just Lovable/Cursor) sees governance before acting.

### Result: 4 redundant layers
1. `.lovable/rules.md` → auto-loaded, full rules
2. `.cursorrules` → auto-loaded, full rules  
3. `mem://index.md` → always in context, hard stops + pointers
4. `README.md` → universal fallback with STOP block