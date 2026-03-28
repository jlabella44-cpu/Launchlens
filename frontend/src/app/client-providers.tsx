"use client";

import type { ReactNode } from "react";
import { ToastProvider } from "@/contexts/toast-context";
import { ErrorBoundary } from "@/components/error-boundary";
import { OfflineBanner } from "@/components/ui/offline-banner";

export function ClientProviders({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <OfflineBanner />
        {children}
      </ToastProvider>
    </ErrorBoundary>
  );
}
