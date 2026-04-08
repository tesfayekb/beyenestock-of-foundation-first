# Performance Strategy

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines performance targets and optimization strategies.

## Scope

Frontend rendering, API response times, database queries, asset loading.

## Performance Targets

| Metric | Target |
|--------|--------|
| First Contentful Paint | < 1.5s |
| Largest Contentful Paint | < 2.5s |
| Time to Interactive | < 3.0s |
| Cumulative Layout Shift | < 0.1 |
| API response (p95) | < 500ms |
| Database query (p95) | < 100ms |
| Bundle size (initial) | < 200KB gzipped |

## Strategies

### Frontend
- Code splitting by route (React.lazy)
- Tree shaking (Vite default)
- Image optimization (lazy loading, WebP)
- Minimize re-renders (React.memo, useMemo, useCallback where measured)

### API
- Minimize round trips (batch queries)
- Use Supabase real-time only where needed
- Paginate all list endpoints

### General
- No premature optimization — measure first
- Performance budgets enforced in CI
- Monitor Core Web Vitals in production

## Dependencies

- [Architecture Overview](../01-architecture/architecture-overview.md)

## Used By / Affects

All modules with UI or data operations.

## Risks If Changed

MEDIUM — loosening targets degrades user experience.

## Related Documents

- [Database Performance](database-performance.md)
- [Caching Strategy](caching-strategy.md)
