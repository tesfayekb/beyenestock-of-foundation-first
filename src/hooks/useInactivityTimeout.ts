/**
 * useInactivityTimeout — signs out the user after a configurable idle period.
 * Listens for mousemove, keydown, touchstart, and scroll events to reset the timer.
 * Default timeout: 30 minutes.
 */
import { useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { DEV_MODE, DEV_INACTIVITY_TIMEOUT_MS } from '@/lib/dev-mode';

const DEFAULT_TIMEOUT_MS = DEV_MODE ? DEV_INACTIVITY_TIMEOUT_MS : 30 * 60 * 1000;
const ACTIVITY_EVENTS: (keyof DocumentEventMap)[] = ['mousemove', 'keydown', 'touchstart', 'scroll', 'visibilitychange'];
// Throttle activity detection to avoid excessive timer resets
const THROTTLE_MS = 30_000; // 30 seconds

interface UseInactivityTimeoutOptions {
  timeoutMs?: number;
  onTimeout: () => Promise<void>;
  enabled?: boolean;
}

export function useInactivityTimeout({
  timeoutMs = DEFAULT_TIMEOUT_MS,
  onTimeout,
  enabled = true,
}: UseInactivityTimeoutOptions) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastActivityRef = useRef<number>(Date.now());
  const navigate = useNavigate();

  const handleTimeout = useCallback(async () => {
    try {
      await onTimeout();
    } catch {
      // Sign-out failed — still redirect
    }
    toast.info('Session expired', {
      description: 'You were signed out due to inactivity.',
    });
    navigate('/sign-in', { replace: true });
  }, [onTimeout, navigate]);

  const resetTimer = useCallback(() => {
    const now = Date.now();
    // Throttle: only reset if enough time has passed since last reset
    if (now - lastActivityRef.current < THROTTLE_MS) return;
    lastActivityRef.current = now;

    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    timerRef.current = setTimeout(handleTimeout, timeoutMs);
  }, [handleTimeout, timeoutMs]);

  useEffect(() => {
    if (!enabled) return;

    // Start the timer immediately
    lastActivityRef.current = Date.now();
    timerRef.current = setTimeout(handleTimeout, timeoutMs);

    const onActivity = (e: Event) => {
      // For visibilitychange, only reset when tab becomes visible (user returning)
      if (e.type === 'visibilitychange' && document.hidden) return;
      resetTimer();
    };

    for (const event of ACTIVITY_EVENTS) {
      document.addEventListener(event, onActivity, { passive: true });
    }

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      for (const event of ACTIVITY_EVENTS) {
        document.removeEventListener(event, onActivity);
      }
    };
  }, [enabled, resetTimer, handleTimeout, timeoutMs]);
}
