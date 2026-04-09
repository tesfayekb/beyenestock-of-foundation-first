/**
 * Auth Event Emission System
 * 
 * Implements event contracts defined in docs/07-reference/event-index.md.
 * Currently emits to console + stores in-memory for audit integration.
 * Will be wired to audit-logging module in Phase 3.
 */



export type AuthEventName =
  | 'auth.signed_up'
  | 'auth.signed_in'
  | 'auth.signed_out'
  | 'auth.password_reset'
  | 'auth.mfa_enrolled'
  | 'auth.mfa_recovered'
  | 'auth.failed_attempt'
  | 'auth.session_revoked';

export interface AuthEvent {
  event_id: string;
  name: AuthEventName;
  version: 'v1';
  timestamp: string;
  correlation_id: string;
  payload: Record<string, unknown>;
}

// In-memory event buffer for audit module integration
const eventBuffer: AuthEvent[] = [];
const MAX_BUFFER_SIZE = 1000;

function generateEventId(): string {
  // Use crypto.randomUUID if available, fallback to timestamp-based
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

function generateCorrelationId(): string {
  return generateEventId();
}

export function emitAuthEvent(
  name: AuthEventName,
  payload: Record<string, unknown>,
  correlationId?: string
): AuthEvent {
  const event: AuthEvent = {
    event_id: generateEventId(),
    name,
    version: 'v1',
    timestamp: new Date().toISOString(),
    correlation_id: correlationId ?? generateCorrelationId(),
    payload,
  };

  // Buffer for audit module consumption
  if (eventBuffer.length >= MAX_BUFFER_SIZE) {
    eventBuffer.shift();
  }
  eventBuffer.push(event);

  // Log for observability (structured logging)
  console.info(`[AUTH_EVENT] ${event.name}`, {
    event_id: event.event_id,
    correlation_id: event.correlation_id,
    timestamp: event.timestamp,
    // Exclude sensitive payload fields from console
    user_id: payload.user_id ?? null,
  });

  return event;
}

/** Retrieve buffered events (for audit module integration) */
export function getBufferedEvents(): ReadonlyArray<AuthEvent> {
  return [...eventBuffer];
}

/** Drain buffered events (audit module calls this after persisting) */
export function drainBufferedEvents(): AuthEvent[] {
  return eventBuffer.splice(0, eventBuffer.length);
}

// Convenience emitters with typed payloads

export function emitSignedUp(userId: string, method: 'email' | 'oauth' = 'email') {
  return emitAuthEvent('auth.signed_up', {
    user_id: userId,
    method,
  });
}

export function emitSignedIn(userId: string, method: 'password' | 'oauth' | 'mfa' = 'password') {
  return emitAuthEvent('auth.signed_in', {
    user_id: userId,
    method,
  });
}

export function emitSignedOut(userId: string, sessionId?: string) {
  return emitAuthEvent('auth.signed_out', {
    user_id: userId,
    session_id: sessionId ?? 'unknown',
  });
}

export function emitPasswordReset(userId: string, stage: 'requested' | 'completed') {
  return emitAuthEvent('auth.password_reset', {
    user_id: userId,
    stage,
  });
}

export function emitMfaEnrolled(userId: string, mfaType: 'totp' | 'sms' = 'totp') {
  return emitAuthEvent('auth.mfa_enrolled', {
    user_id: userId,
    mfa_type: mfaType,
  });
}

export function emitMfaRecovered(userId: string) {
  return emitAuthEvent('auth.mfa_recovered', {
    user_id: userId,
  });
}

export function emitFailedAttempt(
  reason: 'invalid_password' | 'account_locked' | 'mfa_failed' | 'unknown_user',
  userId?: string
) {
  return emitAuthEvent('auth.failed_attempt', {
    user_id: userId ?? null,
    reason,
  });
}

export function emitSessionRevoked(userId: string, sessionId: string) {
  return emitAuthEvent('auth.session_revoked', {
    user_id: userId,
    session_id: sessionId,
  });
}
