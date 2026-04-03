"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

export default function LoginPage() {
  const { login, loginWithGoogle } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  useEffect(() => { document.title = "Sign In | ListingJet"; }, []);

  const handleGoogleResponse = useCallback(
    async (response: { credential: string }) => {
      setError("");
      setGoogleLoading(true);
      try {
        await loginWithGoogle(response.credential);
        router.push("/dashboard");
      } catch (err: any) {
        setError(err.message || "Google sign-in failed");
      } finally {
        setGoogleLoading(false);
      }
    },
    [loginWithGoogle, router]
  );

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = () => {
      window.google?.accounts?.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleResponse,
      });
    };
    document.head.appendChild(script);

    return () => {
      document.head.removeChild(script);
    };
  }, [handleGoogleResponse]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  function handleGoogleClick() {
    if (window.google?.accounts?.id) {
      (window.google.accounts.id as any).prompt();
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="h-screen flex overflow-hidden"
    >
      {/* Left: Hero Panel */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between bg-[#0B1120] relative overflow-hidden p-10">
        {/* Logo */}
        <div className="flex items-center gap-2 z-10">
          <svg className="w-8 h-8 text-[#F97316]" viewBox="0 0 24 24" fill="currentColor">
            <path d="M3.5 18.5L9.5 12.5L13 16L22 6L20.5 4.5L13 12L9.5 8.5L2 16L3.5 18.5Z" />
          </svg>
          <span className="text-white text-xl font-bold tracking-wide" style={{ fontFamily: "var(--font-heading)" }}>
            ListingJet
          </span>
        </div>

        {/* Hero Image */}
        <div className="flex-1 flex items-center justify-center z-10 my-8">
          <div className="relative w-[85%] max-w-md group">
            <div className="absolute inset-0 bg-blue-400/20 blur-3xl rounded-full scale-75 group-hover:scale-110 transition-transform duration-1000" />
            <img
              src="/images/login-villa.jpg"
              alt="Futuristic minimalist villa with cinematic lighting"
              className="relative z-10 w-full h-auto rounded-xl shadow-[0_35px_35px_rgba(0,0,0,0.5)] transform -rotate-3 hover:rotate-0 transition-all duration-700 ease-in-out"
            />
          </div>
        </div>

        {/* Bottom Text */}
        <div className="z-10">
          <h2 className="text-4xl sm:text-5xl font-bold text-white leading-tight" style={{ fontFamily: "var(--font-heading)" }}>
            Put your listings on{" "}
            <span className="text-white">autopilot</span>
          </h2>
          <p className="text-white/60 mt-3 text-base">
            High-performance marketing automation for elite real estate professionals.
          </p>
          <div className="flex items-center gap-2 mt-6">
            <span className="w-2 h-2 rounded-full bg-[#F97316] animate-pulse" />
            <span className="text-xs text-white/40 uppercase tracking-widest">
              System Status: Supersonic
            </span>
          </div>
        </div>
      </div>

      {/* Right: Login Form */}
      <div className="flex-1 flex flex-col bg-[#F5F7FA]">
        {/* Language selector */}
        <div className="hidden lg:flex justify-end p-6">
          <span className="text-xs text-slate-400 uppercase tracking-wider">
            Language: EN US &rsaquo;
          </span>
        </div>

        <div className="flex-1 flex items-center justify-center p-8">
          <div className="w-full max-w-sm">
            <h1
              className="text-3xl font-bold text-[var(--color-text)] mb-2"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Welcome back
            </h1>
            <p className="text-[var(--color-text-secondary)] mb-8">
              Access your command center dashboard.
            </p>

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Email */}
              <div>
                <label htmlFor="email" className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Mission Control Email
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                    </svg>
                  </span>
                  <input
                    id="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316] transition-all text-sm"
                    placeholder="pilot@listingjet.ai"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label htmlFor="password" className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    Security Cipher
                  </label>
                  <Link href="/forgot-password" className="text-[10px] font-semibold uppercase tracking-wider text-[#F97316] hover:text-[#ea580c]">
                    Forgot?
                  </Link>
                </div>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  </span>
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pl-10 pr-12 py-3 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316] transition-all text-sm"
                    placeholder="••••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                      </svg>
                    ) : (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {error && (
                <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
                  {error}
                </p>
              )}

              {/* Sign In Button - Orange, rounded-full, with arrow */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 px-6 rounded-full bg-[#F97316] hover:bg-[#ea580c] text-white font-semibold text-sm transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-orange-200"
              >
                {loading ? (
                  <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : (
                  <>
                    Sign In
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                    </svg>
                  </>
                )}
              </button>
            </form>

            {/* Register Link */}
            <p className="mt-6 text-center text-sm text-[var(--color-text-secondary)]">
              Don&apos;t have an account?{" "}
              <Link
                href="/register"
                className="text-[#F97316] font-medium hover:underline"
              >
                Register
              </Link>
            </p>

            {/* Social Login Divider */}
            <div className="flex items-center gap-3 mt-6">
              <div className="flex-1 h-px bg-slate-200" />
              <span className="text-[10px] text-slate-400 uppercase tracking-wider">Or continue with</span>
              <div className="flex-1 h-px bg-slate-200" />
            </div>

            {/* Social Login Icons */}
            <div className="flex items-center justify-center gap-3 mt-4">
              <button
                type="button"
                onClick={handleGoogleClick}
                className="w-10 h-10 rounded-full border border-slate-200 bg-white flex items-center justify-center hover:bg-slate-50 transition-colors"
                aria-label="Sign in with Google"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
              </button>
              <button
                type="button"
                className="w-10 h-10 rounded-full border border-slate-200 bg-white flex items-center justify-center hover:bg-slate-50 transition-colors"
                aria-label="Sign in with Apple"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
                </svg>
              </button>
              <button
                type="button"
                className="w-10 h-10 rounded-full border border-slate-200 bg-white flex items-center justify-center hover:bg-slate-50 transition-colors"
                aria-label="Sign in with Microsoft"
              >
                <svg className="w-4 h-4" viewBox="0 0 21 21">
                  <rect fill="#F25022" x="0" y="0" width="10" height="10" />
                  <rect fill="#7FBA00" x="11" y="0" width="10" height="10" />
                  <rect fill="#00A4EF" x="0" y="11" width="10" height="10" />
                  <rect fill="#FFB900" x="11" y="11" width="10" height="10" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
