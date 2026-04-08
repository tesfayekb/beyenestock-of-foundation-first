# API Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines the API layer: conventions, error handling, and edge function patterns.

## Scope

All API endpoints: Supabase client queries, edge functions, REST conventions.

## Key Rules

- All API access goes through Supabase client (RLS enforced)
- Edge functions for server-side logic (email, payments, external APIs)
- Consistent error response format
- All inputs validated with Zod schemas
- All responses typed

## API Conventions

### Error Response Format

```json
{
  "error": "Human-readable message",
  "code": "ERROR_CODE",
  "field": "optional_field_name"
}
```

### Edge Function Pattern

```typescript
// Standard edge function structure
serve(async (req) => {
  // 1. Authenticate
  // 2. Validate input
  // 3. Check authorization
  // 4. Execute business logic
  // 5. Log audit event
  // 6. Return response
});
```

### Response Codes

| Code | Usage |
|------|-------|
| 200 | Success |
| 201 | Created |
| 400 | Validation error |
| 401 | Not authenticated |
| 403 | Not authorized |
| 404 | Not found |
| 429 | Rate limited |
| 500 | Internal error (never expose details) |

## Shared Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `apiError(code, message)` | Constructs error response | All edge functions |
| `validateRequest(schema, body)` | Validates request body | All edge functions |
| `authenticateRequest(req)` | Extracts and validates auth token | All edge functions |

## Events

| Event | Emitted When | Consumed By |
|-------|-------------|-------------|
| `api.error` | API returns 5xx | health-monitoring |
| `api.rate_limited` | Request rate limited | audit-logging |

## Jobs

None owned by this module.

## Permissions

API module enforces permissions defined by other modules. It does not define its own permissions.

## Dependencies

- [Auth Module](auth.md)
- [RBAC Module](rbac.md)
- [Input Validation](../02-security/input-validation-and-sanitization.md)

## Used By / Affects

All frontend modules use the API layer.

## Risks If Modified

HIGH — API changes affect all client-server communication.

## Related Documents

- [Input Validation](../02-security/input-validation-and-sanitization.md)
- [Auth Module](auth.md)
- [Route Index](../07-reference/route-index.md)
