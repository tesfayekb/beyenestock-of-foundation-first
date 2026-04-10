import "https://deno.land/std@0.224.0/dotenv/load.ts";
import { assertEquals, assertExists } from "https://deno.land/std@0.224.0/assert/mod.ts";

// Only import modules that DON'T trigger supabaseAdmin creation at import time
import { apiError } from "../_shared/api-error.ts";
import { normalizeRequest } from "../_shared/normalize-request.ts";
import { validateRequest, ValidationError, z } from "../_shared/validate-request.ts";
import { AuthError } from "../_shared/authenticate-request.ts";
import { PermissionDeniedError } from "../_shared/authorization.ts";

// Handler imports authorization.ts which imports supabase-admin.ts at module level.
// We must test handler via a lightweight reimplementation of the error classification logic.

// ─── apiError tests ─────────────────────────────────────────────────

Deno.test("apiError returns structured JSON with correct status", async () => {
  const res = apiError(403, "Permission denied");
  assertEquals(res.status, 403);
  const body = await res.json();
  assertEquals(body.error, "Permission denied");
  assertEquals(body.code, "FORBIDDEN");
});

Deno.test("apiError includes field and correlation_id when provided", async () => {
  const res = apiError(400, "Invalid email", {
    code: "VALIDATION_ERROR",
    field: "email",
    correlationId: "test-123",
  });
  const body = await res.json();
  assertEquals(body.field, "email");
  assertEquals(body.correlation_id, "test-123");
  assertEquals(body.code, "VALIDATION_ERROR");
});

Deno.test("apiError includes CORS headers", () => {
  const res = apiError(401, "Unauthorized");
  assertExists(res.headers.get("Access-Control-Allow-Origin"));
});

Deno.test("apiError maps status codes correctly", async () => {
  const cases: [number, string][] = [
    [400, "BAD_REQUEST"],
    [401, "UNAUTHORIZED"],
    [403, "FORBIDDEN"],
    [404, "NOT_FOUND"],
    [409, "CONFLICT"],
    [429, "RATE_LIMITED"],
    [500, "INTERNAL_ERROR"],
  ];
  for (const [status, expectedCode] of cases) {
    const res = apiError(status, "test");
    const body = await res.json();
    assertEquals(body.code, expectedCode, `Status ${status} should map to ${expectedCode}`);
  }
});

// ─── normalizeRequest tests ─────────────────────────────────────────

Deno.test("normalizeRequest trims strings", () => {
  const result = normalizeRequest({ name: "  John  ", age: 30 });
  assertEquals(result.name, "John");
  assertEquals(result.age, 30);
});

Deno.test("normalizeRequest lowercases email fields", () => {
  const result = normalizeRequest({ email: " User@Example.COM " });
  assertEquals(result.email, "user@example.com");
});

Deno.test("normalizeRequest does not alter non-string values", () => {
  const result = normalizeRequest({ count: 42, active: true, tags: null });
  assertEquals(result.count, 42);
  assertEquals(result.active, true);
  assertEquals(result.tags, null);
});

Deno.test("normalizeRequest does not lowercase non-email string fields", () => {
  const result = normalizeRequest({ display_name: " Alice Bob " });
  assertEquals(result.display_name, "Alice Bob");
});

Deno.test("normalizeRequest handles empty strings", () => {
  const result = normalizeRequest({ name: "   " });
  assertEquals(result.name, "");
});

// ─── validateRequest tests ──────────────────────────────────────────

Deno.test("validateRequest returns typed data on valid input", () => {
  const schema = z.object({ name: z.string().min(1) }).strict();
  const result = validateRequest(schema, { name: "Alice" });
  assertEquals(result.name, "Alice");
});

Deno.test("validateRequest throws ValidationError on invalid input", () => {
  const schema = z.object({ name: z.string().min(1) }).strict();
  let caught = false;
  try {
    validateRequest(schema, { name: "" });
  } catch (err) {
    caught = true;
    assertEquals(err instanceof ValidationError, true);
  }
  assertEquals(caught, true);
});

Deno.test("validateRequest rejects unknown fields in strict mode", () => {
  const schema = z.object({ name: z.string() }).strict();
  let caught = false;
  try {
    validateRequest(schema, { name: "Alice", extra: "field" });
  } catch (err) {
    caught = true;
    assertEquals(err instanceof ValidationError, true);
  }
  assertEquals(caught, true);
});

Deno.test("validateRequest provides field-level errors", () => {
  const schema = z.object({
    email: z.string().email(),
    name: z.string().min(1),
  }).strict();
  try {
    validateRequest(schema, { email: "not-an-email", name: "" });
  } catch (err) {
    if (err instanceof ValidationError) {
      assertExists(err.fieldErrors.email);
      assertExists(err.fieldErrors.name);
    }
  }
});

// ─── Error class tests ──────────────────────────────────────────────

Deno.test("AuthError has correct name", () => {
  const err = new AuthError("test");
  assertEquals(err.name, "AuthError");
  assertEquals(err.message, "test");
});

Deno.test("PermissionDeniedError has correct name and key", () => {
  const err = new PermissionDeniedError("denied", "users.view_all");
  assertEquals(err.name, "PermissionDeniedError");
  assertEquals(err.permissionKey, "users.view_all");
});

Deno.test("ValidationError has field and form errors", () => {
  const err = new ValidationError({ email: ["Required"] }, ["Global error"]);
  assertEquals(err.name, "ValidationError");
  assertExists(err.fieldErrors.email);
  assertEquals(err.formErrors.length, 1);
});
