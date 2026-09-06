"use client";

import { usePathname } from "next/navigation";
import { AuthProvider, useAuth } from "@/contexts/auth-context";
import { PlanProvider } from "@/contexts/plan-context";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { CommandPalette } from "@/components/command-palette";
import { HelpChat } from "@/components/ui/help-chat";
import { KeyboardShortcuts } from "@/components/keyboard-shortcuts";
import { KeyboardNav } from "@/components/keyboard-nav";
import { ToastProvider } from "@/components/ui/toast";
import { FeaturesProvider, useFeature } from "@/hooks/use-features";
import type { ReactNode } from "react";

const PUBLIC_PATHS = ["/", "/login", "/register", "/demo", "/pricing", "/faq", "/privacy", "/terms", "/changelog", "/forgot-password", "/reset-password"];

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"));
}

function GatedHelpChat() {
  const helpAgentEnabled = useFeature("help_agent");
  if (!helpAgentEnabled) return null;
  return <HelpChat />;
}

function AuthenticatedShell({ children }: { children: ReactNode }) {
  const { user } = useAuth();

  return (
    <FeaturesProvider enabled={!!user}>
      <ProtectedRoute>
        {children}
        <GatedHelpChat />
      </ProtectedRoute>
    </FeaturesProvider>
  );
}

export function AuthProviderWrapper({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <AuthProvider>
      <PlanProvider>
        <ToastProvider>
          <CommandPalette />
          <KeyboardShortcuts />
          <KeyboardNav />
          {isPublicPath(pathname) ? (
            children
          ) : (
            <AuthenticatedShell>{children}</AuthenticatedShell>
          )}
        </ToastProvider>
      </PlanProvider>
    </AuthProvider>
  );
}
