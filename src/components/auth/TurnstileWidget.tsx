/**
 * TurnstileWidget — Cloudflare Turnstile CAPTCHA component.
 *
 * Renders a Turnstile widget and exposes imperative execution so
 * managed/invisible challenges can run at form-submit time.
 *
 * Owner: auth module
 * Classification: security-critical
 */
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
} from 'react';

import { DEV_MODE } from '@/lib/dev-mode';

const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY ?? '';
const TURNSTILE_SCRIPT_ID = 'cf-turnstile-script';

interface TurnstileWidgetProps {
  onVerify: (token: string) => void;
  onExpire?: () => void;
  onError?: () => void;
}

export interface TurnstileWidgetHandle {
  execute: () => Promise<string>;
  reset: () => void;
}

declare global {
  interface Window {
    turnstile?: {
      render: (container: HTMLElement, options: Record<string, unknown>) => string;
      reset: (widgetId: string) => void;
      remove: (widgetId: string) => void;
      execute: (widgetId: string) => void;
    };
  }
}

function loadTurnstileScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.turnstile) {
      resolve();
      return;
    }

    const existing = document.getElementById(TURNSTILE_SCRIPT_ID) as HTMLScriptElement | null;
    if (existing) {
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error('Failed to load Turnstile script')), { once: true });
      return;
    }

    const script = document.createElement('script');
    script.id = TURNSTILE_SCRIPT_ID;
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Turnstile script'));
    document.head.appendChild(script);
  });
}

const TurnstileWidget = forwardRef<TurnstileWidgetHandle, TurnstileWidgetProps>(function TurnstileWidget(
  { onVerify, onExpire, onError },
  ref
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);
  const tokenRef = useRef<string | null>(null);
  const resolveRef = useRef<((token: string) => void) | null>(null);
  const rejectRef = useRef<((error: Error) => void) | null>(null);
  const onVerifyRef = useRef(onVerify);
  const onExpireRef = useRef(onExpire);
  const onErrorRef = useRef(onError);

  onVerifyRef.current = onVerify;
  onExpireRef.current = onExpire;
  onErrorRef.current = onError;

  const clearPending = useCallback(() => {
    resolveRef.current = null;
    rejectRef.current = null;
  }, []);

  const rejectPending = useCallback(
    (message: string) => {
      rejectRef.current?.(new Error(message));
      clearPending();
    },
    [clearPending]
  );

  const reset = useCallback(() => {
    tokenRef.current = null;
    onExpireRef.current?.();
    clearPending();

    if (widgetIdRef.current && window.turnstile) {
      window.turnstile.reset(widgetIdRef.current);
    }
  }, [clearPending]);

  const renderWidget = useCallback(async () => {
    if (!containerRef.current || widgetIdRef.current) return;

    await loadTurnstileScript();

    if (!window.turnstile || !containerRef.current) {
      throw new Error('Turnstile is unavailable');
    }

    widgetIdRef.current = window.turnstile.render(containerRef.current, {
      sitekey: TURNSTILE_SITE_KEY,
      theme: 'auto',
      size: 'flexible',
      appearance: 'interaction-only',
      execution: 'execute',
      callback: (token: string) => {
        console.log('[Turnstile] Token received');
        tokenRef.current = token;
        onVerifyRef.current(token);
        resolveRef.current?.(token);
        clearPending();
      },
      'expired-callback': () => {
        console.warn('[Turnstile] Token expired');
        tokenRef.current = null;
        onExpireRef.current?.();
        rejectPending('Verification expired. Please try again.');
      },
      'error-callback': (errorCode: string) => {
        console.error('[Turnstile] Error:', errorCode);
        tokenRef.current = null;
        onErrorRef.current?.();
        rejectPending('Verification failed. Please try again.');
      },
    });
    console.log('[Turnstile] Widget rendered, id:', widgetIdRef.current);
  }, [clearPending, rejectPending]);

  const execute = useCallback(async (): Promise<string> => {
    // DEV_MODE: skip Turnstile entirely, return dummy token
    if (DEV_MODE) {
      const dummyToken = 'dev-mode-bypass-token';
      tokenRef.current = dummyToken;
      onVerifyRef.current(dummyToken);
      return dummyToken;
    }

    await renderWidget();

    if (tokenRef.current) {
      return tokenRef.current;
    }

    if (!window.turnstile || !widgetIdRef.current) {
      throw new Error('Turnstile is unavailable');
    }

    return new Promise<string>((resolve, reject) => {
      const timeout = setTimeout(() => {
        clearPending();
        reject(new Error('Verification timed out. Please try again.'));
      }, 15000);

      resolveRef.current = (token: string) => {
        clearTimeout(timeout);
        resolve(token);
      };
      rejectRef.current = (err: Error) => {
        clearTimeout(timeout);
        reject(err);
      };
      tokenRef.current = null;
      window.turnstile.execute(widgetIdRef.current!);
    });
  }, [renderWidget, clearPending]);

  useImperativeHandle(
    ref,
    () => ({
      execute,
      reset,
    }),
    [execute, reset]
  );

  useEffect(() => {
    // DEV_MODE: don't load Turnstile script at all
    if (DEV_MODE) return;

    renderWidget().catch(() => {
      onErrorRef.current?.();
    });

    return () => {
      rejectPending('Verification was cancelled.');
      if (widgetIdRef.current && window.turnstile) {
        window.turnstile.remove(widgetIdRef.current);
        widgetIdRef.current = null;
      }
    };
  }, [rejectPending, renderWidget]);

  if (DEV_MODE) {
    return (
      <div className="text-center text-xs text-muted-foreground py-1">
        🔓 Dev mode — CAPTCHA bypassed
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div ref={containerRef} className="flex justify-center" aria-label="Complete security verification" role="group" />
      <p className="text-center text-xs text-muted-foreground">
        Protected by Cloudflare Turnstile. Verification runs when you submit.
      </p>
    </div>
  );
});

TurnstileWidget.displayName = 'TurnstileWidget';

export default TurnstileWidget;
