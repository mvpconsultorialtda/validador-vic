/**
 * sentry.client.config.ts — Sentry SDK cliente Next.js
 * Copiado por install-in-app.sh · spec 034 validador-vic
 */
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,       // 10% traces em prod
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  integrations: [
    Sentry.replayIntegration({
      maskAllText: false,
      blockAllMedia: false,
    }),
  ],
  environment: process.env.NODE_ENV,
  enabled: process.env.NODE_ENV === "production",  // dev não polui dashboard
});
