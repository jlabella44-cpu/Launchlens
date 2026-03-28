"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { useAuth } from "@/contexts/auth-context";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";

const SceneWrapper = dynamic(
  () => import("@/components/three/scene-wrapper").then((m) => ({ default: m.SceneWrapper })),
  { ssr: false }
);
const HeroScene = dynamic(
  () => import("@/components/three/hero-scene").then((m) => ({ default: m.HeroScene })),
  { ssr: false }
);

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/listings");
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left: 3D Scene */}
      <div className="hidden lg:flex lg:w-1/2 items-center justify-center bg-gradient-to-br from-[var(--color-primary)] to-[#1E40AF] relative overflow-hidden">
        <SceneWrapper className="w-full h-[500px]" camera={{ position: [0, 0, 6], fov: 50 }}>
          <HeroScene />
        </SceneWrapper>
        <div className="absolute bottom-12 left-12 right-12 text-white">
          <h2
            className="text-3xl font-bold mb-2"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            LaunchLens
          </h2>
          <p className="text-white/80 text-lg">
            From raw listing media to launch-ready marketing in minutes.
          </p>
        </div>
      </div>

      {/* Right: Login Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <GlassCard tilt={false} className="w-full max-w-md">
          <h1
            className="text-2xl font-bold text-[var(--color-text)] mb-1"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Welcome Back
          </h1>
          <p className="text-[var(--color-text-secondary)] mb-8">
            Sign in to your LaunchLens account
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-sm font-medium mb-1.5">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-lg border border-[var(--color-border)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition-shadow"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 rounded-lg border border-[var(--color-border)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition-shadow pr-12"
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-secondary)] text-sm cursor-pointer hover:text-[var(--color-text)]"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
                {error}
              </p>
            )}

            <Button type="submit" loading={loading} className="w-full">
              Sign In
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-[var(--color-text-secondary)]">
            Don&apos;t have an account?{" "}
            <Link
              href="/register"
              className="text-[var(--color-primary)] font-medium hover:underline"
            >
              Register
            </Link>
          </p>
        </GlassCard>
      </div>
    </div>
  );
}
