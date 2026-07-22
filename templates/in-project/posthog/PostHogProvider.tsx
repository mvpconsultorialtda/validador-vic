/**
 * PostHogProvider.tsx — provider de tracking em prod
 * Copiado por install-in-app.sh · spec 034 validador-vic
 *
 * Uso em app/layout.tsx:
 *   import { PostHogProvider } from "@/app/components/PostHogProvider";
 *   <PostHogProvider>{children}</PostHogProvider>
 */
"use client";

import posthog from "posthog-js";
import { PostHogProvider as Provider } from "posthog-js/react";
import { useEffect } from "react";

if (typeof window !== "undefined" && process.env.NODE_ENV === "production") {
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://us.i.posthog.com",
    person_profiles: "identified_only",
    capture_pageview: true,
    capture_pageleave: true,
  });
}

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // pageview inicial já capturado pelo init com capture_pageview: true
  }, []);
  if (process.env.NODE_ENV !== "production") return <>{children}</>;
  return <Provider client={posthog}>{children}</Provider>;
}
