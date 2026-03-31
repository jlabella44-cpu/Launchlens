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
  register: (email: string, password: string, name: string, companyName: string, planTier?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("listingjet_token");
    if (token) {
      apiClient.setToken(token);
      apiClient
        .me()
        .then(setUser)
        .catch(() => {
          localStorage.removeItem("listingjet_token");
          apiClient.setToken(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiClient.login(email, password);
    localStorage.setItem("listingjet_token", res.access_token);
    apiClient.setToken(res.access_token);
    const me = await apiClient.me();
    setUser(me);
  }, []);

  const loginWithGoogle = useCallback(async (idToken: string) => {
    const res = await apiClient.googleLogin(idToken);
    localStorage.setItem("listingjet_token", res.access_token);
    apiClient.setToken(res.access_token);
    const me = await apiClient.me();
    setUser(me);
  }, []);

  const register = useCallback(
    async (email: string, password: string, name: string, companyName: string, planTier?: string) => {
      const res = await apiClient.register(email, password, name, companyName, planTier);
      localStorage.setItem("listingjet_token", res.access_token);
      apiClient.setToken(res.access_token);
      const me = await apiClient.me();
      setUser(me);
    },
    []
  );

  const logout = useCallback(() => {
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
