"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import apiClient from "@/lib/api-client";
import type { UserResponse } from "@/lib/types";

const REFRESH_TOKEN_KEY = "listingjet_refresh_token";
// Access tokens expire after 15 minutes; refresh every 12 to stay ahead.
const REFRESH_INTERVAL_MS = 12 * 60 * 1000;

function storeTokens(accessToken: string | undefined | null, refreshToken: string | undefined | null) {
  if (accessToken) {
    localStorage.setItem("listingjet_token", accessToken);
    apiClient.setToken(accessToken);
  }
  if (refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }
}

interface AuthContextValue {
  user: UserResponse | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  register: (email: string, password: string, name: string, companyName: string, planTier?: string, consent?: boolean, aiConsent?: boolean) => Promise<void>;
  acceptInvite: (token: string, password: string, name?: string) => Promise<void>;
  logout: () => void | Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const refreshingRef = useRef<Promise<string | null> | null>(null);

  const tryRefresh = useCallback(async (): Promise<string | null> => {
    // Coalesce concurrent refresh attempts so we only hit /auth/refresh once.
    if (refreshingRef.current) return refreshingRef.current;
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!refreshToken) return null;
    const p = apiClient
      .refreshAccessToken(refreshToken)
      .then((res) => {
        if (!res?.access_token) return null;
        localStorage.setItem("listingjet_token", res.access_token);
        if (res.refresh_token) {
          localStorage.setItem(REFRESH_TOKEN_KEY, res.refresh_token);
        }
        return res.access_token;
      })
      .finally(() => {
        refreshingRef.current = null;
      });
    refreshingRef.current = p;
    return p;
  }, []);

  const clearSession = useCallback(() => {
    localStorage.removeItem("listingjet_logged_in");
    localStorage.removeItem("listingjet_token");
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    apiClient.setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const savedToken = localStorage.getItem("listingjet_token");
    const savedRefresh = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!savedToken && !savedRefresh) {
      setLoading(false);
      return;
    }
    if (savedToken) apiClient.setToken(savedToken);

    (async () => {
      try {
        const u = await apiClient.me();
        if (cancelled) return;
        setUser(u);
        localStorage.setItem("listingjet_logged_in", "1");
      } catch (err) {
        // Access token likely expired — try to refresh once.
        const status = (err as { status?: number })?.status;
        if (status === 401 && savedRefresh) {
          const newToken = await tryRefresh();
          if (newToken) {
            try {
              const u = await apiClient.me();
              if (cancelled) return;
              setUser(u);
              localStorage.setItem("listingjet_logged_in", "1");
              return;
            } catch {
              // fall through to logout
            }
          }
        }
        if (!cancelled) clearSession();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [tryRefresh, clearSession]);

  // Keep the access token fresh while the user is signed in: periodic refresh
  // for long sessions, plus a refresh on tab becoming visible again.
  useEffect(() => {
    if (!user) return;
    const interval = window.setInterval(() => {
      void tryRefresh();
    }, REFRESH_INTERVAL_MS);
    const onVisibility = () => {
      if (document.visibilityState === "visible") {
        void tryRefresh();
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [user, tryRefresh]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiClient.login(email, password);
    storeTokens(res.access_token, res.refresh_token);
    const me = await apiClient.me();
    setUser(me);
    localStorage.setItem("listingjet_logged_in", "1");
  }, []);

  const loginWithGoogle = useCallback(async (idToken: string) => {
    const res = await apiClient.googleLogin(idToken);
    storeTokens(res.access_token, res.refresh_token);
    const me = await apiClient.me();
    setUser(me);
    localStorage.setItem("listingjet_logged_in", "1");
  }, []);

  const register = useCallback(
    async (email: string, password: string, name: string, companyName: string, planTier?: string, consent?: boolean, aiConsent?: boolean) => {
      const res = await apiClient.register(email, password, name, companyName, planTier, consent ?? true, aiConsent ?? true);
      storeTokens(res.access_token, res.refresh_token);
      const me = await apiClient.me();
      setUser(me);
      localStorage.setItem("listingjet_logged_in", "1");
    },
    []
  );

  const acceptInvite = useCallback(
    async (token: string, password: string, name?: string) => {
      const res = await apiClient.acceptInvite({ token, password, name });
      storeTokens(res.access_token, res.refresh_token);
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
    clearSession();
  }, [clearSession]);

  return (
    <AuthContext.Provider value={{ user, loading, login, loginWithGoogle, register, acceptInvite, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
