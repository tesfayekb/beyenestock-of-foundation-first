/**
 * cleanup-test-users — One-shot cleanup of orphaned test users.
 * Deletes all users with @test.local or @test-rbac.local emails.
 * Self-deletes conceptually — remove from codebase after use.
 */
import { corsHeaders } from '../_shared/cors.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.49.1'

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  const admin = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
    { auth: { autoRefreshToken: false, persistSession: false } },
  )

  const { data: { users } } = await admin.auth.admin.listUsers({ perPage: 1000 })
  const testUsers = users.filter(u =>
    u.email?.endsWith('@test.local') || u.email?.endsWith('@test-rbac.local')
  )

  const results: string[] = []
  for (const u of testUsers) {
    const { error } = await admin.auth.admin.deleteUser(u.id)
    results.push(`${u.email}: ${error ? 'FAIL ' + error.message : 'deleted'}`)
  }

  return new Response(JSON.stringify({ cleaned: results.length, results }), {
    status: 200,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  })
})
