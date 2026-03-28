"use client";

import { motion } from "framer-motion";
import { usePlan } from "@/contexts/plan-context";

interface PlanBadgeProps {
  feature: string;
  onPurchase?: () => void;
  className?: string;
}

/**
 * Shows plan-gating info. For credit users, shows "Add for X credit(s)"
 * with a purchase action. For legacy users, shows "Upgrade to Pro".
 */
export function PlanBadge({ feature, onPurchase, className = "" }: PlanBadgeProps) {
  const { billingModel } = usePlan();

  if (billingModel === "credit") {
    return (
      <motion.button
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={onPurchase}
        className={`
          inline-flex items-center gap-1.5 px-3 py-1.5
          text-xs font-medium rounded-full
          bg-[var(--color-primary)]/10 text-[var(--color-primary)]
          hover:bg-[var(--color-primary)]/20
          cursor-pointer transition-colors
          ${className}
        `}
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
        Add {feature} for 1 credit
      </motion.button>
    );
  }

  return (
    <motion.span
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={`
        inline-flex items-center gap-1.5 px-3 py-1.5
        text-xs font-medium rounded-full
        bg-amber-100 text-amber-700
        ${className}
      `}
    >
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
      Upgrade to Pro
    </motion.span>
  );
}
