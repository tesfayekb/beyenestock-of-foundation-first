# Trading System — Approved Decisions

> **Owner:** tesfayekb | **Version:** 1.0 | **Source:** MARKETMUSE_MASTER.md v4.0, Part 3

## Purpose

All 22 locked decisions governing the MarketMuse trading system. These are **final and binding** — they cannot be modified, deferred, or reinterpreted without explicit owner approval and a new decision record (T-Rule 4).

---

## Decision Register

### D-001: Instruments
- **Decision:** SPX, XSP, NDX, RUT only (Section 1256 contracts)
- **Rationale:** Section 1256 gives 60/40 long-term/short-term tax treatment regardless of holding period. Index options have European-style exercise (no early assignment risk). Limits complexity to a manageable instrument universe.
- **Affected Modules:** strategy_selector, execution_engine, risk_engine, trading_signals schema

### D-002: Primary Mode
- **Decision:** 0DTE (zero days to expiration)
- **Rationale:** 0DTE options offer the highest theta decay rate and most liquid options market. Core edge of the system.
- **Affected Modules:** prediction_engine, strategy_selector, execution_engine, time stops

### D-003: Secondary Mode
- **Decision:** 1–5 day swing, regime-gated, system decides
- **Rationale:** Captures overnight/multi-day moves when regime conditions favor it. System autonomously decides when to use swing mode based on regime classification.
- **Affected Modules:** prediction_engine, strategy_selector, risk_engine

### D-004: Capital Allocation
- **Decision:** Core + Satellites + Reserve (RCS-dynamic)
- **Rationale:** RCS (Regime Confidence Score) dynamically allocates between core positions, satellite positions, and cash reserve. Higher confidence = more capital deployed.
- **Affected Modules:** risk_engine, strategy_selector, trading_sessions

### D-005: Daily Loss Limit
- **Decision:** −3% hardcoded, no override
- **Rationale:** Absolute capital preservation floor. Prevents catastrophic single-day losses. Non-configurable to eliminate human temptation to override during drawdowns.
- **Affected Modules:** risk_engine, sentinel, circuit breakers, trading_sessions

### D-006: Broker
- **Decision:** Tradier API only, OCO pre-submitted at every fill
- **Rationale:** Tradier offers competitive commission structure for options. OCO (One-Cancels-Other) orders ensure every position has both profit target and stop-loss immediately after fill.
- **Affected Modules:** execution_engine, sentinel, trading_operator_config

### D-007: Execution
- **Decision:** Fully automated, single operator account
- **Rationale:** V1 captures the full edge with a single account. Automation removes emotional decision-making. Single operator simplifies regulatory and risk management.
- **Affected Modules:** execution_engine, all modules

### D-008: Data Budget
- **Decision:** ~$150–200/month
- **Rationale:** Databento OPRA (~$150/mo) + CBOE DataShop (~$40–60/mo) covers all required data. Polygon, Unusual Whales, Finnhub already paid.
- **Affected Modules:** data_ingestor

### D-009: X/Twitter Sentiment
- **Decision:** Tier-3 only, ±5% max weight, ≥2 accounts to confirm
- **Rationale:** Social sentiment is noisy. Limited to tier-3 (lowest priority), small weight cap, and requires confirmation from multiple sources to reduce false signals.
- **Affected Modules:** prediction_engine (Layer B features)

### D-010: Short-Gamma Exit
- **Decision:** 2:30 PM EST, automated, no override
- **Rationale:** Short-gamma positions face accelerating risk into the close as gamma increases. 2:30 PM provides sufficient time for orderly exit before the final-hour volatility spike.
- **Affected Modules:** execution_engine, trading_time_stop_230pm job

### D-011: Long-Gamma Exit
- **Decision:** 3:45 PM EST, automated, no override
- **Rationale:** Long-gamma positions benefit from late-day moves but must exit before close to avoid settlement risk. 3:45 PM captures most of the final move while ensuring clean exit.
- **Affected Modules:** execution_engine, trading_time_stop_345pm job

### D-012: RUT Handling
- **Decision:** Satellite-only, 50% size, stricter liquidity requirements
- **Rationale:** RUT options are less liquid than SPX/NDX. Satellite designation limits exposure. 50% size and stricter liquidity thresholds (OI 300, volume 75) protect against adverse fills.
- **Affected Modules:** strategy_selector, risk_engine, execution_engine

### D-013: Paper Phase
- **Decision:** 45 days minimum, 12 go-live criteria, all required
- **Rationale:** Sufficient time to observe the system across multiple market regimes. All 12 criteria must pass simultaneously — no partial graduation. Protects real capital from undertested systems.
- **Affected Modules:** all modules, trading_operator_config, Configuration page

### D-014: Position Sizing
- **Decision:** 4 phases with advance criteria and automatic regression
- **Rationale:** Graduated sizing protects capital during early operation. Automatic regression on drawdown prevents loss acceleration. Each phase has explicit advance criteria preventing premature scaling.
- **Affected Modules:** risk_engine, trading_operator_config

### D-015: Slippage Model
- **Decision:** Predictive LightGBM, not static
- **Rationale:** Static slippage assumptions are inaccurate across market conditions. LightGBM regressor trained on actual fills predicts slippage based on current conditions (spread, volume, volatility).
- **Affected Modules:** learning_engine, strategy_selector, risk_engine

### D-016: Volatility Blending
- **Decision:** sigma = max(realized, 0.70 × implied)
- **Rationale:** Prevents regime-shift lag. Realized vol catches sudden moves; implied vol floor (70%) prevents underestimation during quiet periods that precede moves.
- **Affected Modules:** prediction_engine, risk_engine, exit strategy

### D-017: CV_Stress Exit Condition
- **Decision:** Only triggers when P&L ≥ 50% of max profit
- **Rationale:** Prevents premature exits on positions that haven't yet captured meaningful profit. CV_Stress is a leading indicator, but exiting at a loss due to CV_Stress wastes the signal.
- **Affected Modules:** execution_engine (state machine), risk_engine

### D-018: VVIX Thresholds
- **Decision:** Adaptive Z-score vs 20-day rolling baseline
- **Rationale:** Fixed VVIX thresholds become stale as the volatility regime evolves. Z-score against rolling baseline adapts automatically. Fallback to fixed thresholds (120/140/160) until 20-day history available.
- **Affected Modules:** prediction_engine, risk_engine, circuit breakers

### D-019: Execution Feedback
- **Decision:** If actual > predicted × 1.25 → tighten for session
- **Rationale:** Detects intraday liquidity degradation in real time. Tightens no-trade threshold and reduces position size when execution quality degrades. Resets at next session open.
- **Affected Modules:** execution_engine, risk_engine

### D-020: Trade Frequency
- **Decision:** Max trades per regime type per session
- **Rationale:** Prevents overtrading in any regime. Trend: max 2 core. Range/Pin: max 3. Event: max 1 reduced. Volatile: max 2 reduced. Panic: 0.
- **Affected Modules:** strategy_selector, risk_engine

### D-021: Regime Guard
- **Decision:** HMM ≠ LightGBM → size 50% reduction
- **Rationale:** When the two independent regime classifiers disagree, regime certainty is low. 50% size reduction protects capital during ambiguous market conditions.
- **Affected Modules:** prediction_engine, risk_engine

### D-022: Capital Preservation
- **Decision:** 3 consecutive losses → size 50%; 5 → halt session
- **Rationale:** Automated circuit breaker for losing streaks. Prevents compounding losses during adversarial conditions. 3 consecutive loss sessions → additional 30% reduction + RCS minimum 75.
- **Affected Modules:** risk_engine, trading_sessions, capital preservation state
