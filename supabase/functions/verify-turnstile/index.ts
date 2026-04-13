/**
 * verify-turnstile — Server-side Cloudflare Turnstile token verification.
 *
 * Owner: auth module
 * Classification: security-critical
 * Fail behavior: fail-secure — rejects on any verification failure
 *
 * This endpoint does NOT require authentication (called before login).
 * Rate-limited to prevent abuse.
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { apiError } from '../_shared/api-error.ts'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'

const TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'

const RequestSchema = z.object({
  token: z.string().min(1, 'Turnstile token is required'),
})

const handler = createHandler(async (req: Request): Promise<Response> => {
  if (req.method !== 'POST') {
    return apiError(405, 'Method not allowed')
  }

  const body = await req.json().catch(() => null)
  if (!body) {
    return apiError(400, 'Invalid JSON body')
  }

  const parsed = RequestSchema.safeParse(body)
  if (!parsed.success) {
    return apiError(400, 'Missing turnstile token', { code: 'VALIDATION_ERROR' })
  }

  const secretKey = Deno.env.get('TURNSTILE_SECRET_KEY')
  if (!secretKey) {
    console.error('[verify-turnstile] TURNSTILE_SECRET_KEY not configured')
    return apiError(500, 'CAPTCHA verification not configured')
  }

  const ip = req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() || undefined

  const formData = new FormData()
  formData.append('secret', secretKey)
  formData.append('response', parsed.data.token)
  if (ip) formData.append('remoteip', ip)

  const result = await fetch(TURNSTILE_VERIFY_URL, {
    method: 'POST',
    body: formData,
  })

  const outcome = await result.json()

  if (!outcome.success) {
    return apiError(403, 'CAPTCHA verification failed', { code: 'CAPTCHA_FAILED' })
  }

  return apiSuccess({ success: true })
}, { rateLimit: 'strict' })

Deno.serve(handler)
