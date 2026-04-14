import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";
import App from "./App.tsx";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,
  enabled: import.meta.env.PROD,

  tracesSampleRate: 0.1,

  replaysSessionSampleRate: 0,
  replaysOnErrorSampleRate: 0,

  sendDefaultPii: false,

  beforeSend(event) {
    if (event.user?.email) {
      event.user.email = "[redacted]";
    }
    if (event.request?.headers) {
      delete event.request.headers["Authorization"];
      delete event.request.headers["apikey"];
    }
    return event;
  },

  denyUrls: [
    /challenges\.cloudflare\.com/,
    /extensions\//i,
    /^chrome:\/\//i,
  ],
  ignoreErrors: [
    "ResizeObserver loop limit exceeded",
    "Non-Error promise rejection captured",
  ],
});

// Self-hosted fonts — zero cross-origin requests
import "@fontsource/plus-jakarta-sans/400.css";
import "@fontsource/plus-jakarta-sans/500.css";
import "@fontsource/plus-jakarta-sans/600.css";
import "@fontsource/plus-jakarta-sans/700.css";

import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";

import "./index.css";

/**
 * Suppress unhandled promise rejections for expected API errors (4xx).
 * These are already handled by React Query's onError callbacks and displayed
 * as toasts — they must NOT trigger Lovable's runtime error overlay.
 */
window.addEventListener('unhandledrejection', (event) => {
  const reason = event.reason;
  if (reason && typeof reason === 'object' && reason.name === 'ApiError' && reason.status < 500) {
    event.preventDefault();
  }
});

createRoot(document.getElementById("root")!).render(<App />);
