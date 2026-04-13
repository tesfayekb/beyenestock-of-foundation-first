/**
 * TurnstileWidget — Cloudflare Turnstile CAPTCHA component.
 *
 * Renders an invisible/managed Turnstile widget and returns
 * the verification token via onVerify callback.
 *
 * Owner: auth module
 * Classification: security-critical
 */
import { useEffect, useRef, useCallback } from 'react';

const TURNSTILE_SITE_KEY = '0x4AAAAAAC82V2ZrtUDOUfbx';
const TURNSTILE_SCRIPT_ID = 'cf-turnstile-script';

interface TurnstileWidgetProps {
  onVerify: (token: string) => void;
  onExpire?: () => void;
  onError?: () => void;
}

declare global {
  interface Window {
    turnstile?: {
      render: (container: HTMLElement, options: Record<string, unknown>) => string;
      reset: (widgetId: string) => void;
      remove: (widgetId: string) => void;
    };
    onTurnstileLoad?: () => void;
  }
}

function loadTurnstileScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.turnstile) {
      resolve();
      return;
    }

    const existing = document.getElementById(TURNSTILE_SCRIPT_ID);
    if (existing) {
      // Script is loading — wait for callback
      const prev = window.onTurnstileLoad;
      window.onTurnstileLoad = () => {
        prev?.();
        resolve();
      };
      return;
    }

    window.onTurnstileLoad = () => resolve();

    const script = document.createElement('script');
    script.id = TURNSTILE_SCRIPT_ID;
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onTurnstileLoad&render=explicit';
    script.async = true;
    script.defer = true;
    script.onerror = () => reject(new Error('Failed to load Turnstile script'));
    document.head.appendChild(script);
  });
}

export default function TurnstileWidget({ onVerify, onExpire, onError }: TurnstileWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);
  const onVerifyRef = useRef(onVerify);
  const onExpireRef = useRef(onExpire);
  const onErrorRef = useRef(onError);

  // Keep refs in sync
  onVerifyRef.current = onVerify;
  onExpireRef.current = onExpire;
  onErrorRef.current = onError;

  const renderWidget = useCallback(async () => {
    if (!containerRef.current || widgetIdRef.current) return;

    try {
      await loadTurnstileScript();
    } catch {
      onErrorRef.current?.();
      return;
    }

    if (!window.turnstile || !containerRef.current) return;

    widgetIdRef.current = window.turnstile.render(containerRef.current, {
      sitekey: TURNSTILE_SITE_KEY,
      callback: (token: string) => onVerifyRef.current(token),
      'expired-callback': () => onExpireRef.current?.(),
      'error-callback': () => onErrorRef.current?.(),
      theme: 'auto',
      size: 'flexible',
    });
  }, []);

  useEffect(() => {
    renderWidget();

    return () => {
      if (widgetIdRef.current && window.turnstile) {
        window.turnstile.remove(widgetIdRef.current);
        widgetIdRef.current = null;
      }
    };
  }, [renderWidget]);

  return <div ref={containerRef} className="flex justify-center" />;
}
