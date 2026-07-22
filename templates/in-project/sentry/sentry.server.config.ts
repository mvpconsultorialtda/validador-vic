/**
 * sentry.server.config.ts — Sentry SDK servidor Next.js
 * Copiado por install-in-app.sh · spec 034 validador-vic
 */
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,
  environment: process.env.NODE_ENV,
  enabled: process.env.NODE_ENV === "production",
});
