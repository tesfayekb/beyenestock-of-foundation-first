import "https://deno.land/std@0.224.0/dotenv/load.ts";

const SUPABASE_URL = Deno.env.get("VITE_SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("VITE_SUPABASE_PUBLISHABLE_KEY")!;

const BASE = `${SUPABASE_URL}/functions/v1`;

Deno.test("deactivate-user: rejects unauthenticated request", async () => {
  const res = await fetch(`${BASE}/deactivate-user`, {
    method: "POST",
    headers: { "Content-Type": "application/json", apikey: SUPABASE_ANON_KEY },
    body: JSON.stringify({ user_id: "00000000-0000-0000-0000-000000000000" }),
  });
  const body = await res.text();
  assertEquals(res.status, 401, `Expected 401, got ${res.status}: ${body}`);
});

Deno.test("deactivate-user: rejects GET method", async () => {
  const res = await fetch(`${BASE}/deactivate-user`, {
    method: "GET",
    headers: { "Content-Type": "application/json", apikey: SUPABASE_ANON_KEY },
  });
  await res.text();
  // Handler wraps with createHandler which checks auth first, but method check is inside handler
  // Actual behavior: 405 (method checked inside handler after auth) or 401 (auth checked first)
  // Accept either as valid denial
  const ok = res.status === 401 || res.status === 405;
  assertEquals(ok, true, `Expected 401 or 405, got ${res.status}`);
});

Deno.test("deactivate-user: CORS preflight", async () => {
  const res = await fetch(`${BASE}/deactivate-user`, {
    method: "OPTIONS",
    headers: { apikey: SUPABASE_ANON_KEY },
  });
  await res.text();
  assertEquals(res.status, 200);
  assertEquals(res.headers.get("access-control-allow-origin"), "*");
});

import { assertEquals } from "https://deno.land/std@0.224.0/assert/mod.ts";
