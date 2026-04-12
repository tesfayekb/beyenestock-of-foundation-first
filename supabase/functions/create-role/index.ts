/**
 * create-role — Create a new custom role.
 *
 * Requires: roles.create permission + recent auth.
 * Audit: rbac.role_created (fail-closed with rollback).
 *
 * POST /create-role
 * Body: { key: string, name: string, description?: string }
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow, requireRecentAuth } from '../_shared/authorization.ts'
import { logAuditEvent } from '../_shared/audit.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'
import { validateRequest } from '../_shared/validate-request.ts'

const RESERVED_KEYS = ['superadmin', 'admin', 'user']

const BodySchema = z.object({
  key: z.string().trim().min(1).max(50).regex(
    /^[a-z][a-z0-9_-]*$/,
    'Key must start with a lowercase letter and contain only lowercase letters, numbers, underscores, and hyphens',
  ),
  name: z.string().trim().min(1).max(100),
  description: z.string().trim().max(500).optional().default(''),
})

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'POST') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'roles.create')
  requireRecentAuth(ctx.user.lastSignInAt, 30 * 60 * 1000, ctx.user.id)

  const body = await req.json()
  const { key, name, description } = validateRequest(BodySchema, body)

  // Reject reserved keys
  if (RESERVED_KEYS.includes(key)) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(400, `Role key "${key}" is reserved and cannot be used`, {
      correlationId: ctx.correlationId,
    })
  }

  // Insert the new role (is_base=false, is_immutable=false for custom roles)
  const { data: newRole, error: insertError } = await supabaseAdmin
    .from('roles')
    .insert({ key, name, description: description || null, is_base: false, is_immutable: false })
    .select('id, key, name')
    .single()

  if (insertError) {
    if (insertError.code === '23505') {
      const { apiError } = await import('../_shared/api-error.ts')
      return apiError(409, `Role with key "${key}" already exists`, {
        correlationId: ctx.correlationId,
      })
    }
    throw insertError
  }

  // Audit — fail-closed with rollback
  const auditResult = await logAuditEvent({
    actorId: ctx.user.id,
    action: 'rbac.role_created',
    targetType: 'roles',
    targetId: newRole.id,
    metadata: {
      role_key: newRole.key,
      role_name: newRole.name,
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  if (!auditResult.success) {
    // Rollback: delete the created role
    await supabaseAdmin
      .from('roles')
      .delete()
      .eq('id', newRole.id)

    const { apiError } = await import('../_shared/api-error.ts')
    console.error('[CREATE-ROLE] Audit write failed — rolling back', auditResult)
    return apiError(500, 'Audit logging failed — operation rolled back', {
      code: 'AUDIT_WRITE_FAILED',
      correlationId: ctx.correlationId,
    })
  }

  return apiSuccess({
    id: newRole.id,
    key: newRole.key,
    name: newRole.name,
    correlation_id: ctx.correlationId,
    message: `Role "${name}" created successfully`,
  }, 201)
}))
