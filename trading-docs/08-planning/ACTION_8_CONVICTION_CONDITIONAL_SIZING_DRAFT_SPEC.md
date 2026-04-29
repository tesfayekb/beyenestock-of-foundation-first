# Action 8 — Conviction-Conditional Sizing (DRAFT SPEC)

> **Status:** DRAFT — pending Apr 30 baseline lock-in. Spec drafted in parallel with Action 6 governance review per operator authorization 2026-04-29.
>
> **Note on naming:** This is a Master ROI Plan §3 pre-AI fix-track spec, not an AI-SPEC-NNN catalog item. Earlier draft proposal naming as "AI-SPEC-013" was corrected — that slot is reserved for Item 13 (Drift Detection) per `AI_BUILD_ROADMAP.md §3.11` and the locked spec at `archive/raw-locked-specs-2026-04-26/ITEM_13_DRIFT_DETECTION_LOCKED.md`. This spec lives in `trading-docs/08-planning/` alongside `MASTER_ROI_PLAN.md` and `ACTION_6_GOVERNANCE_REVIEW_WORKING.md`, with filename pattern matching the workstream-prefix + lifecycle-suffix convention.
> **Authority:** Master ROI Plan v2.0.3 §3 Action 8 (lines 343-351); subordinate to current main HEAD.
> **Trigger condition:** ✅ MET. Apr 28 + Apr 29 baselines confirm `direction_signal_weak >50%` of skips (96.2% combined). Apr 30 baseline expected to confirm; if it does, this spec moves from DRAFT to READY-TO-IMPLEMENT.
> **Spec type:** code-change spec (analogous to PRE-P11-3 Action 7b in scope/depth, not Cluster B audit-redline format).

---

## 1. PROBLEM

The system has not opened a paper trade in ≥2 sessions (Apr 28 + Apr 29; expecting Apr 30 to confirm). 100% (Apr 28) and 92.9% (Apr 29) of skip events fired at the conviction gate (`direction_signal_weak`), where the prediction engine tests `abs(p_bull - p_bear) < 0.05`.

The 0.05 threshold was set during an earlier era with fewer indicators; it has become structurally too high under current calibration data + indicator set, producing a binary on/off behavior:
- `|p_bull - p_bear| ≥ 0.05` → trade fires at full size
- `|p_bull - p_bear| < 0.05` → no trade

**The operating regime is currently 100% in the second branch.** Without intervention, the system trades zero. The reverse mode (lowering threshold to 0.01 etc.) would risk producing many trades with insufficient edge — exactly the failure mode that occurred earlier when the system had losing trades.

The redesign threads between these by lowering the threshold AND adding a sizing modifier in the borderline band, so:
- `|p_bull - p_bear| ≥ 0.05` → trade fires at 1.0× sizing (HIGH CONVICTION; unchanged)
- `0.03 ≤ |p_bull - p_bear| < 0.05` → trade fires at **0.5× sizing** (BORDERLINE CONVICTION; new)
- `|p_bull - p_bear| < 0.03` → no trade (skip with `direction_signal_weak`; behavior unchanged for this band)

This approach explicitly trades **lower conviction → smaller position** rather than binary fire-or-skip. Risk per trade in the borderline band is ½ that of high-conviction trades.

---

## 2. ROI RATIONALE

**Why this is profit-positive (not just trade-count-positive):**

1. **The borderline conviction band (0.03 ≤ |p_bull - p_bear| < 0.05) is currently 100% wasted.** Any cycle where the prediction engine has directional opinion at this level is currently treated identically to a tie (50/50 prediction). That's information being thrown away.

2. **0.5× sizing is the bayesian-correct response to lower conviction.** If high-conviction trades have expected value E and full risk R, borderline-conviction trades with ~60-70% of the conviction-density should have proportionally lower position size. 0.5× is conservative: it under-sizes relative to mathematical optimum, sacrificing some expected upside in exchange for faster failure detection if borderline trades systematically lose.

3. **Failure detection is fast.** If borderline trades lose disproportionately, the existing `D-022 consecutive losses` gate at `risk_engine.py` halves risk_pct. Stacked with the 0.5× modifier, post-loss sizing in the borderline band becomes 0.25× — capital-preservation aggressive.

4. **No change to trades that would have fired anyway.** High-conviction trades (|p_bull - p_bear| ≥ 0.05) continue at full sizing. Action 8 is purely additive at the borderline band.

5. **Cleanest possible empirical attribution.** The Apr 28 + Apr 29 + Apr 30 baselines establish the pre-Action-8 state with surgical precision (100% skip rate at conviction gate). Post-Action-8, the system either (a) starts firing borderline trades at 0.5× size, or (b) doesn't change at all (if borderline band is also empty). Either outcome is unambiguously diagnostic.

**Anti-rationale check:**

- ❌ "Just lower the threshold to 0.03" — this is what the prior era did and produced losing trades. The added sizing modifier is what makes the lowered threshold safer.
- ❌ "Wait for Action 9 (AI synthesis) instead" — Action 9 adds an alternative direction signal; it doesn't lower the conviction floor for the rules engine. Action 9 + Action 8 together close both the conviction floor AND the input-signal diversity gap. Action 8 alone is the cheapest single move.

---

## 3. SCOPE

### 3.1 Production code changes (3 sites)

**Site A — `backend/prediction_engine.py:580` (primary classifier path):**
```python
# OLD
signal_weak = abs(p_bull - p_bear) < 0.05

# NEW
_signal_strength = abs(p_bull - p_bear)
signal_weak = _signal_strength < 0.03  # was 0.05; lowered per Action 8
signal_borderline = 0.03 <= _signal_strength < 0.05  # new field
```

**Site B — `backend/prediction_engine.py:649` (secondary fallback path):**
```python
# OLD
signal_weak = abs(p_bull - p_bear) < 0.05  # 0.05: blocks at <0.3% ZG distance, allows at >0.5%

# NEW
_signal_strength = abs(p_bull - p_bear)
signal_weak = _signal_strength < 0.03  # was 0.05; lowered per Action 8
signal_borderline = 0.03 <= _signal_strength < 0.05  # new field
# Comment update: 0.03 = blocks at <0.18% ZG distance; 0.05 borderline band = allows half-size
```

Both sites must be updated together. Updating only one creates an inconsistent gate — STOP if either site cannot be updated.

**Site C — `backend/prediction_engine.py:583-590` and `:659` (signal payload schemas):**
Add `signal_borderline` boolean to both emitted dicts. Existing `signal_weak` field semantic shifts (now `< 0.03` instead of `< 0.05`); downstream consumers must handle the new band.

### 3.2 Sizing modifier wiring (1 site)

**Site D — `backend/strategy_selector.py:1197` `compute_position_size(...)` call:**

The existing `kelly_multiplier` parameter (default 1.0, capped 2.0, floored 0.5) is the natural injection point for the 0.5× modifier — no new parameter needed; signal_borderline → kelly_multiplier=0.5.

```python
# Pseudo-pattern (exact placement TBD during DIAGNOSE):
borderline_modifier = 0.5 if direction_data.get("signal_borderline") else 1.0
existing_kelly = compute_kelly_multiplier(...)  # if exists
combined_kelly = max(0.5, min(2.0, existing_kelly * borderline_modifier))  # respect existing cap/floor
sizing = compute_position_size(
    ...,
    kelly_multiplier=combined_kelly,
    ...,
)
```

If `compute_kelly_multiplier()` doesn't exist or isn't called at this site, simpler:
```python
borderline_modifier = 0.5 if direction_data.get("signal_borderline") else 1.0
sizing = compute_position_size(
    ...,
    kelly_multiplier=borderline_modifier,
    ...,
)
```

**Critical:** the borderline modifier composes multiplicatively with existing risk reductions (`regime_disagreement` → 0.5×, `consecutive_losses` → 0.5×, etc.). Stacking is intended:
- Borderline + regime disagreement → 0.25× sizing
- Borderline + consecutive losses → 0.25× sizing
- Borderline + both → 0.125× sizing (probably 1 contract minimum or 0)

This is correct behavior — borderline conviction in adverse market regime SHOULD size very small. The existing minimum-contracts floor at `risk_engine.py` handles the floor case.

### 3.3 Skip-emission update (1 site)

**Site E — `backend/prediction_engine.py:904-906`:**

Current:
```python
if not no_trade and direction_data.get("signal_weak"):
    no_trade = True
    no_trade_reason = "direction_signal_weak"
```

This logic remains correct — `signal_weak` now means `< 0.03` per Site A/B updates. Borderline trades (`0.03 ≤ |p_bull - p_bear| < 0.05`) will NOT be skipped here because `signal_weak = False` for them. They proceed to sizing with the 0.5× modifier.

**No edit at this site.** Just verify behavior.

### 3.4 Tests (2 new tests + 1 existing test update)

**New test 1 — borderline trades open at reduced size:**
- Test asserts that when `direction_data["signal_borderline"] = True` reaches sizing, the resulting `contracts` is ≤ ½ of what it would be at full sizing
- Verify against calibration values (e.g., $100k account, 10pt SPX spread, Phase 1 → expected contracts at full size vs at 0.5× borderline modifier)

**New test 2 — borderline + adverse modifier stacks correctly:**
- Test asserts borderline + regime_disagreement → 0.25× of full-size baseline
- Test asserts borderline + consecutive_losses=3 → 0.25× of full-size baseline
- Test asserts borderline + both → 0.125× of full-size baseline (or floor case)

**Existing test update — `signal_weak` threshold tests:**
- Find any existing test that asserts threshold = 0.05; update to threshold = 0.03
- Find any existing test that asserts no-trade fires at `|p_bull - p_bear| < 0.05`; update boundary to `< 0.03`
- Add coverage for the new band: trades fire at `0.03 ≤ |p_bull - p_bear| < 0.05` (with 0.5× sizing)

### 3.5 Doc updates (1 file)

**`trading-docs/06-tracking/action-tracker.md`:** add Action 8 entry at the appropriate location with status `shipped pending Apr 30 lock-in`. Cross-reference Master ROI Plan §3 line 343.

---

## 4. OUT OF SCOPE

| Out of scope | Why |
|---|---|
| Action 9 / AI synthesis flag flip | Sequenced after Action 8 + 5 trading days |
| `kelly_multiplier` parameter renaming or extension | The existing parameter has the right semantic; reusing it is the right call |
| `consecutive_losses` modifier separately | Already in production at `risk_engine.py`; stacks correctly with this change |
| Threshold further lowering (0.02 or 0.01) | Out of scope; this spec lowers to 0.03 only. Future spec may calibrate further based on Action 8 deployment data |
| Sizing modifier other than 0.5× (e.g., 0.7× or proportional to conviction) | Out of scope; 0.5× is the Master ROI Plan §3 line 346 specified value. Future calibration may revise |
| Schema migrations | None required — `signal_borderline` is a runtime computed field, not persisted |
| AI-SPEC-008/009/010 audit-driven changes | Different work-stream |

---

## 5. RISKS + MITIGATIONS

| Risk | Severity | Mitigation |
|---|---|---|
| Borderline trades systematically lose, eroding capital | MEDIUM | (a) 0.5× sizing limits per-trade loss to ½ of high-conviction trade loss. (b) `consecutive_losses` modifier compounds — 3 consecutive borderline losses triggers further halving. (c) The 5-trading-day post-deploy observation window per Master ROI Plan §3 line 348 explicitly catches this pattern and triggers Action 7 sequencing or Action 8 rollback before any large drawdown |
| Threshold change to 0.03 produces too many trades, overwhelming Tradier sandbox or producing operational stress | LOW | (a) 0.5× sizing limits per-trade exposure; (b) Existing daily halt gates (D-005 -3% halt) still apply; (c) Frequency rate-limiter (`strategy_blocked_frequency`) still applies — currently dormant, would activate if needed |
| Two-site threshold update creates inconsistency if only one site lands | HIGH if mishandled | DIAGNOSE phase explicitly enforces both-or-neither updates. STOP CONDITION 3 catches partial update |
| `signal_borderline` field added but not consumed by all downstream readers | LOW | Only one downstream consumer (`strategy_selector.py:1197` sizing call) needs to read it; other downstream readers operate on `signal_weak` alone, which still works correctly |
| `kelly_multiplier` parameter composition with existing modifiers produces unexpected stacking | MEDIUM | New test 2 explicitly verifies stacking math. If existing modifier composition is more complex than `multiplicative`, DIAGNOSE phase surfaces it for operator review |
| Apr 30 baseline does NOT confirm trigger | LOW | Action 8 spec stays in DRAFT state until Apr 30 confirms. If Apr 30 shows different gate dominance, the spec doesn't deploy and may be revised based on the actual gate distribution |

---

## 6. SEQUENCING

Per Master ROI Plan v2.0.3 §3 line 348:

> Sequence ≥5 trading days BEFORE Action 7 deploy for clean Sharpe attribution

This means:
- **Action 8 ships first** (this spec when it becomes ready-to-implement)
- **5 trading days of paper-trading data accumulate** with Action 8 active
- **Then Action 7 / Commit 4 ships**, into a known-state system

If Action 8 cannot ship ≥5 trading days before Action 7, the plan reverses:
> if Action 8 cannot ship ≥5 trading days before Action 7, defers to (Action 7 ship + 5 trading days) via Gate E 3-way max formula

So if Action 6 governance review (operator-paced) drags long enough that Action 7 is ready before Action 8 has 5 days of data, Action 8 deploys but Gate E waits until 5 days post-Action-7 instead of 5 days post-Action-8. Either way, the goal is clean Sharpe attribution for at least one of {Action 7, Action 8} before Action 9.

---

## 7. APPROVAL GATES

This spec is in DRAFT until ALL of:
- [ ] Apr 30 baseline append confirms `direction_signal_weak >50%` (lock-in for trigger condition; sessions 1+2+3 all confirming)
- [ ] Operator reviews this spec and authorizes EXECUTE phase
- [ ] No blocking dependency from Action 6 governance review (verified absent — no D-023 enrichment item touches conviction-gate threshold; verified absent — no Class C escalation conflicts with sizing-modifier composition)

Once all 3 conditions met, spec → READY-TO-IMPLEMENT.

After EXECUTE: spec → SHIPPED-AWAITING-OBSERVATION (5 trading days per Gate E sequencing).

After 5 trading days: spec → CLOSED (Action 8 part of permanent system; Gate E condition partially met for sequencing).

---

## 8. IMPLEMENTATION SEQUENCE (when authorized)

1. DIAGNOSE-FIRST per orientation §3
2. Apply Site A + Site B + Site C edits to `backend/prediction_engine.py` (atomic; both sites or neither)
3. Apply Site D edit to `backend/strategy_selector.py:1197`
4. Add 2 new tests; update existing threshold tests
5. Doc batch to `action-tracker.md`
6. Pytest must pass
7. Push branch `fix/action-8-conviction-conditional-sizing`
8. Operator merges
9. Watch deployment; first borderline trade fires within ~1-2 trading days if conviction-gate band is occupied at all

---

## 9. ANCHORS (verified at HEAD `25b2c66`)

- `backend/prediction_engine.py:580` — primary classifier signal_weak
- `backend/prediction_engine.py:649` — secondary fallback signal_weak
- `backend/prediction_engine.py:583-590` — payload schema (primary)
- `backend/prediction_engine.py:659` — payload schema (secondary)
- `backend/prediction_engine.py:904-906` — skip emission `direction_signal_weak`
- `backend/strategy_selector.py:1197` — `compute_position_size(...)` call site
- `backend/risk_engine.py:262` — `compute_position_size` definition (kelly_multiplier parameter at signature)
- `backend/risk_engine.py:5-9` — sizing reduction stacking order (per the docstring, kelly multiplier composes correctly with existing reductions)

All anchors verified by Cursor's DIAGNOSE phase to still match before EXECUTE.

---

## 10. REVISION LOG

| Date | Revision | Reason |
|---|---|---|
| 2026-04-29 | DRAFT v1 — initial spec | Drafted in parallel with Action 6 governance review per operator authorization 2026-04-29 |

Future revisions add rows here. If Action 6 dispositions or Apr 30 baseline data prompt revisions before EXECUTE, capture each revision as a row with date, revision name, and one-line rationale. Post-EXECUTE revisions (Action 8b amendments) become entries here with cross-reference to the relevant PR.

---

*End of spec. DRAFT — pending Apr 30 baseline confirmation + operator authorization.*
