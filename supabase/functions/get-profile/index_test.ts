/**
 * Comprehensive Stage 3C — User management edge function tests.
 *
 * Coverage matrix:
 * - Unauthenticated denial (401) for all 5 endpoints
 * - Method denial (405) for all 5 endpoints
 * - CORS preflight (200) for all 5 endpoints
 * - Validation errors (400): invalid UUID, empty body, missing fields
 * - Authenticated self-access: get-profile (own), update-profile (own)
 * - Admin access: list-users with pagination
 * - Cross-user boundary: admin view_all → 404 for non-existent
 * - Self-deactivation block (400)
 * - Non-existent user deactivation (404)
 * - Non-existent user reactivation (404)
 */
import "https://deno.land/std@0.224.0/dotenv/load.ts";
import { assertEquals } from 'https://deno.land/std@0.208.0/assert/mod.ts'

const BASE = Deno.env.get('VITE_SUPABASE_URL') ?? Deno.env.get('SUPABASE_URL') ?? 'http://localhost:54321'
const ANON_KEY = Deno.env.get('VITE_SUPABASE_PUBLISHABLE_KEY') ?? Deno.env.get('SUPABASE_ANON_KEY') ?? ''

function fnUrl(fn: string, query?: Record<string, string>): string {
  const base = `${BASE}/functions/v1/${fn}`;
  if (!query) return base;
  return `${base}?${new URLSearchParams(query)}`;
}

/** Sign in and return a JWT. Returns null if credentials unavailable. */
async function signIn(email: string, password: string): Promise<string | null> {
  try {
    const res = await fetch(`${BASE}/auth/v1/token?grant_type=password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'apikey': ANON_KEY },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    return data.access_token ?? null;
  } catch {
    return null;
  }
}

const TEST_EMAIL = Deno.env.get('TEST_ADMIN_EMAIL') ?? 'tesfayekb@gmail.com'
const TEST_PASSWORD = Deno.env.get('TEST_ADMIN_PASSWORD') ?? 'Admin123456!'

/** Get an admin token or skip the test */
async function requireAdminToken(): Promise<string> {
  const token = await signIn(TEST_EMAIL, TEST_PASSWORD);
  if (!token) throw new Error('SKIP: Could not obtain admin token — credentials unavailable in this environment');
  return token;
}

// ═══════════════════════════════════════════════════════════════
// SECTION 1: UNAUTHENTICATED DENIAL (401)
// ═══════════════════════════════════════════════════════════════

Deno.test('get-profile: rejects unauthenticated requests', async () => {
  const res = await fetch(fnUrl('get-profile'), {
    headers: { 'Authorization': `Bearer ${ANON_KEY}` },
  })
  assertEquals(res.status, 401)
  await res.body?.cancel()
})

Deno.test('update-profile: rejects unauthenticated requests', async () => {
  const res = await fetch(fnUrl('update-profile'), {
    method: 'PATCH',
    headers: { 'Authorization': `Bearer ${ANON_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ display_name: 'Test' }),
  })
  assertEquals(res.status, 401)
  await res.body?.cancel()
})

Deno.test('list-users: rejects unauthenticated requests', async () => {
  const res = await fetch(fnUrl('list-users'), {
    headers: { 'Authorization': `Bearer ${ANON_KEY}` },
  })
  assertEquals(res.status, 401)
  await res.body?.cancel()
})

Deno.test('deactivate-user: rejects unauthenticated requests', async () => {
  const res = await fetch(fnUrl('deactivate-user'), {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${ANON_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: '00000000-0000-0000-0000-000000000000' }),
  })
  assertEquals(res.status, 401)
  await res.body?.cancel()
})

Deno.test('reactivate-user: rejects unauthenticated requests', async () => {
  const res = await fetch(fnUrl('reactivate-user'), {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${ANON_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: '00000000-0000-0000-0000-000000000000' }),
  })
  assertEquals(res.status, 401)
  await res.body?.cancel()
})

// ═══════════════════════════════════════════════════════════════
// SECTION 2: METHOD DENIAL (405)
// ═══════════════════════════════════════════════════════════════

Deno.test('get-profile: rejects POST method', async () => {
  const res = await fetch(fnUrl('get-profile'), {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${ANON_KEY}` },
  })
  assertEquals(res.status, 405)
  await res.body?.cancel()
})

Deno.test('update-profile: rejects GET method', async () => {
  const res = await fetch(fnUrl('update-profile'), {
    method: 'GET',
    headers: { 'Authorization': `Bearer ${ANON_KEY}` },
  })
  assertEquals(res.status, 405)
  await res.body?.cancel()
})

Deno.test('list-users: rejects POST method', async () => {
  const res = await fetch(fnUrl('list-users'), {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${ANON_KEY}` },
  })
  assertEquals(res.status, 405)
  await res.body?.cancel()
})

Deno.test('deactivate-user: rejects GET method', async () => {
  const res = await fetch(fnUrl('deactivate-user'), {
    method: 'GET',
    headers: { 'Authorization': `Bearer ${ANON_KEY}` },
  })
  assertEquals(res.status, 405)
  await res.body?.cancel()
})

Deno.test('reactivate-user: rejects GET method', async () => {
  const res = await fetch(fnUrl('reactivate-user'), {
    method: 'GET',
    headers: { 'Authorization': `Bearer ${ANON_KEY}` },
  })
  assertEquals(res.status, 405)
  await res.body?.cancel()
})

// ═══════════════════════════════════════════════════════════════
// SECTION 3: CORS PREFLIGHT (200)
// ═══════════════════════════════════════════════════════════════

for (const fn of ['get-profile', 'update-profile', 'list-users', 'deactivate-user', 'reactivate-user']) {
  Deno.test(`${fn}: OPTIONS returns 200 with CORS headers`, async () => {
    const res = await fetch(fnUrl(fn), { method: 'OPTIONS' })
    assertEquals(res.status, 200)
    assertEquals(!!res.headers.get('access-control-allow-origin'), true)
    await res.body?.cancel()
  })
}

// ═══════════════════════════════════════════════════════════════
// SECTION 4: VALIDATION ERRORS (400)
// ═══════════════════════════════════════════════════════════════

Deno.test('get-profile: invalid UUID returns 400', async () => {
  const token = await signIn('tesfayekb@gmail.com', 'Admin123456!')
  const res = await fetch(fnUrl('get-profile', { user_id: 'not-a-uuid' }), {
    headers: { 'Authorization': `Bearer ${token}`, 'apikey': ANON_KEY },
  })
  assertEquals(res.status, 400)
  await res.body?.cancel()
})

Deno.test('update-profile: empty body returns 400', async () => {
  const token = await signIn('tesfayekb@gmail.com', 'Admin123456!')
  const res = await fetch(fnUrl('update-profile'), {
    method: 'PATCH',
    headers: { 'Authorization': `Bearer ${token}`, 'apikey': ANON_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  assertEquals(res.status, 400)
  await res.body?.cancel()
})

Deno.test('deactivate-user: missing user_id returns 400', async () => {
  const token = await signIn('tesfayekb@gmail.com', 'Admin123456!')
  const res = await fetch(fnUrl('deactivate-user'), {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}`, 'apikey': ANON_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  assertEquals(res.status, 400)
  await res.body?.cancel()
})

// ═══════════════════════════════════════════════════════════════
// SECTION 5: AUTHENTICATED SELF-ACCESS (200)
// ═══════════════════════════════════════════════════════════════

Deno.test('get-profile: authenticated user can view own profile', async () => {
  const token = await signIn('tesfayekb@gmail.com', 'Admin123456!')
  const res = await fetch(fnUrl('get-profile'), {
    headers: { 'Authorization': `Bearer ${token}`, 'apikey': ANON_KEY },
  })
  const body = await res.json()
  assertEquals(res.status, 200)
  assertEquals(!!body.profile?.id, true)
  assertEquals(!!body.profile?.status, true)
})

Deno.test('update-profile: authenticated user can update own display_name', async () => {
  const token = await signIn('tesfayekb@gmail.com', 'Admin123456!')
  const testName = `TestName_${Date.now()}`
  const res = await fetch(fnUrl('update-profile'), {
    method: 'PATCH',
    headers: { 'Authorization': `Bearer ${token}`, 'apikey': ANON_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ display_name: testName }),
  })
  const body = await res.json()
  assertEquals(res.status, 200)
  assertEquals(body.profile?.display_name, testName)
})

// ═══════════════════════════════════════════════════════════════
// SECTION 6: ADMIN ACCESS
// ═══════════════════════════════════════════════════════════════

Deno.test('list-users: admin can list users with pagination', async () => {
  const token = await signIn('tesfayekb@gmail.com', 'Admin123456!')
  const res = await fetch(fnUrl('list-users', { limit: '5' }), {
    headers: { 'Authorization': `Bearer ${token}`, 'apikey': ANON_KEY },
  })
  const body = await res.json()
  assertEquals(res.status, 200)
  assertEquals(Array.isArray(body.users), true)
  assertEquals(typeof body.total, 'number')
})

Deno.test('get-profile: admin can access non-existent user (returns 404)', async () => {
  const token = await signIn('tesfayekb@gmail.com', 'Admin123456!')
  const res = await fetch(fnUrl('get-profile', { user_id: '00000000-0000-0000-0000-000000000001' }), {
    headers: { 'Authorization': `Bearer ${token}`, 'apikey': ANON_KEY },
  })
  // Admin has users.view_all → passes permission check → 404 (not found)
  assertEquals(res.status, 404)
  await res.body?.cancel()
})

// ═══════════════════════════════════════════════════════════════
// SECTION 7: DEACTIVATION BOUNDARY TESTS
// ═══════════════════════════════════════════════════════════════

Deno.test('deactivate-user: self-deactivation blocked (400)', async () => {
  const token = await signIn('tesfayekb@gmail.com', 'Admin123456!')
  // Get own ID
  const profileRes = await fetch(fnUrl('get-profile'), {
    headers: { 'Authorization': `Bearer ${token}`, 'apikey': ANON_KEY },
  })
  const profileBody = await profileRes.json()
  const selfId = profileBody.profile?.id

  const res = await fetch(fnUrl('deactivate-user'), {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}`, 'apikey': ANON_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: selfId }),
  })
  assertEquals(res.status, 400)
  await res.body?.cancel()
})

Deno.test('deactivate-user: non-existent user returns 404', async () => {
  const token = await signIn('tesfayekb@gmail.com', 'Admin123456!')
  const res = await fetch(fnUrl('deactivate-user'), {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}`, 'apikey': ANON_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: '00000000-0000-0000-0000-000000000001' }),
  })
  assertEquals(res.status, 404)
  await res.body?.cancel()
})

Deno.test('reactivate-user: non-existent user returns 404', async () => {
  const token = await signIn('tesfayekb@gmail.com', 'Admin123456!')
  const res = await fetch(fnUrl('reactivate-user'), {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}`, 'apikey': ANON_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: '00000000-0000-0000-0000-000000000001' }),
  })
  assertEquals(res.status, 404)
  await res.body?.cancel()
})
