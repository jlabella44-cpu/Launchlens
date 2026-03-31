"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import apiClient from "@/lib/api-client";

const PRICE_IDS: Record<string, string> = {
  lite: "price_1TH4J9RZ4TuRrBpyUHm6Eg5p",
  active_agent: "price_1TH4JARZ4TuRrBpywg1XdkoE",
};

const TIERS = [
  {
    name: "Free",
    price: 0,
    period: "mo",
    description: "Try ListingJet risk-free. No subscription required.",
    includedCredits: 0,
    perListingPrice: 34,
    features: [
      "$34 per listing",
      "MLS + marketing bundles",
      "AI photo analysis",
      "30-day asset hosting",
      "ListingJet watermark",
    ],
  },
  {
    name: "Lite",
    price: 9,
    period: "mo",
    description: "For solo agents. Lower per-listing cost, permanent hosting.",
    includedCredits: 0,
    perListingPrice: 24,
    features: [
      "$24 per listing (save 29%)",
      "Permanent asset hosting",
      "Your logo + brand colors",
      "Priority processing queue",
      "Credit rollover (cap: 3)",
    ],
  },
  {
    name: "Active Agent",
    price: 29,
    period: "mo",
    recommended: true,
    description: "For busy agents listing 4-8 properties/month.",
    includedCredits: 1,
    perListingPrice: 17,
    features: [
      "1 included listing/month",
      "$17 per additional listing",
      "Full white-label (no watermark)",
      "Top priority processing",
      "All integrations (MLS, CRM)",
      "Credit rollover (cap: 10)",
    ],
  },
];

const CREDIT_BUNDLES = [
  { size: 5, price: 100, perCredit: 20 },
  { size: 10, price: 170, perCredit: 17 },
  { size: 25, price: 375, perCredit: 15 },
  { size: 50, price: 650, perCredit: 13 },
];

const ADDONS = [
  { name: "AI Video Tour", cost: "from $24", icon: "🎬" },
  { name: "3D Floorplan", cost: "from $24", icon: "🏠" },
  { name: "Social Content Pack", cost: "1 credit", icon: "📱" },
];

export default function PricingPage() {
  useEffect(() => { document.title = "Pricing | ListingJet"; }, []);

  const [listingsPerMonth, setListingsPerMonth] = useState(3);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const router = useRouter();

  async function handleTierCheckout(tierName: string) {
    const key = tierName.toLowerCase().replace(" ", "_");
    const token = localStorage.getItem("listingjet_token");
    if (!token) {
      router.push(`/register?plan=${key}`);
      return;
    }
    if (key === "free") {
      router.push("/register?plan=free");
      return;
    }
    const priceId = PRICE_IDS[key];
    if (!priceId) return;
    setCheckoutLoading(key);
    try {
      const res = await apiClient.billingCheckout(
        priceId,
        `${window.location.origin}/billing?success=true`,
        `${window.location.origin}/pricing`,
      );
      window.location.href = res.checkout_url;
    } catch (err) {
      console.error("Checkout failed:", err);
      setCheckoutLoading(null);
    }
  }

  async function handleCreditPurchase(bundleSize: number) {
    const token = localStorage.getItem("listingjet_token");
    if (!token) {
      router.push("/register");
      return;
    }
    setCheckoutLoading(`bundle_${bundleSize}`);
    try {
      const res = await apiClient.purchaseCredits(
        bundleSize,
        `${window.location.origin}/billing?success=true`,
        `${window.location.origin}/pricing`,
      );
      window.location.href = res.checkout_url;
    } catch (err) {
      console.error("Purchase failed:", err);
      setCheckoutLoading(null);
    }
  }

  function calculateCost(tier: (typeof TIERS)[number]) {
    const listingCreditsNeeded = Math.max(0, listingsPerMonth - tier.includedCredits);
    return tier.price + listingCreditsNeeded * tier.perListingPrice;
  }

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 py-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <h1
            className="text-4xl font-bold text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Simple, Transparent Pricing
          </h1>
          <p className="text-sm text-slate-400 mt-2 uppercase tracking-wider">
            Atmospheric clarity for your real estate portfolio
          </p>
        </motion.div>

        {/* Volume Calculator */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-2xl border border-slate-100 p-6 mb-10"
        >
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4 flex-wrap">
              <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                Volume Calculator
              </p>
              <div className="flex items-center gap-3">
                <span className="text-sm text-slate-500">I list about</span>
                <input
                  type="range"
                  min={1}
                  max={20}
                  value={listingsPerMonth}
                  onChange={(e) => setListingsPerMonth(Number(e.target.value))}
                  className="w-32 accent-[#F97316]"
                />
                <span className="text-lg font-bold text-[var(--color-text)] min-w-[3ch] text-center">
                  {listingsPerMonth}
                </span>
                <span className="text-sm text-slate-500">properties/month</span>
              </div>
            </div>
            <div className="text-right">
              <p className="text-3xl font-bold text-[var(--color-text)]">
                ${calculateCost(TIERS[2])}
                <span className="text-sm font-normal text-slate-400">/mo</span>
              </p>
              <p className="text-[10px] uppercase tracking-wider text-slate-400">
                Estimated at Active Agent
              </p>
            </div>
          </div>
        </motion.div>

        {/* Tier Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
          {TIERS.map((tier, i) => {
            const monthlyCost = calculateCost(tier);

            return (
              <motion.div
                key={tier.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 + i * 0.1 }}
                className={`rounded-2xl p-6 flex flex-col ${
                  tier.recommended
                    ? "bg-[#0B1120] text-white ring-2 ring-[#F97316]"
                    : "bg-white border border-slate-100"
                }`}
              >
                {tier.recommended && (
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[#F97316] mb-2">
                    Recommended
                  </span>
                )}
                <h3
                  className={`text-lg font-bold ${tier.recommended ? "text-white" : "text-[var(--color-text)]"}`}
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  {tier.name}
                </h3>
                <div className="mt-3 mb-1">
                  <span className={`text-4xl font-bold ${tier.recommended ? "text-white" : "text-[var(--color-text)]"}`}>
                    ${tier.price}
                  </span>
                  <span className={`text-sm ${tier.recommended ? "text-white/60" : "text-slate-400"}`}>
                    /{tier.period}
                  </span>
                </div>
                <p className={`text-xs mb-4 ${tier.recommended ? "text-white/50" : "text-slate-400"}`}>
                  + ${tier.perListingPrice}/listing
                </p>

                {/* Estimated Cost */}
                <div className={`rounded-xl px-4 py-3 mb-4 text-center ${
                  tier.recommended ? "bg-white/10" : "bg-slate-50"
                }`}>
                  <p className={`text-sm font-semibold ${tier.recommended ? "text-white" : "text-[var(--color-text)]"}`}>
                    ~${monthlyCost}/mo
                  </p>
                  <p className={`text-[10px] ${tier.recommended ? "text-white/50" : "text-slate-400"}`}>
                    at {listingsPerMonth} listings
                  </p>
                </div>

                <p className={`text-sm mb-4 ${tier.recommended ? "text-white/70" : "text-slate-500"}`}>
                  {tier.description}
                </p>

                <ul className="space-y-2.5 mb-6 flex-1">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm">
                      <svg className={`w-4 h-4 mt-0.5 flex-shrink-0 ${tier.recommended ? "text-[#F97316]" : "text-green-500"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className={tier.recommended ? "text-white/80" : "text-[var(--color-text)]"}>{f}</span>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleTierCheckout(tier.name)}
                  disabled={checkoutLoading === tier.name.toLowerCase().replace(" ", "_")}
                  className={`w-full py-3 rounded-full font-semibold text-sm transition-colors disabled:opacity-50 ${
                    tier.recommended
                      ? "bg-[#F97316] hover:bg-[#ea580c] text-white shadow-lg shadow-orange-500/30"
                      : "border border-slate-200 text-slate-600 hover:border-slate-300"
                  }`}>
                  {checkoutLoading === tier.name.toLowerCase().replace(" ", "_") ? "Redirecting..." : "Get Started"}
                </button>
              </motion.div>
            );
          })}
        </div>

        {/* Annual Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mb-16"
        >
          <div className="bg-[#0B1120] rounded-2xl p-8 flex flex-col sm:flex-row items-center justify-between gap-6">
            <div>
              <p className="text-[10px] uppercase tracking-widest text-[#F97316] font-bold mb-1">Annual Pass</p>
              <h3
                className="text-2xl font-bold text-white"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                High Altitude Savings
              </h3>
              <p className="text-sm text-white/50 mt-1">
                Prep for the year and clear the runway for maximum ROI.
              </p>
            </div>
            <div className="text-right flex-shrink-0">
              <p className="text-3xl font-bold text-white">
                $349<span className="text-sm font-normal text-white/50">/yr</span>
              </p>
              <p className="text-xs text-white/40">Includes 25 Credits</p>
            </div>
          </div>
        </motion.div>

        {/* Credit Bundles */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="mb-16"
        >
          <h2
            className="text-2xl font-bold text-[var(--color-text)] mb-2 text-center"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Fuel Your Fleet: Credit Bundles
          </h2>
          <p className="text-sm text-slate-400 text-center mb-6">Buy credits in bulk for better per-listing rates.</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {CREDIT_BUNDLES.map((bundle) => (
              <div
                key={bundle.size}
                className="bg-white rounded-2xl border border-slate-100 p-5 text-center hover:border-[#F97316]/30 transition-colors"
              >
                <p className="text-2xl font-bold text-[var(--color-text)]">{bundle.size} <span className="text-sm font-normal text-slate-400">Credits</span></p>
                <p className="text-lg font-bold text-[var(--color-text)] mt-1">${bundle.price}</p>
                <p className="text-xs text-slate-400">${bundle.perCredit}/credit</p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Add-ons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="mb-16"
        >
          <h2
            className="text-2xl font-bold text-[var(--color-text)] mb-2 text-center"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Mission Augments
          </h2>
          <p className="text-sm text-slate-400 text-center mb-6">Enhance your listings with premium capabilities.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {ADDONS.map((addon) => (
              <div key={addon.name} className="bg-white rounded-2xl border border-slate-100 p-5 flex items-start gap-3">
                <span className="text-2xl">{addon.icon}</span>
                <div>
                  <h4 className="font-semibold text-[var(--color-text)]">{addon.name}</h4>
                  <p className="text-sm text-[#F97316] font-medium mt-0.5">{addon.cost}</p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Footer */}
        <footer className="pt-6 border-t border-slate-100 flex items-center justify-between text-[10px] uppercase tracking-wider text-slate-300">
          <span>ListingJet</span>
          <div className="flex items-center gap-6">
            <span className="hover:text-slate-400 cursor-pointer">Support</span>
            <span className="hover:text-slate-400 cursor-pointer">Privacy</span>
            <span className="hover:text-slate-400 cursor-pointer">Terms</span>
          </div>
        </footer>
      </main>
    </>
  );
}
