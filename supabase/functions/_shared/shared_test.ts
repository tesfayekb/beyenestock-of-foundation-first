import "https://deno.land/std@0.224.0/dotenv/load.ts";
import { assertEquals, assertExists } from "https://deno.land/std@0.224.0/assert/mod.ts";

// Unit tests for shared helpers — import directly
import { apiError } from "../_shared/api-error.ts";
import { normalizeRequest } from "../_shared/normalize-request.ts";
import { validateRequest, ValidationError, z } from "../_shared/validate-request.ts";
import { AuthError } from "../_shared/authenticate-request.ts";
import { PermissionDeniedError } from "../_shared/authorization.ts";
import { createHandler, apiSuccess } from "../_shared/handler.ts";

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

Deno.test("createHandler returns 500 for unknown errors", async () => {
  const handler = createHandler(async () => {
    throw new Error("something broke");
  });
  const res = await handler(new Request("http://localhost", { method: "POST" }));
  assertEquals(res.status, 500);
  const body = await res.json();
  assertEquals(body.error, "Internal server error");
  // Should NOT contain the real error message
  assertEquals(body.error.includes("something broke"), false);
});

Deno.test("createHandler handles OPTIONS preflight", async () => {
  const handler = createHandler(async () => {
    return apiSuccess({ ok: true });
  });
  const res = await handler(new Request("http://localhost", { method: "OPTIONS" }));
  assertEquals(res.status, 200);
  await res.text();
});

// ─── apiSuccess tests ───────────────────────────────────────────────

Deno.test("apiSuccess returns JSON with CORS headers", async () => {
  const res = apiSuccess({ message: "ok" });
  assertEquals(res.status, 200);
  assertExists(res.headers.get("Access-Control-Allow-Origin"));
  const body = await res.json();
  assertEquals(body.message, "ok");
});
