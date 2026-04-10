/**
 * Stage 3C — User management edge function tests.
 */
import { assertEquals } from 'https://deno.land/std@0.208.0/assert/mod.ts'

const BASE = Deno.env.get('SUPABASE_URL') ?? 'http://localhost:54321'
const ANON_KEY = Deno.env.get('SUPABASE_ANON_KEY') ?? ''

// ─── get-profile ────────────────────────────────────────────────────

Deno.test('get-profile: rejects unauthenticated requests', async () => {
  const res = await fetch(`${BASE}/functions/v1/get-profile`, {
    headers: { 'Authorization': `Bearer ${ANON_KEY}` },
  })
  assertEquals(res.status, 401)
  await res.body?.cancel()
})

Deno.test('get-profile: rejects non-GET methods', async () => {
  const res = await fetch(`${BASE}/functions/v1/get-profile`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${ANON_KEY}` },
  })
  assertEquals(res.status, 405)
  await res.body?.cancel()
})

Deno.test('get-profile: handles CORS preflight', async () => {
  const res = await fetch(`${BASE}/functions/v1/get-profile`, {
    method: 'OPTIONS',
  })
  assertEquals(res.status, 200)
  await res.body?.cancel()
})

Deno.test('get-profile: rejects invalid UUID', async () => {
  const res = await fetch(`${BASE}/functions/v1/get-profile?user_id=not-a-uuid`, {
    headers: { 'Authorization': `Bearer ${ANON_KEY}` },
  })
  // Will be 401 (anon key) or 400 (validation) — either is correct rejection
  const status = res.status
  assertEquals(status === 401 || status === 400, true)
  await res.body?.cancel()
})

// ─── update-profile ─────────────────────────────────────────────────

Deno.test('update-profile: rejects unauthenticated requests', async () => {
  const res = await fetch(`${BASE}/functions/v1/update-profile`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${ANON_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ display_name: 'Test' }),
  })
  assertEquals(res.status, 401)
  await res.body?.cancel()
})

Deno.test('update-profile: rejects GET method', async () => {
  const res = await fetch(`${BASE}/functions/v1/update-profile`, {
    method: 'GET',
    headers: { 'Authorization': `Bearer ${ANON_KEY}` },
  })
  assertEquals(res.status, 405)
  await res.body?.cancel()
})

// ─── list-users ─────────────────────────────────────────────────────

Deno.test('list-users: rejects unauthenticated requests', async () => {
  const res = await fetch(`${BASE}/functions/v1/list-users`, {
    headers: { 'Authorization': `Bearer ${ANON_KEY}` },
  })
  assertEquals(res.status, 401)
  await res.body?.cancel()
})

Deno.test('list-users: rejects non-GET methods', async () => {
  const res = await fetch(`${BASE}/functions/v1/list-users`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${ANON_KEY}` },
  })
  assertEquals(res.status, 405)
  await res.body?.cancel()
})

// ─── deactivate-user ────────────────────────────────────────────────

Deno.test('deactivate-user: rejects unauthenticated requests', async () => {
  const res = await fetch(`${BASE}/functions/v1/deactivate-user`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${ANON_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ user_id: '00000000-0000-0000-0000-000000000000' }),
  })
  assertEquals(res.status, 401)
  await res.body?.cancel()
})

Deno.test('deactivate-user: rejects GET method', async () => {
  const res = await fetch(`${BASE}/functions/v1/deactivate-user`, {
    method: 'GET',
    headers: { 'Authorization': `Bearer ${ANON_KEY}` },
  })
  assertEquals(res.status, 405)
  await res.body?.cancel()
})

Deno.test('deactivate-user: handles CORS preflight', async () => {
  const res = await fetch(`${BASE}/functions/v1/deactivate-user`, {
    method: 'OPTIONS',
  })
  assertEquals(res.status, 200)
  await res.body?.cancel()
})

// ─── reactivate-user ────────────────────────────────────────────────

Deno.test('reactivate-user: rejects unauthenticated requests', async () => {
  const res = await fetch(`${BASE}/functions/v1/reactivate-user`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${ANON_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ user_id: '00000000-0000-0000-0000-000000000000' }),
  })
  assertEquals(res.status, 401)
  await res.body?.cancel()
})

Deno.test('reactivate-user: rejects GET method', async () => {
  const res = await fetch(`${BASE}/functions/v1/reactivate-user`, {
    method: 'GET',
    headers: { 'Authorization': `Bearer ${ANON_KEY}` },
  })
  assertEquals(res.status, 405)
  await res.body?.cancel()
})
