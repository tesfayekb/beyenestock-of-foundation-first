# backend/scripts/

Standalone scripts for one-time data operations and model training.
These are NOT wired into the production scheduler.

## Usage

Run from the `backend/` directory:
```bash
cd backend
python -m scripts.download_historical_data  # Phase A2: download training data
python -m scripts.train_direction_model     # Phase A3: train LightGBM model (not yet built)
```

## Scripts

| Script | Purpose | When to run |
|---|---|---|
| `download_historical_data.py` | Download SPX/VIX/VVIX historical data for ML training | Once before A3 training |

## Data directory

Downloaded data is saved to `backend/data/historical/`.
This directory is in `.gitignore` — files are NOT committed to git.

After downloading, the following files should exist:
- `spx_5min.parquet` — SPX 5-minute bars 2020-2026 (~118k rows)
- `spx_daily.parquet` — SPX daily OHLCV 2010-2026 (~3700 rows)
- `vix_daily.parquet` — VIX daily 2010-2026 (~3700 rows)
- `vvix_daily.parquet` — VVIX daily 2010-2026 (~3700 rows)
- `vix9d_daily.parquet` — VIX9D daily 2010-2026 (~3700 rows, optional)
- `download_manifest.json` — metadata and row counts
