import "https://deno.land/std@0.224.0/dotenv/load.ts";
import { assertEquals, assertExists } from "https://deno.land/std@0.224.0/assert/mod.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("VITE_SUPABASE_URL")!;
const ANON_KEY = Deno.env.get("VITE_SUPABASE_PUBLISHABLE_KEY")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const TEST_SUPERADMIN_ID = "39977fdf-995a-41af-8be9-d89186131b1e";
const FUNCTION_URL = `${SUPABASE_URL}/functions/v1/revoke-role`;

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

async function createTestUser(): Promise<string> {
  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
  const email = `test-${crypto.randomUUID().slice(0, 8)}@test-rbac.local`;
  const { data, error } = await admin.auth.admin.createUser({
    email, password: "TestTarget123!", email_confirm: true,
  });
  if (error) throw new Error(`Failed to create test user: ${error.message}`);
  return data.user.id;
}

async function getRoleId(key: string): Promise<string> {
  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
  const { data } = await admin.from("roles").select("id").eq("key", key).single();
  return data!.id;
}

async function deleteTestUser(userId: string) {
  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
  await admin.auth.admin.deleteUser(userId);
}

Deno.test("revoke-role: no auth → 401", async () => {
  const res = await fetch(FUNCTION_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_user_id: crypto.randomUUID(), role_id: crypto.randomUUID() }),
  });
  await res.text();
  assertEquals(res.status, 401);
});

Deno.test("revoke-role: superadmin revokes admin role → success + audit", async () => {
  const jwt = await getJwtForUser(TEST_SUPERADMIN_ID);
  const targetUserId = await createTestUser();
  const adminRoleId = await getRoleId("admin");
  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);

  try {
    // First assign admin role to target
    await admin.from("user_roles").insert({
      user_id: targetUserId, role_id: adminRoleId, assigned_by: TEST_SUPERADMIN_ID,
    });

    // Now revoke it
    const res = await fetch(FUNCTION_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwt}`,
      },
      body: JSON.stringify({ target_user_id: targetUserId, role_id: adminRoleId }),
    });
    const body = await res.json();
    console.log("Superadmin revoke-role response:", JSON.stringify(body));
    assertEquals(res.status, 200, `Expected 200: ${JSON.stringify(body)}`);
    assertEquals(body.success, true);
    assertExists(body.correlation_id);

    // Verify audit log
    const { data: auditRows } = await admin
      .from("audit_logs")
      .select("*")
      .eq("action", "rbac.role_revoked")
      .eq("target_id", targetUserId)
      .order("created_at", { ascending: false })
      .limit(1);
    assertEquals(auditRows!.length, 1, "Audit log must exist");
    console.log("✅ Revoke audit verified");

    // Verify role removed from DB
    const { data: remaining } = await admin
      .from("user_roles")
      .select("id")
      .eq("user_id", targetUserId)
      .eq("role_id", adminRoleId);
    assertEquals(remaining!.length, 0, "Role must be removed");
    console.log("✅ Role removal verified in DB");
  } finally {
    await deleteTestUser(targetUserId);
  }
});

Deno.test("revoke-role: last superadmin protection", async () => {
  const jwt = await getJwtForUser(TEST_SUPERADMIN_ID);
  const superadminRoleId = await getRoleId("superadmin");

  // Try to revoke superadmin from the only superadmin
  const res = await fetch(FUNCTION_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${jwt}`,
    },
    body: JSON.stringify({ target_user_id: TEST_SUPERADMIN_ID, role_id: superadminRoleId }),
  });
  const body = await res.json();
  console.log("Last superadmin revoke response:", JSON.stringify(body));
  // Should fail — either 400/403/500 — the DB trigger prevents this
  assertEquals(res.status !== 200, true, "Must NOT succeed in removing last superadmin");
  console.log("✅ Last superadmin protection verified");
});
