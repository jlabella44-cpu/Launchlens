"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import apiClient from "@/lib/api-client";

const PRICE_IDS: Record<string, string> = {
  lite: "price_1TH4J9RZ4TuRrBpyUHm6Eg5p",
  active_agent: "price_1TH4JARZ4TuRrBpywg1XdkoE",
};

const TIERS = [
  {
    key: "free",
    name: "Free",
    price: 0,
    foundingPrice: 0,
    period: "mo",
    description: "Try ListingJet risk-free. Pay only for what you use.",
    includedCredits: 0,
    listingsCovered: 0,
    rolloverCap: 0,
    topUpRate: 0.50,
    features: [
      "Pay-as-you-go ($0.50/credit)",
      "MLS + marketing bundles",
      "AI photo analysis",
      "30-day asset hosting",
      "ListingJet watermark",
    ],
  },
  {
    key: "lite",
    name: "Lite",
    price: 19,
    foundingPrice: 13,
    period: "mo",
    description: "For solo agents. 25 credits/mo, better per-credit rates.",
    includedCredits: 25,
    listingsCovered: 2,
    rolloverCap: 15,
    topUpRate: 0.45,
    features: [
      "25 credits/month (~2 listings)",
      "Top-up at $0.45/credit",
      "Tier 2 AI vision",
      "Your logo + brand colors",
      "Credit rollover (cap: 15)",
    ],
  },
  {
    key: "active_agent",
    name: "Active Agent",
    price: 49,
    foundingPrice: 34,
    period: "mo",
    recommended: true,
    description: "For busy agents. 75 credits/mo, best value per credit.",
    includedCredits: 75,
    listingsCovered: 6,
    rolloverCap: 50,
    topUpRate: 0.40,
    features: [
      "75 credits/month (~6 listings)",
      "Top-up at $0.40/credit",
      "Full white-label (no watermark)",
      "Social content generation",
      "All integrations (MLS, CRM)",
      "Credit rollover (cap: 50)",
    ],
  },
  {
    key: "team",
    name: "Team",
    price: 99,
    foundingPrice: 69,
    period: "mo",
    description: "For teams & brokerages. 250 credits/mo, unlimited listings.",
    includedCredits: 250,
    listingsCovered: 20,
    rolloverCap: 150,
    topUpRate: 0.35,
    features: [
      "250 credits/month (~20 listings)",
      "Top-up at $0.35/credit",
      "Unlimited listings/month",
      "100 assets per listing",
      "Full white-label + API access",
      "Credit rollover (cap: 150)",
    ],
  },
];

const SERVICE_COSTS = [
  { name: "Base Listing", credits: 12, description: "Photo curation, AI descriptions, MLS export, PDF flyer" },
  { name: "AI Video Tour", credits: 20, description: "Kling AI video + ElevenLabs voiceover" },
  { name: "Virtual Staging", credits: 15, description: "AI furniture rendering, up to 4 rooms" },
  { name: "3D Floorplan", credits: 8, description: "GPT-4V analysis + 3D dollhouse view" },
  { name: "AI Image Editing", credits: 6, description: "Object removal, enhancement, compliance fixes" },
  { name: "CMA Report", credits: 5, description: "Comparative market analysis report" },
  { name: "Photo Compliance", credits: 3, description: "Automated FHA + MLS compliance checks" },
  { name: "Social Media Cuts", credits: 3, description: "Platform-sized video clips (IG, TikTok, FB, YT)" },
  { name: "Microsite", credits: 2, description: "Single-property landing page" },
  { name: "Social Content Pack", credits: 2, description: "Instagram/Facebook captions + hashtags" },
];

export default function PricingPage() {
  useEffect(() => { document.title = "Pricing | ListingJet"; }, []);

  const [listingsPerMonth, setListingsPerMonth] = useState(4);
  const [videoTours, setVideoTours] = useState(1);
  const [stagingListings, setStagingListings] = useState(1);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const router = useRouter();

  async function handleTierCheckout(tierKey: string) {
    const token = localStorage.getItem("listingjet_token");
    if (!token) {
      router.push(`/register?plan=${tierKey}`);
      return;
    }
    if (tierKey === "free") {
      router.push("/register?plan=free");
      return;
    }
    const priceId = PRICE_IDS[tierKey];
    if (!priceId) return;
    setCheckoutLoading(tierKey);
    try {
      const res = await apiClient.billingCheckout(
        priceId,
        `${window.location.origin}/billing?success=true`,
        `${window.location.origin}/pricing`,
      );
      const url1 = new URL(res.checkout_url);
      if (!url1.hostname.endsWith("stripe.com")) throw new Error("Invalid checkout URL");
      window.location.href = res.checkout_url;
    } catch (err) {
      console.error("Checkout failed:", err);
      setCheckoutLoading(null);
    }
  }

  function calculateCreditsNeeded() {
    return listingsPerMonth * 12 + videoTours * 20 + stagingListings * 15;
  }

  function calculateMonthlyCost(tier: (typeof TIERS)[number]) {
    const creditsNeeded = calculateCreditsNeeded();
    const extraCredits = Math.max(0, creditsNeeded - tier.includedCredits);
    return tier.price + extraCredits * tier.topUpRate;
  }

  function recommendedTier() {
    const credits = calculateCreditsNeeded();
    if (credits <= 25) return "lite";
    if (credits <= 75) return "active_agent";
    return "team";
  }

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#F97316]/10 border border-[#F97316]/20 mb-4">
            <span className="w-2 h-2 rounded-full bg-[#F97316] animate-pulse" />
            <span className="text-sm font-bold text-[#F97316]">Founding 200: 30% off for life</span>
          </div>
          <h1
            className="text-4xl font-bold text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Weighted Credits. Total Flexibility.
          </h1>
          <p className="text-sm text-[var(--color-text-secondary)] mt-2 max-w-2xl mx-auto">
            Every service costs credits proportional to its complexity. Use your credits on what matters most to your listings.
          </p>
        </motion.div>

        {/* Interactive Calculator */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-[var(--color-surface)] rounded-2xl border border-[var(--color-card-border)] p-6 mb-10"
        >
          <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-semibold mb-4">
            Credit Calculator
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-[var(--color-text-secondary)]">Listings/month</span>
                <span className="text-lg font-bold text-[var(--color-text)]">{listingsPerMonth}</span>
              </div>
              <input type="range" min={0} max={25} value={listingsPerMonth} onChange={(e) => setListingsPerMonth(Number(e.target.value))} className="w-full accent-[#F97316]" />
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-[var(--color-text-secondary)]">Video tours</span>
                <span className="text-lg font-bold text-[var(--color-text)]">{videoTours}</span>
              </div>
              <input type="range" min={0} max={15} value={videoTours} onChange={(e) => setVideoTours(Number(e.target.value))} className="w-full accent-[#F97316]" />
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-[var(--color-text-secondary)]">Virtual staging</span>
                <span className="text-lg font-bold text-[var(--color-text)]">{stagingListings}</span>
              </div>
              <input type="range" min={0} max={15} value={stagingListings} onChange={(e) => setStagingListings(Number(e.target.value))} className="w-full accent-[#F97316]" />
            </div>
          </div>
          <div className="flex items-center justify-between pt-4 border-t border-[var(--color-card-border)]">
            <div>
              <p className="text-sm text-[var(--color-text-secondary)]">Credits needed: <span className="font-bold text-[var(--color-text)]">{calculateCreditsNeeded()}</span></p>
              <p className="text-xs text-[var(--color-text-secondary)]">Recommended tier: <span className="font-semibold text-[#F97316] capitalize">{recommendedTier().replace("_", " ")}</span></p>
            </div>
            <div className="text-right">
              <p className="text-3xl font-bold text-[var(--color-text)]">
                ${calculateMonthlyCost(TIERS.find(t => t.key === recommendedTier())!).toFixed(0)}
                <span className="text-sm font-normal text-[var(--color-text-secondary)]">/mo</span>
              </p>
            </div>
          </div>
        </motion.div>

        {/* Tier Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-16">
          {TIERS.map((tier, i) => {
            const monthlyCost = calculateMonthlyCost(tier);
            const isRecommended = tier.key === recommendedTier();

            return (
              <motion.div
                key={tier.key}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 + i * 0.08 }}
                className={`rounded-2xl p-6 flex flex-col ${
                  isRecommended
                    ? "bg-[#0B1120] text-white ring-2 ring-[#F97316]"
                    : "bg-[var(--color-surface)] border border-[var(--color-card-border)]"
                }`}
              >
                {isRecommended && (
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[#F97316] mb-2">
                    Recommended
                  </span>
                )}
                <h3
                  className={`text-lg font-bold ${isRecommended ? "text-white" : "text-[var(--color-text)]"}`}
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  {tier.name}
                </h3>
                <div className="mt-3 mb-1">
                  <span className={`text-3xl font-bold ${isRecommended ? "text-white" : "text-[var(--color-text)]"}`}>
                    ${tier.foundingPrice}
                  </span>
                  <span className={`text-sm line-through ml-2 ${isRecommended ? "text-white/40" : "text-[var(--color-text-secondary)]"}`}>
                    {tier.price > 0 ? `$${tier.price}` : ""}
                  </span>
                  <span className={`text-sm ${isRecommended ? "text-white/60" : "text-[var(--color-text-secondary)]"}`}>
                    /{tier.period}
                  </span>
                </div>
                {tier.includedCredits > 0 && (
                  <p className={`text-xs mb-1 ${isRecommended ? "text-[#F97316]" : "text-[#F97316]"}`}>
                    {tier.includedCredits} credits/mo included
                  </p>
                )}

                {/* Estimated Cost */}
                <div className={`rounded-xl px-4 py-3 my-3 text-center ${
                  isRecommended ? "bg-white/10" : "bg-[var(--color-background)]"
                }`}>
                  <p className={`text-sm font-semibold ${isRecommended ? "text-white" : "text-[var(--color-text)]"}`}>
                    ~${monthlyCost.toFixed(0)}/mo
                  </p>
                  <p className={`text-[10px] ${isRecommended ? "text-white/50" : "text-[var(--color-text-secondary)]"}`}>
                    at {listingsPerMonth} listings + {videoTours} videos + {stagingListings} staging
                  </p>
                </div>

                <p className={`text-sm mb-4 ${isRecommended ? "text-white/70" : "text-[var(--color-text-secondary)]"}`}>
                  {tier.description}
                </p>

                <ul className="space-y-2 mb-6 flex-1">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm">
                      <svg className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isRecommended ? "text-[#F97316]" : "text-green-500"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className={isRecommended ? "text-white/80" : "text-[var(--color-text)]"}>{f}</span>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleTierCheckout(tier.key)}
                  disabled={checkoutLoading === tier.key}
                  className={`w-full py-3 rounded-full font-semibold text-sm transition-colors disabled:opacity-50 ${
                    isRecommended
                      ? "bg-[#F97316] hover:bg-[#ea580c] text-white shadow-lg shadow-orange-500/30"
                      : "border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-text-secondary)]"
                  }`}>
                  {checkoutLoading === tier.key ? "Redirecting..." : "Get Started"}
                </button>
              </motion.div>
            );
          })}
        </div>

        {/* Service Credit Costs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mb-16"
        >
          <h2
            className="text-2xl font-bold text-[var(--color-text)] mb-2 text-center"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Service Credit Costs
          </h2>
          <p className="text-sm text-[var(--color-text-secondary)] text-center mb-6">
            Each service is weighted by its computational complexity. Mix and match freely.
          </p>
          <div className="bg-[var(--color-surface)] rounded-2xl border border-[var(--color-card-border)] overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-semibold border-b border-[var(--color-card-border)] bg-[var(--color-background)]">
                  <th className="py-3 px-4 text-left">Service</th>
                  <th className="py-3 px-4 text-center">Credits</th>
                  <th className="py-3 px-4 text-left hidden sm:table-cell">What&apos;s Included</th>
                </tr>
              </thead>
              <tbody>
                {SERVICE_COSTS.map((service, i) => (
                  <tr key={service.name} className={i < SERVICE_COSTS.length - 1 ? "border-b border-[var(--color-card-border)]" : ""}>
                    <td className="py-3 px-4 font-medium text-[var(--color-text)]">{service.name}</td>
                    <td className="py-3 px-4 text-center">
                      <span className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-[#F97316]/10 text-[#F97316] font-bold text-sm">
                        {service.credits}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-[var(--color-text-secondary)] hidden sm:table-cell">{service.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-[var(--color-text-secondary)] text-center mt-3">
            Full pipeline listing (base + staging + video + cuts + floorplan + social) = <span className="font-bold text-[var(--color-text)]">60 credits</span>
          </p>
        </motion.div>

        {/* Founding 200 Banner */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="mb-16"
        >
          <div className="bg-[#0B1120] rounded-2xl p-8 text-center">
            <div className="inline-flex items-center gap-2 mb-3">
              <span className="w-2 h-2 rounded-full bg-[#F97316] animate-pulse" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-[#F97316]">Founding 200</span>
            </div>
            <h3
              className="text-2xl font-bold text-white mb-2"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              30% Off For Life
            </h3>
            <p className="text-sm text-white/50 mb-4 max-w-lg mx-auto">
              Be one of the first 200 subscribers and lock in founding pricing forever. Lite at $13/mo, Active Agent at $34/mo, Team at $69/mo.
            </p>
          </div>
        </motion.div>

        {/* Footer */}
        <footer className="pt-6 border-t border-[var(--color-card-border)] flex items-center justify-between text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">
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
