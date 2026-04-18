"""
GEX/ZG Rule-Based Signal Backtest -- 2022-2023 SPX 0DTE

Validates whether the production GEX/ZG classifier has real edge
on historical data before trusting it with live capital.

Signal logic replicates prediction_engine.py exactly:
- dist_pct = (spx_price - zero_gamma) / zero_gamma
- dist_pct > 0.003 and vvix_z < 1.5  -> pin_range  -> iron_condor
- dist_pct > 0.001 and vvix_z < 0.8  -> quiet_bullish -> put_credit_spread
- dist_pct < -0.003 and vvix_z > 1.5 -> volatile_bearish -> sit_out
- dist_pct < -0.001                  -> trend -> sit_out (no edge for credit)
- |vvix_z| > 2.5                     -> crisis -> sit_out
- near ZG                            -> range -> iron_condor

Trade simulation:
- Entry: open a 16-delta credit spread at 9:35 AM
  (approximated from opening SPX price + EOD IV from options_features)
- Credit collected: target_credit from strategy_selector
  (approximated as ATM_IV x spread_width x sqrt(1/252) x 0.5)
- Exit rules:
  (a) 50% profit: credit x 0.5 captured
  (b) 2x stop: credit x 2.0 lost
  (c) EOD: close at intrinsic value (approximated)
- Commissions: $0.35/contract/leg x 4 legs = $1.40/contract
- Contracts: 1 (normalized -- results in $ per contract)

Requires:
  backend/data/historical/options_features.parquet
  backend/data/historical/spx_daily.parquet (or spx_5min.parquet)

Run from backend/ directory:
  python -m scripts.backtest_gex_zg
"""
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import math

DATA_DIR = Path(__file__).parent.parent / "data" / "historical"
OUTPUT_PATH = DATA_DIR / "backtest_results.json"

# Commission: $0.35/contract/leg, 4 legs for spreads
COMMISSION_PER_CONTRACT = 0.35 * 4  # $1.40 total

# Slippage: 1 tick = $0.05 per spread side (conservative)
SLIPPAGE_PER_CONTRACT = 0.05 * 2  # $0.10 entry + exit

# B1: Dynamic spread width table (matches production get_dynamic_spread_width)
VIX_WIDTH_TABLE = [(15.0, 2.50), (20.0, 5.00), (30.0, 7.50), (float("inf"), 10.00)]


def get_backtest_spread_width(iv_atm: float) -> float:
    """Approximate VIX from iv_atm (iv_atm * 100 ≈ VIX) and return dynamic width."""
    vix_approx = iv_atm * 100
    for threshold, width in VIX_WIDTH_TABLE:
        if vix_approx < threshold:
            return width
    return 10.00


# Exit thresholds
PROFIT_TARGET_PCT = 0.40   # B3: Take 40% of max profit
STOP_LOSS_PCT     = 1.50   # B3: Stop at 1.5× credit received


# -- Signal Logic (replicates prediction_engine.py exactly) ----------------

def classify_regime(dist_pct: float, vvix_z: float) -> str:
    """
    Replicate the GEX/ZG regime classifier from prediction_engine.py.
    Returns regime string or 'sit_out'.
    """
    if abs(vvix_z) > 2.5:
        return "crisis"
    if dist_pct > 0.003 and abs(vvix_z) < 1.5:
        return "pin_range"
    if dist_pct > 0.001 and abs(vvix_z) < 0.8:
        return "quiet_bullish"
    if dist_pct < -0.003 and vvix_z > 1.5:
        return "volatile_bearish"
    if dist_pct < -0.001:
        return "trend"
    return "range"


def regime_to_strategy(regime: str) -> str:
    """Map regime to strategy. sit_out for directional regimes."""
    mapping = {
        "pin_range":        "iron_condor",
        "quiet_bullish":    "put_credit_spread",
        "range":            "iron_condor",
        "volatile_bearish": "sit_out",
        "trend":            "sit_out",
        "crisis":           "sit_out",
    }
    return mapping.get(regime, "sit_out")


# -- Credit Estimation -----------------------------------------------------

def estimate_credit(iv_atm: float, spread_width: float,
                    strategy: str) -> float:
    """
    Estimate credit collected for a 0DTE credit spread.

    For a 16-delta credit spread, credit ~= 0.16 * spread_width * ATM_IV
    This is a simplified Black-Scholes approximation for 0DTE.
    Returns credit in dollars per contract (x 100 multiplier).

    For iron_condor: both sides combined ~= 2x single spread credit.
    """
    if iv_atm <= 0 or spread_width <= 0:
        return 0.0

    # Single spread credit (rough 0DTE approximation)
    # At 16-delta, the short strike is ~1 sigma from ATM
    # Credit ~= delta * spread_width (rough rule of thumb for 0DTE)
    single_credit = 0.16 * spread_width

    if strategy == "iron_condor":
        # Both put and call spreads
        credit_per_share = single_credit * 2
    else:
        credit_per_share = single_credit

    # Dollar value (x 100 shares per contract)
    return round(credit_per_share * 100, 2)


# -- Trade Outcome Simulation ----------------------------------------------

def simulate_trade(
    date: str,
    spx_open: float,
    spx_close: float,
    iv_atm: float,
    zero_gamma: float,
    strategy: str,
    spread_width: float,
) -> dict:
    """
    Simulate one 0DTE credit spread trade.

    Entry: 9:35 AM at spx_open price
    Exit rules:
      - If SPX stayed within short strikes: full credit (win)
      - If SPX breached one short strike by close: loss proportional to breach
      - Applied profit target and stop loss thresholds

    Returns trade outcome dict.
    """
    credit = estimate_credit(iv_atm, spread_width, strategy)
    if credit <= 0:
        return {"date": date, "strategy": strategy, "result": "skip",
                "reason": "zero_credit", "pnl": 0.0}

    # Short strike placement: 16-delta ~= 1 sigma away from ATM
    # For 0DTE, 1 sigma ~= ATM_IV * SPX_price * sqrt(1/252)
    one_sigma = iv_atm * spx_open * math.sqrt(1 / 252)

    if strategy == "put_credit_spread":
        short_strike = round((spx_open - one_sigma) / 5) * 5
        # Win if SPX closes above short_strike
        if spx_close >= short_strike:
            gross_pnl = credit  # full credit capture
        else:
            # Loss proportional to breach
            breach = short_strike - spx_close
            loss = min(breach / spread_width, 1.0) * spread_width * 100
            gross_pnl = credit - loss

    elif strategy == "call_credit_spread":
        short_strike = round((spx_open + one_sigma) / 5) * 5
        if spx_close <= short_strike:
            gross_pnl = credit
        else:
            breach = spx_close - short_strike
            loss = min(breach / spread_width, 1.0) * spread_width * 100
            gross_pnl = credit - loss

    elif strategy == "iron_condor":
        put_short = round((spx_open - one_sigma) / 5) * 5
        call_short = round((spx_open + one_sigma) / 5) * 5
        if put_short <= spx_close <= call_short:
            gross_pnl = credit  # both spreads expire worthless
        elif spx_close < put_short:
            breach = put_short - spx_close
            loss = min(breach / spread_width, 1.0) * spread_width * 100
            gross_pnl = credit - loss
        else:
            breach = spx_close - call_short
            loss = min(breach / spread_width, 1.0) * spread_width * 100
            gross_pnl = credit - loss
    else:
        return {"date": date, "strategy": strategy, "result": "skip",
                "reason": "unknown_strategy", "pnl": 0.0}

    # Apply profit target and stop loss
    profit_target = credit * PROFIT_TARGET_PCT
    stop_loss = -credit * STOP_LOSS_PCT

    if gross_pnl >= profit_target:
        gross_pnl = profit_target  # capped at target
    elif gross_pnl <= stop_loss:
        gross_pnl = stop_loss      # stopped out

    # Subtract costs
    total_cost = COMMISSION_PER_CONTRACT + SLIPPAGE_PER_CONTRACT
    net_pnl = gross_pnl - total_cost

    return {
        "date": date,
        "strategy": strategy,
        "spx_open": spx_open,
        "spx_close": spx_close,
        "zero_gamma": zero_gamma,
        "iv_atm": iv_atm,
        "credit": credit,
        "gross_pnl": round(gross_pnl, 2),
        "net_pnl": round(net_pnl, 2),
        "result": "win" if net_pnl > 0 else "loss",
    }


# -- Main ------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("GEX/ZG Backtest -- 2022-2023 SPX 0DTE")
    print("=" * 60)

    # Load options features
    features_path = DATA_DIR / "options_features.parquet"
    if not features_path.exists():
        raise RuntimeError(
            "options_features.parquet not found. "
            "Run: python -m scripts.process_options_data"
        )
    features = pd.read_parquet(features_path)
    features["date"] = pd.to_datetime(features["date"]).dt.date
    print(f"\nOptions features: {len(features)} days, "
          f"{features['date'].min()} -> {features['date'].max()}")

    # Load SPX daily prices — prefer CBOE (full history back to 2010)
    # over Polygon (only ~2 years due to plan limitation)
    spx_cboe_path = DATA_DIR / "spx_daily_cboe.parquet"
    spx_poly_path = DATA_DIR / "spx_daily.parquet"

    if spx_cboe_path.exists():
        spx = pd.read_parquet(spx_cboe_path)
        print(f"SPX daily (CBOE): {len(spx)} rows")
    elif spx_poly_path.exists():
        spx = pd.read_parquet(spx_poly_path)
        print(f"SPX daily (Polygon): {len(spx)} rows")
    else:
        raise RuntimeError(
            "No SPX daily data found. Run: python -m scripts.download_historical_data"
        )

    # Normalize date column
    if "date" in spx.columns:
        spx["date"] = pd.to_datetime(spx["date"]).dt.date
    else:
        spx["date"] = pd.to_datetime(
            spx["timestamp_ms"], unit="ms", utc=True
        ).dt.tz_convert("America/New_York").dt.date
    spx = spx.sort_values("date")
    print(f"SPX date range: {spx['date'].min()} -> {spx['date'].max()}")

    # Compute VVIX Z-score (20-day rolling) from options features
    features = features.sort_values("date").reset_index(drop=True)
    # Use IV rank as VVIX proxy (both measure vol-of-vol stress)
    # IV rank 0-1 -> rescale to z-score-like range
    # iv_rank > 0.8 ~= vvix_z > 1.5 (high stress)
    # iv_rank > 0.95 ~= vvix_z > 2.5 (crisis)
    features["vvix_z_proxy"] = (features["iv_rank"] - 0.5) * 6.0

    # Merge features with SPX prices
    merged = features.merge(
        spx[["date", "open", "close"]].rename(
            columns={"open": "spx_open", "close": "spx_close"}
        ),
        on="date",
        how="inner",
    )
    merged = merged.dropna(subset=["zero_gamma", "iv_atm", "spx_open", "spx_close"])
    print(f"Matched days: {len(merged)}")

    # Run backtest
    print("\n[Running backtest...]")
    trades = []
    sit_out_count = 0

    for _, row in merged.iterrows():
        date_str = str(row["date"])
        spx_open = float(row["spx_open"])
        spx_close = float(row["spx_close"])
        zero_gamma = float(row["zero_gamma"])
        iv_atm = float(row["iv_atm"])
        vvix_z = float(row["vvix_z_proxy"])

        # Apply signal
        dist_pct = (spx_open - zero_gamma) / zero_gamma
        regime = classify_regime(dist_pct, vvix_z)
        strategy = regime_to_strategy(regime)

        if strategy == "sit_out":
            sit_out_count += 1
            continue

        trade = simulate_trade(
            date_str, spx_open, spx_close, iv_atm, zero_gamma, strategy,
            spread_width=get_backtest_spread_width(iv_atm),
        )
        if trade["result"] != "skip":
            trades.append(trade)

    # Compute statistics
    if not trades:
        print("\nNo trades generated -- check data quality")
        return

    df_trades = pd.DataFrame(trades)
    total = len(df_trades)
    wins = (df_trades["net_pnl"] > 0).sum()
    losses = (df_trades["net_pnl"] <= 0).sum()
    win_rate = wins / total

    total_pnl = df_trades["net_pnl"].sum()
    avg_win = df_trades.loc[df_trades["net_pnl"] > 0, "net_pnl"].mean()
    avg_loss = df_trades.loc[df_trades["net_pnl"] <= 0, "net_pnl"].mean()
    profit_factor = (
        df_trades.loc[df_trades["net_pnl"] > 0, "net_pnl"].sum() /
        abs(df_trades.loc[df_trades["net_pnl"] <= 0, "net_pnl"].sum())
        if losses > 0 else float("inf")
    )

    # Sharpe ratio (annualized)
    daily_pnl = df_trades.groupby("date")["net_pnl"].sum()
    sharpe = (
        daily_pnl.mean() / daily_pnl.std() * math.sqrt(252)
        if daily_pnl.std() > 0 else 0.0
    )

    # Max drawdown
    cumulative = daily_pnl.cumsum()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max)
    max_drawdown = drawdown.min()

    # Per-strategy breakdown
    strategy_stats = {}
    for strat in df_trades["strategy"].unique():
        s = df_trades[df_trades["strategy"] == strat]
        sw = (s["net_pnl"] > 0).sum()
        strategy_stats[strat] = {
            "trades": len(s),
            "win_rate": round(sw / len(s), 3),
            "total_pnl": round(s["net_pnl"].sum(), 2),
            "avg_pnl": round(s["net_pnl"].mean(), 2),
        }

    # Print results
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS -- GEX/ZG Rule-Based Signal")
    print("=" * 60)
    print(f"\nPeriod:         {merged['date'].min()} -> {merged['date'].max()}")
    print(f"Trading days:   {len(merged)}")
    print(f"Trades taken:   {total}")
    print(f"Sit-out days:   {sit_out_count} "
          f"({sit_out_count / (sit_out_count + total) * 100:.1f}%)")
    print(f"\nWin rate:       {win_rate:.1%}  ({wins}W / {losses}L)")
    print(f"Profit factor:  {profit_factor:.2f}")
    print(f"Total P&L:      ${total_pnl:,.2f} (per contract)")
    print(f"Avg win:        ${avg_win:.2f}")
    print(f"Avg loss:       ${avg_loss:.2f}")
    print(f"Sharpe ratio:   {sharpe:.2f}")
    print(f"Max drawdown:   ${max_drawdown:.2f}")
    print(f"\nBy strategy:")
    for strat, stats in strategy_stats.items():
        print(f"  {strat:25s} {stats['trades']:3d} trades  "
              f"WR={stats['win_rate']:.1%}  "
              f"P&L=${stats['total_pnl']:,.2f}")

    # Signal quality assessment
    print("\n" + "=" * 60)
    print("SIGNAL ASSESSMENT")
    if win_rate >= 0.65 and profit_factor >= 1.5:
        verdict = "STRONG EDGE -- deploy with confidence"
    elif win_rate >= 0.58 and profit_factor >= 1.2:
        verdict = "MODERATE EDGE -- deploy with monitoring"
    elif win_rate >= 0.52:
        verdict = "WEAK EDGE -- improve before deploying"
    else:
        verdict = "NO EDGE -- do not rely on this signal"
    print(f"Verdict: {verdict}")
    print(f"Win rate target: >=65%  Actual: {win_rate:.1%}")
    print(f"Profit factor target: >=1.5  Actual: {profit_factor:.2f}")
    print("=" * 60)

    # Save results
    results = {
        "backtest_run_at": datetime.now(timezone.utc).isoformat(),
        "period_from": str(merged["date"].min()),
        "period_to":   str(merged["date"].max()),
        "total_trading_days": len(merged),
        "trades_taken":  total,
        "sit_out_days":  sit_out_count,
        "win_rate":      round(win_rate, 4),
        "profit_factor": round(profit_factor, 4),
        "total_pnl":     round(total_pnl, 2),
        "avg_win":       round(avg_win, 2),
        "avg_loss":      round(avg_loss, 2),
        "sharpe_ratio":  round(sharpe, 4),
        "max_drawdown":  round(max_drawdown, 2),
        "verdict":       verdict,
        "by_strategy":   strategy_stats,
    }
    OUTPUT_PATH.write_text(json.dumps(results, indent=2))
    print(f"\n[OK] Results saved -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
