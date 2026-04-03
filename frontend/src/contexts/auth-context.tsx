"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import apiClient from "@/lib/api-client";
import type { UserResponse } from "@/lib/types";

interface AuthContextValue {
  user: UserResponse | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  register: (email: string, password: string, name: string, companyName: string, planTier?: string, consent?: boolean) => Promise<void>;
  logout: () => void | Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Auth is now handled by httpOnly cookies (sent automatically).
    // Try to load user profile; if it fails, the cookie is missing/expired.
    apiClient
      .me()
      .then((u) => {
        setUser(u);
        localStorage.setItem("listingjet_logged_in", "1");
      })
      .catch(() => {
        localStorage.removeItem("listingjet_logged_in");
        apiClient.setToken(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    await apiClient.login(email, password);
    // Cookie is set by the server response; fetch user profile
    const me = await apiClient.me();
    setUser(me);
    localStorage.setItem("listingjet_logged_in", "1");
  }, []);

  const loginWithGoogle = useCallback(async (idToken: string) => {
    await apiClient.googleLogin(idToken);
    const me = await apiClient.me();
    setUser(me);
    localStorage.setItem("listingjet_logged_in", "1");
  }, []);

  const register = useCallback(
    async (email: string, password: string, name: string, companyName: string, planTier?: string, consent?: boolean) => {
      await apiClient.register(email, password, name, companyName, planTier, consent ?? true);
      const me = await apiClient.me();
      setUser(me);
      localStorage.setItem("listingjet_logged_in", "1");
    },
    []
  );

  const logout = useCallback(async () => {
    try {
      // Server clears httpOnly cookies
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api"}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // Best-effort; cookies may already be expired
    }
    localStorage.removeItem("listingjet_logged_in");
    apiClient.setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, loginWithGoogle, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
