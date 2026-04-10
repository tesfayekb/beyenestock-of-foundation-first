/**
 * Runtime verification for Phase 3.5 — DW-014 Denial Audit Logging
 * 
 * Uses admin API to create confirmed user, sign in, trigger denials,
 * then verify audit_logs via admin client.
 */
import "https://deno.land/std@0.224.0/dotenv/load.ts";
import { assertEquals } from "https://deno.land/std@0.224.0/assert/assert_equals.ts";
import { assert } from "https://deno.land/std@0.224.0/assert/assert.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? Deno.env.get("VITE_SUPABASE_URL")!;
const ANON_KEY = Deno.env.get("SUPABASE_PUBLISHABLE_KEY") ?? Deno.env.get("VITE_SUPABASE_PUBLISHABLE_KEY")!;
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const BASE = `${SUPABASE_URL}/functions/v1`;

const adminClient = createClient(SUPABASE_URL, SERVICE_KEY, {
  auth: { autoRefreshToken: false, persistSession: false },
});

const TEST_EMAIL = `denial-rt-${Date.now()}@test.local`;
const TEST_PWD = "DenialRT_Test!456";
let testUserId = "";
let testToken = "";

Deno.test({
  name: "setup: create confirmed test user",
  fn: async () => {
    const { data, error } = await adminClient.auth.admin.createUser({
      email: TEST_EMAIL,
      password: TEST_PWD,
      email_confirm: true,
    });
    assert(!error, `Create user failed: ${error?.message}`);
    testUserId = data.user!.id;

    // Sign in
    const signIn = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
      method: "POST",
      headers: { "Content-Type": "application/json", apikey: ANON_KEY },
      body: JSON.stringify({ email: TEST_EMAIL, password: TEST_PWD }),
    });
    const signInData = await signIn.json();
    testToken = signInData.access_token;
    assert(testToken?.length > 10, "Must get access token");
    await signIn.text().catch(() => {});
  },
  sanitizeResources: false,
  sanitizeOps: false,
});

Deno.test({
  name: "DW-014 TEST 1: permission denial → audit log with correct schema",
  fn: async () => {
    // Regular user → list-users (requires users.view_all)
    const res = await fetch(`${BASE}/list-users`, {
      method: "GET",
      headers: { Authorization: `Bearer ${testToken}`, apikey: ANON_KEY },
    });
    const body = await res.text();
    assertEquals(res.status, 403, `Expected 403, got ${res.status}: ${body}`);

    // Wait for fire-and-forget audit write
    await new Promise((r) => setTimeout(r, 2000));

    // Query audit_logs via admin
    const { data: logs, error } = await adminClient
      .from("audit_logs")
      .select("*")
      .eq("action", "auth.permission_denied")
      .eq("actor_id", testUserId)
      .order("created_at", { ascending: false })
      .limit(5);

    assert(!error, `Query failed: ${error?.message}`);
    assert(logs!.length > 0, "Must have audit entry for permission denial");

    const log = logs![0];
    const meta = log.metadata as Record<string, unknown>;
    console.log("✅ TEST 1 — Sample audit row:", JSON.stringify(log, null, 2));

    assertEquals(log.actor_id, testUserId, "actor_id must be real user");
    assertEquals(log.action, "auth.permission_denied");
    assertEquals(log.target_type, "permission");
    assertEquals(meta.permission_key, "users.view_all");
    assertEquals(meta.reason, "missing_permission");
    assertEquals(meta.actor_known, true);
    assert(typeof meta.correlation_id === "string" && (meta.correlation_id as string).length > 0,
      "correlation_id must be in metadata");
    assert(typeof meta.endpoint === "string", "endpoint must be present");
  },
  sanitizeResources: false,
  sanitizeOps: false,
});

Deno.test({
  name: "DW-014 TEST 2: self-scope violation → audit log with reason",
  fn: async () => {
    // Regular user → get-profile for another user (triggers self-scope or permission check)
    const res = await fetch(`${BASE}/get-profile?user_id=00000000-aaaa-bbbb-cccc-000000000001`, {
      method: "GET",
      headers: { Authorization: `Bearer ${testToken}`, apikey: ANON_KEY },
    });
    const body = await res.text();
    assertEquals(res.status, 403, `Expected 403, got ${res.status}: ${body}`);

    await new Promise((r) => setTimeout(r, 2000));

    const { data: logs } = await adminClient
      .from("audit_logs")
      .select("*")
      .eq("action", "auth.permission_denied")
      .eq("actor_id", testUserId)
      .order("created_at", { ascending: false })
      .limit(10);

    // Find the entry for this denial (could be missing_permission for users.view_all)
    const entry = logs?.find((l) => {
      const m = l.metadata as Record<string, unknown>;
      return m.endpoint?.toString().includes("get-profile");
    });
    assert(entry, "Must have audit entry for get-profile denial");
    const meta = entry!.metadata as Record<string, unknown>;
    assert(typeof meta.correlation_id === "string", "correlation_id must be in metadata");
    assert(typeof meta.reason === "string", "reason must be present");
    console.log("✅ TEST 2 — Self-scope/permission denial verified:", meta.reason);
  },
  sanitizeResources: false,
  sanitizeOps: false,
});

Deno.test({
  name: "DW-014 TEST 3: actor_id is NOT a fake UUID",
  fn: async () => {
    const { data: logs } = await adminClient
      .from("audit_logs")
      .select("actor_id")
      .eq("action", "auth.permission_denied")
      .eq("actor_id", "00000000-0000-0000-0000-000000000000")
      .limit(1);

    assertEquals(logs?.length ?? 0, 0, "No fake sentinel UUIDs should exist in audit_logs");
    console.log("✅ TEST 3 — No fake UUID sentinels in audit_logs");
  },
  sanitizeResources: false,
  sanitizeOps: false,
});

Deno.test({
  name: "cleanup: delete test user",
  fn: async () => {
    await adminClient.auth.admin.deleteUser(testUserId);
    console.log("✅ Cleanup done");
  },
  sanitizeResources: false,
  sanitizeOps: false,
});
