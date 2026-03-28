"use client";

import { usePathname } from "next/navigation";
import { AuthProvider } from "@/contexts/auth-context";
import { ProtectedRoute } from "@/components/layout/protected-route";
import type { ReactNode } from "react";

const PUBLIC_PATHS = ["/login", "/register", "/demo", "/pricing"];

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"));
}

export function AuthProviderWrapper({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <AuthProvider>
      {isPublicPath(pathname) ? children : <ProtectedRoute>{children}</ProtectedRoute>}
    </AuthProvider>
  );
}
