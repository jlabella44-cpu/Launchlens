"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";

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
    addons: true,
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
    addons: true,
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
    addons: true,
  },
];

const CREDIT_BUNDLES = [
  { size: 1, price: 34, perCredit: 34 },
  { size: 3, price: 72, perCredit: 24 },
  { size: 5, price: 100, perCredit: 20 },
  { size: 10, price: 170, perCredit: 17 },
  { size: 25, price: 375, perCredit: 15 },
];

const ADDONS = [
  { name: "AI Video Tour", cost: "from $24", description: "AI-generated property tour video with voiceover" },
  { name: "3D Floorplan", cost: "from $24", description: "Interactive 3D floorplan visualization" },
  { name: "Social Content Pack", cost: "1 credit", description: "5 hook variants per platform (Instagram + Facebook)" },
];

export default function PricingPage() {
  const [listingsPerMonth, setListingsPerMonth] = useState(3);

  function calculateCost(tier: typeof TIERS[number]) {
    const listingCreditsNeeded = Math.max(0, listingsPerMonth - tier.includedCredits);
    return tier.price + listingCreditsNeeded * tier.perListingPrice;
  }

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1
            className="text-4xl font-bold text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Pay for what you use
          </h1>
          <p className="text-lg text-[var(--color-text-secondary)] mt-3 max-w-2xl mx-auto">
            Base account fee + per-listing credits. No wasted capacity in slow months.
          </p>
        </motion.div>

        {/* Cost calculator */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-10"
        >
          <GlassCard tilt={false}>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <span className="text-sm text-[var(--color-text-secondary)]">I list about</span>
              <input
                type="range"
                min={1}
                max={20}
                value={listingsPerMonth}
                onChange={(e) => setListingsPerMonth(Number(e.target.value))}
                className="w-40 accent-[var(--color-cta)]"
              />
              <span className="text-lg font-bold text-[var(--color-text)] min-w-[3ch] text-center">
                {listingsPerMonth}
              </span>
              <span className="text-sm text-[var(--color-text-secondary)]">properties/month</span>
            </div>
          </GlassCard>
        </motion.div>

        {/* Plan cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
          {TIERS.map((tier, i) => {
            const monthlyCost = calculateCost(tier);

            return (
              <motion.div
                key={tier.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 + i * 0.1 }}
              >
                <GlassCard
                  tilt={false}
                  className={`h-full flex flex-col ${
                    tier.recommended
                      ? "border-2 border-[var(--color-cta)] shadow-[0_0_30px_rgba(249,115,22,0.15)]"
                      : ""
                  }`}
                >
                  {tier.recommended && (
                    <span className="text-xs font-bold text-[var(--color-cta)] uppercase tracking-wider mb-2">
                      Most Popular
                    </span>
                  )}
                  <h3
                    className="text-xl font-bold text-[var(--color-text)]"
                    style={{ fontFamily: "var(--font-heading)" }}
                  >
                    {tier.name}
                  </h3>
                  <div className="mt-2 mb-1">
                    <span className="text-3xl font-bold text-[var(--color-text)]">${tier.price}</span>
                    <span className="text-sm text-[var(--color-text-secondary)]">/{tier.period}</span>
                  </div>
                  <p className="text-xs text-[var(--color-text-secondary)] mb-1">
                    + ${tier.perListingPrice}/listing credit
                  </p>
                  <div className="bg-[var(--color-background)] rounded-lg px-3 py-2 mb-4 text-center">
                    <span className="text-sm font-medium text-[var(--color-text)]">
                      ~${monthlyCost}/mo
                    </span>
                    <span className="text-xs text-[var(--color-text-secondary)] ml-1">
                      at {listingsPerMonth} listings
                    </span>
                  </div>
                  <p className="text-sm text-[var(--color-text-secondary)] mb-4">
                    {tier.description}
                  </p>
                  <ul className="space-y-2 mb-6 flex-1">
                    {tier.features.map((f) => (
                      <li key={f} className="text-sm text-[var(--color-text)] flex items-start gap-2">
                        <svg className="w-4 h-4 text-[var(--color-success)] mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Link href={`/register?plan=${tier.name.toLowerCase().replace(" ", "_")}`}>
                    <Button variant={tier.recommended ? "primary" : "secondary"} className="w-full">
                      Get Started
                    </Button>
                  </Link>
                </GlassCard>
              </motion.div>
            );
          })}
        </div>

        {/* Annual option */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mb-16"
        >
          <GlassCard tilt={false}>
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <h3
                  className="text-xl font-bold text-[var(--color-text)]"
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  Annual Credit Bank
                </h3>
                <p className="text-sm text-[var(--color-text-secondary)] mt-1">
                  $349/year with 25 listing credits included. Best value for consistent agents.
                </p>
              </div>
              <div className="text-right">
                <span className="text-2xl font-bold text-[var(--color-text)]">$349</span>
                <span className="text-sm text-[var(--color-text-secondary)]">/year</span>
                <p className="text-xs text-[var(--color-success)]">Save vs monthly</p>
              </div>
              <Link href="/register?plan=annual">
                <Button>Get Annual Plan</Button>
              </Link>
            </div>
          </GlassCard>
        </motion.div>

        {/* Credit bundles */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="mb-16"
        >
          <h2
            className="text-2xl font-bold text-[var(--color-text)] mb-6 text-center"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Credit Bundles
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {CREDIT_BUNDLES.map((bundle) => (
              <GlassCard key={bundle.size} tilt={false} className="text-center">
                <p className="text-2xl font-bold text-[var(--color-text)]">{bundle.size}</p>
                <p className="text-xs text-[var(--color-text-secondary)] mb-2">credits</p>
                <p className="text-lg font-semibold text-[var(--color-text)]">${bundle.price}</p>
                <p className="text-xs text-[var(--color-text-secondary)]">${bundle.perCredit}/credit</p>
              </GlassCard>
            ))}
          </div>
        </motion.div>

        {/* Add-ons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
        >
          <h2
            className="text-2xl font-bold text-[var(--color-text)] mb-6 text-center"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Premium Add-Ons
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {ADDONS.map((addon) => (
              <GlassCard key={addon.name} tilt={false}>
                <h4 className="font-semibold text-[var(--color-text)]">{addon.name}</h4>
                <p className="text-sm text-[var(--color-text-secondary)] mt-1">{addon.description}</p>
                <p className="text-sm font-medium text-[var(--color-cta)] mt-2">{addon.cost}</p>
              </GlassCard>
            ))}
          </div>
        </motion.div>
      </main>
    </>
  );
}
