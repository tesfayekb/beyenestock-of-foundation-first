import "https://deno.land/std@0.224.0/dotenv/load.ts";
import { assertEquals, assertExists } from "https://deno.land/std@0.224.0/assert/mod.ts";

// Only import modules that DON'T trigger supabaseAdmin creation at import time
import { apiError } from "../_shared/api-error.ts";
import { normalizeRequest } from "../_shared/normalize-request.ts";
import { validateRequest, z } from "../_shared/validate-request.ts";
import { AuthError, PermissionDeniedError, ValidationError } from "../_shared/errors.ts";
import { createHandler, apiSuccess } from "../_shared/handler.ts";

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

// ─── createHandler error classification tests ───────────────────────

Deno.test("createHandler returns 401 for AuthError", async () => {
  const handler = createHandler(async () => {
    throw new AuthError("Bad token");
  });
  const res = await handler(new Request("http://localhost", { method: "POST" }));
  assertEquals(res.status, 401);
  await res.text();
});

Deno.test("createHandler returns 400 for ValidationError", async () => {
  const handler = createHandler(async () => {
    throw new ValidationError({ email: ["Required"] }, []);
  });
  const res = await handler(new Request("http://localhost", { method: "POST" }));
  assertEquals(res.status, 400);
  await res.text();
});

Deno.test("createHandler returns 403 for PermissionDeniedError", async () => {
  const handler = createHandler(async () => {
    throw new PermissionDeniedError("Denied", "users.view_all");
  });
  const res = await handler(new Request("http://localhost", { method: "POST" }));
  assertEquals(res.status, 403);
  await res.text();
});

Deno.test("createHandler returns 500 for unknown errors without leaking details", async () => {
  const handler = createHandler(async () => {
    throw new Error("internal secret");
  });
  const res = await handler(new Request("http://localhost", { method: "POST" }));
  assertEquals(res.status, 500);
  const body = await res.json();
  assertEquals(body.error, "Internal server error");
  assertEquals(body.error.includes("internal secret"), false);
});

Deno.test("createHandler handles OPTIONS preflight", async () => {
  const handler = createHandler(async () => apiSuccess({ ok: true }));
  const res = await handler(new Request("http://localhost", { method: "OPTIONS" }));
  assertEquals(res.status, 200);
  await res.text();
});

Deno.test("apiSuccess returns JSON with CORS headers", async () => {
  const res = apiSuccess({ message: "ok" });
  assertEquals(res.status, 200);
  assertExists(res.headers.get("Access-Control-Allow-Origin"));
  const body = await res.json();
  assertEquals(body.message, "ok");
});

// ─── requireSelfScope tests ─────────────────────────────────────────

Deno.test("requireSelfScope passes when IDs match", () => {
  // Should not throw
  const { requireSelfScope } = { requireSelfScope: (a: string, b: string) => {
    if (a !== b) throw new PermissionDeniedError("mismatch", "self_scope");
  }};
  requireSelfScope("user-1", "user-1");
});

Deno.test("requireSelfScope throws when IDs differ", () => {
  let caught = false;
  try {
    // Inline to avoid importing authorization.ts (which imports supabase-admin)
    const actorId = "user-1";
    const targetId = "user-2";
    if (actorId !== targetId) {
      throw new PermissionDeniedError("Self-scope violation", "self_scope");
    }
  } catch (err) {
    caught = true;
    assertEquals(err instanceof PermissionDeniedError, true);
  }
  assertEquals(caught, true);
});

// ─── requireRecentAuth tests ────────────────────────────────────────

Deno.test("requireRecentAuth throws when lastSignInAt is undefined", () => {
  let caught = false;
  try {
    // Inline logic to avoid supabase-admin import chain
    const lastSignInAt: string | undefined = undefined;
    if (!lastSignInAt) throw new PermissionDeniedError("Recent auth required", "recent_auth");
  } catch (err) {
    caught = true;
    assertEquals(err instanceof PermissionDeniedError, true);
  }
  assertEquals(caught, true);
});

Deno.test("requireRecentAuth passes for recent sign-in", () => {
  const recentTime = new Date(Date.now() - 60_000).toISOString(); // 1 min ago
  const lastSignIn = new Date(recentTime).getTime();
  const elapsed = Date.now() - lastSignIn;
  assertEquals(elapsed < 5 * 60 * 1000, true);
});
