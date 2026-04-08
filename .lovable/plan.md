

## Plan: Upgrade Architecture Overview to A+ Institutional Grade

### What changes
Replace the current `docs/01-architecture/architecture-overview.md` with the user-provided A+ version that transforms it from a generic overview into a top-level architectural contract.

### Key additions over current file
1. **Trust boundaries** — explicit classification (browser=untrusted, edge=trusted, service role=privileged)
2. **Canonical request flow** — 10-step standard path from user action through audit/monitoring
3. **Cross-cutting concerns** — auth, RBAC, audit, validation, error handling, monitoring
4. **Security boundary rules** — no client-side trust, no service role in client, no RLS bypass
5. **Dependency rules** — no hidden coupling, shared services tracked, consistent layer direction
6. **Operational rules** — retry, idempotency, error propagation, health signals
7. **Expanded communication table** — with enforcement rules per path
8. **Expanded architecture layers diagram** — 4-layer with descriptions

### Files modified
- `docs/01-architecture/architecture-overview.md` — full replacement with A+ version

### No other files affected
The existing cross-references from other docs already point to this file correctly. No new links needed.

