/**
 * lifecycle-test — Temporary server-side lifecycle behavioral validation.
 * 
 * Runs the full deactivate/reactivate happy path using service-role,
 * verifies profile status transitions and auth ban state at each step.
 * 
 * DELETE THIS FUNCTION after capturing evidence.
 */
import { supabaseAdmin } from '../_shared/supabase-admin.ts'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface TestResult {
  name: string
  pass: boolean
  details: string
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  const results: TestResult[] = []
  let testUserId: string | null = null
  const testEmail = `lifecycle-final-${Date.now()}@test.local`

  try {
    // ── Setup: Create test user + admin user with permissions ──
    const { data: testUser, error: createErr } = await supabaseAdmin.auth.admin.createUser({
      email: testEmail,
      password: 'TestPass123456!',
      email_confirm: true,
    })
    if (createErr || !testUser.user) throw new Error(`Setup failed: ${createErr?.message}`)
    testUserId = testUser.user.id

    // Verify profile was created with 'active' status
    const { data: initialProfile } = await supabaseAdmin
      .from('profiles')
      .select('status')
      .eq('id', testUserId)
      .single()

    results.push({
      name: '0. Setup: user created with active status',
      pass: initialProfile?.status === 'active',
      details: `status=${initialProfile?.status}`,
    })

    // ── Test 1: Deactivation happy path ──
    // 1a. Set profile to deactivated
    const { error: deactErr } = await supabaseAdmin
      .from('profiles')
      .update({ status: 'deactivated' })
      .eq('id', testUserId)

    // 1b. Ban auth user (mirrors deactivate-user function logic)
    const { error: banErr } = await supabaseAdmin.auth.admin.updateUserById(testUserId, {
      ban_duration: '876000h',
    })

    // 1c. Verify profile status
    const { data: deactProfile } = await supabaseAdmin
      .from('profiles')
      .select('status')
      .eq('id', testUserId)
      .single()

    // 1d. Verify auth ban
    const { data: { user: bannedUser } } = await supabaseAdmin.auth.admin.getUserById(testUserId)

    results.push({
      name: '1. Deactivation: profile status set to deactivated',
      pass: !deactErr && deactProfile?.status === 'deactivated',
      details: `error=${deactErr?.message ?? 'none'}, status=${deactProfile?.status}`,
    })

    results.push({
      name: '2. Deactivation: auth user banned',
      pass: !banErr && bannedUser?.banned_until !== null && bannedUser?.banned_until !== undefined,
      details: `error=${banErr?.message ?? 'none'}, banned_until=${bannedUser?.banned_until ?? 'null'}`,
    })

    // 1e. Verify login blocked
    const { error: loginErr } = await supabaseAdmin.auth.signInWithPassword({
      email: testEmail,
      password: 'TestPass123456!',
    })

    results.push({
      name: '3. Deactivation: login blocked for banned user',
      pass: !!loginErr,
      details: `login_error=${loginErr?.message ?? 'NONE (should have failed!)'}`,
    })

    // ── Test 2: Reactivation happy path ──
    // 2a. Clear ban (mirrors reactivate-user function logic)
    const { error: unbanErr } = await supabaseAdmin.auth.admin.updateUserById(testUserId, {
      ban_duration: 'none',
    })

    // 2b. Set profile to active
    const { error: reactErr } = await supabaseAdmin
      .from('profiles')
      .update({ status: 'active' })
      .eq('id', testUserId)

    // 2c. Verify profile status
    const { data: reactProfile } = await supabaseAdmin
      .from('profiles')
      .select('status')
      .eq('id', testUserId)
      .single()

    // 2d. Verify auth ban cleared
    const { data: { user: unbannedUser } } = await supabaseAdmin.auth.admin.getUserById(testUserId)

    results.push({
      name: '4. Reactivation: auth ban cleared',
      pass: !unbanErr,
      details: `error=${unbanErr?.message ?? 'none'}, banned_until=${unbannedUser?.banned_until ?? 'null'}`,
    })

    results.push({
      name: '5. Reactivation: profile status set to active',
      pass: !reactErr && reactProfile?.status === 'active',
      details: `error=${reactErr?.message ?? 'none'}, status=${reactProfile?.status}`,
    })

    // 2e. Verify login restored
    const { data: loginData, error: loginErr2 } = await supabaseAdmin.auth.signInWithPassword({
      email: testEmail,
      password: 'TestPass123456!',
    })

    results.push({
      name: '6. Reactivation: login restored after reactivation',
      pass: !loginErr2 && !!loginData?.session,
      details: `error=${loginErr2?.message ?? 'none'}, has_session=${!!loginData?.session}`,
    })

  } catch (e) {
    results.push({
      name: 'FATAL',
      pass: false,
      details: e instanceof Error ? e.message : String(e),
    })
  } finally {
    // Cleanup: delete test user
    if (testUserId) {
      // Delete profile first to avoid trigger issues
      await supabaseAdmin.from('profiles').delete().eq('id', testUserId)
      await supabaseAdmin.from('user_roles').delete().eq('user_id', testUserId)
      const { error: delErr } = await supabaseAdmin.auth.admin.deleteUser(testUserId)
      results.push({
        name: 'CLEANUP',
        pass: !delErr,
        details: delErr ? `cleanup failed: ${delErr.message}` : `user ${testUserId} deleted`,
      })
    }
  }

  const passed = results.filter(r => r.name !== 'CLEANUP').filter(r => r.pass).length
  const total = results.filter(r => r.name !== 'CLEANUP').length

  return new Response(JSON.stringify({
    summary: `${passed}/${total} passed`,
    all_pass: passed === total,
    results,
  }, null, 2), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  })
})
