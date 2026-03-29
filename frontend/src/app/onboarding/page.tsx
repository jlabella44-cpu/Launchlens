"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import apiClient from "@/lib/api-client";

interface Step {
  id: string;
  title: string;
  description: string;
  actionLabel: string;
  actionHref: string;
  skipLabel: string;
}

const STEPS: Step[] = [
  {
    id: "brand",
    title: "Set up your branding",
    description: "Add your logo, brand colors, and brokerage info. This personalizes your flyers, watermarks, and marketing exports.",
    actionLabel: "Go to Settings",
    actionHref: "/settings",
    skipLabel: "Skip for now",
  },
  {
    id: "listing",
    title: "Upload your first listing",
    description: "Create a listing and upload photos. Our AI pipeline will curate, score, and package them into launch-ready materials.",
    actionLabel: "Create Listing",
    actionHref: "/listings?create=true",
    skipLabel: "Skip for now",
  },
  {
    id: "credits",
    title: "Get credits to start processing",
    description: "Each listing costs 1 credit to process through the AI pipeline. Your plan may include free credits — or you can buy more anytime.",
    actionLabel: "View Plans",
    actionHref: "/pricing",
    skipLabel: "I have credits",
  },
];

function OnboardingFlow() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
  const [hasBrandKit, setHasBrandKit] = useState<boolean | null>(null);

  useEffect(() => {
    // Check if brand kit already exists
    apiClient
      .getBrandKit()
      .then((kit) => {
        if (kit) {
          setHasBrandKit(true);
          setCompletedSteps((prev) => new Set([...prev, "brand"]));
        } else {
          setHasBrandKit(false);
        }
      })
      .catch(() => setHasBrandKit(false));

    // Load completed steps from localStorage
    const saved = localStorage.getItem("listingjet_onboarding_done");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setCompletedSteps(new Set(parsed));
      } catch {
        // ignore
      }
    }
  }, []);

  function handleSkip() {
    const step = STEPS[currentStep];
    const updated = new Set([...completedSteps, step.id]);
    setCompletedSteps(updated);
    localStorage.setItem("listingjet_onboarding_done", JSON.stringify([...updated]));

    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      router.push("/listings");
    }
  }

  function handleFinish() {
    localStorage.setItem("listingjet_onboarding_done", JSON.stringify([...completedSteps, STEPS[currentStep].id]));
    router.push("/listings");
  }

  const step = STEPS[currentStep];
  const isLast = currentStep === STEPS.length - 1;

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-2xl mx-auto w-full px-6 py-12">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <h1
            className="text-3xl font-bold text-[var(--color-text)] mb-2"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Welcome to ListingJet
          </h1>
          <p className="text-[var(--color-text-secondary)] mb-8">
            Let&apos;s get you set up in a few quick steps.
          </p>

          {/* Progress */}
          <div className="flex gap-2 mb-8">
            {STEPS.map((s, i) => (
              <div
                key={s.id}
                className={`flex-1 h-1.5 rounded-full transition-colors ${
                  i <= currentStep
                    ? "bg-[var(--color-primary)]"
                    : "bg-white/30"
                }`}
              />
            ))}
          </div>

          {/* Step indicator */}
          <p className="text-xs text-[var(--color-text-secondary)] mb-4">
            Step {currentStep + 1} of {STEPS.length}
          </p>

          {/* Current step card */}
          <motion.div
            key={step.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
          >
            <GlassCard>
              <h2 className="text-xl font-semibold text-[var(--color-text)] mb-2">
                {step.title}
              </h2>
              <p className="text-[var(--color-text-secondary)] mb-6">
                {step.description}
              </p>

              {step.id === "brand" && hasBrandKit && (
                <p className="text-sm text-green-600 mb-4 font-medium">
                  Brand kit already configured!
                </p>
              )}

              <div className="flex items-center gap-3">
                <Link href={step.actionHref}>
                  <Button>{step.actionLabel}</Button>
                </Link>
                <button
                  onClick={isLast ? handleFinish : handleSkip}
                  className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
                >
                  {isLast ? "Go to Dashboard" : step.skipLabel}
                </button>
              </div>
            </GlassCard>
          </motion.div>

          {/* Skip all */}
          <div className="mt-8 text-center">
            <button
              onClick={handleFinish}
              className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors underline"
            >
              Skip onboarding and go to dashboard
            </button>
          </div>
        </motion.div>
      </main>
    </>
  );
}

export default function OnboardingPage() {
  return (
    <ProtectedRoute>
      <OnboardingFlow />
    </ProtectedRoute>
  );
}
