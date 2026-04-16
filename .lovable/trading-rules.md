# Trading System — Lovable Constraint Rules

## Scope
These rules apply ONLY to trading system work (trading-docs/, src/pages/admin/trading/, src/components/trading/, src/hooks/trading/).

## Hard Rules

1. **DO NOT modify foundation docs/** — trading documentation lives in `trading-docs/` only.
2. **DO NOT modify existing foundation tables** — except the approved ALTER on `profiles` (Part 4.1 of MARKETMUSE_MASTER.md).
3. **All new trading tables use `trading_` prefix** — completely isolated from foundation tables.
4. **Trading health is SEPARATE from system health** — `trading_system_health` is NOT `system_health_snapshots`. Never mix them.
5. **Follow existing frontend patterns exactly** — `PageHeader`, `StatCard`, `LoadingSkeleton`, `ErrorState`, `RequirePermission`, lazy loading, `useQuery`.
6. **All trading pages are permission-gated** — minimum `trading.view`, configuration requires `trading.configure`.
7. **Never expose Tradier API keys in frontend** — encrypted storage only, display last 4 chars max.
8. **Kill-switch requires `trading.kill_switch` permission** — separate from `trading.admin`.
9. **All automated trading actions logged to `audit_logs`** — with `correlation_id` linking to `job_executions`.
10. **RLS on every trading table** — `service_role` writes, `authenticated` reads.

## Reading Order for Trading Tasks

1. `MARKETMUSE_MASTER.md` — the single source of truth for the trading system
2. `trading-docs/` — trading-specific documentation (this folder)
3. `docs/` — foundation governance (do not modify, only reference)

## Build Phase Reference

See MARKETMUSE_MASTER.md Part 11 for the 7-phase build order:
- Phase 1: Data Infrastructure (Weeks 1–2)
- Phase 2: Virtual Trade Engine (Weeks 3–5)
- Phase 3: Admin Console (Weeks 6–7)
- Phase 4: Paper Phase (Weeks 8–14)
- Phase 5: Live Execution (Week 15+)
- Phase 6: Learning Engine (Parallel with Phase 5)
- Phase 7: Phase 3 Sizing (Month 6+)
