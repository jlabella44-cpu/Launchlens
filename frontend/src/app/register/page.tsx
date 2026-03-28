"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import { useAuth } from "@/contexts/auth-context";
import apiClient from "@/lib/api-client";
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

export default function RegisterPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <RegisterForm />
    </Suspense>
  );
}

function RegisterForm() {
  const { register } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const plan = searchParams.get("plan");
  const claimId = searchParams.get("claim");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(email, password, name);

      // If claiming a demo, convert it to a real listing
      if (claimId) {
        try {
          const result = await apiClient.demoClaim(claimId);
          router.push(`/listings/${result.listing_id}`);
          return;
        } catch {
          // Claim failed — still redirect to listings
        }
      }

      router.push("/listings");
    } catch (err: any) {
      setError(err.message || "Registration failed");
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
            The AI-powered listing creation platform.
          </p>
        </div>
      </div>

      {/* Right: Register Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <GlassCard tilt={false} className="w-full max-w-md">
          <h1
            className="text-2xl font-bold text-[var(--color-text)] mb-1"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Create Account
          </h1>
          <p className="text-[var(--color-text-secondary)] mb-2">
            {claimId
              ? "Create an account to claim your AI-curated package"
              : "Start launching listings in minutes"}
          </p>
          {plan && (
            <p className="text-sm text-[var(--color-primary)] font-medium mb-6">
              Selected plan: <span className="capitalize">{plan}</span>
            </p>
          )}
          {!plan && <div className="mb-6" />}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="name" className="block text-sm font-medium mb-1.5">
                Full Name
              </label>
              <input
                id="name"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-3 rounded-lg border border-[var(--color-border)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition-shadow"
                placeholder="Jane Smith"
              />
            </div>

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
              <input
                id="password"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-lg border border-[var(--color-border)] bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition-shadow"
                placeholder="Min 8 characters"
              />
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
                {error}
              </p>
            )}

            <Button type="submit" loading={loading} className="w-full">
              Create Account
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-[var(--color-text-secondary)]">
            Already have an account?{" "}
            <Link
              href="/login"
              className="text-[var(--color-primary)] font-medium hover:underline"
            >
              Sign In
            </Link>
          </p>
        </GlassCard>
      </div>
    </div>
  );
}
