# Caching Strategy

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines caching patterns to reduce unnecessary data fetching.

## Scope

Client-side caching, API-level caching, CDN caching.

## Caching Layers

### Client-Side (TanStack Query)
- Default stale time: 5 minutes for read-heavy data
- Immediate invalidation on mutations
- Optimistic updates for user-initiated actions
- Cache keys follow module naming: `['module', 'resource', id]`

### API-Level
- Edge function responses: Cache-Control headers where appropriate
- Static configuration data: long cache (1 hour+)
- User-specific data: no caching at CDN level

### CDN / Static Assets
- Vite content-hashed filenames for cache busting
- Long-lived cache for static assets (1 year)
- Service worker for offline-capable assets (if needed)

## Cache Invalidation Rules

- Mutation → invalidate related queries immediately
- Role change → invalidate all permission-dependent queries
- Configuration change → invalidate all config queries
- Never rely on time-based expiry alone for security-sensitive data

## Dependencies

- [Performance Strategy](performance-strategy.md)

## Used By / Affects

All modules with data fetching.

## Risks If Changed

LOW-MEDIUM — incorrect caching causes stale data display.

## Related Documents

- [Performance Strategy](performance-strategy.md)
- [Database Performance](database-performance.md)
