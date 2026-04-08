# Database Performance

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines database performance rules and optimization patterns.

## Scope

PostgreSQL database: schema design, queries, indexes.

## Rules

### Schema Design
- Normalize to 3NF minimum; denormalize only with documented justification
- Use appropriate column types (no `text` for booleans, no `varchar` without length)
- All foreign keys indexed
- Timestamps on every table (`created_at`, `updated_at`)
- Soft delete where appropriate (`deleted_at`)

### Query Performance
- No `SELECT *` — always specify columns
- All queries must use indexes (verify with `EXPLAIN ANALYZE`)
- No N+1 queries — use joins or batch fetching
- Paginate all list queries (cursor-based preferred)
- Limit result sets (max 100 rows per page)

### Indexing Strategy
- Primary keys: automatic
- Foreign keys: always indexed
- Columns used in WHERE/ORDER BY: indexed
- Composite indexes for common query patterns
- Review index usage periodically (drop unused)

### Connection Management
- Use connection pooling (Supabase default)
- Close connections properly in edge functions
- No long-running transactions

## Dependencies

- [Performance Strategy](performance-strategy.md)
- [Architecture Overview](../01-architecture/architecture-overview.md)

## Used By / Affects

All modules that interact with the database.

## Risks If Changed

MEDIUM — database changes can cause cascading performance issues.

## Related Documents

- [Performance Strategy](performance-strategy.md)
- [Caching Strategy](caching-strategy.md)
