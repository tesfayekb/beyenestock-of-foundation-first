# Input Validation and Sanitization

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines enforced rules for validating, sanitizing, and safely handling all input entering the system.

## Scope

All external input sources:

- Forms
- API payloads
- URL parameters (query + path)
- Headers
- Cookies
- File uploads
- External integrations

## Enforcement Rule (CRITICAL)

- All input MUST follow these rules
- Any violation results in an **INVALID** implementation
- No input may be trusted without validation and sanitization
- Validation rules override convenience or performance

## Input Handling Pipeline

All input must follow this sequence:

1. **Normalize**
2. **Validate**
3. **Sanitize**
4. **Authorize** (if applicable)
5. **Process**

## Normalization

- Trim whitespace
- Normalize casing where applicable (e.g., emails)
- Canonicalize formats before validation

## Validation Rules

- All input MUST be validated server-side
- Client-side validation is UX only
- Use Zod schemas for all validation
- Validation schemas are shared between client and server
- Reject unknown fields (strict parsing)
- No implicit type coercion unless explicitly defined
- All fields must have explicit constraints (length, format, type)

## Sanitization Rules

- **HTML:** strip all tags unless explicitly allowlisted
- **Output encoding** required for any rendered content
- **URLs:** allow only safe protocols (`https://`)
- **JSON:** strict parsing, reject malformed payloads
- **File uploads:**
  - Validate MIME type, extension, and size
  - Store outside executable paths
  - Prevent direct execution
- **Prevent injection:**
  - No string concatenation in queries
  - Always use parameterized queries

## File Upload Security

- Enforce file size limits
- Restrict allowed MIME types
- Store files in isolated storage
- Do not trust client-provided metadata
- (Optional) Integrate scanning for malicious content

## Rate Limiting Integration

- Apply rate limiting at API boundary
- Enforce per-IP and per-user limits
- Critical endpoints (auth, password reset) must have stricter limits

## Forbidden Patterns

- Dynamic query construction via string concatenation
- Trusting client-side validation
- Using unvalidated input in business logic
- Unsafe parsing (`eval`, dynamic execution)
- Accepting unknown fields without validation

Violations = **INVALID** implementation.

## Validation Schema Pattern

```typescript
const createUserSchema = z.object({
  email: z.string().email().max(255),
  name: z.string().min(1).max(100).trim(),
  role: z.enum(['admin', 'moderator', 'user']).optional(),
}).strict();
```

## Error Handling

- Never expose internal errors to the client
- Return structured errors: `{ error: string, field?: string }`
- Log full error details server-side with context

## Dependencies

- [Security Architecture](security-architecture.md)
- [API Module](../04-modules/api.md)

## Used By / Affects

All modules that accept or process external input.

## Risks If Changed

HIGH — improper validation or sanitization enables injection, XSS, and system compromise.

## Related Documents

- [Security Architecture](security-architecture.md)
- [API Module](../04-modules/api.md)
