"""
OptionsDX SPX EOD data processor.

Reads 24 monthly SPX option chain CSV files from:
  backend/data/historical/options/spx_eod_YYYYMM.txt

Computes daily metrics:
  - IV rank (where today's IV sits in 252-day range)
  - IV percentile (% of days with lower IV in past year)
  - Put/call volume ratio
  - Zero-gamma level (strike where net gamma crosses zero)
  - 25-delta IV skew (put IV - call IV at 25 delta)
  - 50-delta (ATM) IV

Outputs:
  backend/data/historical/options_features.parquet

Run from backend/ directory:
  python -m scripts.process_options_data
"""
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

OPTIONS_DIR = Path(__file__).parent.parent / "data" / "historical" / "options"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "historical" / "options_features.parquet"


def load_monthly_file(filepath: Path) -> pd.DataFrame:
    """Load one OptionsDX monthly CSV file."""
    df = pd.read_csv(
        filepath,
        skipinitialspace=True,
    )
    # Strip brackets from column names: [STRIKE] -> STRIKE
    df.columns = [c.strip().strip("[]") for c in df.columns]
    return df


def compute_daily_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Given a full option chain DataFrame, compute one row per trading day.
    Columns: date, iv_atm, iv_rank, iv_percentile, pc_ratio,
             zero_gamma_level, skew_25d
    """
    results = []

    for date_str, day_df in df.groupby("QUOTE_DATE"):
        try:
            # --- 0DTE rows only (DTE == 0) ---
            dte0 = day_df[day_df["DTE"] == 0].copy()
            if len(dte0) < 5:
                continue

            underlying = float(dte0["UNDERLYING_LAST"].iloc[0])
            if underlying <= 0:
                continue

            # Restrict to strikes within 5% of underlying — drops deep OTM noise
            dte0 = dte0[
                (dte0["STRIKE"] >= underlying * 0.95) &
                (dte0["STRIKE"] <= underlying * 1.05)
            ].copy()
            if len(dte0) < 3:
                continue

            # --- ATM IV (strike closest to underlying) ---
            dte0["strike_dist"] = abs(dte0["STRIKE"] - underlying)
            # Only use rows with valid IV for ATM selection
            iv_valid = dte0.dropna(subset=["C_IV", "P_IV"])
            iv_valid = iv_valid[
                (iv_valid["C_IV"] > 0.01) & (iv_valid["P_IV"] > 0.01)
            ]
            if len(iv_valid) == 0:
                continue
            atm_row = iv_valid.loc[iv_valid["strike_dist"].idxmin()]
            iv_atm = float(
                (atm_row.get("C_IV", 0) + atm_row.get("P_IV", 0)) / 2
            )

            # --- Put/call volume ratio ---
            total_call_vol = dte0["C_VOLUME"].sum()
            total_put_vol = dte0["P_VOLUME"].sum()
            pc_ratio = (
                total_put_vol / total_call_vol
                if total_call_vol > 0 else 1.0
            )

            # --- Zero-gamma level ---
            # Net gamma per strike: call_gamma - put_gamma (signed by dealer position)
            # Dealers are short calls and long puts -> net_gamma = C_GAMMA - P_GAMMA
            # Zero-gamma = strike where net gamma changes sign
            dte0["net_gamma"] = dte0["C_GAMMA"] - dte0["P_GAMMA"]
            dte0_sorted = dte0.sort_values("STRIKE")

            zero_gamma = None
            net_g = dte0_sorted["net_gamma"].values
            strikes = dte0_sorted["STRIKE"].values
            for i in range(len(net_g) - 1):
                if (net_g[i] * net_g[i + 1] <= 0
                        and net_g[i] != net_g[i + 1]
                        and abs(net_g[i]) > 1e-5
                        and abs(net_g[i + 1]) > 1e-5):
                    # Linear interpolation
                    frac = abs(net_g[i]) / (abs(net_g[i]) + abs(net_g[i + 1]))
                    zero_gamma = strikes[i] + frac * (strikes[i + 1] - strikes[i])
                    break

            # --- 25-delta IV skew ---
            # Find strikes closest to 25-delta put and 25-delta call
            dte0["put_delta_dist"] = abs(abs(dte0["P_DELTA"]) - 0.25)
            dte0["call_delta_dist"] = abs(dte0["C_DELTA"] - 0.25)
            put_25d = dte0.loc[dte0["put_delta_dist"].idxmin()]
            call_25d = dte0.loc[dte0["call_delta_dist"].idxmin()]
            skew_25d = float(put_25d.get("P_IV", 0)) - float(call_25d.get("C_IV", 0))

            results.append({
                "date": date_str,
                "underlying": round(underlying, 2),
                "iv_atm": round(iv_atm, 4),
                "pc_ratio": round(pc_ratio, 4),
                "zero_gamma": round(zero_gamma, 2) if zero_gamma is not None else None,
                "skew_25d": round(skew_25d, 4),
                "n_strikes": len(dte0),
            })

        except Exception as e:
            import logging
            logging.warning(f"options_day_skipped date={date_str} error={e}")
            continue

    return pd.DataFrame(results)


def compute_iv_rank(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Add IV rank and IV percentile using 252-day rolling window."""
    daily_df = daily_df.sort_values("date").reset_index(drop=True)
    iv = daily_df["iv_atm"]
    window = 252

    iv_rank = []
    iv_pct = []
    for i in range(len(iv)):
        start = max(0, i - window)
        window_iv = iv.iloc[start:i + 1]
        lo, hi = window_iv.min(), window_iv.max()
        cur = iv.iloc[i]
        rank = (cur - lo) / (hi - lo) if hi > lo else 0.5
        pct = (window_iv < cur).mean()
        iv_rank.append(round(rank, 4))
        iv_pct.append(round(pct, 4))

    daily_df["iv_rank"] = iv_rank
    daily_df["iv_percentile"] = iv_pct
    return daily_df


def main() -> None:
    print("=" * 60)
    print("OptionsDX SPX EOD Data Processor")
    print(f"Input:  {OPTIONS_DIR}")
    print(f"Output: {OUTPUT_PATH}")
    print("=" * 60)

    # Find all monthly files
    files = sorted(OPTIONS_DIR.glob("spx_eod_*.txt"))
    if not files:
        raise RuntimeError(
            f"No spx_eod_*.txt files found in {OPTIONS_DIR}\n"
            "Run Phase A2 first to download and extract OptionsDX data."
        )
    print(f"\nFound {len(files)} monthly files:")
    for f in files:
        print(f"  {f.name}  ({f.stat().st_size / 1e6:.1f} MB)")

    # Process each monthly file
    all_daily = []
    for i, fpath in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] Processing {fpath.name}...")
        try:
            df = load_monthly_file(fpath)
            print(f"  Loaded {len(df):,} rows, {df['QUOTE_DATE'].nunique()} trading days")
            daily = compute_daily_features(df)
            print(f"  Computed features for {len(daily)} days")
            all_daily.append(daily)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

    if not all_daily:
        raise RuntimeError("No data processed successfully")

    # Combine and sort
    combined = pd.concat(all_daily, ignore_index=True)
    combined = combined.sort_values("date").drop_duplicates("date").reset_index(drop=True)
    print(f"\nTotal: {len(combined)} trading days, "
          f"{combined['date'].min()} -> {combined['date'].max()}")

    # Compute IV rank across full history
    print("\nComputing IV rank (252-day rolling window)...")
    combined = compute_iv_rank(combined)

    # Validate
    print("\n[Validation]")
    nulls = combined.isnull().sum()
    print(f"  zero_gamma null: {nulls.get('zero_gamma', 0)} days "
          f"({nulls.get('zero_gamma', 0) / len(combined) * 100:.1f}%)")
    print(f"  iv_atm range: [{combined['iv_atm'].min():.3f}, "
          f"{combined['iv_atm'].max():.3f}]")
    print(f"  pc_ratio range: [{combined['pc_ratio'].min():.2f}, "
          f"{combined['pc_ratio'].max():.2f}]")
    print(f"  zero_gamma vs underlying:")
    valid_zg = combined.dropna(subset=["zero_gamma"])
    if len(valid_zg) > 0:
        diff = (valid_zg["zero_gamma"] - valid_zg["underlying"]).abs()
        print(f"    median distance: {diff.median():.1f} pts")
        print(f"    max distance: {diff.max():.1f} pts")

    # Save
    combined.to_parquet(OUTPUT_PATH, index=False)
    print(f"\n[OK] Saved {len(combined)} rows -> {OUTPUT_PATH}")

    # Write manifest
    manifest = {
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "source_files": len(files),
        "trading_days": len(combined),
        "date_from": str(combined["date"].min()),
        "date_to": str(combined["date"].max()),
        "columns": list(combined.columns),
        "zero_gamma_coverage_pct": round(
            combined["zero_gamma"].notna().mean() * 100, 1
        ),
    }
    manifest_path = OUTPUT_PATH.parent / "options_features_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"[OK] Manifest -> {manifest_path}")

    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print(f"  Trading days: {len(combined)}")
    print(f"  IV rank coverage: 100%")
    print(f"  Zero-gamma coverage: "
          f"{combined['zero_gamma'].notna().mean() * 100:.1f}%")
    print("=" * 60)
    print("\nNext step: run GEX/ZG backtest")
    print("  python -m scripts.backtest_gex_zg")


if __name__ == "__main__":
    main()
