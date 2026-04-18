# Trading System — System State
Owner: tesfayekb | Last Updated: 2026-04-18 | Status: ACTIVE

## Current Phase
trading_phase: phase_1_stabilizing
code_generation: allowed
paper_trading: active
live_trading: blocked_until_90day_AB_test_passes
data_feeds: active
tradier_connection: active_sandbox
databento_opra: active
kelly_sizing: active
deployment: railway_diplomatic-mercy

## What Is Deployed and Working
- GEX/ZG regime classifier (rule-based, VVIX Z-score)
- Iron condor execution via Tradier sandbox
- Databento OPRA feed (fixed April 2026, real SPXW symbols)
- Kelly position sizing (activates at 20 closed trades)
- Dynamic spread width B1, asymmetric wings B2, exits B3
- Session management, health monitoring
- Supabase outcome tracking (Phase A1)

## What Is Next (Phase 2)
- Phase 2A: Catalyst gate + Iron Butterfly + Long Straddle
- Phase 2B: Bull/Bear debit spreads
- Phase 2C: Multi-agent AI morning brief (backend_agents/)

## Phase Gate for Real Capital Deployment
- Paper trading A/B test: 90 days, Portfolio B must show ≥+8% annualized uplift
- Minimum 100 closed paper trades for meta-label model
- All 7 market conditions covered by strategy library

## Multi-User Policy
- Phase 4: 1-3 invited users, read-only dashboard + optional paper mirror
- No subscription billing until system proven
- Real-broker mirroring requires governance/disclaimer review first

## Sizing Phase
current_sizing_phase: 1
core_risk_pct: 0.005
satellite_risk_pct: 0.0025
margin_enabled: false
daily_loss_limit: -3%_hardcoded_no_override
