"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";

const TIERS = [
  {
    name: "Starter",
    price: 29,
    recommended: false,
    features: {
      "Listings / month": "5",
      "Photos / listing": "25",
      "AI Vision (Tier 2)": false,
      "Social Content": false,
      "AI Video Tours": false,
      "MLS Export": true,
      "Marketing Export": true,
    },
  },
  {
    name: "Pro",
    price: 99,
    recommended: true,
    features: {
      "Listings / month": "50",
      "Photos / listing": "50",
      "AI Vision (Tier 2)": true,
      "Social Content": true,
      "AI Video Tours": true,
      "MLS Export": true,
      "Marketing Export": true,
    },
  },
  {
    name: "Enterprise",
    price: 299,
    recommended: false,
    features: {
      "Listings / month": "500",
      "Photos / listing": "100",
      "AI Vision (Tier 2)": true,
      "Social Content": true,
      "AI Video Tours": true,
      "MLS Export": true,
      "Marketing Export": true,
    },
  },
];

export default function PricingPage() {
  return (
    <>
      <Nav />
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-16">
        <div className="text-center mb-12">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-4xl font-bold text-[var(--color-text)] mb-3"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Listing Media OS
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-lg text-[var(--color-text-secondary)]"
          >
            From raw listing media to launch-ready marketing in minutes.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {TIERS.map((tier, i) => (
            <motion.div
              key={tier.name}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              <GlassCard
                tilt
                className={`relative ${
                  tier.recommended
                    ? "border-[var(--color-cta)] border-2 shadow-[0_0_30px_rgba(249,115,22,0.15)]"
                    : ""
                }`}
              >
                {tier.recommended && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[var(--color-cta)] text-white text-xs font-bold px-3 py-1 rounded-full">
                    Recommended
                  </span>
                )}
                <h2
                  className="text-xl font-bold text-[var(--color-text)] mb-1"
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  {tier.name}
                </h2>
                <div className="mb-6">
                  <span className="text-3xl font-bold text-[var(--color-text)]">
                    ${tier.price}
                  </span>
                  <span className="text-sm text-[var(--color-text-secondary)]">/mo</span>
                </div>

                <ul className="space-y-3 mb-6">
                  {Object.entries(tier.features).map(([feature, value]) => (
                    <li key={feature} className="flex items-center justify-between text-sm">
                      <span className="text-[var(--color-text-secondary)]">{feature}</span>
                      {typeof value === "boolean" ? (
                        value ? (
                          <span className="text-green-500 font-bold">&#10003;</span>
                        ) : (
                          <span className="text-slate-300">&#x2014;</span>
                        )
                      ) : (
                        <span className="font-medium text-[var(--color-text)]">{value}</span>
                      )}
                    </li>
                  ))}
                </ul>

                <Link href={`/register?plan=${tier.name.toLowerCase()}`}>
                  <Button
                    className="w-full"
                    variant={tier.recommended ? "primary" : "secondary"}
                  >
                    Get Started
                  </Button>
                </Link>
              </GlassCard>
            </motion.div>
          ))}
        </div>
      </main>
    </>
  );
}
