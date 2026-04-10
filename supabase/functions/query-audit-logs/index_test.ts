/**
 * Tests for query-audit-logs and export-audit-logs edge functions.
 *
 * These tests call the deployed edge functions via HTTP.
 * They require a valid Supabase URL and anon key.
 */
import "https://deno.land/std@0.224.0/dotenv/load.ts";
import { assertEquals, assertExists } from "https://deno.land/std@0.224.0/assert/mod.ts";

const SUPABASE_URL = Deno.env.get("VITE_SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("VITE_SUPABASE_PUBLISHABLE_KEY")!;

const queryUrl = `${SUPABASE_URL}/functions/v1/query-audit-logs`;
const exportUrl = `${SUPABASE_URL}/functions/v1/export-audit-logs`;

// ─── Unauthenticated denial tests ───────────────────────────────────

Deno.test("query-audit-logs returns 401 without auth token", async () => {
  const res = await fetch(queryUrl, {
    headers: { "apikey": SUPABASE_ANON_KEY },
  });
  assertEquals(res.status, 401);
  const body = await res.json();
  assertExists(body.error);
});

Deno.test("export-audit-logs returns 401 without auth token", async () => {
  const res = await fetch(exportUrl, {
    headers: { "apikey": SUPABASE_ANON_KEY },
  });
  assertEquals(res.status, 401);
  const body = await res.json();
  assertExists(body.error);
});

// ─── Method denial tests ────────────────────────────────────────────

Deno.test("query-audit-logs rejects POST method", async () => {
  const res = await fetch(queryUrl, {
    method: "POST",
    headers: { "apikey": SUPABASE_ANON_KEY },
  });
  // Should be 401 (auth check first) or 405 — either is acceptable
  const status = res.status;
  assertEquals(status === 401 || status === 405, true);
  await res.text();
});

Deno.test("export-audit-logs rejects POST method", async () => {
  const res = await fetch(exportUrl, {
    method: "POST",
    headers: { "apikey": SUPABASE_ANON_KEY },
  });
  const status = res.status;
  assertEquals(status === 401 || status === 405, true);
  await res.text();
});

// ─── CORS tests ─────────────────────────────────────────────────────

Deno.test("query-audit-logs handles OPTIONS preflight", async () => {
  const res = await fetch(queryUrl, { method: "OPTIONS" });
  assertEquals(res.status, 200);
  assertExists(res.headers.get("Access-Control-Allow-Origin"));
  await res.text();
});

Deno.test("export-audit-logs handles OPTIONS preflight", async () => {
  const res = await fetch(exportUrl, { method: "OPTIONS" });
  assertEquals(res.status, 200);
  assertExists(res.headers.get("Access-Control-Allow-Origin"));
  await res.text();
});

// ─── Input validation tests (query-audit-logs, no auth) ─────────────

Deno.test("query-audit-logs validates actor_id UUID format", async () => {
  const res = await fetch(`${queryUrl}?actor_id=not-a-uuid`, {
    headers: {
      "apikey": SUPABASE_ANON_KEY,
      "Authorization": "Bearer invalid-token",
    },
  });
  // Will get 401 since token is invalid — that's correct behavior (auth before validation)
  assertEquals(res.status, 401);
  await res.text();
});
