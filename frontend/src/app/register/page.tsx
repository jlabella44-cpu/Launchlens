"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import apiClient from "@/lib/api-client";

const PLAN_DISPLAY: Record<string, { name: string; price: string; features: string[] }> = {
  lite: { name: "Lite", price: "$9/mo", features: ["Basic AI Listing Descriptions", "Standard Photo Curation", "MLS-Ready Exports"] },
  active_agent: { name: "Active Agent", price: "$29/mo", features: ["Unlimited AI Listing Descriptions", "Advanced Market Analytics HUD", "Priority Cloud Rendering"] },
  team: { name: "Team", price: "$99/mo", features: ["Everything in Active Agent", "Team Collaboration", "API Access"] },
};

const ADDONS = [
  { id: "video_tour", name: "AI Video Tour", description: "Automated cinematic fly-throughs", price: 49, priceLabel: "+$49" },
  { id: "floorplan", name: "3D Floorplan", description: "Interactive spatial visualization", price: 79, priceLabel: "+$79" },
  { id: "social_pack", name: "Social Pack", description: "Multi-platform campaign delivery", price: 39, priceLabel: "+$39" },
];

export default function RegisterPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#F97316] border-t-transparent rounded-full animate-spin" />
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
  const [companyName, setCompanyName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [selectedAddons, setSelectedAddons] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => { document.title = "Create Account | ListingJet"; }, []);

  const planInfo = plan ? PLAN_DISPLAY[plan] : PLAN_DISPLAY["active_agent"];

  function toggleAddon(id: string) {
    setSelectedAddons((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(email, password, name, companyName, plan || undefined);

      if (claimId) {
        try {
          const result = await apiClient.demoClaim(claimId);
          router.push(`/listings/${result.listing_id}`);
          return;
        } catch {
          // Claim failed — still redirect to onboarding
        }
      }

      router.push("/onboarding");
    } catch (err: any) {
      setError(err.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left: Hero Panel */}
      <div className="hidden lg:flex lg:w-[45%] flex-col justify-between bg-[#0B1120] relative overflow-hidden">
        {/* Background image placeholder */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#1a2744] via-[#2d4a6f] to-[#0d1b2a]" />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />

        {/* Logo */}
        <div className="relative z-10 p-10">
          <div className="flex items-center gap-2">
            <svg className="w-6 h-6 text-[#F97316]" viewBox="0 0 24 24" fill="currentColor">
              <path d="M3.5 18.5L9.5 12.5L13 16L22 6L20.5 4.5L13 12L9.5 8.5L2 16L3.5 18.5Z" />
            </svg>
            <span className="text-white text-lg font-bold" style={{ fontFamily: "var(--font-heading)" }}>
              ListingJet
            </span>
          </div>
        </div>

        {/* Headline */}
        <div className="relative z-10 px-10 pb-6">
          <h2 className="text-4xl font-bold text-white leading-tight" style={{ fontFamily: "var(--font-heading)" }}>
            Elevate Your{" "}
            <em className="italic text-white">Market Presence.</em>
          </h2>
          <p className="text-white/60 mt-3 text-sm leading-relaxed">
            Experience the next generation of real estate marketing automation. High-altitude precision for elite brokerages.
          </p>
        </div>

        {/* Plan Card Overlay */}
        {planInfo && (
          <div className="relative z-10 mx-10 mb-10">
            <div className="bg-white rounded-xl p-5 shadow-xl">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Active Selection</p>
                  <p className="text-lg font-bold text-[var(--color-text)]" style={{ fontFamily: "var(--font-heading)" }}>
                    {planInfo.name}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-[var(--color-text)]">{planInfo.price}</p>
                  <p className="text-[10px] text-slate-400 uppercase">Per Month</p>
                </div>
              </div>
              <ul className="space-y-1.5">
                {planInfo.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-xs text-slate-600">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#F97316]" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex items-center gap-2 mt-4">
              <span className="w-2 h-2 rounded-full bg-[#F97316] animate-pulse" />
              <span className="text-[10px] text-white/40 uppercase tracking-widest">
                System Status: Ready for Deployment
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Right: Register Form */}
      <div className="flex-1 flex flex-col bg-[#F5F7FA]">
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="w-full max-w-md">
            <h1
              className="text-3xl font-bold text-[var(--color-text)] mb-2"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Create Account
            </h1>
            <p className="text-[var(--color-text-secondary)] mb-8 text-sm">
              {claimId
                ? "Create an account to claim your AI-curated package"
                : "Initiate your command center access."}
            </p>

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Name + Company side by side */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="name" className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                    Full Name
                  </label>
                  <input
                    id="name"
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316] transition-all text-sm"
                    placeholder="John Doe"
                  />
                </div>
                <div>
                  <label htmlFor="company" className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                    Company/Brokerage
                  </label>
                  <input
                    id="company"
                    type="text"
                    required
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316] transition-all text-sm"
                    placeholder="Elite Realty"
                  />
                </div>
              </div>

              {/* Email */}
              <div>
                <label htmlFor="email" className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Email Address
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-3 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316] transition-all text-sm"
                  placeholder="commander@listingjet.ai"
                />
              </div>

              {/* Password */}
              <div>
                <label htmlFor="password" className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316] transition-all text-sm"
                  placeholder="••••••••"
                />
                <p className="text-[10px] text-slate-400 mt-1">
                  Required: 8+ characters including an uppercase, lowercase, and digit.
                </p>
              </div>

              {/* Mission Add-Ons */}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-3">
                  Mission Add-Ons
                </p>
                <div className="space-y-2">
                  {ADDONS.map((addon) => (
                    <button
                      key={addon.id}
                      type="button"
                      onClick={() => toggleAddon(addon.id)}
                      className={`w-full flex items-center justify-between p-3 rounded-lg border transition-all text-left ${
                        selectedAddons.has(addon.id)
                          ? "border-[#F97316] bg-[#F97316]/5"
                          : "border-slate-200 bg-white hover:border-slate-300"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors ${
                          selectedAddons.has(addon.id) ? "border-[#F97316] bg-[#F97316]" : "border-slate-300"
                        }`}>
                          {selectedAddons.has(addon.id) && (
                            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-[var(--color-text)]">{addon.name}</p>
                          <p className="text-[11px] text-slate-400">{addon.description}</p>
                        </div>
                      </div>
                      <span className="text-sm font-semibold text-[#F97316]">{addon.priceLabel}</span>
                    </button>
                  ))}
                </div>
              </div>

              {error && (
                <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
                  {error}
                </p>
              )}

              {/* Create Account Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 px-6 rounded-full bg-[#F97316] hover:bg-[#ea580c] text-white font-semibold text-sm transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-orange-200"
              >
                {loading ? (
                  <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : (
                  <>
                    Create Account
                    <span className="text-base">✈</span>
                  </>
                )}
              </button>
            </form>

            {/* Sign In Link */}
            <p className="mt-6 text-center text-sm text-[var(--color-text-secondary)]">
              Already have an account?{" "}
              <Link
                href="/login"
                className="text-[#F97316] font-medium hover:underline"
              >
                Sign in
              </Link>
            </p>

            {/* Footer Links */}
            <div className="flex items-center justify-center gap-6 mt-8">
              {["Privacy Policy", "Terms of Flight", "System Status"].map((link) => (
                <span key={link} className="text-[10px] text-slate-400 uppercase tracking-wider hover:text-slate-600 cursor-pointer">
                  {link}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
