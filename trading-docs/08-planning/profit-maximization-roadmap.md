# Profit Maximization Roadmap
**Single Objective: Maximum Net After-Tax P&L**
**Repo:** https://github.com/tesfayekb/beyenestock-of-foundation-first.git
**Last updated:** 2026-04-17

---

## Current Honest State

| What was promised | What exists today | ROI impact of gap |
|---|---|---|
| 6-state HMM + LightGBM regime | VVIX Z-score if/else | −8% annually |
| 93-feature LightGBM direction | Hardcoded probability tables | −10% annually |
| Walk-the-book execution | random.gauss() noise on static table | −2% annually |
| Predictive slippage model | Static lookup by strategy type | −2% annually |
| Learning engine retrains weekly | Job exists, no model to retrain | −5% annually (compounding) |
| Outcome labels for accuracy | Never implemented | Blocks all training |
| Historical data training | Never done | Blocks all ML |

**Current realistic annual return: 5-9%**
**Target annual return (all gaps closed): 28-38% in good years**

---

## ROI Ladder — What Each Phase Adds

| After completing | Win rate | Annual net return | Cumulative gain vs now |
|---|---|---|---|
| Now (Phase 2 rule-based) | 65-70% | 5-9% | baseline |
| Phase A: Outcome labels + historical LightGBM | 74-78% | 14-20% | +9-11pp |
| Phase B: Real HMM + full feature set | 76-80% | 18-24% | +13-15pp |
| Phase C: Walk-the-book execution | 76-80% | 20-26% | +15-17pp |
| Phase D: Live retraining + learning engine | 79-83% | 24-32% | +19-23pp |
| Phase E: Full sizing + margin + satellites | 79-83% | 28-38% | +23-29pp |

---

## PHASE A — Foundation for All ML (Do Before Going Live)
**Timeline: ~6 weeks | ROI unlock: +9-11pp (5-9% → 14-20%)**
**These must be done BEFORE the 45-day paper phase completes.**

### A1 — Fix Group 11: Outcome Labels (Week 1)
**The prerequisite for all ML training. Without this nothing else trains.**

| Task | What it builds | File |
|---|---|---|
| A1.1 | EOD job reads each prediction from yesterday | `model_retraining.py` |
| A1.2 | Looks up SPX close vs SPX at prediction time | `model_retraining.py` |
| A1.3 | Writes `outcome_direction`, `outcome_correct`, `spx_return_30min` back to `trading_prediction_outputs` | `model_retraining.py` |
| A1.4 | New Supabase migration: add outcome columns to `trading_prediction_outputs` | `supabase/migrations/` |
| A1.5 | Backfill historical SPX close prices via Polygon API for past predictions | `model_retraining.py` |

Cursor task: 1 session. New migration + ~100 lines Python.

---

### A2 — Historical Data Download (Week 1, parallel with A1)
**Downloads 2 years of training data using APIs you already pay for.**

| Task | Data | Source | Cost |
|---|---|---|---|
| A2.1 | SPX 5-minute OHLCV bars, 2020-2026 | Polygon.io REST (already paying) | $0 |
| A2.2 | VIX daily history 2010-2026 | CBOE free CSV download | $0 |
| A2.3 | VVIX daily history 2010-2026 | CBOE free CSV download | $0 |
| A2.4 | SPX 0DTE option chain history 2022-2026 | OptionsDX.com | ~$50/month |
| A2.5 | Store all data in `/backend/data/historical/` | Local + Railway volume | $0 |

Note: A2.4 (OptionsDX) is optional for Phase A but enables GEX feature reconstruction.
Without it, Phase A trains on price/vol features only (still +9-11pp vs current).
With it, Phase A trains on price/vol + GEX features (additional +3-5pp).

Cursor task: 1 session. Download scripts + data pipeline.

---

### A3 — LightGBM Direction Model (Week 2-3)
**Replaces hardcoded probability tables with real trained model.**

| Task | What it builds |
|---|---|
| A3.1 | Feature engineering pipeline: 47 features from SPX OHLCV + VIX + VVIX |
| A3.2 | Label generation: SPX return over next 30 minutes → bull/bear/neutral |
| A3.3 | Train LightGBM classifier, tune hyperparameters, evaluate on holdout 2025-2026 |
| A3.4 | Save model to `backend/models/direction_lgbm_v1.pkl` |
| A3.5 | Load in `_compute_direction` — replace hardcoded tables |
| A3.6 | Backtest: verify 74%+ win rate on 2025-2026 holdout before deploying |

47 features include:
- SPX: 5m/30m/1h/4h returns, RSI, MACD, Bollinger position, overnight gap
- VIX: level, 5d change, Z-score, term structure (VIX9D/VIX)
- VVIX: Z-score (already computed)
- Time: hour of day, day of week, days to Fed/CPI/NFP
- Regime: previous day return, 20d realized vol, IV rank

Cursor tasks: 2 sessions (feature engineering + training).

---

### A4 — Real HMM Regime Classifier (Week 3, parallel with A3)
**Replaces VVIX Z-score if/else with trained 6-state HMM.**

| Task | What it builds |
|---|---|
| A4.1 | Fit Gaussian HMM (6 states) on SPX daily log-returns + VIX change 2010-2026 |
| A4.2 | Label HMM states: low-vol-bull, high-vol-bull, low-vol-bear, high-vol-bear, crisis, mean-revert |
| A4.3 | Save model to `backend/models/regime_hmm_v1.pkl` |
| A4.4 | Load in `_compute_regime` — replace VVIX if/else for `regime_hmm` branch |
| A4.5 | `regime_lgbm` branch stays GEX/ZG rule-based (already real signal) |
| A4.6 | D-021 now fires on genuine HMM vs ZG disagreement |

Cursor task: 1 session.

---

### A5 — GLC-001/002 Proper Accuracy Measurement (Week 3)
**Replaces win-rate proxy with real direction-match accuracy.**
**Required to pass paper phase and graduate to live.**

| Task | What it builds |
|---|---|
| A5.1 | `evaluate_glc001` reads `outcome_correct` from prediction outputs (built in A1) |
| A5.2 | Computes `correct / total` as real directional accuracy |
| A5.3 | `evaluate_glc002` computes per-regime accuracy using regime labels |
| A5.4 | GLC-001 can now pass (target ≥58%) or fail with real data |

Cursor task: 1 session, ~60 lines.

---

**Phase A Expected ROI: 14-20% annually**
**Phase A total Cursor sessions: 5-6**
**Phase A total cost: ~$50/month for OptionsDX (optional but recommended)**

---

## PHASE B — Complete the Prediction Engine (Months 2-3)
**Timeline: ~4 weeks | ROI unlock: +4-6pp additional (14-20% → 18-26%)**

### B1 — Expand Feature Set to 93 Features (Week 5-6)
Add features that price/vol alone cannot capture:

| Feature group | Features | Source |
|---|---|---|
| GEX features | flip_zone, nearest_wall, net_gex, gex_confidence | Redis (already computing) |
| Options flow | Put/call ratio, unusual options activity score | Databento OPRA (already have) |
| Cross-asset | Dollar index direction, 10Y yield change, gold return | Polygon (already paying) |
| Microstructure | Bid/ask spread at target strikes, open interest by strike | Tradier chain (already fetching) |
| Event calendar | Days to Fed, CPI, NFP, opex (binary flags) | Static calendar + Polygon econ |
| Intraday momentum | VWAP distance, morning range, gap fill probability | SPX 5-min bars |

Cursor task: 1 session — extend feature engineering pipeline from A3.

---

### B2 — Retrain LightGBM on Full 93-Feature Set (Week 6)
- Rebuild training dataset with all 93 features
- Tune hyperparameters via cross-validation
- Target: ≥76% out-of-sample win rate on 2025-2026 holdout
- Save as `direction_lgbm_v2.pkl`
- Deploy as champion, keep v1 as challenger

Cursor task: 1 session.

---

### B3 — Dynamic Spread Width Optimizer (Week 7)
**Currently: hardcoded $5 spread width. This leaves money on the table.**

| Market condition | Optimal spread width | Why |
|---|---|---|
| Low IV (VIX < 15) | $2.50 wide | Tighter = more premium per dollar risked |
| Normal IV (15-20) | $5.00 wide | Standard |
| High IV (20-30) | $7.50-10.00 wide | Wider = more credit, same delta |
| Crisis (VIX > 30) | Sit out or $2.50 very far OTM | Gamma risk too high |

ROI impact: +1-3% annually. Capturing correct spread width at the right IV regime is direct P&L improvement.

Files: `strike_selector.py` + `risk_engine.py`.
Cursor task: 1 session.

---

### B4 — Iron Condor Optimizer (Week 7, parallel with B3)
**Currently: iron condor wing widths are symmetric. Real edge is asymmetric.**

When GEX shows strong support below and resistance above:
- Widen the put spread (more room to run down)
- Tighten the call spread (more premium, less exposure)
- Net result: higher credit for same delta exposure

Cursor task: 1 session — modify `strike_selector.py`.

---

**Phase B Expected ROI: 18-26% annually**
**Phase B total Cursor sessions: 4**

---

## PHASE C — Execution Alpha (Month 3-4)
**Timeline: ~3 weeks | ROI unlock: +2-4pp additional (18-26% → 20-28%)**

### C1 — Walk-the-Book Execution (Week 9-10)
**Replaces `random.gauss()` with real fill price modeling.**

| Task | What it builds |
|---|---|
| C1.1 | Fetch live bid/ask/size at target strike from Tradier chain |
| C1.2 | Model: fill = mid − (position_size / open_interest) × half_spread |
| C1.3 | For paper phase: simulate using actual chain data from Tradier |
| C1.4 | For live phase: submit limit orders at computed price, not market |
| C1.5 | Track actual fill vs predicted — feed into slippage model |

Cursor task: 1-2 sessions.

---

### C2 — Predictive Slippage Model (Week 10-11)
**Replaces static lookup table with trained regression.**
**Requires 200+ observations in `trading_calibration_log` (GLC-011).**

| Feature | Why it predicts slippage |
|---|---|
| VIX level | Higher vol = wider spreads = more slippage |
| Time of day | First/last 30 min are widest |
| Contract size | Larger orders move the market |
| Strike distance from ATM | OTM options less liquid |
| IV rank | High IV rank = compressed spreads |

Training: LightGBM regression on calibration log.
Save to `backend/models/slippage_lgbm_v1.pkl`.

Cursor task: 1 session (after 200 observations).

---

### C3 — OCO Order Pre-Submission (Week 11)
**Currently: stop-loss and take-profit managed by polling. Real edge is OCO orders.**

OCO (One-Cancels-Other): submit both exit orders simultaneously at fill.
Tradier supports bracket orders. This:
- Eliminates polling latency (currently 60 seconds between checks)
- Guarantees exit at target price even if system goes offline
- Reduces slippage on exits by 30-50%

ROI impact: saves 0.3-0.8% annually from avoided adverse exits.

Files: `execution_engine.py` + new `order_manager.py`.
Cursor task: 2 sessions.

---

**Phase C Expected ROI: 20-28% annually**
**Phase C total Cursor sessions: 4-5**

---

## PHASE D — Learning Engine (Months 4-6, parallel with live trading)
**Timeline: ongoing | ROI unlock: +4-8pp additional (20-28% → 24-34%)**
**This phase runs alongside live trading — models improve from real fills.**

### D1 — Daily Outcome Loop (Week 13)
Every day at 4:15 PM ET:
1. Label yesterday's predictions with actual SPX outcomes
2. Run isotonic recalibration on probability outputs
3. Update slippage MAE
4. Run drift z-test — alert if accuracy drops >5pp in 10 days

Cursor task: 1 session — extend `model_retraining.py`.

---

### D2 — Weekly Retrain Loop (Week 14)
Every Sunday 6 PM ET:
1. Collect all labeled predictions from last 90 days
2. Retrain LightGBM on rolling window
3. Champion/challenger: compare new model vs current on holdout
4. Swap if new model wins by >1pp on holdout
5. Keep previous model as fallback

Cursor task: 1 session — extend `model_retraining.py`.

---

### D3 — Regime × Strategy Performance Matrix (Week 15)
Track which strategies outperform in which regimes:
- Running P&L × strategy × regime matrix
- If put_credit_spread loses 3 sessions in pin_range → auto-reduce allocation
- If iron_condor dominates in quiet_bullish → increase allocation
- Updates daily from closed positions

Cursor task: 1 session — new `strategy_performance_matrix.py`.

---

### D4 — Counterfactual Engine (Week 16)
After each session, simulate what would have happened with:
- Different strike widths
- Earlier/later entries
- Skipped vs traded signals

Identifies systematic P&L improvements without new risk.
Feeds back into feature importance for next weekly retrain.

Cursor task: 2 sessions.

---

### D5 — Intraday Micro-Calibration (Week 17)
Every 2 hours during market hours:
- Check if morning's prediction is still consistent with current GEX
- If regime has shifted, emit advisory (not forced exit — human decides)
- Update `signal_weak` threshold based on intraday vol realized

Cursor task: 1 session.

---

**Phase D Expected ROI: 24-34% annually**
**Phase D total Cursor sessions: 6**

---

## PHASE E — Sizing Ramp + Satellites (Months 6-18)
**Timeline: milestone-gated | ROI unlock: +4-6pp additional (24-34% → 28-38%)**
**Cannot be rushed — requires live performance data.**

### E1 — Phase 2 Sizing Advance (after 45 live days + Sharpe ≥1.2)
- Core: 0.5% → 1.0% per trade
- Satellite: 0.25% → 0.5% per trade
- ROI impact: doubles gross P&L dollar amount

### E2 — Phase 3 Sizing Advance (after 90 live days + Sharpe ≥1.5)
- Core: 1.0% → 1.5% per trade
- Satellite: 0.5% → 0.75% per trade
- Begin exploring RUT satellites (smaller notional, different liquidity)

### E3 — Multi-Instrument Expansion (after 120 live days)
- Add XSP (mini-SPX) for smaller satellite positions
- Add NDX for tech-regime satellites
- Add RUT for divergence trades (SPX vs small-cap)
- Each instrument adds ~2-3% to annual return when regime supports it

### E4 — Margin Utilization (after 180 live days + stable performance)
- Use portfolio margin to increase notional without increasing cash risk
- Target: 1.5-2.0× leverage on credit spreads
- Net effect: same positions, ~60-80% more profit per dollar of equity

### E5 — 0DTE Every Day (currently Mon/Wed/Fri only)
- SPX now has daily options (Tuesday/Thursday gaps fill in)
- Adds ~40% more trading opportunities
- Requires: real-time regime detection every morning (already built)
- Enable after learning engine has 90+ days of daily data

---

**Phase E Expected ROI: 28-38% annually in good years**
**Phase E total Cursor sessions: 3-4 (mostly gating logic)**

---

## PHASE F — Tax Alpha Maximization (Months 3-6)
**This is free money. Section 1256 is already the instrument choice. Optimize it.**

### F1 — After-Tax P&L Engine
Currently: P&L reported gross.
Build: real after-tax P&L using 60/40 rate modeling.
- Shows true ROI number you actually keep
- Guides decisions about position sizing near year-end
- Surfaces tax-loss harvest opportunities

### F2 — Year-End Mark-to-Market Election
Section 1256 allows marking open positions to market on Dec 31.
- Converts unrealized gains to recognized gains in current tax year
- Allows loss carryback to prior 3 years
- Can save 8-15% additional tax in loss years

### F3 — Wash Sale Avoidance
0DTE positions expire same day — no wash sale risk.
But swing positions (1-5 day holds) need tracking.
Build: wash sale detection in close_virtual_position.

---

## COMPLETE TASK SEQUENCE — Priority Ordered

Priority is purely by ROI per hour of effort:

| Priority | Task | ROI unlock | Cursor sessions | When |
|---|---|---|---|---|
| 1 | A1: Fix Group 11 outcome labels | Enables all training | 1 | Now |
| 2 | A2: Download historical data | Training data | 1 | Now |
| 3 | A3: Train LightGBM direction model | +9-11pp | 2 | Week 2-3 |
| 4 | A4: Train HMM regime model | +2-3pp | 1 | Week 3 |
| 5 | A5: Fix GLC-001/002 accuracy | Paper phase passes | 1 | Week 3 |
| 6 | B1-B2: 93-feature model | +4-6pp | 2 | Month 2 |
| 7 | B3: Dynamic spread width | +1-3pp | 1 | Month 2 |
| 8 | B4: Asymmetric condor wings | +1-2pp | 1 | Month 2 |
| 9 | C1: Walk-the-book | +1-2pp | 2 | Month 3 |
| 10 | C3: OCO orders | +0.5-1pp | 2 | Month 3 |
| 11 | C2: Slippage model | +1-2pp | 1 | Month 4 |
| 12 | D1-D2: Daily/weekly retrain | +3-5pp compounding | 2 | Month 4-5 |
| 13 | D3: Strategy-regime matrix | +1-2pp | 1 | Month 5 |
| 14 | D4: Counterfactual engine | +1-2pp | 2 | Month 5-6 |
| 15 | E1-E2: Sizing advance | 2× P&L dollars | 2 | After 45/90 live days |
| 16 | E3: Multi-instrument | +2-4pp | 2 | Month 8-10 |
| 17 | E5: Daily 0DTE | +3-5pp | 1 | Month 9 |
| 18 | E4: Margin utilization | +5-8pp | 2 | Month 12+ |
| 19 | F1-F3: Tax optimization | +2-4pp (free money) | 2 | Month 3-6 |

---

## Fix Group 8 — Security Hardening
**Do NOT do this until P1-P4 above are complete. Zero ROI impact.**
**Required before Phase 5 (live trading) — not before.**
All 12 items (TPLAN-HARD-008-A through L) documented in master-plan.md.
Trigger: GLC-001 through GLC-006 show in_progress + 25+ paper sessions.

---

## ROI Projection by Calendar Date

| Date | Phase complete | Annual return |
|---|---|---|
| May 2026 | Phase A complete, paper phase running with trained model | — (paper) |
| July 2026 | Paper phase complete, GLC criteria pass | — (paper) |
| August 2026 | LIVE — Phase B complete, 93-feature model | **16-22%** |
| November 2026 | Phase C complete, walk-the-book + OCO | **20-26%** |
| February 2027 | Phase D complete, learning engine active | **24-32%** |
| August 2027 | Phase E complete, full sizing + multi-instrument | **28-38%** |

---

*This document is the single authoritative profit roadmap.*
*Security, performance, and drawdown are important only insofar as they protect the ability to keep trading.*
*Every decision must be filtered through one question: does this increase net after-tax P&L?*
