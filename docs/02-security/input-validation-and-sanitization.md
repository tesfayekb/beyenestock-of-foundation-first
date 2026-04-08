# Input Validation and Sanitization

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines rules for validating and sanitizing all user input.

## Scope

All user-facing inputs: forms, URL parameters, API payloads, file uploads.

## Rules

### Validation

1. All input MUST be validated server-side (edge functions / RLS)
2. Client-side validation is for UX only — never a security boundary
3. Use Zod schemas for type-safe validation
4. Validation schemas are defined once and shared between client and server
5. Reject unknown fields — no permissive parsing

### Sanitization

1. HTML content: strip all tags unless explicitly allowlisted
2. SQL: never construct queries with string concatenation (use parameterized queries)
3. URLs: validate protocol (only `https://`)
4. File uploads: validate MIME type, file size, and extension server-side
5. JSON: parse with strict schemas, reject malformed payloads

### Validation Schema Pattern

```typescript
// Shared validation schema
const createUserSchema = z.object({
  email: z.string().email().max(255),
  name: z.string().min(1).max(100).trim(),
  role: z.enum(['admin', 'moderator', 'user']).optional(),
});

// Use in both client forms AND edge functions
```

### Error Handling

- Never expose internal errors to the client
- Return structured error responses: `{ error: string, field?: string }`
- Log full errors server-side with context

## Dependencies

- [Security Architecture](security-architecture.md)
- [API Module](../04-modules/api.md)

## Used By / Affects

All modules that accept user input.

## Risks If Changed

HIGH — input validation is a primary security boundary.

## Related Documents

- [Security Architecture](security-architecture.md)
- [API Module](../04-modules/api.md)
