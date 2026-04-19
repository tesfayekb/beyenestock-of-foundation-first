/**
 * subscription-key-status — Returns key configured/masked status for
 * every external API key the trading system uses.
 *
 * Why this proxy exists: the Lovable-hosted frontend's Content
 * Security Policy blocks direct browser fetches to the Railway API.
 * The Railway endpoint reads `os.environ` and returns masked
 * previews. Mirroring that into Postgres would persist
 * sensitive-adjacent data, so we instead read from Supabase Edge
 * secrets here and produce the same response shape on the fly.
 *
 * Owner: trading-console module
 * Classification: read-only (no state mutation)
 * Authorization: trading.view permission required
 *
 * GET /subscription-key-status
 * Response: { keys: Record<string, KeyStatus> }
 *
 * SECRET MIRRORING: every secret listed below must be set as a
 * Supabase Edge function secret with the SAME name used on Railway.
 * Configure with `supabase secrets set` after deploying this function.
 *
 * NOTE: This file is intentionally self-contained (no _shared/ imports)
 * so it can deploy without dragging in transitive dependencies.
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

interface KeyStatus {
    configured: boolean
    masked: string
    env_var: string
    sandbox?: boolean
    today_tokens_in?: number
    today_tokens_out?: number
    provider?: string
    model?: string
}

// Mask helper: first 4 chars + '...' + last 6 chars. Returns
// 'not set' when empty. Mirrors backend/main.py::_mask_key exactly.
function maskKey(value: string): string {
    if (!value) return 'not set'
    if (value.length <= 10) return '****'
    return `${value.slice(0, 4)}...${value.slice(-6)}`
}

function readSecret(name: string): string {
    return Deno.env.get(name) ?? ''
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

    // Token counters live in Redis on Railway and are NOT mirrored
    // into Edge secrets — they would be stale and noisy. The dashboard
    // tolerates 0/0 here; the canonical view stays on Railway.
    const today_tokens_in = 0
    const today_tokens_out = 0

    const supabaseUrl = readSecret('SUPABASE_URL')
    const databento = readSecret('DATABENTO_API_KEY')
    const tradier = readSecret('TRADIER_API_KEY')
    const polygon = readSecret('POLYGON_API_KEY')
    const finnhub = readSecret('FINNHUB_API_KEY')
    const anthropic = readSecret('ANTHROPIC_API_KEY')
    const openai = readSecret('OPENAI_API_KEY')
    const unusualWhales = readSecret('UNUSUAL_WHALES_API_KEY')
    const newsapi = readSecret('NEWSAPI_KEY')

    // TRADIER_SANDBOX is "true"/"false" string-typed in env. Default
    // to true when unset to match backend/config.py defensive default.
    const tradierSandboxRaw = readSecret('TRADIER_SANDBOX').toLowerCase()
    const tradierSandbox = tradierSandboxRaw !== 'false'

    const keys: Record<string, KeyStatus> = {
        supabase_url: {
            configured: Boolean(supabaseUrl),
            masked: maskKey(supabaseUrl),
            env_var: 'SUPABASE_URL',
        },
        databento: {
            configured: Boolean(databento),
            masked: maskKey(databento),
            env_var: 'DATABENTO_API_KEY',
        },
        tradier: {
            configured: Boolean(tradier),
            masked: maskKey(tradier),
            env_var: 'TRADIER_API_KEY',
            sandbox: tradierSandbox,
        },
        polygon: {
            configured: Boolean(polygon),
            masked: maskKey(polygon),
            env_var: 'POLYGON_API_KEY',
        },
        finnhub: {
            configured: Boolean(finnhub),
            masked: maskKey(finnhub),
            env_var: 'FINNHUB_API_KEY',
        },
        anthropic: {
            configured: Boolean(anthropic),
            masked: maskKey(anthropic),
            env_var: 'ANTHROPIC_API_KEY',
            today_tokens_in,
            today_tokens_out,
        },
        openai: {
            configured: Boolean(openai),
            masked: maskKey(openai),
            env_var: 'OPENAI_API_KEY',
        },
        unusual_whales: {
            configured: Boolean(unusualWhales),
            masked: maskKey(unusualWhales),
            env_var: 'UNUSUAL_WHALES_API_KEY',
        },
        newsapi: {
            configured: Boolean(newsapi),
            masked: maskKey(newsapi),
            env_var: 'NEWSAPI_KEY',
        },
        ai_provider: {
            configured: true,
            masked: '',
            env_var: 'AI_PROVIDER',
            provider: readSecret('AI_PROVIDER') || 'anthropic',
            model: readSecret('AI_MODEL') || 'claude-sonnet-4-5',
        },
    }

    return jsonResponse({ keys }, 200)
})
