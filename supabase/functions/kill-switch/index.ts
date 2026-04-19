/**
 * kill-switch — Halt or resume today's trading session.
 *
 * The KillSwitchButton previously wrote directly to trading_sessions,
 * but RLS only allows the service role to UPDATE that table.
 * Authenticated users (even with trading.configure) were silently
 * denied — the toast said "halted" but the row never changed.
 *
 * This Edge Function uses the service role client to perform the
 * update server-side after verifying the caller's permission.
 *
 * POST /kill-switch
 * Body: { session_id: string, action: 'halt' | 'resume' }
 * Response: { ok: true, session_id, action } on success.
 *
 * Owner: trading-console module
 * Classification: security-sensitive (mutates trading-engine state)
 * Authorization: trading.configure permission required
 *
 * NOTE: This file is intentionally self-contained (no _shared/ imports)
 * so it can deploy without dragging in transitive dependencies.
 * Pattern mirrors supabase/functions/set-feature-flag/index.ts.
 */
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.7'

const corsHeaders: Record<string, string> = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers':
        'authorization, x-client-info, apikey, content-type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Vary': 'Origin',
}

function jsonResponse(
    body: Record<string, unknown>,
    status: number,
): Response {
    return new Response(JSON.stringify(body), {
        status,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    })
}

interface AuthCtx {
    userId: string
    serviceClient: ReturnType<typeof createClient>
}

async function authenticate(req: Request): Promise<AuthCtx> {
    const authHeader = req.headers.get('Authorization')
    if (!authHeader?.startsWith('Bearer ')) {
        throw new Error('UNAUTHORIZED')
    }
    const token = authHeader.replace('Bearer ', '')

    const supabaseUrl = Deno.env.get('SUPABASE_URL') ?? ''
    const serviceRoleKey =
        Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''

    if (!supabaseUrl || !serviceRoleKey) {
        throw new Error('SERVER_MISCONFIGURED')
    }

    const serviceClient = createClient(supabaseUrl, serviceRoleKey, {
        auth: { persistSession: false },
    })

    const {
        data: { user },
        error,
    } = await serviceClient.auth.getUser(token)

    if (error || !user) throw new Error('UNAUTHORIZED')

    return { userId: user.id, serviceClient }
}

async function checkPermission(
    ctx: AuthCtx,
    permissionKey: string,
): Promise<void> {
    const { data, error } = await ctx.serviceClient.rpc('has_permission', {
        _user_id: ctx.userId,
        _permission_key: permissionKey,
    })
    if (error || data !== true) {
        throw new Error('FORBIDDEN')
    }
}

interface KillSwitchBody {
    session_id: string
    action: 'halt' | 'resume'
}

function parseBody(raw: unknown): KillSwitchBody {
    if (!raw || typeof raw !== 'object') {
        throw new Error('INVALID_BODY')
    }
    const obj = raw as Record<string, unknown>
    const session_id = obj.session_id
    const action = obj.action
    if (
        typeof session_id !== 'string' ||
        session_id.length < 1 ||
        session_id.length > 64
    ) {
        throw new Error('INVALID_BODY')
    }
    if (action !== 'halt' && action !== 'resume') {
        throw new Error('INVALID_BODY')
    }
    return { session_id, action }
}

Deno.serve(async (req: Request): Promise<Response> => {
    if (req.method === 'OPTIONS') {
        return new Response('ok', { headers: corsHeaders })
    }
    if (req.method !== 'POST') {
        return jsonResponse({ error: 'Method not allowed' }, 405)
    }

    let ctx: AuthCtx
    try {
        ctx = await authenticate(req)
    } catch (err) {
        const msg = String((err as Error).message)
        if (msg === 'SERVER_MISCONFIGURED') {
            return jsonResponse(
                { error: 'Server misconfigured' },
                500,
            )
        }
        return jsonResponse({ error: 'Unauthorized' }, 401)
    }

    try {
        await checkPermission(ctx, 'trading.configure')
    } catch {
        return jsonResponse(
            { error: 'Forbidden: requires trading.configure' },
            403,
        )
    }

    let body: KillSwitchBody
    try {
        const raw = await req.json()
        body = parseBody(raw)
    } catch {
        return jsonResponse({ error: 'Invalid request body' }, 400)
    }

    // Service-role UPDATE bypasses RLS safely (already auth+perm checked).
    const updatePayload =
        body.action === 'halt'
            ? {
                  session_status: 'halted',
                  halt_reason: 'operator_kill_switch',
              }
            : { session_status: 'active', halt_reason: null }

    const { error: updateError } = await ctx.serviceClient
        .from('trading_sessions')
        .update(updatePayload)
        .eq('id', body.session_id)

    if (updateError) {
        console.error('[KILL-SWITCH] update failed', {
            session_id: body.session_id,
            action: body.action,
            error: updateError.message,
        })
        return jsonResponse(
            { error: 'Failed to update session' },
            500,
        )
    }

    return jsonResponse(
        { ok: true, session_id: body.session_id, action: body.action },
        200,
    )
})
