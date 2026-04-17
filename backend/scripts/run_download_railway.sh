#!/bin/bash
# Run historical data download on Railway one-off instance
# Usage: railway run bash scripts/run_download_railway.sh
set -e
cd /app
echo "Starting Phase A2 historical data download..."
python -m scripts.download_historical_data
echo "Done. Files:"
ls -lh data/historical/
