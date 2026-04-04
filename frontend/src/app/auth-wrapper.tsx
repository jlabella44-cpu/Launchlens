"use client";

import { usePathname } from "next/navigation";
import { AuthProvider } from "@/contexts/auth-context";
import { PlanProvider } from "@/contexts/plan-context";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { CommandPalette } from "@/components/command-palette";
import { HelpChat } from "@/components/ui/help-chat";
import { ToastProvider } from "@/components/ui/toast";
import type { ReactNode } from "react";

const PUBLIC_PATHS = ["/", "/login", "/register", "/demo", "/pricing", "/faq", "/privacy", "/terms", "/forgot-password", "/reset-password"];

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"));
}

export function AuthProviderWrapper({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <AuthProvider>
      <PlanProvider>
        <ToastProvider>
          <CommandPalette />
          {isPublicPath(pathname) ? (
            children
          ) : (
            <ProtectedRoute>
              {children}
              <HelpChat />
            </ProtectedRoute>
          )}
        </ToastProvider>
      </PlanProvider>
    </AuthProvider>
  );
}
