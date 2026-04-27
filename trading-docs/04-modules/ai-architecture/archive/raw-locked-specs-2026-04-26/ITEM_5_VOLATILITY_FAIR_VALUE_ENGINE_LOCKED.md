# Item 5: Volatility Fair-Value Engine — LOCKED SPECIFICATION

**Status:** 🔒 LOCKED
**Locked:** 2026-04-25
**Tier:** V0.2 (Alpha Generation)
**Sources:** GPT-5.5 Pro Round 1 + Claude refinements + GPT Round 2 + Verification round
**Expected ROI contribution at maturity (months 7-12):** +5% to +10% annual full-account ROI

---

## Architectural Commitment

The Volatility Fair-Value Engine is a **deterministic pricing/forecasting module, not an AI module**. It outputs measurements; downstream systems decide what to do with them. The engine produces a strategy-conditional EV table. The meta-labeler and AI Risk Governor consume the table. The deterministic arbiter enforces final risk gates. **The engine never directly chooses trades.**

Authority chain: `Vol Engine → Meta-labeler + AI Risk Governor → Deterministic Arbiter → Execution`

The LLM never reads raw option chains. The LLM never performs vol math. The LLM consumes a compact summary (iv_rv_ratio, skew_z, surface scores, EV table top-3) and uses it as one input to qualitative reasoning.

---

## 1. Realized Volatility Model

**Choice:** HAR-RV remainder model on 5-minute SPX bars.

Rejected: GARCH (convergence issues, distribution assumptions, intraday seasonality complexity).

### Forecast Target

Forecast **remaining realized variance** from decision time to planned exit/expiry, not generic daily volatility.

```
r_i = log(S_i / S_{i-1})
RV_so_far(t) = Σ r_i² from open to current time
RV_remaining(t) = Σ r_i² from current time to close / forced exit

Model predicts: log(RV_remaining(t) + ε)
```

Log target reduces instability; exponentiation guarantees positive forecasts.

### Lag Structure

```
log_RV_remaining =
    β0
  + β1 * log(RV_D + ε)              # prior session
  + β2 * log(RV_W + ε)              # prior 5 sessions
  + β3 * log(RV_M + ε)              # prior 22 sessions
  + β4 * log(RV_so_far_scaled + ε)  # intraday running
  + β5 * abs(overnight_gap)
  + β6 * vix_change_from_prior_close
  + β7 * event_day_flag
  + β8 * time_bucket
  + error

RV_so_far_scaled = RV_so_far / expected_fraction_elapsed(time_bucket)
```

`expected_fraction_elapsed` comes from historical intraday variance seasonality.

### Time Buckets

Single pooled model with time-bucket dummies:
```
09:35, 10:00, 10:30, 11:30, 12:30, 13:30, 14:00
```

After 14:00: engine becomes low-authority for new long-vol entries.

### Training Window

```
rolling 252 sessions if available
minimum 90 clean post-Commit-4 sessions
```

Note: contaminated pre-Commit-4 trade P&L is NOT used for labels. Clean SPX 5-minute bars CAN be used for vol forecasting since price data itself is uncontaminated.

### Baseline Fallback

Ship with EWMA fallback:
```
RV_forecast_EWMA =
    λ * recent_same_bucket_RV_remaining
  + (1 - λ) * long_run_same_bucket_RV_remaining

λ ∈ [0.35, 0.50], calibrated in replay
```

If HAR-RV underperforms EWMA by >15% QLIKE over rolling 20 sessions, fall back to EWMA.

### Output Fields

```
rv_forecast_har
rv_forecast_ewma
rv_forecast_final
rv_model_confidence
forecast_error_recent
```

---

## 2. Implied Volatility Extraction

**Two-layer approach:** model-free option-strip primary, ATM straddle fallback.

### Step A — Chain Cleaning

For each option:
- Reject if bid <= 0, ask <= bid, spread_pct > tolerance (see §6 below)
- Reject if volume/OI quality too poor or quote stale
- Reject if delta missing and not estimable
- Use mid = (bid + ask) / 2

### Step B — Forward Price

Put-call parity around ATM:
```
F ≈ K + C_mid - P_mid
```
For 0DTE, rates/dividends negligible. Use median across several strikes near spot:
```
F = median(K_i + C_i - P_i for strikes near spot)
```

### Step C — Model-Free Implied Variance

Truncated option-strip variance:
```
Q(K) = put_mid  if K < F
Q(K) = call_mid if K > F
Q(K0) = average ATM call/put contribution

IVar_Q ≈ (2/T) * Σ [ΔK/K² * Q(K)] - (1/T) * (F/K0 - 1)²
```

Use only liquid strikes within authority-defined range (see §5).

```
implied_sigma_remaining = sqrt(max(IVar_Q, floor))
implied_move_points = S0 * implied_sigma_remaining * sqrt(T_years)
```

Store both annualized and horizon-scaled variance.

### Step D — ATM Straddle Sanity Proxy

```
K_atm = strike closest to F
atm_straddle = call_mid(K_atm) + put_mid(K_atm)
atm_move_proxy = 0.85 * atm_straddle
```

Used as: tradable-price proxy and divergence check, NOT as primary truth source.

### Step E — Skew Extraction

16-delta risk reversal (matches existing strategy structure):
```
skew_asymmetry_raw = put_16_iv - call_16_iv
skew_asymmetry_norm = skew_asymmetry_raw / atm_iv
skew_z = zscore(skew_asymmetry_norm, same time bucket, trailing 20 sessions)
```

Positive skew_z: puts rich relative to calls.

Fallback if IVs unreliable:
```
put_spread_richness = mid(16Δ/8Δ put credit spread) / width
call_spread_richness = mid(16Δ/8Δ call credit spread) / width
skew_proxy = put_spread_richness - call_spread_richness
```

### Step F — Surface Features

Beyond skew_z, also compute:

```
smile_asymmetry_score = (put_16_iv - call_16_iv) / atm_iv
smile_width_score     = ((put_16_iv + call_16_iv)/2 - atm_iv) / atm_iv
tail_width_score      = ((put_8_iv + call_8_iv)/2 - atm_iv) / atm_iv
```

Z-score against same-time-bucket trailing 20 sessions; fall back to 60-session if <20 same-bucket observations.

**CRITICAL — Anti-double-counting rule:**
- `skew_z` is the production decision signal consumed by deterministic thresholds, EV table penalties, Governor summary
- `smile_asymmetry_score`, `smile_width_score`, `tail_width_score` are meta-labeler features ONLY
- Deterministic decision formulas use skew_z; do NOT also add smile_asymmetry_score as a separate penalty term

### Step G — Term Structure Feature

```
iv_0dte = same-day implied variance
iv_1dte = next-expiry implied variance
term_slope = iv_1dte - iv_0dte
```

Used as risk feature, not full multi-day model. Cases:
- 0DTE cheap, 1DTE expensive → cheapness may be event-deferred
- 0DTE expensive, 1DTE normal → possible intraday event premium
- 0DTE cheap, 1DTE cheap → avoid long-vol unless catalyst confirms

### Step H — Time-To-Expiry Authority Degradation

| Time to expiry | Strip strike range | Authority |
|---|---|---|
| > 4 hours | ±2.5% spot | normal |
| 2-4 hours | ±2.0% spot | medium |
| 1-2 hours | ±1.5% spot | low |
| < 1 hour | ATM sanity proxy only | advisory/exits only |

Rules:
```
After 14:00 ET:
  no new long straddle from vol-cheapness alone
  no full-size long-vol signal
  vol-cheapness requires event/flow/price confirmation

After 15:00 ET:
  no new vol-engine-enabled entries
  engine may inform exits/marks/risk only
```

Divergence check:
```
if abs(strip_move - atm_proxy_move) / strip_move > 0.30:
    confidence = low

if divergence > 0.50:
    disable trade-enabling authority
```

---

## 3. Terminal Distribution Simulation

Generate N = 10,000 terminal scenarios for S_T:

```
r_T ~ StudentT(df=df_calibrated), scaled so variance = RV_forecast_remaining
S_T = S0 * exp(r_T)
```

### Calibrated Student-t df

Fit on **forecast-standardized residuals**, not raw returns:
```
z_i = log(S_exit_i / S_t_i) / sqrt(RV_forecast_remaining_i)

Grid MLE over df ∈ [3, 12]:
df* = argmax_df Σ log StudentT_pdf(z_i, df=df, loc=0, scale=sqrt((df-2)/df))

window: 60-252 sessions, minimum 60 observations
```

Regime-conditional df (when sample size permits):
```
if n_regime_bucket >= 100:
    df_final = w * df_regime + (1-w) * df_time_bucket
    w = n_regime_bucket / (n_regime_bucket + 60)
else:
    df_final = df_time_bucket

regime buckets: ordinary, event_day, high_vix, low_vix
```

Fallback:
```
if df estimate hits boundary or likelihood unstable:
    df = 6, confidence = low
```

Recalibration cadence: weekly recalibration, daily monitoring.

### LightGBM Directional Tilt (Capped)

Apply small mean shift only when conditions met:
```
edge = p_bull - p_bear
mu_tilt = clip(0.25 * edge, -0.10, 0.10) * sqrt(RV_forecast_remaining)
```

**Tilt suppression — set mu_tilt = 0 if ANY of:**
- ml_confidence <= 0.65
- ml_calibration_ok = false
- data_quality_ok = false
- ai_event_conflict = true
- governor.uncertainty_score >= 0.70
- governor.data_freshness_warning = true
- governor.event_class ∈ {crisis, geopolitical_shock, surprise_macro, unknown, data_conflict, regime_transition}

For scheduled events:
```
if event_class = scheduled_macro_post_release
   AND uncertainty_score < 0.70
   AND price/flow confirmation exists
   AND release has already occurred
then tilt may remain allowed, capped at 0.10 sigma
```

**Pre-release tilts on scheduled events are NEVER allowed.** Only post-release with confirmation.

---

## 4. Strategy-Conditional EV Table

For each candidate strategy, compute:
```
EV = mean(payoff(S_T)) - entry_cost - slippage - fees
EV_per_margin = EV / max_capital_at_risk
POP = probability(payoff(S_T) > 0)
CVaR_5 = average payoff in worst 5% scenarios
breach_probability = probability(short strike breached)
```

Output:
```
strategy_ev_table = [
  {
    strategy, strikes, entry_mid, max_risk,
    ev_dollars, ev_per_margin, pop, p_max_loss, cvar_5,
    iv_rv_ratio, skew_z, confidence, flags
  }, ...
]
```

### Strategy-Specific Decision Rules

**Iron Condor (16Δ short, 8Δ long):**
```
IC_quality = EV_per_margin
           - 0.40 * abs(skew_z)
           - 0.60 * event_risk_score
           - 0.50 * signal_conflict_score

Allow IC only if:
  iv_rv_ratio >= 1.12
  EV_per_margin > threshold
  p_max_loss <= threshold
  event_risk low
  skew_z not extreme
```

**Iron Butterfly (ATM short, defined-width long):**
```
IB_quality = EV_per_margin
           + 0.50 * pin_score
           - 0.70 * trend_score
           - 0.50 * abs(skew_z)
           - 0.80 * event_risk_score

Allow IB only if:
  EV_IB_after_slippage > 0
  P(breakeven_lower <= S_T <= breakeven_upper) >= 0.60
  P(|S_T - body| >= width) <= 0.10
  event_risk_score <= low_threshold
  signal_conflict_score <= low_threshold

Optional A+ condition:
  Q75(abs(S_T - body)) < credit - slippage_buffer
```

**Put Credit Spread (16Δ short, 8Δ long):**
```
PCS_quality = EV_per_margin
            + 0.30 * max(skew_z, 0)
            - 0.80 * downside_tail_probability
            - 0.70 * bearish_event_score

Allow PCS only if:
  iv_rv_ratio >= 1.10
  EV_per_margin > threshold
  downside_tail_probability acceptable
  AI Governor does not flag downside shock
```

**Long Straddle (ATM both):**
```
straddle_quality = EV_per_margin
                 + 0.70 * event_catalyst_score
                 + 0.50 * realized_vol_acceleration
                 - 0.80 * theta_bleed_risk
                 - 0.50 * late_day_penalty

Allow long straddle in PAPER only if:
  iv_rv_ratio <= 0.88
  EV_straddle > 0 after slippage
  event_catalyst_score high OR OPRA flow confirms expansion
  time_to_expiry > 120 minutes

Threshold zone (no signal):
  0.88 < iv_rv_ratio < 0.95: feature only

No edge:
  iv_rv_ratio > 0.95
```

**Debit Call Spread (~60-70Δ long, ~30-40Δ short):**
```
DCS_quality = EV_per_margin
            + 0.80 * calibrated_bullish_probability
            + 0.30 * max(skew_z, 0)
            - 0.40 * max(iv_rv_ratio - 1, 0)
            - 0.50 * theta_bleed_risk

Allow only if:
  calibrated_bullish_probability strong
  EV_DCS > 0 after slippage
  iv_rv_ratio not extremely expensive
  AI Governor does not flag headline reversal risk
```

### Decision Weight Calibration

V0.2 ships with hand-set priors above. Calibration harness uses:
- Coordinate search or Latin-hypercube search (NOT full Cartesian)
- Weight grid: {0.0, 0.2, 0.4, 0.6, 0.8, 1.0}

Joint scoring metric:
```
J = ΔSharpe
  + 0.50 * log(MaxDD_baseline / MaxDD_candidate)
  + 0.25 * log(ProfitFactor_candidate / ProfitFactor_baseline)
  - 1.00 * max(0, WorstDay_candidate / WorstDay_baseline - 1)
  - 0.25 * max(0, 0.60 - TradeRetention)
```

Promotion requires:
- J > 0
- Sharpe improves
- Max drawdown does not worsen
- Worst day does not worsen
- Trade retention >= 60% (prevents "improving Sharpe by blocking everything")

V0.2: hand-set priors. V0.3: calibrated weights if replay + paper data support them.

---

## 5. Engine Reliability Score with Recovery

### Authority Levels

Per-channel authority (track separately):
- `short_gamma_filter_authority`
- `long_vol_enable_authority`
- `strategy_ev_ranking_authority`

Levels: normal → reduced → advisory

### Degradation Triggers

```
3 consecutive long-vol signal losses:
  long_vol_authority → paper_only_low_size

5 consecutive vol-edge signals wrong:
  reduce engine weight by 50%

Rolling 20-signal EV residual < threshold:
  authority → advisory_only for affected channel

HAR QLIKE >15% worse than EWMA over rolling 20 sessions:
  fallback to EWMA, flag model_degraded = true

Forecast coverage error exceeds threshold for 10 sessions:
  reduce engine authority
```

### Recovery Mechanism

```
After degradation:
  minimum_cooldown = 30 sessions

Recovery window:
  20 qualified signals within last 30-45 sessions
  (qualified = sufficient chain quality + RV forecast quality + strategy candidate quality)

Recovery criteria (ALL must pass):
  forecast_calibration_pass:
    >= 70% of qualified signals have realized move within 1 forecast-error band
  ev_calibration_pass:
    cumulative realized EV over recovery window > 0
  relative_model_pass:
    HAR-RV QLIKE not worse than EWMA by more than 5%
  safety_pass:
    no engine-enabled trade produced worse-than-baseline worst-day loss

Recovery progression:
  one-step only
  advisory → reduced
  reduced → normal
  normal NEVER reached directly from advisory
```

Per-channel recovery: short-gamma filter, long-vol enable, EV ranking can recover independently.

---

## 6. Bid-Ask Spread Tolerance

Per-leg filter (both percent AND absolute):

```
spread = ask - bid
spread_pct = spread / mid
```

Time-based percent tolerance:

| Time to expiry | Max spread_pct |
|---|---|
| > 4 hours | 8% |
| 2-4 hours | 12% |
| 1-2 hours | 18% |
| < 1 hour | 25% (marks/exits only) |

Absolute spread sanity (also required):
```
if mid >= 1.00:
    spread_points <= max_abs_spread_points = 0.40
else:
    spread_points <= cheap_option_abs_limit = 0.10 to 0.15
```

Strategy-level slippage budget:
```
estimated_round_trip_slippage =
    0.5 * sum(entry_leg_spreads)
  + 0.5 * expected_exit_spreads

Trade allowed only if:
  EV_after_slippage > 0
  slippage_cost <= 35% of gross_EV_edge
```

In final hour: wider spread tolerance for marks/exits, NOT for enabling new trades.

---

## 7. Replay Calibration Harness

### Inputs
- SPX 5-minute bars (clean)
- Tradier option chains / greeks
- Polygon VIX
- Databento OPRA-derived features
- Existing rules-engine candidate decisions
- Post-Commit-4 clean marks/slippage

### Decision Times
```
09:35, 10:00, 10:30, 11:30, 12:30, 13:30, 14:00
```

### Per-Timestamp Procedure
```
1. Build RV forecast using only past data
2. Extract implied move from option chain at that timestamp
3. Generate candidate strategies using fixed delta rules
4. Calculate strategy_ev_table
5. Simulate fills using realistic slippage
6. Simulate exits using existing risk/time-stop logic
7. Compare forecast EV to realized outcome
```

### Baselines

```
A: rules-only
B: rules + EWMA vol fair-value
C: rules + HAR-RV vol fair-value
D: rules + HAR-RV + strategy EV table + meta-labeler
E: full production stack:
   rules + LightGBM + HAR-RV + strategy EV table
   + meta-labeler + AI Governor veto
F: full production stack MINUS Vol Engine:
   rules + LightGBM + meta-labeler + AI Governor veto
```

**Promotion gate: Baseline E must beat Baseline F.** Not just A. F isolates the engine's marginal contribution within the full stack.

### Forecast Metrics
```
QLIKE loss vs EWMA baseline
log-RV RMSE
realized move coverage by forecast decile
calibration of iv_rv_ratio buckets
forecast stability by time bucket
```

Minimum research-to-production bar:
```
HAR-RV QLIKE >= 5% better than EWMA, OR
HAR-RV equal to EWMA but strategy EV table improves trade selection
```

### Trading Metrics
```
incremental Sharpe
max drawdown reduction
profit factor
EV by forecast decile
false-block cost
long-vol signal P&L
short-vol signal P&L
worst-day impact
```

Production authority thresholds:
```
Rules + Vol Engine must:
  improve Sharpe by >= 0.20
  AND reduce max drawdown by >= 10%
  AND top EV decile must outperform bottom EV decile monotonically
  AND no increase in worst-day loss
```

For long-vol trades specifically:
```
minimum 30 replay + paper signals
positive expectancy after slippage
profit factor > 1.15
no cluster of theta-bleed losses larger than threshold
```

If sample insufficient: long-vol remains paper-only.

### Fallback Levels If Calibration Fails

```
Level 1 (full): strategy_ev_table feeds meta-labeler
Level 2 (partial): engine ships as risk filter only — block bad short-gamma, no long-vol enable
Level 3 (advisory): logging only, no production authority
```

Ship Level 3 even if Levels 1-2 fail — value in collecting clean forward data.

---

## 8. Retraining Cadence

```
HAR-RV coefficients:    daily after EOD, rolling 252 sessions
Intraday:               no retraining, only input updates
Student-t df:           weekly recalibration, daily monitoring
EWMA parameters:        weekly recalibration, daily performance check
Decision-score weights: monthly OR after 60 new qualified signals (never daily)
Reliability fallback:   continuous monitoring per §5
```

---

## 9. Integration with AI Risk Governor

### Data Flow
```
Option Chain + SPX Bars
        ↓
Vol Fair-Value Engine
        ↓
Supabase: vol_fair_value_snapshots
        ↓
strategy_ev_table
        ↓
Meta-labeler + Deterministic Arbiter
        ↓
Market State Card summary
        ↓
AI Risk Governor
```

### What LLM Sees (Compact Summary)
```
0DTE implied move: $XX
HAR forecast realized move: $XX
iv_rv_ratio: X.XX
skew_z: ±X.X
term structure: 1D vol richer/cheaper than 0DTE
strategy_ev_table top-3 (with EV, POP, max-loss prob)
late-day penalty: bool
engine confidence: high/medium/low
authority_level per channel
degradation_flags
```

LLM does NOT see raw 500+ option strikes.

---

## 10. Expected ROI Trajectory

| Period | Contribution | Authority |
|---|---|---|
| Months 1-3 | -2% to +3% | advisory / calibration only |
| Months 4-6 | +1% to +5% | short-gamma filter only, limited authority |
| Months 7-12 | +5% to +10% | mature if validation passes |

**Critical: Months 1-3 should not affect live P&L.** Paper-only during calibration period. Realized live contribution effectively zero; paper ledgers estimate promotion-worthiness.

### ROI Mechanism Breakdown

Lower bound (+5%) primarily from:
- Avoiding low-credit IC/IB days where realized > implied
- Avoiding symmetric short-gamma when skew/event asymmetric
- Preferring PCS/CCS over IC when one side mispriced
- Skipping negative-EV-after-slippage trades

Upper bound (+10%) requires:
- Short-vol selection improves materially
- Strategy choice improves (IC vs IB vs PCS vs debit spread)
- Rare confirmed cheap-vol opportunities add convex wins

---

## 11. Pre-V0.2 Data Requirements

| Use case | Minimum | Preferred |
|---|---|---|
| EWMA fallback | 30-60 sessions | 90+ |
| HAR-RV pooled model | 90 sessions | 126+ |
| Time-bucket df calibration | 60 bucket observations | 126+ |
| Regime-conditional df | 100 per regime bucket | 252+ |
| Strategy EV thresholds | 100+ signals | 200+ |
| Long-vol production authority | 30+ clean signals | 60+ |

**6 months of post-Commit-4 data is enough for V0.2 ship with constrained authority.** Not enough for unconstrained long-vol authority — that requires 60+ clean signals.

V0.2 ship-able with:
- Short-gamma filter authority
- EV table advisory authority
- Long-vol paper-only authority

---

## 12. V0.2 Build Scope

**Build:**
- HAR-RV-Remainder model
- EWMA fallback
- Calibrated Student-t terminal simulation (df fitting)
- LightGBM directional tilt with cap and suppression rules
- Model-free option-strip implied move
- ATM straddle sanity proxy
- 16Δ and 8Δ surface features
- Time-to-expiry authority degradation
- Strategy-specific EV table
- Replay calibration harness with Baselines A-F
- Engine reliability score with per-channel recovery
- LLM-facing compact summary
- Daily HAR retrain
- Weekly df/EWMA recalibration
- Monthly/60-signal decision-weight recalibration

**Do not build in V0.2:**
- GARCH production model
- Full vol surface model
- LLM raw chain reasoning
- Long-vol live authority
- Cross-index volatility model

---

## 13. Final Architectural Statement

The Volatility Fair-Value Engine is an **EV and mispricing measurement system, not a trading brain**. Its highest ROI contribution is preventing short-gamma entries when implied premium is not rich enough for the forecast move. Later, after calibration proves the engine survives slippage and theta bleed, it enables small convex trades on rare confirmed cheap-vol days.

The engine respects the Round 2 architectural commitment: **AI controls admissibility and size ceilings, not trade execution.** The deterministic arbiter remains the final gate. The rules engine remains the safety floor. Hard risk gates remain constitutional.

---

*Spec produced through Cursor + Claude + GPT-5.5 Pro collaboration over 2026-04-25. Locked after three rounds of iteration. No code changes during specification.*
