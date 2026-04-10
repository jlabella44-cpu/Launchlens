"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import apiClient from "@/lib/api-client";
import { trackEvent, AnalyticsEvents } from "@/lib/analytics";

const PLAN_DISPLAY: Record<string, { name: string; price: string; founding: string; features: string[] }> = {
  free: { name: "Free", price: "$0/mo", founding: "$0/mo", features: ["Pay-as-you-go ($0.50/credit)", "AI photo analysis", "MLS + marketing bundles"] },
  lite: { name: "Lite", price: "$19/mo", founding: "$13/mo", features: ["25 credits/month (~2 listings)", "Tier 2 AI vision", "Your logo + brand colors"] },
  active_agent: { name: "Active Agent", price: "$49/mo", founding: "$34/mo", features: ["75 credits/month (~6 listings)", "Full white-label", "Social content generation"] },
  team: { name: "Team", price: "$99/mo", founding: "$69/mo", features: ["250 credits/month (~20 listings)", "Unlimited listings/month", "Full white-label + API access"] },
};

export default function RegisterPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[var(--color-cta)] border-t-transparent rounded-full animate-spin" />
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
  const referralParam = searchParams.get("ref");
  const [name, setName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [referralCode, setReferralCode] = useState(referralParam || "");
  const [consent, setConsent] = useState(false);
  const [aiConsent, setAiConsent] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => { document.title = "Create Account | ListingJet"; }, []);

  // Persist referral code from URL param to sessionStorage
  useEffect(() => {
    if (referralParam) {
      sessionStorage.setItem("lj_ref", referralParam);
      setReferralCode(referralParam);
    } else {
      const stored = sessionStorage.getItem("lj_ref");
      if (stored) setReferralCode(stored);
    }
  }, [referralParam]);

  const planInfo = plan ? PLAN_DISPLAY[plan] : PLAN_DISPLAY["active_agent"];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(email, password, name, companyName, plan || undefined, consent, aiConsent);

      trackEvent(AnalyticsEvents.SIGNUP, {
        plan: plan || "active_agent",
        referral_code: referralCode || null,
      });

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
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left: Hero Panel */}
      <div className="hidden lg:flex lg:w-[45%] flex-col justify-between bg-[var(--color-primary)] relative overflow-hidden">
        <img
          src="/images/register-bg.jpg"
          alt=""
          className="absolute inset-0 w-full h-full object-cover opacity-40"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[var(--color-primary)]/80 via-[var(--color-secondary)]/60 to-[var(--color-primary)]" />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />

        {/* Logo */}
        <div className="relative z-10 p-10">
          <div className="flex items-center gap-2">
            <svg className="w-6 h-6 text-[var(--color-cta)]" viewBox="0 0 24 24" fill="currentColor">
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
                  <p className="text-2xl font-bold text-[var(--color-text)]">{planInfo.founding}</p>
                  <p className="text-[10px] text-slate-400 uppercase">
                    <span className="line-through mr-1">{planInfo.price !== planInfo.founding ? planInfo.price : ""}</span>
                    Founding Price
                  </p>
                </div>
              </div>
              <ul className="space-y-1.5">
                {planInfo.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-xs text-slate-600">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-cta)]" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex items-center gap-2 mt-4">
              <span className="w-2 h-2 rounded-full bg-[var(--color-cta)] animate-pulse" />
              <span className="text-[10px] text-white/40 uppercase tracking-widest">
                System Status: Ready for Deployment
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Right: Register Form */}
      <div className="flex-1 flex flex-col bg-[var(--color-background)]">
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
                    className="w-full px-4 py-3 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-cta)]/30 focus:border-[var(--color-cta)] transition-all text-sm"
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
                    className="w-full px-4 py-3 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-cta)]/30 focus:border-[var(--color-cta)] transition-all text-sm"
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
                  className="w-full px-4 py-3 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-cta)]/30 focus:border-[var(--color-cta)] transition-all text-sm"
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
                  className="w-full px-4 py-3 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-cta)]/30 focus:border-[var(--color-cta)] transition-all text-sm"
                  placeholder="••••••••"
                />
                <p className="text-[10px] text-slate-400 mt-1">
                  Required: 8+ characters including an uppercase, lowercase, and digit.
                </p>
              </div>

              {/* Referral Code */}
              <div>
                <label htmlFor="referral" className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Referral Code <span className="font-normal">(optional)</span>
                </label>
                <input
                  id="referral"
                  type="text"
                  value={referralCode}
                  onChange={(e) => setReferralCode(e.target.value.trim())}
                  className="w-full px-4 py-3 rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-[var(--color-cta)]/30 focus:border-[var(--color-cta)] transition-all text-sm"
                  placeholder="e.g. SARAH30"
                />
                {referralCode && (
                  <p className="text-[11px] text-[var(--color-cta)] mt-1 flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7" />
                    </svg>
                    30 bonus credits will be applied after signup
                  </p>
                )}
              </div>

              {/* ToS Consent */}
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded border-slate-300 text-[var(--color-cta)] focus:ring-[var(--color-cta)]/30"
                  required
                />
                <span className="text-xs text-slate-500">
                  I agree to the{" "}
                  <Link href="/terms" className="text-[var(--color-cta)] hover:underline" target="_blank">
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link href="/privacy" className="text-[var(--color-cta)] hover:underline" target="_blank">
                    Privacy Policy
                  </Link>.
                </span>
              </label>

              {/* AI Processing Consent (separate, optional) */}
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={aiConsent}
                  onChange={(e) => setAiConsent(e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded border-slate-300 text-[#F97316] focus:ring-[#F97316]/30"
                />
                <span className="text-xs text-slate-500">
                  I consent to my listing photos and data being processed by third-party AI
                  services (vision analysis, video generation, content writing) to produce my
                  marketing package. You can change this later in Settings — without it, AI
                  features are disabled.
                </span>
              </label>

              {error && (
                <p role="alert" className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
                  {error}
                </p>
              )}

              {/* Create Account Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 px-6 rounded-full bg-[var(--color-cta)] hover:brightness-90 text-white font-semibold text-sm transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
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
                className="text-[var(--color-cta)] font-medium hover:underline"
              >
                Sign in
              </Link>
            </p>

            {/* Footer Links */}
            <div className="flex items-center justify-center gap-6 mt-8">
              <Link href="/privacy" className="text-[10px] text-slate-400 uppercase tracking-wider hover:text-slate-600">
                Privacy Policy
              </Link>
              <Link href="/terms" className="text-[10px] text-slate-400 uppercase tracking-wider hover:text-slate-600">
                Terms of Service
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
