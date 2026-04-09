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

    const { data: hasPermission } = await supabaseAdmin.rpc('has_permission', {
      _user_id: user.id, _permission_key: 'permissions.assign'
    })
    if (!hasPermission) {
      return new Response(JSON.stringify({ error: 'Permission denied' }), {
        status: 403, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    const body = await req.json()
    const { role_id, permission_id } = body
    if (!role_id || !permission_id ||
        typeof role_id !== 'string' || typeof permission_id !== 'string') {
      return new Response(JSON.stringify({ error: 'Invalid input: role_id and permission_id required' }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    if (!uuidRegex.test(role_id) || !uuidRegex.test(permission_id)) {
      return new Response(JSON.stringify({ error: 'Invalid UUID format' }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    // Validate role exists
    const { data: role } = await supabaseAdmin
      .from('roles').select('id, key').eq('id', role_id).single()
    if (!role) {
      return new Response(JSON.stringify({ error: 'Role not found' }), {
        status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    // Validate permission exists
    const { data: permission } = await supabaseAdmin
      .from('permissions').select('id, key').eq('id', permission_id).single()
    if (!permission) {
      return new Response(JSON.stringify({ error: 'Permission not found' }), {
        status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    const correlation_id = crypto.randomUUID()

    const { error: insertError } = await supabaseAdmin
      .from('role_permissions')
      .insert({ role_id, permission_id })

    if (insertError) {
      if (insertError.code === '23505') {
        return new Response(JSON.stringify({ error: 'Permission already assigned to role' }), {
          status: 409, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        })
      }
      throw insertError
    }

    const { error: auditError } = await supabaseAdmin
      .from('audit_logs')
      .insert({
        actor_id: user.id,
        action: 'rbac.permission_assigned',
        target_type: 'role_permissions',
        target_id: role_id,
        metadata: {
          role_id, role_key: role.key,
          permission_id, permission_key: permission.key,
          correlation_id
        },
        ip_address: req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() || null,
        user_agent: req.headers.get('user-agent')
      })

    if (auditError) {
      await supabaseAdmin
        .from('role_permissions')
        .delete()
        .eq('role_id', role_id)
        .eq('permission_id', permission_id)
      return new Response(JSON.stringify({ error: 'Audit logging failed — operation rolled back' }), {
        status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    return new Response(JSON.stringify({
      success: true, correlation_id,
      message: `Permission ${permission.key} assigned to role ${role.key}`
    }), {
      status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })

  } catch (error) {
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })
  }
})
