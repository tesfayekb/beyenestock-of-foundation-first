# Item 8: OPRA Flow Alpha — Structured Features — LOCKED SPECIFICATION

**Status:** 🔒 LOCKED
**Locked:** 2026-04-25
**Tier:** V0.3 (Edge Stacking)
**Sources:** GPT-5.5 Pro Round 1 + Claude verification round + GPT verification accept
**Expected ROI contribution at maturity (months 7-12):** +4% to +8% base case, +8% to +12% bull case
**Architectural role:** Deterministic feature producer feeding Items 5/6/Governor. NOT a new decision layer. NOT raw LLM input.

---

## Architectural Commitment

Databento OPRA stream → deterministic flow_alpha_engine → Redis live snapshots → Supabase durable bars → Items 5/6/Governor as features. **The LLM never reads raw OPRA data.** OPRA flow features inform decisions made by other components.

The locked architectural commitment from Items 5-7 holds: AI controls admissibility and size ceilings, deterministic features inform but don't decide.

**Core production test:** Item 6 with OPRA features must beat Item 6 without OPRA features on calibration, realized utility, and drawdown. If it does not, OPRA stays logging/research only.

---

## 1. Feature Inventory (20 Production Features)

### Base Definitions

```
premium = option_price * contract_size * 100

mid = (bid + ask) / 2
spread = ask - bid
epsilon = max(0.01, 0.05 * spread)

aggressor_sign:
  if quote_stale_or_missing OR locked/crossed market:
      0
  elif trade_price > mid + epsilon:
      +1
  elif trade_price < mid - epsilon:
      -1
  else (within epsilon of mid — Lee-Ready tick rule):
      Find prior trade in SAME underlying/expiry/strike/right
      Prior tick max age = 30 seconds
      if prior_tick_price > current_trade_price: -1
      if prior_tick_price < current_trade_price: +1
      if unchanged: use prior nonzero tick direction if recent (within 30s)
      else: 0

NBBO_age > 1 second → quote_stale = true

customer_delta = aggressor_sign * option_delta * size * 100
```

### The 20 Production Features

| # | Feature | Formula |
|---|---|---|
| 1 | `opra_premium_z_5m` | zscore(sum(premium_5m), same_time_bucket trailing_20) |
| 2 | `zero_dte_premium_share_5m` | sum(premium_0dte_5m) / sum(total_premium_5m) |
| 3 | `unknown_aggressor_share_5m` | sum(premium where aggressor_sign=0) / total_premium |
| 4 | `directional_pressure_5m` | sum(customer_delta_5m) / sum(abs(customer_delta_5m)+ε) |
| 5 | `directional_pressure_accel` | directional_pressure_1m - directional_pressure_15m |
| 6 | `vol_demand_pressure_5m` | sum(aggressor_sign * premium) / sum(premium+ε) |
| 7 | `put_call_dollar_imbalance_5m` | (put_premium - call_premium) / total_premium |
| 8 | `aggressive_put_call_imbalance_5m` | (bought_put_premium - bought_call_premium) / aggressive_premium |
| 9 | `wing_delta_pressure_5m` | directional pressure for 0.05–0.12 abs(delta) |
| 10 | `short_delta_pressure_5m` | directional pressure for 0.12–0.22 abs(delta) |
| 11 | `medium_delta_pressure_5m` | directional pressure for 0.22–0.35 abs(delta) |
| 12 | `atm_delta_pressure_5m` | directional pressure for 0.35–0.60 abs(delta) |
| 13 | `sweep_premium_share_1m` | sweep_cluster_premium_1m / total_premium_1m |
| 14 | `sweep_directional_pressure_1m` | sum(customer_delta in sweeps) / sum(abs(customer_delta in sweeps)+ε) |
| 15 | `block_premium_share_5m` | block_trade_premium_5m / total_premium_5m |
| 16 | `flow_persistence_15m` | (see formula below) |
| 17 | `zero_dte_vs_1_3dte_ratio` | 0DTE premium / 1–3DTE premium |
| 18 | `key_strike_flow_concentration_5m` | premium near gamma walls / GEX flip / large OI strikes ÷ total |
| 19 | `dealer_hedge_pressure_z_5m` | zscore(sum(customer_delta_5m), same_time_bucket trailing_20) |
| 20 | `flow_price_divergence_5m` | -zscore(directional_pressure_5m) * zscore(spx_return_5m) |

### Cross-DTE Derived Feature

```
zero_dte_minus_1_3dte_pressure = directional_pressure_0dte - directional_pressure_1_3dte
```

Tracks divergence between retail-heavy 0DTE flow and institutional-heavier 1-3DTE flow. May be more predictive than either side alone.

### Flow Persistence Formula

```
directional_pressure_15m =
  sum(customer_delta over last 15 one-minute bars)
  / sum(abs(customer_delta over last 15 one-minute bars) + ε)

dominant_sign = sign(directional_pressure_15m)

consistency =
  count(
    sign(directional_pressure_1m_i) == dominant_sign
    AND abs(directional_pressure_1m_i) >= min_pressure
  ) / 15

flow_persistence_15m =
  consistency
  * dominant_sign
  * abs(directional_pressure_15m)

min_pressure = 0.10
```

Range: [-1.0, +1.0]
- +1.0: all 15 minutes pressing strongly in same direction
- 0.0: mixed/choppy flow
- min_pressure threshold prevents tiny noisy 1-min bars from being counted as real persistence

### Sweep Detection

```
Same underlying
Same expiry
Same strike
Same right (call/put)
Same aggressor_sign
Within 100 ms
Price within 2 ticks
>= 3 exchanges OR >= 4 prints
cluster_premium >= threshold
```

### Block Trade Detection

```
Single print premium >= 95th percentile same-time-bucket
OR size >= 95th percentile same-symbol trailing distribution
```

### Key-Strike Band

```
max(5 SPX points, 0.10% of spot)
```

### Quality Tracking Features

In addition to the 20 production features, track:
```
lee_ready_inferred_share_5m = premium_signed_by_tick_rule / total_premium
unknown_aggressor_share_5m  = (already in 20 features list as #3)
```

These let downstream consumers de-weight signals when too much was inferred.

---

## 2. Time Aggregation

### Mixed Aggregation Strategy

| Time Level | Used For |
|---|---|
| Tick-level | Aggressor inference, sweep detection, block detection |
| 1-minute | Sweep share, pressure acceleration, burst detection |
| 5-minute | **Production features for Items 5/6/Governor** |
| 15-minute | Repeat-flow persistence, thesis confirmation/contradiction |

### Update Discipline

- Engine updates internal counters tick-by-tick
- Engine emits stable features only on 1-minute and 5-minute closes
- No downstream model updates on every tick
- Trading cycle never waits on per-tick computation

---

## 3. Storage Architecture

### Redis (Live State)

```
opra:flow_alpha:latest
  TTL = 15 minutes

opra:flow_alpha:bars:1m
  LTRIM last 120 bars
  TTL = trading day

opra:flow_alpha:bars:5m
  LTRIM last 80 bars
  TTL = trading day

opra:flow_alpha:health
  TTL = 5 minutes
```

**Critical:** Do NOT store unbounded raw OPRA lists in Redis. The Commit 2 LTRIM fix (already deployed) handles existing `databento:opra:trades` — apply same discipline to all new keys.

### Supabase (Durable Tables)

```sql
opra_flow_feature_bars
  - timestamp
  - window_seconds
  - symbol
  - feature_version
  - dte_bucket
  - feature columns (20 production features)
  - features_jsonb (full feature dictionary)
  - data_quality_flags
  - lee_ready_inferred_share
  - unknown_aggressor_share
  - created_at

opra_flow_events
  - timestamp
  - event_type: sweep | block | burst
  - expiry
  - strike
  - right
  - premium
  - aggressor_sign
  - direction
  - confidence
```

Store bars and event summaries, NOT raw ticks. Raw tick storage would be unbounded and expensive.

---

## 4. Compute Budget

### Latency Targets

```
Per-trade aggregate update: < 1 ms
1-minute feature emit:      < 250 ms
5-minute feature emit:      < 500 ms
Redis write:                < 50 ms
Supabase batch insert:      every 1-5 minutes
```

### Memory Footprint

```
50-200 MB for rolling windows and aggregation state
```

### Architecture: Separate Process

Run flow_alpha_engine as a **separate Railway worker process** to isolate latency risk. If feature computation gets slow or stuck, it doesn't block the trading cycle.

### Backpressure Handling

```
If feed bursts:
  preserve aggregate counters
  drop noncritical event-detail logging
  mark data_quality = degraded

If lag > 5 seconds:
  downstream treats OPRA features as stale

If unknown_aggressor_share > threshold:
  reduce feature confidence
```

**Trading should never wait on OPRA recomputation.** If features are stale, downstream consumers use last-known features with stale flag rather than blocking.

---

## 5. Integration With Items 5, 6, Governor

### Item 5 — Volatility Fair-Value Engine (8 Features)

```
vol_demand_pressure_5m
zero_dte_vs_1_3dte_ratio
sweep_premium_share_1m
aggressive_put_call_imbalance_5m
short_delta_pressure_5m
atm_delta_pressure_5m
dealer_hedge_pressure_z_5m
flow_price_divergence_5m
```

**Use cases:**
- Penalize short-gamma EV when gamma-buying flow is strong
- Raise realized-vol forecast confidence when flow and price align
- Reduce long-vol confidence when cheap vol lacks flow confirmation

### Item 6 — Meta-Labeler (All 20 Features)

The meta-labeler receives all 20 production features plus quality flags as input vector.

**Most useful meta-labeler features (highest expected feature importance):**
```
directional_pressure_5m
flow_persistence_15m
flow_price_divergence_5m
key_strike_flow_concentration_5m
dealer_hedge_pressure_z_5m
unknown_aggressor_share_5m (as quality signal)
zero_dte_minus_1_3dte_pressure (cross-DTE divergence)
```

### AI Risk Governor (Compact Summary Only)

```json
{
  "flow_direction": "bearish",
  "flow_strength": "high",
  "vol_demand": "aggressive option buying",
  "sweeps": "put sweeps elevated",
  "price_alignment": "confirms downside",
  "confidence": "medium"
}
```

**No raw OPRA rows. No LLM math.** The Governor receives narrative summaries derived deterministically from features.

---

## 6. Validation Methodology

### Replay Process

For each timestamp in walk-forward window:
```
1. Reconstruct only prior OPRA trades
2. Emit features exactly as live engine would (deterministic)
3. Join to SPX bars, option chain, Item 5 EV row, Item 6 label
4. Score against:
   - Next 30/60/120 min SPX move
   - Remaining-day realized vol
   - Strategy utility (from Item 6's labels)
   - Short-gamma stress events
```

### Feature-Level Acceptance Gates (ALL Required)

```
1. IC_abs >= 0.04 in at least 70% of walk-forward windows
   Preferred: IC_abs >= 0.05

2. Top-decile minus bottom-decile outcome separation
   Minimum: >= 0.30 sigma
   Preferred: >= 0.40 sigma

3. Marginal R² above SPX/VIX/Item5 baseline
   Minimum: >= 0.20%
   Preferred: >= 0.30%

4. No statistically significant adverse sign flip
   in any major walk-forward window

5. Worst-day P&L with feature active
   not worse than baseline worst-day P&L

6. Out-of-sample stability:
   Months 4-6 performance not worse than months 1-3 by more than 30%
```

### Promotion Rule

```
Feature becomes production feature if:
  ALL minimum gates pass
  AND (IC_abs >= 0.05 OR top-bottom separation >= 0.40 sigma)
```

Features that fail individual gates but improve full meta-labeler jointly may remain in **research/logging mode** until more data accumulates. Do NOT sneak weak features into production based on intuition.

### 0DTE-Specific Validation (Mandatory)

Validate every feature on:
```
0DTE-only flow
1-3DTE flow
4-10DTE flow
10+DTE flow
all-DTE aggregate
```

Production eligibility for 0DTE prediction system requires:
```
0DTE IC_abs >= 0.04 minimum
0DTE preferred IC_abs >= 0.05
0DTE top-bottom separation >= 0.30 sigma minimum
```

If `longer_dated IC_abs > 0.05 BUT 0DTE IC_abs < 0.02`:
```
Feature is NOT valid for 0DTE production decisions
Feature can still inform Governor summaries or longer-term research
NOT a production input to 0DTE trade selection
```

### Production Acceptance Requirements

```
Minimum 90 clean replay sessions
Minimum 30 paper-shadow sessions
Positive marginal value in at least 2 walk-forward windows
Item 6 with OPRA features beats Item 6 without OPRA features:
  - Calibration improvement
  - Realized utility improvement
  - Drawdown improvement
```

If the joint test fails, OPRA features remain logging-only.

---

## 7. Pattern Detection Deferred to V0.4+

### V0.3 Scope (Statistical Features Only)

```
Sweeps (deterministic detection)
Blocks (deterministic detection)
Bursts (deterministic detection)
Repeat-flow (deterministic computation)
Key-strike concentration (deterministic computation)
```

### Deferred to V0.4+

```
Sequence ML (LSTMs, transformers on OPRA tick sequences)
Institutional order reconstruction
Hidden-order inference
Iceberg detection via repeat-pattern ML
```

### Promotion Criteria for Pattern ML

Pattern ML may be added only after:
```
6-12 months of clean feature history accumulated
Stable strategy labels established
Clear empirical proof that statistical features have plateaued
Sample size sufficient for validation (estimated 500+ trade outcomes)
```

---

## 8. flow_agent Migration Path

**Both components, separated by role:**

```
flow_alpha_engine = deterministic feature producer (this Item 8)
flow_agent       = optional LLM summarizer (existing, post-fix)
```

### Architectural Boundary

```
Deterministic math: flow_alpha_engine
LLM narrative interpretation: flow_agent (consuming features, not raw OPRA)
```

Do NOT expand flow_agent into computation. Deterministic math belongs outside the LLM. flow_agent's role becomes "translate the structured flow_alpha_engine output into a narrative summary suitable for the Governor."

After Commits 6, 9, 10 (flow_agent fixes) deploy and verify, flow_agent's role narrows to summarizer rather than feature computer.

---

## 9. Failure Modes And Mitigations

| Failure Mode | Mitigation |
|---|---|
| Spurious correlations | 20-feature ceiling, walk-forward validation only |
| Market structure drift | Rolling validation, feature deprecation gates |
| 0DTE noise flow | Premium weighting, persistence min_pressure threshold, 0DTE-specific validation gates |
| Dealer proxy overfit | Treat as feature input, not truth signal |
| Sweep false positives | Strict cluster definition (3+ exchanges, 4+ prints, 100ms window) |
| Aggressor inference errors | unknown_aggressor_share_5m + lee_ready_inferred_share_5m as quality flags |
| Storage blowup | Redis TTL + LTRIM, Supabase bars-only |
| Latency spikes | Separate worker process, async Supabase writes, 5-second staleness handling |
| Feature creep | Quantitative acceptance gates with minimum + preferred tiers |
| Cross-DTE confusion | Mandatory per-DTE validation, can't promote a feature on aggregate alone |

---

## 10. Iran-Day Walkthrough

Primary protection still comes from Governor + Meta-Labeler. OPRA is supporting evidence.

If OPRA reacted early on Iran day, the engine likely shows:
```
directional_pressure_5m: bearish
aggressive_put_call_imbalance_5m: elevated
sweep_directional_pressure_1m: bearish
dealer_hedge_pressure_z_5m: negative
flow_price_alignment: confirms downside
vol_demand_pressure_5m: aggressive option buying
flow_persistence_15m: -0.6 to -0.8 (sustained bearish)
zero_dte_minus_1_3dte_pressure: divergent (retail puts vs institutional puts)
```

### Effects on Downstream Components

**Item 5 (Vol Fair-Value Engine):**
- Short-gamma EV confidence reduced
- Long-vol confidence increases (cheap vol with strong flow confirmation)

**Item 6 (Meta-Labeler):**
- Iron butterfly p_take reduced (multiple OPRA features point bearish)
- Combined with `event_day_short_gamma_flag`, p_take likely 0.10-0.20

**AI Risk Governor:**
- Flow summary confirms bearish event pressure
- Reinforces existing geopolitical_shock event class

If OPRA had not reacted yet (early in the day), Item 8 should NOT save the system alone. It is a feature layer, not a veto layer. Governor + Meta-Labeler remain the primary defense.

---

## 11. Expected ROI Trajectory

| Period | Live Contribution | Authority |
|---|---|---|
| Months 1-3 | 0% | Collect, replay, paper-shadow |
| Months 4-6 | +0% to +2% | Advisory / meta-labeler shadow influence |
| Months 7-12 | +4% to +8% (base), +8% to +12% (bull) | Production if marginal value proven |

### ROI Mechanism

**Lower bound (+4%) from:**
- Avoiding several short-gamma entries when OPRA shows aggressive gamma buying or directional pressure
- Improving meta-labeler discrimination on borderline trades

**Upper bound (+8% to +12%) from:**
- Better strategy selection (IC vs PCS vs CCS vs no trade)
- Better confirmation for opportunity leans
- Catching dealer hedging dynamics that drive intraday SPX moves

### Underperformance Risks

- Aggressor inference is noisier than expected
- Features duplicate price action information already captured
- Flow signal decays out-of-sample (regime drift)
- Slippage absorbs the edge
- 0DTE flow is mostly noise (most retail speculation has no predictive content)

---

## 12. V0.3 Build Scope

**Build:**
- flow_alpha_engine separate Railway worker process
- 20 production features with mathematical definitions
- Lee-Ready aggressor classification with quality flags
- Sweep detection with strict clustering rules
- Block trade detection with percentile thresholds
- Mixed time aggregation (tick / 1m / 5m / 15m)
- Redis live state with TTL + LTRIM discipline
- Supabase durable feature bars table
- Walk-forward validation harness with quantitative gates
- 0DTE-specific validation splits
- Cross-DTE divergence feature
- Backpressure handling and staleness flags
- Integration shims for Items 5, 6, Governor

**Do not build in V0.3:**
- Pattern ML on raw OPRA sequences
- Hidden-order or iceberg detection
- LLM consumption of raw OPRA data
- Flow-following strategies (this is feature infrastructure, not a trading strategy)

---

## 13. Final Architectural Statement

OPRA flow features must improve **trade rejection and strategy selection**, not create a new flow-following strategy. The ROI comes from making Items 5 and 6 smarter, not from chasing every sweep.

**The production test is simple:** Item 6 with OPRA features must beat Item 6 without OPRA features on calibration, realized utility, and drawdown. If it does not, OPRA stays logging/research only.

The architectural commitments hold:
- AI controls admissibility and size ceilings, not trade execution
- Constitutional gates remain non-overridable
- Caps compose by minimum
- OPRA features are deterministic, never raw LLM input

---

*Spec produced through GPT-5.5 Pro Round 1 + Claude verification + GPT verification accept over 2026-04-25. Locked after one full round plus verification. No code changes during specification.*
