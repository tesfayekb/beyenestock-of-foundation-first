/**
 * set-feature-flag — POST proxy that toggles a Redis-backed trading
 * feature flag on the Railway backend.
 *
 * Why this proxy exists: the Lovable-hosted frontend's Content
 * Security Policy blocks direct browser fetches to the Railway API.
 * Edge Functions run server-side on Supabase infrastructure (already
 * CSP-allowed) and can forward the call without restriction. The
 * Railway URL is hardcoded here because this is server-side code.
 *
 * Owner: trading-console module
 * Classification: security-sensitive (mutates trading-engine state)
 * Authorization: trading.configure permission required
 *
 * POST /set-feature-flag
 * Body: { flag_key: string, enabled: boolean }
 * Response: { ok: true, flag_key, enabled } on success.
 *
 * NOTE: This file is intentionally self-contained (no _shared/ imports)
 * so it can deploy without dragging in transitive dependencies.
 */
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.7'

// Railway base URL is hardcoded here intentionally — this code runs
// server-side in the Supabase Edge runtime, not in the browser, so
// it is not subject to the Lovable CSP. If Railway is ever moved,
// rotate this constant and redeploy the function.
const RAILWAY_URL = 'https://diplomatic-mercy-production-7e61.up.railway.app'

// S4 / C-β: shared secret protecting the Railway flag endpoint.
// Must match the RAILWAY_ADMIN_KEY env var on the Railway service.
// Forwarded as X-Api-Key on every Railway request. When unset, the
// Railway endpoint logs an open-mode warning but still accepts the
// call so existing deploys keep working — operators MUST set both
// secrets before enabling real capital.
const RAILWAY_ADMIN_KEY = Deno.env.get('RAILWAY_ADMIN_KEY') ?? ''

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

interface FlagBody {
    flag_key: string
    enabled: boolean
}

function parseBody(raw: unknown): FlagBody {
    if (!raw || typeof raw !== 'object') {
        throw new Error('INVALID_BODY')
    }
    const obj = raw as Record<string, unknown>
    const flag_key = obj.flag_key
    const enabled = obj.enabled
    if (
        typeof flag_key !== 'string' ||
        flag_key.length < 1 ||
        flag_key.length > 120
    ) {
        throw new Error('INVALID_BODY')
    }
    if (typeof enabled !== 'boolean') {
        throw new Error('INVALID_BODY')
    }
    return { flag_key, enabled }
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

    let body: FlagBody
    try {
        const raw = await req.json()
        body = parseBody(raw)
    } catch {
        return jsonResponse({ error: 'Invalid request body' }, 400)
    }

    let railwayResponse: Response
    try {
        const railwayHeaders: Record<string, string> = {
            'Content-Type': 'application/json',
        }
        // S4 / C-β: forward shared admin secret when configured. When
        // RAILWAY_ADMIN_KEY is empty the header is omitted and Railway
        // falls back to its open-mode warning path — same end-to-end
        // behaviour as before this fix.
        if (RAILWAY_ADMIN_KEY) {
            railwayHeaders['X-Api-Key'] = RAILWAY_ADMIN_KEY
        }
        railwayResponse = await fetch(
            `${RAILWAY_URL}/admin/trading/feature-flags`,
            {
                method: 'POST',
                headers: railwayHeaders,
                body: JSON.stringify({
                    flag_key: body.flag_key,
                    enabled: body.enabled,
                }),
            },
        )
    } catch (fetchErr) {
        console.error(
            '[SET-FEATURE-FLAG] Railway fetch failed',
            String(fetchErr),
        )
        return jsonResponse(
            { error: 'Failed to reach Railway backend' },
            502,
        )
    }

    let railwayBody: Record<string, unknown> = {}
    try {
        railwayBody = await railwayResponse.json()
    } catch {
        railwayBody = {}
    }

    if (!railwayResponse.ok || railwayBody.error) {
        console.error(
            '[SET-FEATURE-FLAG] Railway rejected flag change',
            {
                status: railwayResponse.status,
                error: railwayBody.error ?? null,
                flag_key: body.flag_key,
            },
        )
        return jsonResponse(
            { error: 'Backend rejected flag change' },
            502,
        )
    }

    return jsonResponse(
        { ok: true, flag_key: body.flag_key, enabled: body.enabled },
        200,
    )
})
