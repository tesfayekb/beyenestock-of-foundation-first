# Item 11: Event-Day Playbooks with Microstructure Timing — LOCKED SPECIFICATION

**Status:** 🔒 LOCKED
**Locked:** 2026-04-26
**Tier:** V0.4 Maturation (6-12 months after V0.3)
**Architectural Role:** Deterministic event-day policy overlay. Constraint-first, not prediction model.
**Sources:** GPT Round 2 + Items 1-10 dependencies + Claude verification + GPT verification accept

---

## Architectural Commitment

**Item 11 is a policy overlay, not another prediction model.**

It imposes event-window constraints on the already-locked stack (Items 1, 5, 6, 7, 8, 9). It must NOT duplicate:
- Governor's event detection (Item 1)
- Vol Engine's EV math (Item 5)
- Meta-Labeler's trade/no-trade scoring (Item 6)

Item 11's job is narrower: when event-day microstructure is structurally known, restrict what the rest of the system is allowed to do.

**Strongest commitment:** Item 11 prevents structurally dumb trades on event days. Upside capture remains the job of Item 5 + Item 6 + Opportunity Lean, under Item 11's time-window constraints. It does NOT predict event direction.

---

## 1. Event Taxonomy

### V0.4 Binding Scope

```
FOMC decision days
CPI release
NFP / Employment Situation
PCE release
FOMC minutes (3 weeks after decision)
Monthly OpEx (3rd Friday)
Quarterly OpEx / quad witching (4/year)
Unscheduled events (via unscheduled_event_playbook)
```

### V0.4 Advisory Only

```
GDP releases
Fed Chair speeches
Treasury refunding / auction days
Mega-cap earnings (context only - see Section 6)
Month-end / quarter-end rebalancing
```

These matter but sample sizes and event structure are less uniform. NOT given binding playbook authority in V0.4.

### V0.5+ Deferrals

```
Russell rebalance
Treasury auctions / refunding (full playbook)
VIX expiration interactions
Earnings-season aggregate playbook
Event-specific Opportunity Lean expansion
```

### Out of Scope

```
Mega-cap earnings as full playbook
  (Use as context only — see Section 6)
  SPX 0DTE intraday is structurally insulated from after-hours earnings
```

---

## 2. Microstructure Timing Rules

### FOMC Decision Day

```
09:35–13:30   pre_decision
13:30–13:55   pre_release_embargo_window
13:55–14:05   release_dislocation
14:05–14:25   first_reaction
14:25–14:35   press_conference_transition
14:35–15:15   press_conference_wave
15:15–15:45   post_press_stabilization
15:45–close   exit_only
```

**Behavior per window:**

```
pre_decision:
  implied move still embedded
  short gamma vulnerable
  liquidity okay but event risk dominates

pre_release_embargo:
  market positioning for release
  most strategies should restrict
  
release_dislocation:
  quotes unreliable
  spreads widen 5-10x
  no entries

first_reaction:
  initial move often unstable
  require confirmation

press_conference_wave:
  second volatility wave possible
  trend can reverse or extend

post_press:
  only trade if confirmation + flow + EV agree
```

### CPI / NFP / PCE (8:30 AM ET releases)

```
pre_market_release:     08:30
cash_open_reset:        09:30–09:45
first_cash_reaction:    09:45–10:15
trend_confirmation:     10:15–11:30
midday_decay:           11:30–13:30
late_day:               13:30–14:30
exit_only:              after 14:30
```

**Behavior per window:**

```
09:30–09:45:
  cash open absorbs overnight / futures reaction
  do NOT sell neutral short gamma immediately

09:45–10:15:
  allow only small directional debit / defined-risk if 
  confirmation exists

10:15–11:30:
  best window for confirmed post-data directional or vol trades

11:30+:
  normal stack may resume, but event-day caps remain
```

### OpEx / Quad Witching

```
09:35–10:30   opening_inventory_adjustment
10:30–13:30   pin_or_unwind_detection
13:30–15:00   gamma_pinning_or_unwind
15:00–close   closing_flow_distortion
```

**Behavior per window:**

```
opening:
  avoid assuming clean trend/range

midday:
  pin strategies allowed only if GEX/key-strike evidence confirms

late_day:
  short gamma near key strikes attractive but fragile

close:
  no new entries; exit / risk only
```

---

## 3. Strategy-Class Restrictions

### FOMC Playbook

```
fomc_playbook = {
  pre_decision: {
    blocked: ['iron_butterfly'],
    restricted: ['iron_condor', 'put_credit_spread', 
                 'call_credit_spread'],
    default: ['debit_call_spread', 'debit_put_spread'],
    favored: []
  },

  pre_release_embargo_window: {
    blocked: ['iron_condor', 'iron_butterfly', 
              'put_credit_spread', 'call_credit_spread'],
    restricted: ['debit_call_spread', 'debit_put_spread', 
                 'long_straddle'],
    long_vol_authority: 'permitted_if_confirmed_pre_event'
  },

  release_dislocation: {
    blocked: ['ALL'],
    restricted: [],
    default: [],
    favored: []
  },

  first_reaction: {
    blocked: ['iron_condor', 'iron_butterfly'],
    restricted: ['put_credit_spread', 'call_credit_spread', 
                 'long_straddle'],
    default: ['debit_call_spread', 'debit_put_spread'],
    favored: []
  },

  press_conference_wave: {
    blocked: ['iron_butterfly'],
    restricted: ['iron_condor', 'put_credit_spread', 
                 'call_credit_spread'],
    default: ['debit_call_spread', 'debit_put_spread', 
              'long_straddle'],
    favored: []
  },

  post_press_stabilization: {
    blocked: [],
    restricted: ['iron_butterfly', 'iron_condor'],
    default: ['put_credit_spread', 'call_credit_spread', 
              'debit_call_spread', 'debit_put_spread'],
    favored: []
  }
}
```

**Critical rule:** Nothing is automatically favored on FOMC. Favoring requires Item 5 EV + Item 6 Meta + Item 8 flow confirmation.

### CPI / NFP / PCE Playbook

```
macro_830_playbook = {
  cash_open_reset: {
    blocked: ['iron_condor', 'iron_butterfly'],
    restricted: ['put_credit_spread', 'call_credit_spread', 
                 'long_straddle'],
    default: ['debit_call_spread', 'debit_put_spread'],
    favored: []
  },

  first_cash_reaction: {
    blocked: ['iron_butterfly'],
    restricted: ['iron_condor', 'put_credit_spread', 
                 'call_credit_spread'],
    default: ['debit_call_spread', 'debit_put_spread', 
              'long_straddle'],
    favored: []
  },

  trend_confirmation: {
    blocked: [],
    restricted: ['iron_butterfly'],
    default: ['iron_condor', 'put_credit_spread', 
              'call_credit_spread', 'debit_call_spread', 
              'debit_put_spread'],
    favored: ['directional_debit_if_confirmed']
  },

  midday_decay: {
    blocked: [],
    restricted: ['iron_butterfly'],
    default: ['iron_condor', 'put_credit_spread', 
              'call_credit_spread'],
    favored: []
  }
}
```

### OpEx / Quad Witching Playbook

```
opex_playbook = {
  opening_inventory_adjustment: {
    blocked: ['iron_butterfly'],
    restricted: ['iron_condor', 'put_credit_spread', 
                 'call_credit_spread'],
    default: ['debit_call_spread', 'debit_put_spread'],
    favored: []
  },

  pin_or_unwind_detection: {
    blocked: [],
    restricted: ['iron_butterfly'],
    default: ['iron_condor', 'put_credit_spread', 
              'call_credit_spread'],
    favored: ['iron_butterfly_only_if_pin_score_high']
  },

  gamma_pinning_or_unwind: {
    blocked: [],
    restricted: ['iron_butterfly', 'iron_condor'],
    default: ['single_side_credit', 'directional_debit'],
    favored: []
  },

  closing_flow_distortion: {
    blocked: ['ALL_NEW_ENTRIES'],
    restricted: [],
    default: [],
    favored: []
  }
}
```

---

## 4. Long Straddle Pre-FOMC Authority

Long straddle in pre_release_embargo_window is RESTRICTED, not blocked. Permitted only when Item 5 confirms cheap convexity AND quality conditions met.

### Required Conditions

```
Item5.iv_rv_ratio <= 0.85
Item5.confidence >= 0.65
option_strip_vs_atm_divergence <= 0.30
quote_quality_ok = true
estimated_slippage <= 35% of gross_edge
Meta-labeler p_eff passes
Governor uncertainty < 0.70
size_cap = 0.25
```

If live authority enabled, also triggers Item 7 adversarial review.

### Status Framing

```
long_straddle pre-FOMC = permitted_if_confirmed
                       = NOT favored
                       = NEVER full-size
```

This preserves the structural commitment (no naked exposure to release dislocation) while allowing Item 5's vol-underpricing signal to enable convex pre-event trades when conditions align.

---

## 5. Unscheduled Event Playbook

### Trigger Conditions

```
unscheduled_event_playbook fires if ANY:
  surprise_detector.severity >= 0.70
  OR Governor.event_class in [
       'geopolitical_shock',
       'surprise_macro',
       'crisis'
     ]
  OR market_dislocation_score >= 0.65
```

### Market Dislocation Score Computation

Use normalized component scores via ramp function:

```
ramp(z, low, high) = clip((z - low) / (high - low), 0, 1)

spx_component   = ramp(abs(spx_5m_return_z), 2.0, 3.5)
vix_component   = ramp(vix_1m_jump_z,        2.0, 3.5)
basis_component = ramp(abs(futures_cash_basis_z), 1.5, 3.0)
news_component  = ramp(news_flux_z,          1.5, 3.0)

market_dislocation_score =
    0.30 * spx_component
  + 0.25 * vix_component
  + 0.20 * basis_component
  + 0.25 * news_component
```

### Multi-Confirmation Guard

```
if score is triggered by only one non-news component:
    status = watch_mode
    not binding playbook

Binding requires:
  market_dislocation_score >= 0.65
  AND at least two components >= 0.50
```

OR high-confidence source path:
```
Governor.event_class in crisis/geopolitical_shock/surprise_macro
OR surprise_detector.severity >= 0.70
```

### Restrictions When Triggered

```
block neutral_short_gamma
disable opportunity lean unless price + flow confirmation exists
cap all new defined-risk trades at 0.25
increase Item 7 adversarial trigger probability
require operator review if severity high
```

### Differentiation From Item 1's Iran-Day Rule

```
Item 1: detects and scores novelty/uncertainty
Item 11: imposes concrete event-window policy after detection
```

For Iran-day:
```
event_class = 'geopolitical_shock'
unscheduled_playbook fires
iron_butterfly + iron_condor blocked
single-side credit restricted
directional debit only after confirmation
```

---

## 6. Earnings Context

Earnings is NOT a full Item 11 playbook in V0.4. Used as context only.

### Outputs

```
mega_cap_earnings_today: boolean
mega_cap_earnings_tomorrow: boolean
mega_cap_earnings_weight_bucket: low | medium | high
earnings_season_intensity: low | medium | high
earnings_aggregate_within_5d: integer
```

### Mega-Cap Basket

```
AAPL, MSFT, NVDA, GOOGL/GOOG, META, AMZN, TSLA
```

### Effects

```
if mega_cap_earnings_today after-hours:
    no direct constraint on same-day 0DTE intraday trades
    flag next_session_gap_risk = true

if mega_cap_earnings_tomorrow:
    Item 12 receives elevated_gap_risk
    no overnight-risk allocation expansion

if earnings_season_intensity == 'high':
    Item 7 adversarial trigger score += 0.10
    Governor uncertainty floor += 0.05 IF news/flow conflict exists

if post-15:00 entries are ever allowed:
    size cap = 0.85 when mega_cap_earnings_tomorrow = true
```

**Rationale:** SPX 0DTE positions close at 14:30 ET regardless of after-hours earnings. Today's intraday trades aren't directly exposed. Real effect is overnight gap risk for tomorrow's open and Item 12 allocation decisions.

---

## 7. Federal Holiday Handling

### Source of Truth

```
official exchange calendar (NYSE/CBOE)
NOT vendor calendar
NOT manual list
```

### Stored Fields

```
session_type:
  regular
  early_close
  holiday_closed

market_open_time
market_close_time
```

### Early-Close Day Rules (Time-Anchored)

```
mandatory_close_time = market_close_time - 30 minutes
exit_only_start      = market_close_time - 60 minutes
no_new_entries_after = market_close_time - 90 minutes
```

**Example for 13:00 ET close:**
```
no_new_entries_after = 11:30
exit_only_start      = 12:00
mandatory_close      = 12:30
```

This works regardless of normal (16:00) or early (13:00) close. No hardcoded 14:30.

### Post-Holiday Open

```
cash_open_reset = 09:30–10:00 (vs normal 09:30–09:45)
```

### Long-Weekend Friday Constraint

```
if pre_holiday_or_long_weekend:
    neutral short-gamma max size cap = 0.85
    iron_butterfly blocked in final shortened-session hour
    no expansion of opportunity lean solely due to theta
```

**Note:** SPX 0DTE options expire same-day, so weekend theta is NOT a direct edge for them. Holiday context affects liquidity, gap risk, and shortened-session behavior — not theta accumulation.

---

## 8. Interaction With Items 1, 5, 6 (Composition Model)

### Architectural Choice: Option A (Additional Constraints)

```
Item 5 Vol Engine
+ Item 8 OPRA
+ Rules / LightGBM
→ Market State Card
→ Item 1 Governor
→ Item 6 Meta-Labeler
→ Item 11 Playbook Constraints
→ preliminary arbiter
→ Item 7 if triggered
→ final arbiter
```

### Final Arbiter Composition

```
final_size = min(
  constitutional_cap,
  rules_cap,
  governor_cap,
  meta_labeler_cap,
  event_playbook_cap,
  adversarial_cap_if_present
)
```

Most restrictive wins.

### Why Not Override Authority

Item 11 is hand-coded prior knowledge with sparse event samples. It should restrict risky behavior, NOT force trades.

### Why Not Pure Input Feature

Some timing rules are structural:
```
FOMC 14:00 release window = no entries
```

That should NOT be left to a probabilistic model.

---

## 9. Structured Priors vs Empirical Calibration

### Hand-Coded Structural Priors (No Learning)

```
event source calendars
event scheduled release times
no entries during release_dislocation windows
constitutional exits remain absolute
no short-gamma neutral entries immediately before known 
  high-impact release
no new entries after existing time-stop rules
```

### Empirically Calibrated (Via Item 4 Replay Harness)

```
pre-release block window length
post-release wait time
restricted size cap (0.25 vs 0.50)
when short gamma can resume
whether long straddle is allowed after event
minimum OPRA confirmation threshold
minimum Item 5 EV threshold
minimum Meta p_eff threshold
```

### Calibration Method

```
event-type walk-forward replay
compare default stack vs stack + Item 11
optimize only small discrete parameter set
do not overfit per-event micro windows
```

### Discrete Parameter Search Space

```
post_release_wait ∈ {5, 10, 15, 30 minutes}
short_gamma_resume ∈ {30, 60, 90 minutes, never}
restricted_cap ∈ {0.25, 0.50}
```

---

## 10. Data Source Authority

### Locked Hierarchy

```
FOMC: Federal Reserve calendar
CPI / NFP: BLS release schedule
PCE / GDP: BEA release schedule
OpEx / quarterly options: OCC / Cboe calendars
Earnings: Finnhub + existing earnings_scanner
Unscheduled: surprise_detector + Polygon/news + price/VIX/futures 
             confirmation
```

### Required Event Fields

```
event_id
event_class
event_subtype
source
source_confidence
scheduled_date
scheduled_release_time_et
expected_impact_level
pre_window_start
release_window_start
release_window_end
post_window_end
playbook_version
data_last_verified_at
```

### Conflict Resolution

```
official government / exchange source beats vendor
vendor source can warn but cannot create binding playbook 
  if official source disagrees
if conflict unresolved → advisory only, no binding Item 11 
  restriction except generic caution
```

---

## 11. Empirical Validation via Item 4

### Replay Test Structure

```
Baseline A: default stack without Item 11
Candidate B: default stack + Item 11 constraints
```

### Event-Day Metrics

```
event_day_PnL_delta
max_drawdown_delta
worst_event_day_delta
false_restriction_cost
short_gamma_loss_avoided
opportunity_lean_cost_or_benefit
trade_retention
slippage_impact
```

### Promotion Gates

```
minimum 20 total event days across all core event types
minimum 6 FOMC days preferred
minimum 6 CPI/NFP/PCE days combined
minimum 6 OpEx/quad days

Candidate must:
  improve event-day max drawdown by >= 10%
  not worsen total event-day P&L by > 2R
  reduce short-gamma event losses
  not increase worst event-day loss
  pass in at least 2 walk-forward folds
```

### Failure Mode

```
If samples smaller than minimum: advisory only
If gates not met: do not promote, keep current champion
```

---

## 12. Playbook Versioning Lifecycle

### Lifecycle States

```
development → challenger → champion → deprecated → rollback
```

### Semver Format

```
fomc_playbook v1.2.3
cpi_playbook v1.0.0
opex_playbook v1.1.0
unscheduled_event_playbook v1.0.0
```

### Per-Decision Logging

```
event_id
event_class
event_window
playbook_name
playbook_version
constraint_applied
event_playbook_cap
```

### Promotion Requirements

```
challenger → champion requires:
  replay validation against prior champion
  no worsening of worst event-day loss
  no increase in false-restriction cost beyond threshold
  operator approval
```

### Minimum Sample Sizes

```
minor wording / logging change:
  2+ historical event days where output differs is acceptable

binding rule change:
  6+ historical event days preferred
  otherwise challenger remains advisory only
```

### Rollback Protocol

```
operator can rollback immediately
rollback creates incident record
previous champion restored
postmortem REQUIRED before re-promotion
```

---

## 13. Interaction With Item 12 (Dynamic Capital Allocation)

### Relationship

```
Item 12 allocates capital across allowed opportunities.
Item 11 restricts what is allowed on event days.
```

### Priority Rule

```
Item 12 cannot allocate around an Item 11 block.
event_playbook_cap feeds into Item 12 max_daily_risk_budget
```

### Example

```
FOMC release day:
  Item 12 may want high allocation (volatility opportunity)
  Item 11 says no entries during release window AND no neutral 
    short gamma pre-release
  Item 11 wins
```

---

## 14. V0.4 Ship Scope

### Required for V0.4

```
1. CREATE TABLE event_calendar (binding events with required fields)
2. CREATE TABLE playbook_versions (versioned playbook configs)
3. CREATE TABLE playbook_decisions (audit log per decision)
4. backend/event_playbook_engine.py (main orchestrator)
5. backend/event_calendar_loader.py (official source ingestion)
6. backend/unscheduled_detector.py (market_dislocation_score + triggers)
7. backend/playbook_constraint_applier.py (final arbiter integration)
8. backend/holiday_calendar_overlay.py (early close handling)
9. FOMC, CPI, NFP, OpEx playbooks (binding)
10. PCE, FOMC minutes playbooks (advisory)
11. unscheduled_event_playbook (binding)
12. Earnings context computer (advisory)
13. Item 4 replay validation runs for all binding playbooks
14. Operator playbook review UI
```

### V0.4 Defers

```
- Russell rebalance playbook
- Treasury auction playbook
- VIX expiration playbook
- Earnings-season aggregate playbook
- Event-specific Opportunity Lean expansion
```

### Never Build

```
- Event-direction prediction (Items 5, 6, 8 own this)
- Override authority that bypasses constitutional caps
- Hand-coded micro-windows that overfit to specific event memories
- Vendor-only calendar sources without official confirmation path
```

---

## 15. ROI Priority

### Most Load-Bearing

```
1. Unscheduled event playbook (Iran-day prevention)
2. FOMC playbook (highest-impact scheduled event)
3. Holiday early-close handling (operational correctness)
4. CPI/NFP playbook (frequent + high-impact)
```

### Nice-to-Have

```
- PCE/GDP advisory playbooks
- OpEx playbook (lower variance vs FOMC)
- Earnings context effects
- Long-weekend Friday constraints
```

---

## 16. Final Architectural Statement

**Item 11 prevents structurally bad timing. It does NOT predict event direction.**

ROI comes from avoiding structurally bad timing — selling neutral short gamma before known release windows, trading during quote-dislocation windows, or trusting ordinary-day rules during OpEx/quad flow distortion.

Directional opportunity still belongs to Item 5 (vol fair-value EV) + Item 6 (meta-labeler utility filter) + Item 8 (OPRA flow confirmation), under Item 11's constraints.

The composition pattern — Item 11 as additional constraint in the final arbiter min() — preserves the architectural commitment that no single component can increase risk. Items 1, 5, 6, 8 generate signal quality; Item 11 enforces structural caution; the arbiter takes the most restrictive of all signals.

**Item 11's value is preventing the system from making structurally dumb trades on event days.** The ~30-50 event days per year include the highest-leverage failure modes (Iran-day-style unscheduled events, FOMC release dislocations, OpEx flow distortions). Avoiding these failure modes is more valuable than capturing marginal event-day alpha.

---

*Spec produced through GPT-5.5 Pro Round 2 + Items 1-10 dependencies + Claude verification + GPT verification accept on 2026-04-26. Locked after one full audit round plus verification. Constraint layer for V0.4.*
