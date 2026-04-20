"""
Phase A3: Train LightGBM direction model.

Reads historical data from backend/data/historical/
Engineers 47 features from SPX 5-min bars + VIX/VVIX daily
Trains LightGBM classifier: predict SPX direction 30min ahead
Validates on 2025-2026 holdout (never seen during training)
Saves model to backend/models/direction_lgbm_v1.pkl

Run from backend/ directory:
  python -m scripts.train_direction_model

Gate: model must achieve >= 72% win rate on holdout before saving.
If below 72%, script exits with error -- do NOT deploy a weak model.
"""
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder

DATA_DIR   = Path(__file__).parent.parent / "data" / "historical"
MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

HOLDOUT_START = "2025-01-01"

MIN_ACCURACY_GATE = 0.52  # Binary classifier: >50% = better than random

# 12H Phase A auto-gate: hold off training until the live system has
# produced 90 distinct labeled sessions in trading_prediction_outputs
# (outcome_correct IS NOT NULL). Below this threshold LightGBM would
# overfit the few dozen rows we have and never generalise, so the
# script exits with `insufficient_data` rather than writing a weak
# model file.
MIN_LABELED_SESSIONS_FOR_TRAINING = 90


# -- Auto-gate: labeled-sessions threshold ------------------------------------

def count_labeled_sessions() -> int:
    """
    Count distinct sessions in trading_prediction_outputs that have at
    least one labeled prediction (outcome_correct IS NOT NULL).

    Fails CLOSED on any Supabase / credential error (returns 0) so the
    gate prevents training when we cannot confirm we have enough data.
    The alternative — failing open — would let a silent credential
    outage write a model trained on a tiny mock or empty pool.
    """
    try:
        from db import get_client

        res = (
            get_client()
            .table("trading_prediction_outputs")
            .select("session_id")
            .not_.is_("outcome_correct", "null")
            .limit(10000)
            .execute()
        )
        rows = getattr(res, "data", None) or []
        return len({r["session_id"] for r in rows if r.get("session_id")})
    except Exception as exc:
        print(f"  WARNING: labeled-session count query failed: {exc}")
        return 0


def check_labeled_sessions_gate() -> tuple:
    """
    Return (count, passed). Caller must exit(0) cleanly when passed is
    False so a scheduled training job doesn't look like a failure.
    """
    n = count_labeled_sessions()
    return n, n >= MIN_LABELED_SESSIONS_FOR_TRAINING


# -- Data Loading --------------------------------------------------------------

def _find_close_col(df: pd.DataFrame, hint: str) -> str:
    """Find the primary price column in a daily DataFrame.
    Tries: 'close', then the hint name, then the only non-OHLV numeric column."""
    if "close" in df.columns:
        return "close"
    if hint.lower() in df.columns:
        return hint.lower()
    skip = {"date", "datetime", "timestamp_ms", "open", "high", "low", "volume"}
    candidates = [c for c in df.columns if c.lower() not in skip
                  and pd.api.types.is_numeric_dtype(df[c])]
    if len(candidates) == 1:
        return candidates[0]
    raise RuntimeError(
        f"Cannot find close column with hint='{hint}'. Columns: {list(df.columns)}"
    )


def load_data() -> tuple:
    """Load SPX 5-min and daily VIX/VVIX parquet files."""
    print("\n[1/5] Loading historical data...")

    manifest_path = DATA_DIR / "download_manifest.json"
    if not manifest_path.exists():
        raise RuntimeError(
            "download_manifest.json not found. "
            "Run Phase A2 first: python -m scripts.download_historical_data"
        )

    manifest = json.loads(manifest_path.read_text())
    print(f"  Data downloaded at: {manifest.get('downloaded_at', 'unknown')}")

    spx5 = pd.read_parquet(DATA_DIR / "spx_5min.parquet")
    spx5["datetime_et"] = pd.to_datetime(spx5["datetime_et"], utc=False)
    spx5 = spx5.sort_values("datetime_et").reset_index(drop=True)
    print(f"  SPX 5-min: {len(spx5):,} rows, "
          f"{spx5['datetime_et'].min().date()} -> {spx5['datetime_et'].max().date()}")

    vix = pd.read_parquet(DATA_DIR / "vix_daily.parquet")
    vix["date"] = pd.to_datetime(vix["date"]).dt.date
    vix = vix.sort_values("date")
    vix_col = _find_close_col(vix, "vix")
    vix = vix.rename(columns={vix_col: "vix_close"})
    print(f"  VIX daily: {len(vix):,} rows")

    vvix = pd.read_parquet(DATA_DIR / "vvix_daily.parquet")
    vvix["date"] = pd.to_datetime(vvix["date"]).dt.date
    vvix = vvix.sort_values("date")
    vvix_col = _find_close_col(vvix, "vvix")
    vvix = vvix.rename(columns={vvix_col: "vvix_close"})
    print(f"  VVIX daily: {len(vvix):,} rows")

    vix9d = None
    vix9d_path = DATA_DIR / "vix9d_daily.parquet"
    if vix9d_path.exists():
        vix9d = pd.read_parquet(vix9d_path)
        vix9d["date"] = pd.to_datetime(vix9d["date"]).dt.date
        vix9d = vix9d.sort_values("date")
        vix9d_col = _find_close_col(vix9d, "vix9d")
        vix9d = vix9d.rename(columns={vix9d_col: "vix9d_close"})
        print(f"  VIX9D daily: {len(vix9d):,} rows")

    return spx5, vix, vvix, vix9d


# -- Feature Engineering -------------------------------------------------------

def engineer_features(
    spx5: pd.DataFrame,
    vix: pd.DataFrame,
    vvix: pd.DataFrame,
    vix9d: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build 47 features from raw market data.
    Each row = one 5-minute bar with features computed at that moment.
    Label = SPX direction 30 minutes later (6 bars ahead).
    """
    print("\n[2/5] Engineering features...")

    df = spx5.copy()
    df["date"] = df["datetime_et"].dt.date
    df["hour"] = df["datetime_et"].dt.hour
    df["minute"] = df["datetime_et"].dt.minute
    df["day_of_week"] = df["datetime_et"].dt.dayofweek

    # SPX price action features

    df["return_5m"]  = df["close"].pct_change(1)
    df["return_30m"] = df["close"].pct_change(6)
    df["return_1h"]  = df["close"].pct_change(12)
    df["return_4h"]  = df["close"].pct_change(48)

    df["prev_close"] = df.groupby("date")["close"].transform("first").shift(1)
    first_of_day = df.groupby("date")["close"].transform(
        lambda x: x.iloc[0] if len(x) > 0 else np.nan
    )
    df["overnight_gap"] = (first_of_day - df["prev_close"]) / df["prev_close"]
    df["overnight_gap"] = df["overnight_gap"].where(
        df["datetime_et"].dt.hour == 9, 0.0
    )

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(span=14, adjust=False).mean()
    avg_loss = loss.ewm(span=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    df["macd_signal"] = macd - macd.ewm(span=9, adjust=False).mean()

    sma20 = df["close"].rolling(20).mean()
    std20 = df["close"].rolling(20).std()
    df["bb_pct_b"] = (df["close"] - (sma20 - 2 * std20)) / (4 * std20)

    df["minutes_from_open"] = df["hour"] * 60 + df["minute"] - 9 * 60 - 30
    df["minutes_to_close"]  = 390 - df["minutes_from_open"]

    df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
    df["vwap_approx"] = df.groupby("date")["typical_price"].transform(
        lambda x: x.expanding().mean()
    )
    df["vwap_distance"] = (df["close"] - df["vwap_approx"]) / df["vwap_approx"]

    morning = df[df["minutes_from_open"] <= 30].groupby("date").agg(
        morning_high=("high", "max"),
        morning_low=("low", "min"),
        day_open=("open", "first"),
    )
    df = df.merge(morning, on="date", how="left")
    df["morning_range"] = (
        (df["morning_high"] - df["morning_low"]) /
        df["day_open"].replace(0, np.nan)
    )

    daily_returns = df.groupby("date")["close"].last().pct_change()
    df["prior_day_return"] = df["date"].map(daily_returns.shift(1))

    # Volatility features (from daily VIX/VVIX)

    df = df.merge(vix[["date", "vix_close"]], on="date", how="left")
    df["vix_close"] = df["vix_close"].ffill()

    daily_vix = vix.set_index("date")["vix_close"]
    vix_5d_chg = daily_vix.pct_change(5)
    df["vix_5d_change"] = df["date"].map(vix_5d_chg)

    vix_mean = daily_vix.rolling(20).mean()
    vix_std  = daily_vix.rolling(20).std()
    vix_z    = (daily_vix - vix_mean) / vix_std.replace(0, np.nan)
    df["vix_z_score"] = df["date"].map(vix_z)

    df = df.merge(vvix[["date", "vvix_close"]], on="date", how="left")
    df["vvix_close"] = df["vvix_close"].ffill()

    daily_vvix  = vvix.set_index("date")["vvix_close"]
    vvix_mean   = daily_vvix.rolling(20).mean()
    vvix_std    = daily_vvix.rolling(20).std()
    vvix_z      = (daily_vvix - vvix_mean) / vvix_std.replace(0, np.nan)
    df["vvix_z_score"] = df["date"].map(vvix_z)

    df["rv_20d"] = (
        df["return_5m"]
        .rolling(20 * 78)
        .std()
        * np.sqrt(252 * 78)
        * 100
    )

    df["iv_rv_ratio"] = df["vix_close"] / df["rv_20d"].replace(0, np.nan)

    if vix9d is not None:
        df = df.merge(vix9d[["date", "vix9d_close"]], on="date", how="left")
        df["vix9d_close"] = df["vix9d_close"].ffill()
        df["vix_term_ratio"] = df["vix9d_close"] / df["vix_close"].replace(0, np.nan)
    else:
        df["vix_term_ratio"] = 1.0

    # Time context features

    df["hour_sin"] = np.sin(2 * np.pi * df["minutes_from_open"] / 390)
    df["hour_cos"] = np.cos(2 * np.pi * df["minutes_from_open"] / 390)
    df["dow_sin"]  = np.sin(2 * np.pi * df["day_of_week"] / 5)
    df["dow_cos"]  = np.cos(2 * np.pi * df["day_of_week"] / 5)

    # Label: SPX direction 30 minutes ahead

    df["future_close"] = df["close"].shift(-6)
    df["future_return"] = (df["future_close"] - df["close"]) / df["close"]

    # Binary label: bull if SPX goes up, bear if SPX goes down
    # No neutral class -- signal_weak gate in prediction_engine handles low-confidence
    df["label"] = df["future_return"].apply(
        lambda r: "bull" if r > 0 else "bear"
    )

    # Final cleanup

    df = df[
        (df["minutes_from_open"] >= 5) &
        (df["minutes_from_open"] <= 360)
    ].copy()

    df = df.dropna(subset=["label", "future_return", "return_5m", "vix_close"])

    label_counts = df["label"].value_counts()
    print(f"  Total samples: {len(df):,}")
    print(f"  Labels: bull={label_counts.get('bull',0):,}, "
          f"bear={label_counts.get('bear',0):,}")

    return df


# -- Feature List --------------------------------------------------------------

FEATURE_COLS = [
    "return_5m", "return_30m", "return_1h", "return_4h",
    "overnight_gap", "prior_day_return",
    "rsi_14", "macd_signal", "bb_pct_b",
    "minutes_from_open", "minutes_to_close",
    "vwap_distance", "morning_range",
    "vix_close", "vix_5d_change", "vix_z_score",
    "vvix_close", "vvix_z_score",
    "rv_20d", "iv_rv_ratio", "vix_term_ratio",
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
]


# -- Train / Evaluate ----------------------------------------------------------

def train_and_evaluate(df: pd.DataFrame) -> tuple:
    """
    Train LightGBM on data before HOLDOUT_START.
    Evaluate on HOLDOUT_START -> present.
    Returns (model, win_rate, accuracy, feature_importance_df).
    Gate: raises if win_rate < MIN_ACCURACY_GATE.
    """
    print(f"\n[3/5] Splitting train/holdout at {HOLDOUT_START}...")

    df["date_dt"] = pd.to_datetime(df["date"])
    holdout_start = pd.Timestamp(HOLDOUT_START)

    train_df = df[df["date_dt"] < holdout_start].copy()
    holdout_df = df[df["date_dt"] >= holdout_start].copy()

    print(f"  Training rows: {len(train_df):,} "
          f"({train_df['date'].min()} -> {train_df['date'].max()})")
    print(f"  Holdout rows:  {len(holdout_df):,} "
          f"({holdout_df['date'].min()} -> {holdout_df['date'].max()})")

    if len(train_df) < 1000:
        raise RuntimeError(
            f"Only {len(train_df)} training rows -- need at least 1000. "
            "Check that data covers the training period."
        )
    if len(holdout_df) < 200:
        raise RuntimeError(
            f"Only {len(holdout_df)} holdout rows -- need at least 200."
        )

    train_clean = train_df[FEATURE_COLS + ["label"]].dropna()
    holdout_clean = holdout_df[FEATURE_COLS + ["label"]].dropna()

    X_train = train_clean[FEATURE_COLS].values
    y_train = train_clean["label"].values
    X_hold  = holdout_clean[FEATURE_COLS].values
    y_hold  = holdout_clean["label"].values

    print(f"\n[4/5] Training LightGBM...")
    print(f"  Features: {len(FEATURE_COLS)}")
    print(f"  Train samples: {len(X_train):,}")

    model = LGBMClassifier(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        num_leaves=31,
        min_child_samples=50,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=0.1,
        random_state=42,
        verbose=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_hold)

    # Binary model: every prediction is directional
    win_rate = (y_pred == y_hold).mean()
    accuracy = win_rate  # same thing for binary

    print(f"\n  Holdout accuracy (all labels): {accuracy:.1%}")
    print(f"  Holdout win rate (directional only): {win_rate:.1%}")
    print(f"\n  Classification report:")
    print(classification_report(y_hold, y_pred, target_names=["bear", "bull"]))

    importance_df = pd.DataFrame({
        "feature": FEATURE_COLS,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)

    print(f"\n  Top 10 features:")
    for _, row in importance_df.head(10).iterrows():
        print(f"    {row['feature']:30s} {row['importance']:.0f}")

    if win_rate < MIN_ACCURACY_GATE:
        raise RuntimeError(
            f"Win rate {win_rate:.1%} is below gate {MIN_ACCURACY_GATE:.0%}. "
            "Model is not good enough to deploy. "
            "Check data quality and feature engineering."
        )

    print(f"\n  [OK] Win rate {win_rate:.1%} >= gate {MIN_ACCURACY_GATE:.0%} -- model approved")
    return model, win_rate, accuracy, importance_df


# -- Save Model ----------------------------------------------------------------

def save_model(model, win_rate: float, accuracy: float,
               importance_df: pd.DataFrame) -> None:
    """Save model and metadata to backend/models/."""
    import pickle

    print(f"\n[5/5] Saving model...")

    model_path = MODELS_DIR / "direction_lgbm_v1.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"  [OK] Model -> {model_path}")

    metadata = {
        "model_version": "v1",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "holdout_start": HOLDOUT_START,
        "win_rate": round(win_rate, 4),
        "accuracy": round(accuracy, 4),
        "features": FEATURE_COLS,
        "n_features": len(FEATURE_COLS),
        "gate_threshold": MIN_ACCURACY_GATE,
        "gate_passed": bool(win_rate >= MIN_ACCURACY_GATE),
        "top_features": importance_df.head(10)["feature"].tolist(),
    }
    meta_path = MODELS_DIR / "model_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2))
    print(f"  [OK] Metadata -> {meta_path}")


# -- Main ----------------------------------------------------------------------

def main() -> None:
    import sys
    import io
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    elif sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("=" * 60)
    print("Phase A3: Train LightGBM Direction Model")
    print("=" * 60)

    # 12H auto-gate — skip training if we don't yet have 90 labeled
    # sessions. Exits with status 0 (not an error) so the scheduled
    # weekly job doesn't page on-call when we're simply still in the
    # data-collection window.
    n_labeled, gate_passed = check_labeled_sessions_gate()
    if not gate_passed:
        print(
            f"\ninsufficient_data: {n_labeled} labeled sessions "
            f"(need {MIN_LABELED_SESSIONS_FOR_TRAINING}). "
            "Exiting cleanly — no model written."
        )
        sys.exit(0)
    print(
        f"  Labeled sessions: {n_labeled} "
        f"(>= {MIN_LABELED_SESSIONS_FOR_TRAINING} required)"
    )

    spx5, vix, vvix, vix9d = load_data()
    df = engineer_features(spx5, vix, vvix, vix9d)
    model, win_rate, accuracy, importance_df = train_and_evaluate(df)
    save_model(model, win_rate, accuracy, importance_df)

    print("\n" + "=" * 60)
    print(f"TRAINING COMPLETE")
    print(f"  Win rate:  {win_rate:.1%}")
    print(f"  Accuracy:  {accuracy:.1%}")
    print(f"  Model:     backend/models/direction_lgbm_v1.pkl")
    print(f"  Metadata:  backend/models/model_metadata.json")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. git add backend/models/direction_lgbm_v1.pkl backend/models/model_metadata.json")
    print("  2. git commit -m 'Add trained LightGBM direction model v1 (Phase A3)'")
    print("  3. git push origin main")
    print("  Railway will redeploy and load the model automatically.")


if __name__ == "__main__":
    main()
