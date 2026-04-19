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
 * Audit: trading.feature_flag_changed
 *
 * POST /set-feature-flag
 * Body: { flag_key: string, enabled: boolean }
 * Response: { ok: true, flag_key, enabled } on success.
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow } from '../_shared/authorization.ts'
import { validateRequest, z } from '../_shared/validate-request.ts'
import { logAuditEvent } from '../_shared/audit.ts'
import { apiError } from '../_shared/api-error.ts'

// Railway base URL is hardcoded here intentionally — this code runs
// server-side in the Supabase Edge runtime, not in the browser, so
// it is not subject to the Lovable CSP. If Railway is ever moved,
// rotate this constant and redeploy the function.
const RAILWAY_URL = 'https://diplomatic-mercy-production-7e61.up.railway.app'

const BodySchema = z.object({
    flag_key: z.string().min(1).max(120),
    enabled: z.boolean(),
})

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
    if (req.method !== 'POST') {
        return apiError(405, 'Method not allowed', {
            correlationId: crypto.randomUUID(),
        })
    }

    const ctx = await authenticateRequest(req)
    await checkPermissionOrThrow(ctx.user.id, 'trading.configure')

    const body = validateRequest(BodySchema, await req.json())

    // Forward to the Railway backend. The backend whitelists the
    // flag_key against _TRADING_FLAG_KEYS and applies signal-flag
    // polarity inversion server-side, so we just relay verbatim.
    let railwayResponse: Response
    try {
        railwayResponse = await fetch(
            `${RAILWAY_URL}/admin/trading/feature-flags`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
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
        return apiError(502, 'Failed to reach Railway backend', {
            correlationId: ctx.correlationId,
        })
    }

    let railwayBody: Record<string, unknown> = {}
    try {
        railwayBody = await railwayResponse.json()
    } catch {
        // Railway returned non-JSON — treat as failure.
        railwayBody = {}
    }

    if (!railwayResponse.ok || railwayBody.error) {
        await logAuditEvent({
            actorId: ctx.user.id,
            action: 'trading.feature_flag_change_failed',
            targetType: 'feature_flag',
            targetId: body.flag_key,
            metadata: {
                enabled: body.enabled,
                railway_status: railwayResponse.status,
                railway_error: railwayBody.error ?? null,
            },
            ipAddress: ctx.ipAddress,
            userAgent: ctx.userAgent,
            correlationId: ctx.correlationId,
        })
        return apiError(502, 'Backend rejected flag change', {
            correlationId: ctx.correlationId,
        })
    }

    await logAuditEvent({
        actorId: ctx.user.id,
        action: 'trading.feature_flag_changed',
        targetType: 'feature_flag',
        targetId: body.flag_key,
        metadata: {
            flag_key: body.flag_key,
            enabled: body.enabled,
        },
        ipAddress: ctx.ipAddress,
        userAgent: ctx.userAgent,
        correlationId: ctx.correlationId,
    })

    return apiSuccess({
        ok: true,
        flag_key: body.flag_key,
        enabled: body.enabled,
    })
}, { rateLimit: 'strict' }))
