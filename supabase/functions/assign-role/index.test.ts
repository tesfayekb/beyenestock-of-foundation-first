import "https://deno.land/std@0.224.0/dotenv/load.ts";
import { assertEquals, assertExists } from "https://deno.land/std@0.224.0/assert/mod.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("VITE_SUPABASE_URL")!;
const ANON_KEY = Deno.env.get("VITE_SUPABASE_PUBLISHABLE_KEY")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const TEST_SUPERADMIN_ID = "39977fdf-995a-41af-8be9-d89186131b1e";
const FUNCTION_URL = `${SUPABASE_URL}/functions/v1/assign-role`;

// Helper: get a real JWT for a user via service role
async function getJwtForUser(userId: string): Promise<string> {
  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
  // Set a temp password, then sign in to get a real JWT
  const { error: updateErr } = await admin.auth.admin.updateUserById(userId, {
    password: "TestPass123!_temp",
  });
  if (updateErr) throw new Error(`Failed to set temp password: ${updateErr.message}`);

  const { data: userData } = await admin.auth.admin.getUserById(userId);
  const email = userData.user?.email;
  if (!email) throw new Error("No email for test user");

  const anonClient = createClient(SUPABASE_URL, ANON_KEY);
  const { data, error } = await anonClient.auth.signInWithPassword({
    email,
    password: "TestPass123!_temp",
  });
  if (error) throw new Error(`Sign-in failed: ${error.message}`);
  return data.session!.access_token;
}

// Helper: create a throwaway user for target
async function createTestUser(): Promise<string> {
  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
  const email = `test-${crypto.randomUUID().slice(0, 8)}@test-rbac.local`;
  const { data, error } = await admin.auth.admin.createUser({
    email,
    password: "TestTarget123!",
    email_confirm: true,
  });
  if (error) throw new Error(`Failed to create test user: ${error.message}`);
  return data.user.id;
}

// Helper: get role ID
async function getRoleId(key: string): Promise<string> {
  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
  const { data } = await admin.from("roles").select("id").eq("key", key).single();
  return data!.id;
}

// Helper: cleanup user
async function deleteTestUser(userId: string) {
  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
  await admin.auth.admin.deleteUser(userId);
}

// Helper: get user JWT for a non-superadmin
async function getRegularUserJwt(): Promise<{ jwt: string; userId: string }> {
  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
  const email = `regular-${crypto.randomUUID().slice(0, 8)}@test-rbac.local`;
  const { data, error } = await admin.auth.admin.createUser({
    email,
    password: "RegularUser123!",
    email_confirm: true,
  });
  if (error) throw new Error(`Failed to create regular user: ${error.message}`);

  const anonClient = createClient(SUPABASE_URL, ANON_KEY);
  const { data: session, error: signErr } = await anonClient.auth.signInWithPassword({
    email,
    password: "RegularUser123!",
  });
  if (signErr) throw new Error(`Sign-in failed: ${signErr.message}`);
  return { jwt: session.session!.access_token, userId: data.user.id };
}

Deno.test("assign-role: no auth → 401", async () => {
  const res = await fetch(FUNCTION_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_user_id: crypto.randomUUID(), role_id: crypto.randomUUID() }),
  });
  const body = await res.text();
  assertEquals(res.status, 401);
  console.log("No-auth test:", body);
});

Deno.test("assign-role: superadmin → success + audit log", async () => {
  const jwt = await getJwtForUser(TEST_SUPERADMIN_ID);
  const targetUserId = await createTestUser();
  const adminRoleId = await getRoleId("admin");

  try {
    const res = await fetch(FUNCTION_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwt}`,
      },
      body: JSON.stringify({ target_user_id: targetUserId, role_id: adminRoleId }),
    });
    const body = await res.json();
    console.log("Superadmin assign-role response:", JSON.stringify(body));
    assertEquals(res.status, 200, `Expected 200 but got ${res.status}: ${JSON.stringify(body)}`);
    assertEquals(body.success, true);
    assertExists(body.correlation_id);

    // Verify audit log was created
    const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);
    const { data: auditRows } = await admin
      .from("audit_logs")
      .select("*")
      .eq("action", "rbac.role_assigned")
      .eq("target_id", targetUserId)
      .order("created_at", { ascending: false })
      .limit(1);
    console.log("Audit log entry:", JSON.stringify(auditRows));
    assertEquals(auditRows!.length, 1, "Audit log row must exist");
    assertEquals(auditRows![0].metadata.correlation_id, body.correlation_id);

    // Verify role actually assigned in DB
    const { data: userRoles } = await admin
      .from("user_roles")
      .select("role_id")
      .eq("user_id", targetUserId)
      .eq("role_id", adminRoleId);
    assertEquals(userRoles!.length, 1, "Role must be assigned in user_roles");
    console.log("✅ Role verified in DB");
  } finally {
    await deleteTestUser(targetUserId);
  }
});

Deno.test("assign-role: regular user (no roles.assign) → 403", async () => {
  const { jwt, userId } = await getRegularUserJwt();
  const targetUserId = await createTestUser();
  const adminRoleId = await getRoleId("admin");

  try {
    const res = await fetch(FUNCTION_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwt}`,
      },
      body: JSON.stringify({ target_user_id: targetUserId, role_id: adminRoleId }),
    });
    const body = await res.json();
    console.log("Regular user assign-role response:", JSON.stringify(body));
    assertEquals(res.status, 403, "Regular user must be denied");
    assertEquals(body.error, "Permission denied");
  } finally {
    await deleteTestUser(targetUserId);
    await deleteTestUser(userId);
  }
});

Deno.test("assign-role: duplicate assignment → 409", async () => {
  const jwt = await getJwtForUser(TEST_SUPERADMIN_ID);
  const targetUserId = await createTestUser();
  const userRoleId = await getRoleId("user");

  try {
    // User already has 'user' role from handle_new_user_role trigger
    const res = await fetch(FUNCTION_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwt}`,
      },
      body: JSON.stringify({ target_user_id: targetUserId, role_id: userRoleId }),
    });
    const body = await res.json();
    console.log("Duplicate assign response:", JSON.stringify(body));
    assertEquals(res.status, 409);
  } finally {
    await deleteTestUser(targetUserId);
  }
});

Deno.test("assign-role: invalid UUID → 400", async () => {
  const jwt = await getJwtForUser(TEST_SUPERADMIN_ID);
  const res = await fetch(FUNCTION_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${jwt}`,
    },
    body: JSON.stringify({ target_user_id: "not-a-uuid", role_id: "also-not" }),
  });
  const body = await res.text();
  assertEquals(res.status, 400);
  console.log("Invalid UUID test:", body);
});
