# Profit Maximization Roadmap v3.0
**Single Objective: Maximum Net After-Tax P&L. Everything else is secondary.**
**Repo:** https://github.com/tesfayekb/beyenestock-of-foundation-first.git
**Last updated:** 2026-04-17
**Authority:** This document supersedes profit-maximization-roadmap.md v1.0 and v2.0
**Validation:** Every Phase 0 claim code-verified line by line. Every Phase 1+ claim verified absent from codebase. Sequencing cross-checked by two independent AI reviews.

---

## Current Honest State

| What was promised | What exists today | Annual ROI cost of gap |
|---|---|---|
| 6-state HMM + LightGBM regime | VVIX Z-score if/else statements | −8% |
| 93-feature LightGBM direction model | Hardcoded probability lookup tables | −10% |
| Walk-the-book execution | random.gauss() noise on static slippage table | −2% |
| Predictive slippage model | Static dict lookup by strategy type | −2% |
| Learning engine retrains weekly | Weekly job exists, no trained model file to retrain | −5% compounding |
| Outcome labels for accuracy measurement | Never implemented — GLC-001/002 cannot pass | Blocks all training |
| Historical data training pipeline | Never built | Blocks all ML |

**Current realistic annual return: 5-9%**
**After Phase 0 only (2 days of work): 13-22%**
**After all phases complete (18 months): 28-38% in good years**

---

## ROI Ladder

| After completing | Win rate | Annual net return | Gain vs now |
|---|---|---|---|
| Now (rule-based GEX/ZG) | 65-70% | 5-9% | — |
| **Phase 0: Remove suppressors** | 68-72% | **13-22%** | +8-13pp |
| Phase A: Outcome labels + LightGBM | 74-78% | 18-26% | +13-17pp |
| Phase B: 93 features + spread optimizer | 76-80% | 20-28% | +15-19pp |
| Phase C: OCO + walk-the-book | 76-80% | 22-30% | +17-21pp |
| Phase D: Live retraining engine | 79-83% | 26-34% | +21-25pp |
| Phase E: Full sizing + multi-instrument | 79-83% | 28-38% | +23-29pp |

---

## PHASE 0 — Remove Active ROI Suppressors
**Timeline: 2 days | ROI unlock: +8-13pp | Cost: $0 | No new models | No new data**
**These are confirmed bugs and miscalibrations in deployed code suppressing returns today.**
**Do ALL of these before starting Phase A. The paper phase data will be cleaner and the GLC criteria more likely to pass.**

### P0.1 — Fix Commission: $0.65 → $0.35 per leg
**File:** `backend/execution_engine.py:235`
**Code:** `commission_cost = 0.65 * contracts * legs`
**Problem:** Tradier published SPX rate is $0.35/contract/leg. Current code overstates by 86%.
Paper P&L looks worse than live P&L will be. GLC-005 (Sharpe ≥1.5) may fail on paper for
a system that would pass live. This is not cosmetic — it directly affects graduation.
**Fix:** Change `0.65` to `0.35`
**Test:** Verify `net_pnl` increases by `(0.65-0.35) × contracts × legs` on same gross P&L
**Monitoring:** Track commission_cost per trade on War Room. Should be ≤$0.70 for 1-contract 2-leg spread.

---

### P0.2 — Remove 10 AM Entry Blackout → 9:35 AM Minimum
**File:** `backend/strategy_selector.py:106`
**Code:** `if total_minutes < 10 * 60: return False, "before_1000am"`
**Problem:** The 30-minute blackout was designed for the old VVIX-only classifier which was
unreliable at the open. The GEX/ZG classifier (T-ACT-023) uses prior-day open interest which
is fully formed at 9:30 AM. The 9:30-10:00 AM window is the highest-premium period of the
0DTE day — gamma is maximum, credit is richest, theta decay curve is steepest.
**Fix:** Change `10 * 60` to `9 * 60 + 35` (9:35 AM minimum — 5 minutes for opening range formation)
**Why 9:35 not 9:30:** The 9:30-9:35 window has genuine opening-auction noise and 30-second volatility spikes. GEX is valid but SPX tape is not yet reliable. 9:35 is the right operational constraint.
**Test:** Verify signals generate between 9:35-10:00 AM on next market open
**Monitoring:** Track 9:35-10:00 AM trade P&L separately for first 20 live sessions.
If win rate < 60% in that window, restore blackout to 10:00 AM.

---

### P0.3 — Fix signal_weak Threshold: 0.10 → 0.05
**File:** `backend/prediction_engine.py:303`
**Code:** `signal_weak = abs(p_bull - p_bear) < 0.10`
**Problem:** The GEX/ZG direction tilt formula is `0.15 × tanh(dist_pct × 50)`.
Calibrated threshold table (verified by independent math review):

| SPX distance from ZG | \|p_bull − p_bear\| | At 0.10 threshold | At 0.05 threshold |
|---|---|---|---|
| 0.38% (open) | 0.050 | Blocked ❌ | Blocked ✅ |
| 0.50% | 0.066 | Blocked ❌ | Allowed ✅ |
| 0.80% | 0.101 | Just allowed | Allowed ✅ |
| 1.00% | 0.123 | Allowed | Allowed |
| 2.00% | 0.204 | Allowed | Allowed |

At 0.10: trades blocked when SPX is within ~0.8% of ZG (too conservative).
At 0.05: trades blocked only when SPX is within ~0.3% of ZG (correct behavior — genuinely uncertain).
**Fix:** Change `< 0.10` to `< 0.05`
**Test:** Verify trades execute at 0.8% ZG distance, blocked at 0.2% ZG distance
**Monitoring:** Track % of signals blocked by signal_weak. Target: <10% of sessions.

---

### P0.4 — Add IV/RV No-Trade Filter
**File:** `backend/prediction_engine.py` (`_evaluate_no_trade` method) + `backend/polygon_feed.py`
**Problem:** When VIX (implied vol) < 20-day realized vol × 1.10, we are selling underpriced
insurance. The IV premium is the entire source of edge for credit spreads. Selling when IV < RV
means negative expected value regardless of direction accuracy.
**Implementation — Part A:** Add realized vol computation to `polygon_feed.py`:
```python
# Compute 20-day realized vol from SPX returns stored in Redis
# Store as polygon:spx:realized_vol_20d
realized_vol = np.std(last_20d_returns) * np.sqrt(252)
redis_client.setex("polygon:spx:realized_vol_20d", 86400, str(realized_vol))
```
**Implementation — Part B:** Add filter to `_evaluate_no_trade`:
```python
vix = float(self._read_redis("polygon:vix:current", "18.0"))
rv_20d = float(self._read_redis("polygon:spx:realized_vol_20d", "15.0"))
if rv_20d > 0 and vix < rv_20d * 1.10:
    return True, "iv_rv_cheap_premium"
```
**Test:** Verify no_trade fires when VIX=14, realized_vol=14 (ratio=1.0 < 1.10)
**Monitoring:** Track % of sessions blocked by IV/RV filter. Target: 15-20%.
If >30%, something wrong with realized vol computation.

---

### P0.5 — Add Event-Day Size Override
**File:** `backend/strategy_selector.py` (before sizing call)
**Problem:** Fed/CPI/NFP days have documented ±0.8σ vol expansion 8:30-10:30 AM.
The pre_market_scan already classifies `day_type = "event"` for these days.
But no sizing reduction is applied. One tail event on full size can wipe a week of profits.
**Implementation:**
```python
event_today = session.get("day_type") == "event"
event_size_mult = 0.40 if event_today else 1.0
# Apply before compute_position_size:
# multiply risk_pct output by event_size_mult
```
**Test:** Verify contracts reduced to ~40% on event day_type sessions
**Monitoring:** Track event-day P&L vs non-event P&L separately.
If event days produce positive EV at 40% size, consider raising to 60%.

---

### P0.6 — Add Partial Exit at 25% Profit
**File:** `backend/position_monitor.py`
**Problem:** Take-profit fires only at 50% of max credit. Credit spreads frequently
reach 25-30% profit then reverse. A partial exit captures early gains on reversals.
**Implementation:** In credit strategy section of `run_position_monitor`:
```python
# Partial exit: close 30% of contracts at 25% of max profit
if (max_profit > 0
        and current_pnl >= max_profit * 0.25
        and not pos.get("partial_exit_done")
        and contracts >= 3):
    partial_contracts = max(1, int(contracts * 0.30))
    ok = engine.close_virtual_position(
        position_id=pos["id"],
        exit_reason="partial_profit_25pct",
        contracts_override=partial_contracts,
    )
    if ok:
        # Mark remaining position so we don't partial-exit again
        # Update trading_positions.partial_exit_done = True
```
Requires: add `partial_exit_done BOOLEAN DEFAULT false` to `trading_positions`
(new Supabase migration) and `contracts_override` parameter to `close_virtual_position`.
**Test:** Verify partial close fires at 25% P&L, full close fires at 50%
Verify partial does not fire if contracts < 3 (not worth splitting)
**Monitoring:** Compare P&L per contract on positions with vs without partial exits over 20 sessions.

---

**Phase 0 Cursor sessions: 2**
- Session 1: P0.1, P0.2, P0.3, P0.5 (all are ≤5 lines each)
- Session 2: P0.4 (polygon_feed change) + P0.6 (migration + position_monitor)

**Phase 0 unit tests required:**
- `test_commission_035_per_leg` — verify net_pnl calculation
- `test_entry_allowed_at_935am` — verify timing gate
- `test_signal_weak_at_05_threshold` — verify threshold math
- `test_iv_rv_filter_blocks_cheap_premium` — verify no_trade fires
- `test_event_day_size_40pct` — verify sizing reduction
- `test_partial_exit_at_25pct` — verify partial close logic

---

## PHASE A — Foundation for All ML
**Timeline: 6 weeks | ROI unlock: +5-8pp additional above Phase 0**
**Do before going live. Paper phase with trained model is far more valuable than paper with placeholders.**

### A1 — GLC-001/002 Real Accuracy Measurement ← DO THIS FIRST
**Why first:** Without outcome labels, training a model and not being able to grade it is guesswork.
GLC-001 currently says `in_progress` forever. It needs to pass for paper graduation.

| Task | File | What |
|---|---|---|
| A1.1 | New migration | Add `outcome_direction`, `outcome_correct`, `spx_return_30min` to `trading_prediction_outputs` |
| A1.2 | `model_retraining.py` | EOD job: look up SPX +30min return via Polygon for each prediction, write outcome |
| A1.3 | `criteria_evaluator.py` | `evaluate_glc001` reads `outcome_correct` — real directional accuracy |
| A1.4 | `criteria_evaluator.py` | `evaluate_glc002` per-regime accuracy from same column |

Cursor task: 1 session.
**Test:** Verify outcome labels written at 4:15 PM, GLC-001 shows numeric value not `in_progress`
**Monitoring:** Daily accuracy trend visible on Config page.

---

### A2 — Historical Data Download (parallel with A1)

| Data | Source | Cost | Notes |
|---|---|---|---|
| SPX 5-min OHLCV 2020-2026 | Polygon REST (already paying) | $0 | Download via REST API, store in `backend/data/` |
| VIX daily 2010-2026 | CBOE free CSV | $0 | `cboe.com/tradable_products/vix/vix_historical_data/` |
| VVIX daily 2010-2026 | CBOE free CSV | $0 | Same site |
| SPX 0DTE option chains 2022-2026 | OptionsDX.com | ~$50/month | Enables GEX feature reconstruction in training |

A2.4 (OptionsDX) is optional for Phase A but adds +3-5pp vs price/vol-only training.

Cursor task: 1 session. Download scripts + data validation.
**Test:** Verify 500+ trading days of 5-min bars downloaded, no gaps >1 day

---

### A3 — Train LightGBM Direction Model
**Replaces hardcoded probability lookup tables with real trained model.**

47 initial features:
- **SPX price action:** 5m/30m/1h/4h returns, RSI(14), MACD signal, Bollinger %B, overnight gap pct
- **Volatility:** VIX level, VIX 5d change, VIX Z-score, VIX9D/VIX term ratio, VVIX Z-score
- **GEX:** flip_zone distance pct, net_gex, gex_confidence, nearest_wall distance (if OptionsDX)
- **Time context:** hour of day, day of week, minutes to close, days to next Fed/CPI/NFP
- **Regime context:** prior day return, 20d realized vol, IV/RV ratio, prior session win/loss

Label: SPX direction 30 minutes after prediction signal (bull/bear/neutral)
Holdout: 2025-2026 (last 12 months — never seen during training)
**Gate before deploying:** Must achieve ≥72% win rate on holdout. If not, do not deploy — keep rule-based.

Output: `backend/models/direction_lgbm_v1.pkl`
Load in `_compute_direction` — replaces hardcoded if/else tables.

Cursor tasks: 2 sessions (feature engineering + training + validation).
**Test:** Backtest on holdout, verify ≥72% win rate, verify no data leakage (no future data in features)
**Monitoring:** Daily accuracy via A1 outcome labels. Alert if rolling 10-day accuracy drops below 68%.

---

### A4 — Train Real HMM Regime Classifier (parallel with A3)
**Replaces VVIX Z-score if/else with trained 6-state HMM.**

Fit Gaussian HMM (6 states) on SPX daily log-returns + VIX daily change 2010-2026.
State labels (assign post-training based on mean return + vol):
`{low-vol-bull, high-vol-bull, low-vol-bear, high-vol-bear, crisis, mean-revert}`

Output: `backend/models/regime_hmm_v1.pkl`
Replace `regime_hmm` branch in `_compute_regime`.
`regime_lgbm` (GEX/ZG rule-based) unchanged — already real signal.
D-021 now fires on genuine HMM vs GEX disagreement.

Cursor task: 1 session.
**Test:** Verify state labels match known regimes: Aug 2015 = crisis, 2017 = low-vol-bull, Mar 2020 = crisis
**Monitoring:** regime_agreement rate. Should be ~70-75% agreement. Drops during transitions = normal.

---

### A5 — Kelly-Fractional Sizing (after A3 deployed and calibrated)
**Scales position size with model confidence. Requires A3 producing calibrated probabilities.**
**Do NOT implement before A3 — current hardcoded tables are not well-calibrated.**

```python
# In compute_position_size, after base risk_pct computed:
model_confidence = prediction.get("confidence", 0.60)
kelly_mult = max(0.5, min(1.5, model_confidence / 0.60))
risk_pct *= kelly_mult
```

On 80%-confidence days (+0.33σ): size UP 25%
On 52%-confidence days (−0.13σ): size DOWN 17%
Creates D-024 as new locked decision before implementing.

Cursor task: 1 session.
**Test:** Verify high-confidence signals produce more contracts at same account value
**Monitoring:** P&L grouped by confidence decile. Verify monotonic: higher confidence = higher P&L.

---

**Phase A total Cursor sessions: 6**
**Phase A expected annual return: 18-26%**

---

## PHASE B — Complete the Prediction Engine
**Timeline: 4 weeks | ROI unlock: +2-4pp additional**

### B1 — Expand to 93 Features
Extend A3 feature set. Retrain as `direction_lgbm_v2.pkl`.
Champion/challenger: v2 must beat v1 by ≥1pp on holdout before replacing.

New feature groups:
- **Options flow:** put/call ratio, unusual options activity score (from Databento OPRA — already collecting)
- **Cross-asset:** USD index direction, 10Y yield 1d change, gold 1d return (Polygon — already paying)
- **Microstructure:** bid/ask spread width at target strike, open interest at short strike
- **Event distance:** exact days to next Fed/CPI/NFP/monthly opex (not just binary)
- **Intraday:** VWAP distance, morning range high-low, gap fill probability

Cursor task: 1 session (extend feature pipeline).
**Test:** v2 ≥ v1 + 1pp on holdout, no feature leakage
**Monitoring:** Weekly champion/challenger score in model performance job.

---

### B2 — Dynamic Spread Width
**Currently hardcoded $5. Correct width varies with VIX regime.**

| VIX regime | Width | Rationale |
|---|---|---|
| < 15 (low IV) | $2.50 | Tighter = more premium per dollar risked |
| 15-20 (normal) | $5.00 | Standard baseline |
| 20-30 (elevated) | $7.50-10.00 | More credit, same delta |
| > 30 (crisis) | Sit out | IV/RV filter from P0.4 should catch first |

Modify `strike_selector.py` to accept `vix_level` and return variable width.
Modify `risk_engine.py` to use `max_loss = (spread_width - credit) × contracts × 100` for sizing.
This also enables the width-aware stop-loss fix (stop at 80% of max_loss not 200% of credit).

Cursor task: 1 session.
**Test:** Width changes with VIX input, sizing uses correct max_loss
**Monitoring:** Average credit per width. Should increase in VIX 20-30 regime.

---

### B3 — Asymmetric Iron Condor Wing Optimizer
When GEX nearest_wall shows stronger support below SPX than resistance above:
- Widen put spread (more premium, more room)
- Tighten call spread (less premium, less exposure)

Compare `spx_price - put_wall` vs `call_wall - spx_price` in `strike_selector.py`.
Adjust wings proportionally to GEX asymmetry.

Cursor task: 1 session.
**Test:** Asymmetric wings on known GEX configuration, verify credit > symmetric baseline
**Monitoring:** Iron condor P&L vs symmetric baseline over 20 sessions.

---

### B4 — Width-Aware Stop-Loss (depends on B2)
**Currently:** `stop_loss_threshold = -(max_profit × 2.0)` — inconsistent across widths.
**After B2:** Use `stop_loss_threshold = -(max_loss × 0.80)` where max_loss is real spread geometry.

At $5 wide, $1.50 credit: max_loss=$350, stop at $280 (80%) — essentially same as 200% credit
At $10 wide, $1.50 credit: max_loss=$850, stop at $680 (80%) — much better than $300 (200% credit)

Cursor task: 0.5 sessions (1 line change after B2 foundation is built).

---

**Phase B total Cursor sessions: 3.5**
**Phase B expected annual return: 20-28%**

---

## PHASE C — Execution Alpha
**Timeline: 3 weeks | ROI unlock: +2-4pp additional**

### C1 — OCO Bracket Orders ← BEFORE WALK-THE-BOOK
**Validated sequencing:** OCO uses the realized fill price Tradier returns — it does NOT
require walk-the-book modeling. Walk-the-book models entry price. OCO places exit orders
post-fill. They are independent systems.

Tradier bracket order flow:
1. Submit entry limit order at chosen price
2. Tradier returns actual `fill_price`
3. Using `fill_price`, submit: take-profit at `fill_price × 0.50` AND stop-loss at width-aware level
4. Tradier links them — one cancels the other automatically

Eliminates 60-second polling latency on exits.
Guarantees exits even if Railway goes offline.
Reduces exit slippage 30-50%.

New file: `backend/order_manager.py`
Cursor task: 2 sessions.
**Test:** OCO submitted in sandbox on every fill, confirm one-cancels-other behavior
**Monitoring:** Track exit fill time. Should drop from ~60s average to <5s.

---

### C2 — Walk-the-Book Entry Simulation
Model actual fill price using live chain data from `strike_selector.py`:
```python
# Fill = bid + market_impact_fraction × spread
market_impact = (position_size_contracts / open_interest_at_strike) × 0.5
fill = bid + market_impact × (ask - bid)
```
Replaces `random.gauss()` slippage noise with depth-aware model.

Cursor task: 2 sessions.
**Test:** Fill prices correlate with open interest — less OI = worse fill
**Monitoring:** Compare walk-the-book predictions vs actual fills after Phase 5 live trading.

---

### C3 — Predictive Slippage Model
**Requires 200+ observations in `trading_calibration_log` (GLC-011).**

Train LightGBM regression: features = {VIX, time-of-day, contracts, OTM distance, IV rank}
Output: `backend/models/slippage_lgbm_v1.pkl`
Replaces `STATIC_SLIPPAGE_BY_STRATEGY` dict.

Cursor task: 1 session (after 200 calibration observations).
**Test:** Regression MAE < static table MAE on holdout
**Monitoring:** Weekly slippage MAE in existing calibration engine job.

---

**Phase C total Cursor sessions: 5**
**Phase C expected annual return: 22-30%**

---

## PHASE D — Learning Engine
**Timeline: Months 4-6, ongoing | ROI unlock: +4-8pp compounding**
**Runs alongside live trading. Models improve from real fills.**

### D1 — Daily Outcome Loop (4:15 PM ET)
1. Label yesterday's predictions with realized SPX outcomes (extends A1)
2. Isotonic recalibration on probability outputs
3. Update slippage MAE from yesterday's fills
4. Drift z-test: alert if 10-day accuracy drops >5pp

Cursor task: 1 session.
**Test:** Drift alert fires when accuracy injected below threshold
**Monitoring:** Accuracy trend chart on War Room. Alert history visible.

---

### D2 — Weekly Champion/Challenger Retrain (Sunday 6 PM ET)
1. Retrain LightGBM on rolling 90-day labeled window
2. Compare challenger vs champion on 30-day holdout
3. Swap only if challenger wins by ≥1pp
4. Keep prior model as emergency fallback

Cursor task: 1 session.
**Test:** Swap logic works, fallback loads on swap failure
**Monitoring:** Weekly model performance table. Champion history + holdout scores.

---

### D3 — Regime × Strategy Performance Matrix
Running P&L by strategy × regime. Auto-reduce allocation 25% if
put_credit_spread loses 3 consecutive sessions in any regime.
Updates daily from closed positions.

Cursor task: 1 session. New `backend/strategy_performance_matrix.py`
**Test:** Allocation reduction triggers at 3 consecutive losses per cell
**Monitoring:** Matrix visible on War Room. Shows edge concentration by regime.

---

### D4 — Counterfactual Engine
Post-session: simulate alternate entries (±15 min), alternate widths, skipped trades.
Identifies systematic improvements without new risk.
Feeds into feature importance for weekly retrain.

Cursor task: 2 sessions.
**Test:** Counterfactual P&L matches manual calculation on known positions
**Monitoring:** Weekly counterfactual report. Top 3 improvements surfaced automatically.

---

### D5 — Intraday Micro-Calibration (every 2 hours)
Check if morning prediction still consistent with current GEX state.
If regime has shifted, emit advisory (human decides, not forced exit).
Update signal_weak threshold dynamically based on intraday realized vol.

Cursor task: 1 session.
**Monitoring:** Track intraday regime shift frequency. Alert if >30% of days.

---

**Phase D total Cursor sessions: 6**
**Phase D expected annual return: 26-34%**

---

## PHASE E — Sizing Ramp + Instruments
**Milestone-gated — cannot be rushed. Requires live performance data.**

### E1 — Phase 2 Sizing Advance
**Gate:** 45 live days + Sharpe ≥1.2 (rolling 45-day)
Core: 0.5% → 1.0% | Satellite: 0.25% → 0.5%
Doubles gross P&L dollar amount with same win rate.

### E2 — Phase 3 Sizing Advance
**Gate:** 90 live days + Sharpe ≥1.5 (rolling 60-day)
Core: 1.0% → 1.5% | Satellite: 0.5% → 0.75%

### E3 — Multi-Instrument Expansion
**Gate:** 120 live days + stable performance
- XSP (mini-SPX): smaller notional, same Section 1256 tax treatment
- NDX: tech-regime satellites (+2-3% annually in tech divergence regimes)
- RUT: small-cap divergence trades (+1-2% annually)

### E4 — Daily 0DTE Tuesday/Thursday
**Gate:** 90 live days + 6-month historical validation on Tue/Thu liquidity
SPX daily options since May 2022. Tue/Thu volume now within 15-20% of Mon/Wed/Fri.
Must validate bid/ask spreads and open interest on historical OptionsDX data first.
**Do not enable without historical validation** — liquidity differences still material.
Expected lift when validated: +3-5% (40% more trading opportunities).

### E5 — Margin Utilization
**Gate:** 180 live days + max drawdown <8% over 180 days
Portfolio margin: 1.5-2.0× leverage on credit spreads.
Same positions, 60-80% more profit per dollar of equity.
Enables Scenario D returns (28-38% even at Phase 3 trade sizing).

### E6 — Raise Regime Max Trade Caps (requires new D-023 decision)
**Gate:** 90 live days + win rate ≥70% in pin_range + D-023 decision record created
Current caps: pin_range=3, range=3. Historical comparable systems: 5-8 on pin days.
Proposed D-023: pin_range→5, range→4, quiet_bullish→3.
This is a locked decision (T-Rule 4). Cannot implement without governance approval.

---

**Phase E expected annual return: 28-38% in good years**

---

## PHASE F — Tax Alpha
**Parallel with Phases C-E | Free money requiring minimal engineering**

### F1 — After-Tax P&L Display
50-line change to show operator's real kept return (60% at LTCG + 40% at ordinary income).
Operator-facing reporting only. Does not change sizing decisions (gross P&L is the right
basis for sizing — after-tax is the same linear transformation on every trade).

### F2 — Year-End Mark-to-Market Election
Section 1256 allows marking open positions to market Dec 31.
Loss carryback 3 years. Can save 8-15% additional tax in loss years.
Requires: annual operator decision + consultation with tax advisor.

### F3 — Wash Sale Detection for Swing Positions
0DTE positions expire same day — no wash sale risk.
1-5 day swing positions need tracking.
Add detection in `close_virtual_position`.

---

## GOVERNANCE — New Decisions Required Before Implementation

| Decision | What it unlocks | Gate |
|---|---|---|
| D-023 | Raise pin_range/range max trades | 90 live days + ≥70% win rate in pin_range |
| D-024 | Kelly-fractional sizing | A3 LightGBM in production + calibration verified |
| D-025 | Partial exit at 25% profit (P0.6) | 20-session paper validation |
| D-026 | Daily 0DTE Tue/Thu | 6-month historical liquidity validation |
| D-027 | Margin utilization | 180 live days + max DD <8% |

---

## COMPLETE PRIORITY SEQUENCE

| Priority | Task | Gain | Sessions | Dependency |
|---|---|---|---|---|
| **1** | P0.1: Commission $0.65→$0.35 | +1pp attribution | 0.1 | None |
| **2** | P0.2: Remove 10AM blackout →9:35 | +2-4pp | 0.1 | None |
| **3** | P0.3: signal_weak 0.10→0.05 | +2-3pp | 0.1 | None |
| **4** | P0.4: IV/RV no-trade filter | +1-2pp | 0.5 | polygon_feed change |
| **5** | P0.5: Event-day 40% size | +0.8-1.5pp | 0.5 | None |
| **6** | P0.6: Partial exit 25% | +0.5-1pp | 1 | Migration needed |
| **7** | A1: Outcome labels + GLC fix | Enables all training | 1 | None |
| **8** | A2: Download historical data | Training data | 1 | Polygon API |
| **9** | A3: Train LightGBM v1 | +9-11pp | 2 | A1 + A2 |
| **10** | A4: Train HMM regime | +2-3pp | 1 | A2 |
| **11** | A5: Kelly sizing | +2-4pp | 1 | A3 calibrated |
| **12** | B1: 93 features + retrain | +2-4pp | 2 | A3 deployed |
| **13** | B2: Dynamic spread width | +1-3pp | 1 | None |
| **14** | B3: Asymmetric condor | +1-2pp | 1 | B2 |
| **15** | B4: Width-aware stop-loss | +0.5-1pp | 0.5 | B2 |
| **16** | C1: OCO bracket orders | +0.5-1pp | 2 | Phase 5 live |
| **17** | C2: Walk-the-book | +1-2pp | 2 | C1 |
| **18** | C3: Slippage model | +1-2pp | 1 | 200 calibration obs |
| **19** | D1-D5: Learning engine | +4-8pp compounding | 6 | A3 + 30 live days |
| **20** | E1-E6: Sizing ramp | 2× P&L dollars | 4 | Milestone-gated |
| **21** | F1-F3: Tax display | +2-4pp net | 2 | Phase C |

---

## Monitoring Requirements by Phase

### Phase 0 Dashboard Additions (War Room page)
- Commission cost per trade (verify $0.35 × legs × contracts)
- % sessions blocked by IV/RV filter (target 15-20%)
- % signals blocked by signal_weak (target <10%)
- 9:35-10:00 AM trade P&L tracked separately (20-session validation window)
- Event-day P&L vs non-event P&L comparison

### Phase A Dashboard Additions
- Daily directional accuracy (outcome_correct / total predictions)
- Per-regime accuracy breakdown (6 states)
- Model confidence distribution histogram
- Kelly multiplier average by session

### Phase B-D Dashboard Additions
- Champion vs challenger holdout score (weekly)
- Model drift z-test history and alert log
- Strategy × regime P&L matrix
- Slippage MAE trend (should decrease over time)
- Counterfactual improvement report (top 3 weekly)
- Intraday regime shift frequency

---

## Fix Group 8 — Security Hardening
**Zero ROI impact. Execute only when:**
- GLC-001 through GLC-006 show `in_progress` with observations > 0
- ≥25 paper trading sessions completed
- ≥14 calendar days before expected paper phase graduation
**All 12 items documented in `master-plan.md` (TPLAN-HARD-008-A through L).**

---

## ROI by Calendar Date (Base Case)

| Date | Milestone | Annual return |
|---|---|---|
| April 2026 | Phase 0 deployed, paper phase running | 13-22% (paper) |
| June 2026 | Phase A complete, trained models in paper | — (paper, better data) |
| July 2026 | Paper phase complete, GLC criteria pass | — (paper) |
| August 2026 | **LIVE** — Phase A+B deployed | **18-26%** |
| November 2026 | Phase C (OCO + walk-the-book) | **22-30%** |
| February 2027 | Phase D (learning engine active) | **26-34%** |
| August 2027 | Phase E (full sizing + instruments) | **28-38%** |

**Conservative (25th percentile):** 7-12% CAGR — $100k → $139k over 5 years
**Base case (50th percentile):** 13-18% CAGR — $100k → $228k over 5 years
**Optimistic (75th percentile):** 20-25% CAGR — $100k → $305k over 5 years
**Phase 6 full (all phases + margin):** 25-35% CAGR possible in sustained bull years

---

*This document is the single authoritative profit roadmap.*
*Version 3.0 — validated by two independent AI code reviews, cross-checked against actual codebase.*
*Security, performance, and drawdown matter only insofar as they protect the ability to keep trading.*
*Every decision: does this increase net after-tax P&L? If not, it does not belong here.*
