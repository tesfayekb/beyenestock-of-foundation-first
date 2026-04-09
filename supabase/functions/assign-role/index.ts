import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from 'https://esm.sh/@supabase/supabase-js@2/cors'

const supabaseAdmin = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
)

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // 1. Validate JWT
    const authHeader = req.headers.get('Authorization')
    if (!authHeader) {
      return new Response(JSON.stringify({ error: 'Missing authorization header' }), {
        status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    const { data: { user }, error: authError } = await supabaseAdmin.auth.getUser(
      authHeader.replace('Bearer ', '')
    )
    if (authError || !user) {
      return new Response(JSON.stringify({ error: 'Invalid token' }), {
        status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    // 2. Check permission
    const { data: hasPermission } = await supabaseAdmin.rpc('has_permission', {
      _user_id: user.id, _permission_key: 'roles.assign'
    })
    if (!hasPermission) {
      return new Response(JSON.stringify({ error: 'Permission denied' }), {
        status: 403, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    // 3. Parse and validate input
    const body = await req.json()
    const { target_user_id, role_id } = body
    if (!target_user_id || !role_id ||
        typeof target_user_id !== 'string' || typeof role_id !== 'string') {
      return new Response(JSON.stringify({ error: 'Invalid input: target_user_id and role_id required' }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    // UUID format validation
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    if (!uuidRegex.test(target_user_id) || !uuidRegex.test(role_id)) {
      return new Response(JSON.stringify({ error: 'Invalid UUID format' }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    // 4. Validate target user exists
    const { data: targetUser } = await supabaseAdmin.auth.admin.getUserById(target_user_id)
    if (!targetUser?.user) {
      return new Response(JSON.stringify({ error: 'Target user not found' }), {
        status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    // 5. Validate role exists
    const { data: role, error: roleError } = await supabaseAdmin
      .from('roles').select('id, key').eq('id', role_id).single()
    if (roleError || !role) {
      return new Response(JSON.stringify({ error: 'Role not found' }), {
        status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    // 6. Assign role + audit log in transaction via RPC
    const correlation_id = crypto.randomUUID()

    const { error: insertError } = await supabaseAdmin
      .from('user_roles')
      .insert({ user_id: target_user_id, role_id, assigned_by: user.id })

    if (insertError) {
      if (insertError.code === '23505') {
        return new Response(JSON.stringify({ error: 'Role already assigned' }), {
          status: 409, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        })
      }
      throw insertError
    }

    // 7. Write audit log
    const { error: auditError } = await supabaseAdmin
      .from('audit_logs')
      .insert({
        actor_id: user.id,
        action: 'rbac.role_assigned',
        target_type: 'user_roles',
        target_id: target_user_id,
        metadata: {
          role_id, role_key: role.key,
          target_user_id, correlation_id
        },
        ip_address: req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() || null,
        user_agent: req.headers.get('user-agent')
      })

    if (auditError) {
      // Rollback: remove the role assignment if audit fails
      await supabaseAdmin
        .from('user_roles')
        .delete()
        .eq('user_id', target_user_id)
        .eq('role_id', role_id)
      return new Response(JSON.stringify({ error: 'Audit logging failed — operation rolled back' }), {
        status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    return new Response(JSON.stringify({
      success: true, correlation_id,
      message: `Role ${role.key} assigned to user`
    }), {
      status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })

  } catch (error) {
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })
  }
})
