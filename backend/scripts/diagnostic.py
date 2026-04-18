"""Monday morning system diagnostic.

Run via:
    railway run python -m scripts.diagnostic

Prints a snapshot of:
    - Databento OPRA tail (3 most recent trades)
    - Today's economic calendar (if written)
    - Last 3 prediction outputs
    - Last 3 trading positions
    - Current GEX values
    - Feature flag status
    - Closed paper-trade count vs activation thresholds
"""
import json
import os
import sys

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

import redis  # noqa: E402

from db import get_client  # noqa: E402

r = redis.from_url(os.environ["REDIS_URL"])

# Databento
entries = r.lrange("databento:opra:trades", -3, -1)
print("=== Databento (most recent 3) ===")
for e in entries:
    d = json.loads(e)
    print(
        f"  symbol={d.get('symbol')!r} "
        f"price={d.get('price')} strike={d.get('strike')}"
    )

# Calendar
cal = r.get("calendar:today:intel")
if cal:
    c = json.loads(cal)
    print(
        f"\n=== Calendar: {c['day_classification']} "
        f"({len(c['events'])} events, "
        f"{len(c['earnings'])} earnings) ==="
    )
    for ev in c.get("events", []):
        marker = "MAJOR" if ev["is_major"] else "minor"
        print(f"  {marker}: {ev['event']}")
else:
    print("\n=== Calendar: NOT YET WRITTEN ===")

# Predictions
r2 = (
    get_client()
    .table("trading_prediction_outputs")
    .select("predicted_at,no_trade_signal,direction,no_trade_reason")
    .order("predicted_at", desc=True)
    .limit(3)
    .execute()
)
print("\n=== Last 3 predictions ===")
for p in r2.data or []:
    print(
        f"  {p['predicted_at']} no_trade={p['no_trade_signal']} "
        f"reason={p.get('no_trade_reason')} dir={p['direction']}"
    )

# Positions
r3 = (
    get_client()
    .table("trading_positions")
    .select("id,strategy_type,entry_at,status,net_pnl")
    .order("entry_at", desc=True)
    .limit(3)
    .execute()
)
print("\n=== Last 3 positions ===")
for p in r3.data or []:
    print(
        f"  {p['entry_at']} {p['strategy_type']} "
        f"{p['status']} pnl={p.get('net_pnl')}"
    )

# GEX
print("\n=== GEX values ===")
for k in [
    "gex:net",
    "gex:confidence",
    "gex:flip_zone",
    "gex:nearest_wall",
]:
    print(f"  {k}: {r.get(k)}")

# Feature flags
print("\n=== Feature Flag Status ===")
flags = [
    "agents:ai_synthesis:enabled",
    "agents:flow_agent:enabled",
    "agents:sentiment_agent:enabled",
    "strategy:iron_butterfly:enabled",
    "strategy:long_straddle:enabled",
    "strategy:ai_hint_override:enabled",
]
for f in flags:
    v = r.get(f)
    status = "ON" if v in ("true", b"true") else "OFF"
    print(f"  {status}  {f}")

# Trade count
closed = (
    get_client()
    .table("trading_positions")
    .select("id", count="exact")
    .eq("status", "closed")
    .eq("position_mode", "virtual")
    .execute()
)
print(f"\n=== Closed paper trades: {closed.count} ===")
print(
    "Thresholds: 5=butterfly, "
    "20=kelly+straddle+flow+sentiment, "
    "40=ai_hint, 100=meta_label"
)
