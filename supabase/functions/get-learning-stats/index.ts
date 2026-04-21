/**
 * get-learning-stats — Section 13 UI-2 proxy to Railway.
 *
 * Why this proxy exists: the Lovable-hosted frontend's Content
 * Security Policy blocks direct browser fetches to the Railway API,
 * and the admin secret (RAILWAY_ADMIN_KEY) must NEVER ship in the
 * browser bundle. This Edge function authenticates the Supabase
 * session, enforces trading.view permission, and forwards to
 * Railway with the admin key attached server-side. Same pattern as
 * set-feature-flag, subscription-key-status, kill-switch.
 *
 * Owner: trading-console module
 * Classification: read-only (no state mutation — wraps a backend
 *   GET that itself is side-effect free).
 * Authorization: trading.view permission required.
 *
 * GET /get-learning-stats  →  passes through to
 *   GET $RAILWAY_API_URL/admin/trading/learning-stats
 *   with `X-Api-Key: $RAILWAY_ADMIN_KEY`.
 *
 * REQUIRED SECRETS (set via `supabase secrets set ...`):
 *   RAILWAY_API_URL      — e.g. https://trading-api.up.railway.app
 *   RAILWAY_ADMIN_KEY    — same value as the Railway env var, must
 *                          match config.RAILWAY_ADMIN_KEY on Railway.
 *
 * NOTE: Self-contained (no _shared/ imports) so this function
 * deploys without dragging in transitive dependencies. Mirrors
 * subscription-key-status layout.
 */
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.7'

const corsHeaders: Record<string, string> = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers':
        'authorization, x-client-info, apikey, content-type',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
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

// The fail-open skeleton the frontend will display when Railway is
// unreachable. Keeping the shape stable means the UI always renders
// the 7 panels in their "warming up" state instead of erroring out.
const FAIL_OPEN_PAYLOAD: Record<string, unknown> = {
    realized_vol_20d: null,
    vix_current: null,
    iv_rv_ratio: null,
    realized_vol_last_date: null,
    butterfly_gates: {},
    butterfly_allowed_today: 0,
    strategy_matrix: [],
    halt_threshold_pct: null,
    halt_threshold_source: 'default',
    butterfly_thresholds: {
        gex_conf: 0.40,
        wall_distance: 0.003,
        concentration: 0.25,
        source: 'default',
    },
    model_drift_alert: false,
    sizing_phase: 1,
    sizing_phase_advanced_at: null,
}

Deno.serve(async (req: Request): Promise<Response> => {
    if (req.method === 'OPTIONS') {
        return new Response('ok', { headers: corsHeaders })
    }
    if (req.method !== 'GET') {
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
        await checkPermission(ctx, 'trading.view')
    } catch {
        return jsonResponse(
            { error: 'Forbidden: requires trading.view' },
            403,
        )
    }

    const railwayBase = (Deno.env.get('RAILWAY_API_URL') ?? '').replace(
        /\/+$/,
        '',
    )
    const adminKey = Deno.env.get('RAILWAY_ADMIN_KEY') ?? ''

    if (!railwayBase || !adminKey) {
        // Fail-open shape — the UI renders every panel in warmup
        // state rather than showing a broken console. Log on the
        // server side so an operator can spot the misconfiguration.
        console.warn(
            'get-learning-stats: RAILWAY_API_URL or RAILWAY_ADMIN_KEY unset',
        )
        return jsonResponse(
            { ...FAIL_OPEN_PAYLOAD, error: 'proxy_misconfigured' },
            200,
        )
    }

    const url = `${railwayBase}/admin/trading/learning-stats`

    try {
        const res = await fetch(url, {
            method: 'GET',
            headers: {
                'X-Api-Key': adminKey,
                Accept: 'application/json',
            },
        })

        // Railway side returns a 200-shaped fail-open body even on
        // internal errors (see backend/main.py::get_learning_stats),
        // so anything but 200 here is a genuine infrastructure
        // failure — log and fall back to the warmup skeleton.
        if (!res.ok) {
            console.warn(
                'get-learning-stats: upstream status',
                res.status,
            )
            return jsonResponse(
                { ...FAIL_OPEN_PAYLOAD, error: `upstream_${res.status}` },
                200,
            )
        }

        const body = await res.json()
        return jsonResponse(body, 200)
    } catch (err) {
        console.warn(
            'get-learning-stats: fetch failed',
            String((err as Error).message),
        )
        return jsonResponse(
            { ...FAIL_OPEN_PAYLOAD, error: 'upstream_unreachable' },
            200,
        )
    }
})
