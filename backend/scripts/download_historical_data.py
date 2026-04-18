"""
Phase A2: Historical data download for LightGBM training.

Downloads SPX 5-min bars, SPX/VIX/VVIX/VIX9D daily history.
Run once: python -m scripts.download_historical_data

Requires POLYGON_API_KEY in environment.
VIX/VVIX/VIX9D are free from CBOE — no API key needed.

Output: backend/data/historical/*.parquet + download_manifest.json
"""
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Ensure backend/ is on path when run as a module
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
import pandas as pd


# ── Configuration ─────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data" / "historical"
DATA_DIR.mkdir(parents=True, exist_ok=True)

POLYGON_BASE = "https://api.polygon.io"
SPX_5MIN_START = "2020-01-01"   # 5 years of intraday data
DAILY_START    = "2010-01-01"   # 15 years of daily data for RV/regime features
END_DATE       = date.today().isoformat()

# CBOE free CSV URLs (no API key needed)
CBOE_VIX_URL   = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"
CBOE_VVIX_URL  = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VVIX_History.csv"
CBOE_VIX9D_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX9D_History.csv"
CBOE_SPX_URL   = "https://cdn.cboe.com/api/global/us_indices/daily_prices/SPX_History.csv"


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_polygon_key() -> str:
    """Load API key from environment or .env file."""
    key = os.getenv("POLYGON_API_KEY")
    if not key:
        # Try loading from backend/.env
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("POLYGON_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not key:
        raise RuntimeError(
            "POLYGON_API_KEY not found. Set it in environment or backend/.env"
        )
    return key


def polygon_get(
    url: str,
    params: dict,
    api_key: str,
    retries: int = 3,
    delay: float = 1.0,
) -> dict:
    """
    GET a Polygon endpoint with retry on 429 (rate limit) and 5xx errors.
    Returns parsed JSON or raises on persistent failure.
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 403:
                raise RuntimeError(
                    f"Polygon 403 on {url} — check plan covers this endpoint. "
                    f"I:SPX minute data requires Starter plan or above."
                )
            if resp.status_code == 429:
                wait = delay * (2 ** attempt)
                print(f"  Rate limited. Waiting {wait:.0f}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        except httpx.TimeoutException:
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            raise
    raise RuntimeError(f"Polygon request failed after {retries} retries: {url}")


# ── Downloader: SPX 5-minute bars ─────────────────────────────────────────────

def download_spx_5min(api_key: str) -> pd.DataFrame:
    """
    Download SPX 5-minute OHLCV bars from Polygon.
    Uses I:SPX ticker. Returns ~118k rows for 2020-2026.
    Polygon returns max 50000 results per call — paginates automatically.
    """
    print(f"\n[1/5] Downloading SPX 5-minute bars {SPX_5MIN_START} -> {END_DATE}...")

    all_results = []
    url = f"{POLYGON_BASE}/v2/aggs/ticker/I:SPX/range/5/minute/{SPX_5MIN_START}/{END_DATE}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": 50000,
    }

    page = 0
    while url:
        page += 1
        print(f"  Fetching page {page}...", end=" ", flush=True)
        data = polygon_get(url, params, api_key)
        results = data.get("results", [])
        all_results.extend(results)
        print(f"{len(results)} bars (total: {len(all_results)})")

        # Polygon paginates via next_url
        next_url = data.get("next_url")
        if next_url:
            url = next_url
            params = {}  # next_url already has params embedded
            time.sleep(0.2)  # be polite
        else:
            break

    if not all_results:
        raise RuntimeError("No SPX 5-minute data returned — check Polygon plan")

    df = pd.DataFrame(all_results)
    # Polygon columns: t=timestamp_ms, o=open, h=high, l=low, c=close, v=volume, vw=vwap, n=trades
    df = df.rename(columns={"t": "timestamp_ms", "o": "open", "h": "high",
                             "l": "low", "c": "close", "v": "volume",
                             "vw": "vwap", "n": "n_trades"})
    df["datetime"] = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True)
    df["datetime_et"] = df["datetime"].dt.tz_convert("America/New_York")
    df = df.sort_values("timestamp_ms").reset_index(drop=True)

    out = DATA_DIR / "spx_5min.parquet"
    df.to_parquet(out, index=False)
    print(f"  [OK] Saved {len(df):,} rows -> {out}")
    return df


# ── Downloader: SPX daily bars ─────────────────────────────────────────────────

def download_spx_daily(api_key: str) -> pd.DataFrame:
    """Download SPX daily OHLCV from Polygon for realized vol features."""
    print(f"\n[2/5] Downloading SPX daily bars {DAILY_START} -> {END_DATE}...")

    data = polygon_get(
        f"{POLYGON_BASE}/v2/aggs/ticker/I:SPX/range/1/day/{DAILY_START}/{END_DATE}",
        {"adjusted": "true", "sort": "asc", "limit": 50000},
        api_key,
    )
    results = data.get("results", [])
    if not results:
        raise RuntimeError("No SPX daily data returned")

    df = pd.DataFrame(results)
    df = df.rename(columns={"t": "timestamp_ms", "o": "open", "h": "high",
                             "l": "low", "c": "close", "v": "volume"})
    df["date"] = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True).dt.date
    df = df.sort_values("timestamp_ms").reset_index(drop=True)

    out = DATA_DIR / "spx_daily.parquet"
    df.to_parquet(out, index=False)
    print(f"  [OK] Saved {len(df):,} rows -> {out}")
    return df


# ── Downloader: CBOE free CSVs ────────────────────────────────────────────────

def download_cboe_csv(url: str, name: str, out_file: str) -> pd.DataFrame:
    """
    Download a CBOE historical CSV. Free, no API key required.
    CBOE CSV format: DATE,OPEN,HIGH,LOW,CLOSE
    """
    print(f"\nDownloading {name} from CBOE...")
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url)
    if resp.status_code != 200:
        raise RuntimeError(
            f"CBOE {name} download failed: HTTP {resp.status_code}\n"
            f"URL: {url}\n"
            f"If the URL is broken, download manually from cboe.com/tradable_products/{name.lower()}/"
        )

    from io import StringIO
    df = pd.read_csv(StringIO(resp.text))

    # Standardize column names (CBOE uses uppercase)
    df.columns = [c.lower().strip() for c in df.columns]

    # CBOE sometimes has a header row "DATE,OPEN,HIGH,LOW,CLOSE"
    # and data rows like "01/02/2024,13.19,13.34,12.83,13.15"
    # Parse date column
    date_col = [c for c in df.columns if "date" in c][0]
    df = df.rename(columns={date_col: "date"})
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df = df[df["date"] >= pd.Timestamp(DAILY_START)]

    out = DATA_DIR / out_file
    df.to_parquet(out, index=False)
    print(f"  [OK] Saved {len(df):,} rows -> {out}")
    return df


# ── Downloader: SPX daily from CBOE (free, no API key) ───────────────────────

def download_spx_daily_cboe() -> pd.DataFrame:
    """
    Download SPX daily OHLC from CBOE's free public CSV.
    No API key required. Covers 1990-present and complements Polygon
    (whose I:SPX daily coverage depends on plan tier).
    Saves to backend/data/historical/spx_daily_cboe.parquet.
    """
    return download_cboe_csv(CBOE_SPX_URL, "SPX", "spx_daily_cboe.parquet")


def download_spx_daily_yfinance() -> pd.DataFrame:
    """
    Download SPX daily OHLC from Yahoo Finance via yfinance.
    Ticker: ^GSPC (S&P 500 index). Free, no auth, back to 1950s.
    Saves to spx_daily_stooq.parquet (same filename so backtest loader
    requires no changes).
    """
    print(f"\nDownloading SPX OHLC from Yahoo Finance (yfinance)...")
    import yfinance as yf
    ticker = yf.Ticker("^GSPC")
    df = ticker.history(start=DAILY_START, end=END_DATE, interval="1d")
    if df.empty:
        raise RuntimeError("yfinance returned empty data for ^GSPC")

    df = df.reset_index()
    df.columns = [c.lower() for c in df.columns]

    # yfinance returns 'date' as datetime — normalize to date
    date_col = "date" if "date" in df.columns else df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col]).dt.date
    df = df.rename(columns={date_col: "date"})
    df = df[["date", "open", "high", "low", "close", "volume"]].copy()
    df = df.sort_values("date").dropna(subset=["open", "close"])

    out = DATA_DIR / "spx_daily_stooq.parquet"
    df.to_parquet(out, index=False)
    print(f"  [OK] Saved {len(df):,} rows -> {out}")
    print(f"  Date range: {df['date'].min()} -> {df['date'].max()}")
    print(f"  Close range: {df['close'].min():.0f} - {df['close'].max():.0f}")
    return df


# ── Validation ────────────────────────────────────────────────────────────────

def validate_downloads(dfs: dict) -> None:
    """
    Validate downloaded data quality. Prints warnings for issues found.
    Raises are handled in main() — this function never raises directly.
    """
    print("\n[Validation]")

    # SPX 5-min: check for large gaps (>1 trading day)
    spx5 = dfs.get("spx_5min")
    if spx5 is not None and len(spx5) > 0:
        spx5_sorted = spx5.sort_values("timestamp_ms")
        gaps = spx5_sorted["timestamp_ms"].diff()
        large_gaps = gaps[gaps > 24 * 60 * 60 * 1000 * 3]  # >3 calendar days
        if len(large_gaps) > 10:
            print(f"  WARNING: {len(large_gaps)} large gaps in SPX 5-min data (expected for holidays/weekends)")
        print(f"  [OK] SPX 5-min: {len(spx5):,} rows, "
              f"from {spx5['datetime_et'].min()} "
              f"to {spx5['datetime_et'].max()}")

    # SPX daily: should have ~3600+ rows for 2010-2026
    spx_d = dfs.get("spx_daily")
    if spx_d is not None:
        if len(spx_d) < 3000:
            print(f"  WARNING: SPX daily only {len(spx_d)} rows — expected ~3600+")
        else:
            print(f"  [OK] SPX daily: {len(spx_d):,} rows")

    # VIX/VVIX/VIX9D: check reasonable value ranges
    for name, col, lo, hi in [
        ("vix_daily",   "close", 8.0,  90.0),
        ("vvix_daily",  "close", 50.0, 200.0),
        ("vix9d_daily", "close", 5.0,  80.0),
    ]:
        df = dfs.get(name)
        if df is not None and "close" in df.columns:
            out_range = df[(df["close"] < lo) | (df["close"] > hi)]
            if len(out_range) > 0:
                print(f"  WARNING: {name} has {len(out_range)} rows outside "
                      f"expected range [{lo}, {hi}]")
            else:
                print(f"  [OK] {name}: {len(df):,} rows, "
                      f"close range [{df['close'].min():.1f}, {df['close'].max():.1f}]")

    print("  Validation complete.")


# ── Manifest ──────────────────────────────────────────────────────────────────

def write_manifest(dfs: dict) -> None:
    """Write download_manifest.json with metadata for A3 to read."""
    manifest = {
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "spx_5min_start": SPX_5MIN_START,
        "daily_start": DAILY_START,
        "end_date": END_DATE,
        "files": {},
    }
    for name, df in dfs.items():
        if df is not None:
            manifest["files"][name] = {
                "rows": len(df),
                "file": f"{name}.parquet",
            }
            if "datetime_et" in df.columns:
                manifest["files"][name]["from"] = str(df["datetime_et"].min())
                manifest["files"][name]["to"] = str(df["datetime_et"].max())
            elif "date" in df.columns:
                manifest["files"][name]["from"] = str(df["date"].min())
                manifest["files"][name]["to"] = str(df["date"].max())

    out = DATA_DIR / "download_manifest.json"
    out.write_text(json.dumps(manifest, indent=2, default=str))
    print(f"\n  [OK] Manifest written -> {out}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    import sys
    import io
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    elif sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    print("=" * 60)
    print("Phase A2: Historical Data Download")
    print(f"Output: {DATA_DIR}")
    print("=" * 60)

    api_key = get_polygon_key()
    print(f"Polygon key: {api_key[:8]}...")

    dfs = {}
    errors = []

    # 1. SPX 5-minute bars (Polygon)
    try:
        dfs["spx_5min"] = download_spx_5min(api_key)
    except Exception as e:
        print(f"  ERROR: SPX 5-min download failed: {e}")
        errors.append(("spx_5min", str(e)))

    # 2. SPX daily bars (Polygon)
    try:
        dfs["spx_daily"] = download_spx_daily(api_key)
    except Exception as e:
        print(f"  ERROR: SPX daily download failed: {e}")
        errors.append(("spx_daily", str(e)))

    # 2a. SPX daily OHLC from Yahoo Finance (free, back to 1950s, has open/close)
    try:
        dfs["spx_daily_stooq"] = download_spx_daily_yfinance()
    except Exception as e:
        print(f"  WARNING: yfinance SPX download failed (optional): {e}")

    # 2b. SPX daily (CBOE free CSV — covers 2022+ regardless of Polygon plan)
    try:
        dfs["spx_daily_cboe"] = download_spx_daily_cboe()
    except Exception as e:
        print(f"  WARNING: SPX daily CBOE download failed (optional): {e}")

    # 3. VIX daily (CBOE)
    try:
        dfs["vix_daily"] = download_cboe_csv(
            CBOE_VIX_URL, "VIX", "vix_daily.parquet"
        )
    except Exception as e:
        print(f"  ERROR: VIX download failed: {e}")
        errors.append(("vix_daily", str(e)))

    # 4. VVIX daily (CBOE)
    try:
        dfs["vvix_daily"] = download_cboe_csv(
            CBOE_VVIX_URL, "VVIX", "vvix_daily.parquet"
        )
    except Exception as e:
        print(f"  ERROR: VVIX download failed: {e}")
        errors.append(("vvix_daily", str(e)))

    # 5. VIX9D daily (CBOE — short-term vol for term structure feature)
    try:
        dfs["vix9d_daily"] = download_cboe_csv(
            CBOE_VIX9D_URL, "VIX9D", "vix9d_daily.parquet"
        )
    except Exception as e:
        print(f"  WARNING: VIX9D download failed (optional): {e}")
        # VIX9D is optional — term structure feature degrades to None if missing

    # Validate
    validate_downloads(dfs)

    # Write manifest
    write_manifest(dfs)

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"COMPLETED WITH {len(errors)} ERROR(S):")
        for name, err in errors:
            print(f"  [FAIL] {name}: {err}")
        if any(n in ("spx_5min", "spx_daily", "vix_daily") for n, _ in errors):
            print("\nCRITICAL: SPX 5-min, SPX daily, and VIX daily are required for A3.")
            print("Fix the errors above before running A3 training.")
            sys.exit(1)
    else:
        print("ALL DOWNLOADS SUCCESSFUL")

    print(f"\nFiles in {DATA_DIR}:")
    for f in sorted(DATA_DIR.iterdir()):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f.name:40s} {size_mb:.1f} MB")
    print("=" * 60)
    print("\nNext step: run Phase A3 training script")
    print("  python -m scripts.train_direction_model")


if __name__ == "__main__":
    main()
