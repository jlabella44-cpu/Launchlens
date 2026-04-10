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
  register: (email: string, password: string, name: string, companyName: string, planTier?: string, consent?: boolean, aiConsent?: boolean) => Promise<void>;
  logout: () => void | Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Only attempt /auth/me if we have a saved token. This avoids a noisy
    // 401 console error on every unauthenticated page load.
    const savedToken = localStorage.getItem("listingjet_token");
    if (!savedToken) {
      setLoading(false);
      return;
    }
    apiClient.setToken(savedToken);
    apiClient
      .me()
      .then((u) => {
        setUser(u);
        localStorage.setItem("listingjet_logged_in", "1");
      })
      .catch(() => {
        localStorage.removeItem("listingjet_logged_in");
        localStorage.removeItem("listingjet_token");
        apiClient.setToken(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiClient.login(email, password);
    // Store token for Bearer auth (works cross-origin); cookies are backup (same-origin)
    if (res.access_token) {
      localStorage.setItem("listingjet_token", res.access_token);
      apiClient.setToken(res.access_token);
    }
    const me = await apiClient.me();
    setUser(me);
    localStorage.setItem("listingjet_logged_in", "1");
  }, []);

  const loginWithGoogle = useCallback(async (idToken: string) => {
    const res = await apiClient.googleLogin(idToken);
    if (res.access_token) {
      localStorage.setItem("listingjet_token", res.access_token);
      apiClient.setToken(res.access_token);
    }
    const me = await apiClient.me();
    setUser(me);
    localStorage.setItem("listingjet_logged_in", "1");
  }, []);

  const register = useCallback(
    async (email: string, password: string, name: string, companyName: string, planTier?: string, consent?: boolean, aiConsent?: boolean) => {
      const res = await apiClient.register(email, password, name, companyName, planTier, consent ?? true, aiConsent ?? true);
      if (res.access_token) {
        localStorage.setItem("listingjet_token", res.access_token);
        apiClient.setToken(res.access_token);
      }
      const me = await apiClient.me();
      setUser(me);
      localStorage.setItem("listingjet_logged_in", "1");
    },
    []
  );

  const logout = useCallback(async () => {
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api"}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // Best-effort
    }
    localStorage.removeItem("listingjet_logged_in");
    localStorage.removeItem("listingjet_token");
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
