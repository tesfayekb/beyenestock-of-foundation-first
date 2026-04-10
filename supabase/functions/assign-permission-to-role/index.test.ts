import "https://deno.land/std@0.224.0/dotenv/load.ts";
import { assertEquals, assertExists } from "https://deno.land/std@0.224.0/assert/mod.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("VITE_SUPABASE_URL")!;
const ANON_KEY = Deno.env.get("VITE_SUPABASE_PUBLISHABLE_KEY")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const TEST_SUPERADMIN_ID = "39977fdf-995a-41af-8be9-d89186131b1e";
const FUNCTION_URL = `${SUPABASE_URL}/functions/v1/assign-permission-to-role`;

async function getJwtForUser(userId: string): Promise<string> {
  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
  await admin.auth.admin.updateUserById(userId, { password: "TestPass123!_temp" });
  const { data: userData } = await admin.auth.admin.getUserById(userId);
  const anonClient = createClient(SUPABASE_URL, ANON_KEY);
  const { data, error } = await anonClient.auth.signInWithPassword({
    email: userData.user!.email!, password: "TestPass123!_temp",
  });
  if (error) throw new Error(`Sign-in failed: ${error.message}`);
  return data.session!.access_token;
}

async function getRegularUserJwt(): Promise<{ jwt: string; userId: string }> {
  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
  const email = `regular-${crypto.randomUUID().slice(0, 8)}@test-rbac.local`;
  const { data, error } = await admin.auth.admin.createUser({
    email, password: "RegularUser123!", email_confirm: true,
  });
  if (error) throw new Error(`Failed: ${error.message}`);
  const anonClient = createClient(SUPABASE_URL, ANON_KEY);
  const { data: session, error: signErr } = await anonClient.auth.signInWithPassword({
    email, password: "RegularUser123!",
  });
  if (signErr) throw new Error(`Sign-in failed: ${signErr.message}`);
  return { jwt: session.session!.access_token, userId: data.user.id };
}

async function deleteTestUser(userId: string) {
  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
  await admin.auth.admin.deleteUser(userId);
}

Deno.test("assign-permission-to-role: no auth → 401", async () => {
  const res = await fetch(FUNCTION_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role_id: crypto.randomUUID(), permission_id: crypto.randomUUID() }),
  });
  await res.text();
  assertEquals(res.status, 401);
});

Deno.test("assign-permission-to-role: superadmin → success + audit", async () => {
  const jwt = await getJwtForUser(TEST_SUPERADMIN_ID);
  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);

  // Create a test role and use an existing permission
  const { data: testRole } = await admin.from("roles").insert({
    key: `test-role-${crypto.randomUUID().slice(0, 8)}`,
    name: "Test Role",
    is_base: false,
    is_immutable: false,
  }).select("id, key").single();

  const { data: perm } = await admin.from("permissions").select("id, key").limit(1).single();

  try {
    const res = await fetch(FUNCTION_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwt}`,
      },
      body: JSON.stringify({ role_id: testRole!.id, permission_id: perm!.id }),
    });
    const body = await res.json();
    console.log("Superadmin assign-permission response:", JSON.stringify(body));
    assertEquals(res.status, 200, `Expected 200: ${JSON.stringify(body)}`);
    assertEquals(body.success, true);
    assertExists(body.correlation_id);

    // Verify mapping in DB
    const { data: mapping } = await admin
      .from("role_permissions")
      .select("id")
      .eq("role_id", testRole!.id)
      .eq("permission_id", perm!.id);
    assertEquals(mapping!.length, 1, "Permission mapping must exist");

    // Verify audit log
    const { data: auditRows } = await admin
      .from("audit_logs")
      .select("*")
      .eq("action", "rbac.permission_assigned")
      .eq("target_id", testRole!.id)
      .order("created_at", { ascending: false })
      .limit(1);
    assertEquals(auditRows!.length, 1);
    console.log("✅ Permission assignment + audit verified");
  } finally {
    // Cleanup
    await admin.from("role_permissions").delete().eq("role_id", testRole!.id);
    await admin.from("roles").delete().eq("id", testRole!.id);
  }
});

Deno.test("assign-permission-to-role: regular user → 403", async () => {
  const { jwt, userId } = await getRegularUserJwt();
  try {
    const res = await fetch(FUNCTION_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwt}`,
      },
      body: JSON.stringify({ role_id: crypto.randomUUID(), permission_id: crypto.randomUUID() }),
    });
    const body = await res.json();
    console.log("Regular user response:", JSON.stringify(body));
    assertEquals(res.status, 403);
  } finally {
    await deleteTestUser(userId);
  }
});
