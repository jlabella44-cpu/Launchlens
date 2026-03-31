"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ProtectedRoute } from "@/components/layout/protected-route";
import apiClient from "@/lib/api-client";

interface Step {
  id: string;
  title: string;
  description: string;
  actionLabel: string;
  actionHref: string;
  icon: React.ReactNode;
}

const STEPS: Step[] = [
  {
    id: "brand",
    title: "Brand Setup",
    description:
      "Define your visual identity, voice, and assets to ensure every generated listing feels uniquely yours.",
    actionLabel: "Set Up Brand Kit",
    actionHref: "/settings",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
  },
  {
    id: "listing",
    title: "First Listing",
    description:
      "Launch your first property listing. Our AI will handle the copy, SEO, and formatting in seconds.",
    actionLabel: "Create Listing",
    actionHref: "/listings?create=true",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    id: "credits",
    title: "Get Credits",
    description:
      "Fuel your growth with listing credits. Choose a plan that scales with your real estate portfolio.",
    actionLabel: "View Pricing",
    actionHref: "/pricing",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
];

function OnboardingFlow() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
  const [hasBrandKit, setHasBrandKit] = useState(false);

  useEffect(() => {
    apiClient
      .getBrandKit()
      .then((kit) => {
        if (kit) {
          setHasBrandKit(true);
          setCompletedSteps((prev) => new Set([...prev, "brand"]));
        }
      })
      .catch(() => {});

    const saved = localStorage.getItem("listingjet_onboarding_done");
    if (saved) {
      try {
        setCompletedSteps(new Set(JSON.parse(saved)));
      } catch {}
    }
  }, []);

  function handleStepAction(stepIndex: number) {
    setCurrentStep(stepIndex);
  }

  function handleSkipAll() {
    localStorage.setItem(
      "listingjet_onboarding_done",
      JSON.stringify(STEPS.map((s) => s.id))
    );
    router.push("/dashboard");
  }

  function markComplete(stepId: string) {
    const updated = new Set([...completedSteps, stepId]);
    setCompletedSteps(updated);
    localStorage.setItem(
      "listingjet_onboarding_done",
      JSON.stringify([...updated])
    );
    // Advance to next incomplete step
    const nextIndex = STEPS.findIndex((s) => !updated.has(s.id));
    if (nextIndex >= 0) {
      setCurrentStep(nextIndex);
    } else {
      router.push("/dashboard");
    }
  }

  const progressPercent = ((currentStep + 1) / STEPS.length) * 100;

  return (
    <div className="min-h-screen bg-[#F5F7FA] flex flex-col">
      {/* Header */}
      <header className="pt-10 pb-6 text-center">
        <div className="flex items-center justify-center gap-2 mb-1">
          <svg className="w-6 h-6 text-[#F97316]" viewBox="0 0 24 24" fill="currentColor">
            <path d="M3.5 18.5L9.5 12.5L13 16L22 6L20.5 4.5L13 12L9.5 8.5L2 16L3.5 18.5Z" />
          </svg>
          <span
            className="text-xl font-bold text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            ListingJet
          </span>
        </div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400 font-medium">
          Pre-Flight Checklist
        </p>
      </header>

      {/* Progress Bar */}
      <div className="max-w-md mx-auto w-full px-6 mb-10">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] uppercase tracking-wider font-semibold text-[#F97316] border-b-2 border-[#F97316] pb-0.5">
            Mission Status
          </span>
          <span className="text-[10px] uppercase tracking-wider text-slate-400">
            Step {currentStep + 1} of {STEPS.length}
          </span>
        </div>
        <div className="h-0.5 bg-slate-200 rounded-full">
          <motion.div
            className="h-full bg-[#F97316] rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progressPercent}%` }}
            transition={{ duration: 0.4 }}
          />
        </div>
      </div>

      {/* Steps */}
      <div className="max-w-md mx-auto w-full px-6 space-y-4 flex-1">
        {STEPS.map((step, i) => {
          const isActive = i === currentStep;
          const isCompleted = completedSteps.has(step.id);

          return (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className={`rounded-xl transition-all ${
                isActive
                  ? "bg-white shadow-lg border border-slate-100 p-6"
                  : "px-6 py-4"
              }`}
            >
              <div className="flex items-start gap-4">
                {/* Icon */}
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                    isActive
                      ? "bg-[#0B1120] text-white"
                      : isCompleted
                      ? "bg-green-100 text-green-600"
                      : "bg-slate-100 text-slate-400"
                  }`}
                >
                  {isCompleted ? (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    step.icon
                  )}
                </div>

                {/* Content */}
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3
                      className={`font-semibold ${
                        isActive
                          ? "text-[var(--color-text)]"
                          : "text-slate-400"
                      }`}
                      style={{ fontFamily: "var(--font-heading)" }}
                    >
                      {step.title}
                    </h3>
                    {isActive && !isCompleted && (
                      <span className="text-[9px] uppercase tracking-wider font-bold bg-[#F97316] text-white px-2 py-0.5 rounded">
                        Current
                      </span>
                    )}
                    {isCompleted && (
                      <span className="text-[9px] uppercase tracking-wider font-bold bg-green-100 text-green-700 px-2 py-0.5 rounded">
                        Complete
                      </span>
                    )}
                  </div>
                  <p
                    className={`text-sm leading-relaxed ${
                      isActive ? "text-slate-500" : "text-slate-400"
                    }`}
                  >
                    {step.description}
                  </p>

                  {/* Action button */}
                  {isActive && !isCompleted ? (
                    <Link href={step.actionHref}>
                      <button className="mt-4 px-5 py-2 rounded-full bg-[#F97316] hover:bg-[#ea580c] text-white text-sm font-semibold transition-colors inline-flex items-center gap-1.5 shadow-md shadow-orange-200">
                        {step.actionLabel}
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                        </svg>
                      </button>
                    </Link>
                  ) : !isActive && !isCompleted ? (
                    <button
                      onClick={() => handleStepAction(i)}
                      className="mt-3 px-4 py-1.5 rounded-full border border-slate-200 text-slate-400 text-sm hover:border-slate-300 hover:text-slate-500 transition-colors"
                    >
                      {step.actionLabel}
                    </button>
                  ) : null}

                  {step.id === "brand" && hasBrandKit && isActive && (
                    <button
                      onClick={() => markComplete("brand")}
                      className="mt-2 text-xs text-green-600 hover:underline"
                    >
                      Already configured — mark complete
                    </button>
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Skip All Footer */}
      <div className="py-8 text-center">
        <button
          onClick={handleSkipAll}
          className="text-xs uppercase tracking-wider text-slate-400 hover:text-slate-600 transition-colors font-medium"
        >
          Skip All → Go to Dashboard →
        </button>
      </div>
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <ProtectedRoute>
      <OnboardingFlow />
    </ProtectedRoute>
  );
}
