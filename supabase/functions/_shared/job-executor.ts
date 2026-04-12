/**
 * Job execution utilities — shared by all job edge functions.
 *
 * Provides:
 *   - executeWithRetry()  — retry wrapper with backoff, jitter, error classification
 *   - classifyError()     — maps errors to failure_type enum values
 *   - detectPoisonJob()   — checks consecutive cross-execution failure count
 *
 * Consumers: all Stage 5D job edge functions (health_check, metrics_aggregate,
 *            alert_evaluation, audit_cleanup)
 *
 * Owner: jobs-and-scheduler module
 * Sync rule: changes here affect ALL job consumers — update function-index.md
 */

import { supabaseAdmin } from './supabase-admin.ts'
import { logAuditEvent } from './audit.ts'

// ---------------------------------------------------------------------------
// Error classification
// ---------------------------------------------------------------------------

export type FailureType = 'transient' | 'dependency' | 'validation' | 'authorization' | 'permanent'

/**
 * Classifies an error into one of the five failure types.
 *
 * - transient: timeouts, rate limits, network errors → retry
 * - dependency: external service unavailable → retry with longer backoff
 * - validation: bad input/data → fail fast, no retry
 * - authorization: permission denied → fail fast, no retry
 * - permanent: unrecoverable → fail fast, dead-letter
 */
export function classifyError(error: unknown): FailureType {
  if (!(error instanceof Error)) return 'permanent'

  const msg = error.message.toLowerCase()
  const name = error.name.toLowerCase()

  // Authorization errors
  if (msg.includes('permission denied') || msg.includes('unauthorized') ||
      msg.includes('forbidden') || msg.includes('jwt')) {
    return 'authorization'
  }

  // Validation errors
  if (msg.includes('validation') || msg.includes('invalid input') ||
      msg.includes('constraint') || msg.includes('violates check')) {
    return 'validation'
  }

  // Transient errors (timeouts, rate limits, network)
  if (msg.includes('timeout') || msg.includes('timed out') ||
      msg.includes('rate limit') || msg.includes('too many requests') ||
      msg.includes('econnrefused') || msg.includes('econnreset') ||
      msg.includes('fetch failed') || msg.includes('network') ||
      name.includes('aborterror')) {
    return 'transient'
  }

  // Dependency errors (external services down)
  if (msg.includes('service unavailable') || msg.includes('503') ||
      msg.includes('502') || msg.includes('bad gateway') ||
      msg.includes('upstream')) {
    return 'dependency'
  }

  return 'permanent'
}

/**
 * Returns true if a failure type should be retried.
 */
export function isRetryable(failureType: FailureType): boolean {
  return failureType === 'transient' || failureType === 'dependency'
}

// ---------------------------------------------------------------------------
// Retry backoff
// ---------------------------------------------------------------------------

/** Backoff schedule in milliseconds: 30s → 2m → 10m → dead-letter */
const BACKOFF_MS = [30_000, 120_000, 600_000]

/**
 * Computes backoff delay with ±25% jitter.
 */
function backoffWithJitter(attempt: number): number {
  const base = BACKOFF_MS[Math.min(attempt - 1, BACKOFF_MS.length - 1)]
  const jitter = base * 0.25 * (Math.random() * 2 - 1) // ±25%
  return Math.max(0, Math.round(base + jitter))
}

// ---------------------------------------------------------------------------
// Poison job detection
// ---------------------------------------------------------------------------

const POISON_THRESHOLD = 5
const DEFAULT_CIRCUIT_BREAKER_THRESHOLD = 3

/**
 * Checks if a job has consecutive cross-execution failures meeting the
 * poison threshold (default: 5). Looks at the most recent N executions
 * and checks if ALL are in a terminal failure state.
 */
export async function detectPoisonJob(jobId: string): Promise<boolean> {
  const { data, error } = await supabaseAdmin
    .from('job_executions')
    .select('state')
    .eq('job_id', jobId)
    .order('created_at', { ascending: false })
    .limit(POISON_THRESHOLD)

  if (error || !data || data.length < POISON_THRESHOLD) return false

  const failureStates = new Set(['failed', 'dead_lettered'])
  return data.every((row: { state: string }) => failureStates.has(row.state))
}

// ---------------------------------------------------------------------------
// Circuit breaker — auto-pause on repeated dependency failures
// ---------------------------------------------------------------------------

/**
 * Checks if a job has N consecutive dependency failures (cross-execution).
 * If so, auto-pauses the job and emits job.circuit_breaker_tripped.
 */
async function checkCircuitBreaker(
  jobId: string,
  threshold: number,
  correlationId: string,
): Promise<boolean> {
  const { data, error } = await supabaseAdmin
    .from('job_executions')
    .select('failure_type')
    .eq('job_id', jobId)
    .in('state', ['failed', 'dead_lettered'])
    .order('created_at', { ascending: false })
    .limit(threshold)

  if (error || !data || data.length < threshold) return false

  const allDependency = data.every(
    (row: { failure_type: string | null }) => row.failure_type === 'dependency',
  )

  if (!allDependency) return false

  // Auto-pause the job
  await supabaseAdmin
    .from('job_registry')
    .update({ status: 'paused', enabled: false, updated_at: new Date().toISOString() })
    .eq('id', jobId)

  await logAuditEvent({
    actorId: null,
    action: 'job.circuit_breaker_tripped',
    targetType: 'job',
    metadata: {
      jobId,
      threshold,
      reason: `${threshold} consecutive dependency failures`,
    },
    correlationId,
  })

  console.warn(
    `[JOB-EXECUTOR] Circuit breaker tripped: job ${jobId} auto-paused after ${threshold} consecutive dependency failures`,
  )

  return true
}

// ---------------------------------------------------------------------------
// Kill switch & class pause checks
// ---------------------------------------------------------------------------

/**
 * Checks if the global kill switch is active.
 * Kill switch row: __kill_switch__ — active when enabled = false.
 */
async function isGlobalKillSwitchActive(): Promise<boolean> {
  const { data } = await supabaseAdmin
    .from('job_registry')
    .select('enabled')
    .eq('id', '__kill_switch__')
    .single()

  // If no row or enabled = true → kill switch is NOT active
  // If enabled = false → kill switch IS active (jobs should stop)
  return data ? !data.enabled : false
}

/**
 * Checks if the class-level pause is active for a given job class.
 */
async function isClassPaused(jobClass: string): Promise<boolean> {
  const { data } = await supabaseAdmin
    .from('job_registry')
    .select('enabled')
    .eq('id', `__class_pause:${jobClass}__`)
    .single()

  return data ? !data.enabled : false
}

/**
 * Marks a job as poison in the registry.
 */
async function markJobPoison(jobId: string): Promise<void> {
  await supabaseAdmin
    .from('job_registry')
    .update({ status: 'poison', enabled: false })
    .eq('id', jobId)
}

// ---------------------------------------------------------------------------
// executeWithRetry
// ---------------------------------------------------------------------------

export interface ExecuteOptions {
  /** The job ID from job_registry */
  jobId: string
  /** Correlation ID for audit trail */
  correlationId?: string
  /** Schedule window ID for dedup */
  scheduleWindowId?: string
  /** Override max retries (defaults to job_registry.max_retries) */
  maxRetries?: number
  /** Actor ID for audit events (system jobs use a sentinel) */
  actorId?: string
  /** IP address for audit */
  ipAddress?: string
  /** User agent for audit */
  userAgent?: string
  /** Scheduled time from pg_cron context (ISO string). Falls back to now() for manual triggers. */
  scheduledTime?: string
}

export interface ExecutionResult {
  success: boolean
  executionId: string
  state: string
  attempt: number
  durationMs: number
  error?: { message: string; failureType: FailureType }
}

/**
 * Executes a job handler with retry, backoff, jitter, error classification,
 * poison detection, and full audit trail.
 *
 * Returns the final execution result. Does NOT throw — all errors are
 * captured in the result object.
 */
export async function executeWithRetry(
  handler: () => Promise<{ affectedRecords?: number; resourceUsage?: Record<string, unknown> }>,
  options: ExecuteOptions,
): Promise<ExecutionResult> {
  const { jobId, correlationId, scheduleWindowId, actorId, ipAddress, userAgent, scheduledTime } = options

  // Fetch job config from registry
  const { data: jobConfig, error: jobError } = await supabaseAdmin
    .from('job_registry')
    .select('*')
    .eq('id', jobId)
    .single()

  if (jobError || !jobConfig) {
    return {
      success: false,
      executionId: '',
      state: 'failed',
      attempt: 0,
      durationMs: 0,
      error: { message: `Job not found: ${jobId}`, failureType: 'permanent' },
    }
  }

  // Check if job is enabled
  if (!jobConfig.enabled || jobConfig.status === 'poison') {
    return {
      success: false,
      executionId: '',
      state: 'cancelled',
      attempt: 0,
      durationMs: 0,
      error: { message: `Job disabled or poisoned: ${jobId}`, failureType: 'permanent' },
    }
  }

  // ── Global kill switch check ──
  const killSwitchActive = await isGlobalKillSwitchActive()
  if (killSwitchActive) {
    return {
      success: false,
      executionId: '',
      state: 'cancelled',
      attempt: 0,
      durationMs: 0,
      error: { message: 'Global kill switch is active — all job execution halted', failureType: 'permanent' },
    }
  }

  // ── Class-level pause check ──
  const classPaused = await isClassPaused(jobConfig.class)
  if (classPaused) {
    return {
      success: false,
      executionId: '',
      state: 'cancelled',
      attempt: 0,
      durationMs: 0,
      error: { message: `Class-level pause active for ${jobConfig.class}`, failureType: 'permanent' },
    }
  }

  // Schedule window dedup check (for exactly_once / at_least_once with dedup)
  if (scheduleWindowId) {
    const { data: existing } = await supabaseAdmin
      .from('job_executions')
      .select('id')
      .eq('job_id', jobId)
      .eq('schedule_window_id', scheduleWindowId)
      .in('state', ['running', 'succeeded'])
      .limit(1)

    if (existing && existing.length > 0) {
      return {
        success: true,
        executionId: existing[0].id,
        state: 'succeeded',
        attempt: 0,
        durationMs: 0,
      }
    }
  }

  // Concurrency check (forbid policy)
  if (jobConfig.concurrency_policy === 'forbid') {
    const { data: running } = await supabaseAdmin
      .from('job_executions')
      .select('id')
      .eq('job_id', jobId)
      .eq('state', 'running')
      .limit(1)

    if (running && running.length > 0) {
      return {
        success: false,
        executionId: '',
        state: 'cancelled',
        attempt: 0,
        durationMs: 0,
        error: { message: 'Concurrency policy: forbid — another execution is running', failureType: 'transient' },
      }
    }
  }

  const maxRetries = options.maxRetries ?? jobConfig.max_retries ?? 3
  let attempt = 0
  let lastFailureType: FailureType = 'permanent'
  let lastErrorMessage = ''
  let executionId = ''

  // Create initial execution record
  const { data: execRecord, error: execError } = await supabaseAdmin
    .from('job_executions')
    .insert({
      job_id: jobId,
      schedule_window_id: scheduleWindowId,
      state: 'running',
      job_version: jobConfig.version,
      attempt: 1,
      started_at: new Date().toISOString(),
      scheduled_time: scheduledTime ?? new Date().toISOString(),
      correlation_id: correlationId,
    })
    .select('id, execution_id')
    .single()

  if (execError || !execRecord) {
    return {
      success: false,
      executionId: '',
      state: 'failed',
      attempt: 0,
      durationMs: 0,
      error: { message: `Failed to create execution record: ${execError?.message}`, failureType: 'permanent' },
    }
  }

  executionId = execRecord.id

  // Emit job start audit event
  await logAuditEvent({
    actorId: actorId ?? null,
    action: 'job.started',
    targetType: 'job',
    metadata: { jobId, executionId, attempt: 1, scheduleWindowId },
    ipAddress: ipAddress ?? '0.0.0.0',
    userAgent: userAgent ?? 'system/job-executor',
    correlationId: correlationId ?? executionId,
  })

  const startTime = Date.now()

  while (attempt < maxRetries) {
    attempt++

    try {
      const result = await handler()
      const durationMs = Date.now() - startTime

      // Update execution record to succeeded
      await supabaseAdmin
        .from('job_executions')
        .update({
          state: 'succeeded',
          attempt,
          completed_at: new Date().toISOString(),
          duration_ms: durationMs,
          queue_delay_ms: scheduledTime ? Math.max(0, startTime - new Date(scheduledTime).getTime()) : 0,
          affected_records: result.affectedRecords ?? 0,
          resource_usage: result.resourceUsage ?? {},
        })
        .eq('id', executionId)

      // Emit job completed audit event
      await logAuditEvent({
        actorId: actorId ?? null,
        action: 'job.completed',
        targetType: 'job',
        metadata: { jobId, executionId, attempt, durationMs, affectedRecords: result.affectedRecords },
        ipAddress: ipAddress ?? '0.0.0.0',
        userAgent: userAgent ?? 'system/job-executor',
        correlationId: correlationId ?? executionId,
      })

      // SLO breach detection: emit job.slo_breach if duration exceeds 80% of timeout budget
      const sloThresholdMs = (jobConfig.timeout_seconds ?? 30) * 1000 * 0.8
      if (durationMs > sloThresholdMs) {
        await logAuditEvent({
          actorId: actorId ?? null,
          action: 'job.slo_breach',
          targetType: 'job',
          metadata: {
            jobId,
            executionId,
            attempt,
            durationMs,
            sloThresholdMs,
            timeoutSeconds: jobConfig.timeout_seconds,
            budgetUsedPct: Math.round((durationMs / (jobConfig.timeout_seconds * 1000)) * 100),
          },
          ipAddress: ipAddress ?? '0.0.0.0',
          userAgent: userAgent ?? 'system/job-executor',
          correlationId: correlationId ?? executionId,
        })
        console.warn(`[JOB-EXECUTOR] SLO breach: job ${jobId} took ${durationMs}ms (threshold: ${sloThresholdMs}ms, budget: ${jobConfig.timeout_seconds}s)`)
      }

      return { success: true, executionId, state: 'succeeded', attempt, durationMs }
    } catch (err) {
      lastFailureType = classifyError(err)
      lastErrorMessage = err instanceof Error ? err.message : String(err)

      // Non-retryable → break immediately
      if (!isRetryable(lastFailureType)) break

      // Update execution to retry_pending
      await supabaseAdmin
        .from('job_executions')
        .update({
          state: 'retry_pending',
          attempt,
          failure_type: lastFailureType,
          error: { message: lastErrorMessage, attempt },
        })
        .eq('id', executionId)

      // If more retries left, wait with backoff
      if (attempt < maxRetries) {
        const delay = backoffWithJitter(attempt)
        await new Promise(resolve => setTimeout(resolve, delay))

        // Update state back to running for next attempt
        await supabaseAdmin
          .from('job_executions')
          .update({ state: 'running', attempt: attempt + 1 })
          .eq('id', executionId)
      }
    }
  }

  // All retries exhausted or non-retryable error
  const durationMs = Date.now() - startTime
  const terminalState = attempt >= maxRetries ? 'dead_lettered' : 'failed'

  await supabaseAdmin
    .from('job_executions')
    .update({
      state: terminalState,
      attempt,
      completed_at: new Date().toISOString(),
      duration_ms: durationMs,
      failure_type: lastFailureType,
      error: { message: lastErrorMessage, failureType: lastFailureType, attempt },
    })
    .eq('id', executionId)

  // Emit job failed audit event
  await logAuditEvent({
    actorId: actorId ?? null,
    action: 'job.failed',
    targetType: 'job',
    metadata: { jobId, executionId, attempt, durationMs, failureType: lastFailureType, terminalState },
    ipAddress: ipAddress ?? '0.0.0.0',
    userAgent: userAgent ?? 'system/job-executor',
    correlationId: correlationId ?? executionId,
  })

  // Poison detection
  const isPoisoned = await detectPoisonJob(jobId)
  if (isPoisoned) {
    await markJobPoison(jobId)
    console.error(`[JOB-EXECUTOR] Job ${jobId} marked as POISON after ${POISON_THRESHOLD} consecutive failures`)
  }

  // Circuit breaker: auto-pause on repeated dependency failures
  if (lastFailureType === 'dependency' && !isPoisoned) {
    const cbThreshold = jobConfig.circuit_breaker_threshold ?? DEFAULT_CIRCUIT_BREAKER_THRESHOLD
    await checkCircuitBreaker(jobId, cbThreshold, correlationId ?? executionId)
  }

  return {
    success: false,
    executionId,
    state: terminalState,
    attempt,
    durationMs,
    error: { message: lastErrorMessage, failureType: lastFailureType },
  }
}
