"use client";

import { motion } from "framer-motion";

const STATE_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  new: { bg: "bg-slate-100", text: "text-slate-700", dot: "bg-slate-400" },
  uploading: { bg: "bg-blue-100", text: "text-blue-700", dot: "bg-blue-500" },
  analyzing: { bg: "bg-indigo-100", text: "text-indigo-700", dot: "bg-indigo-500" },
  awaiting_review: { bg: "bg-amber-100", text: "text-amber-700", dot: "bg-amber-500" },
  in_review: { bg: "bg-orange-100", text: "text-orange-700", dot: "bg-orange-500" },
  approved: { bg: "bg-green-100", text: "text-green-700", dot: "bg-green-500" },
  exporting: { bg: "bg-cyan-100", text: "text-cyan-700", dot: "bg-cyan-500" },
  delivered: { bg: "bg-emerald-100", text: "text-emerald-700", dot: "bg-emerald-500" },
  demo: { bg: "bg-purple-100", text: "text-purple-700", dot: "bg-purple-500" },
  failed: { bg: "bg-red-100", text: "text-red-700", dot: "bg-red-500" },
};

// Autopilot-themed display labels
const STATE_LABELS: Record<string, string> = {
  new: "Pre-Flight",
  uploading: "Loading Cargo",
  analyzing: "Ascending",
  awaiting_review: "Awaiting Clearance",
  in_review: "Under Review",
  approved: "Cleared for Takeoff",
  exporting: "In Transit",
  delivered: "Mission Complete",
  demo: "Demo Flight",
  failed: "Course Correction Required",
  pipeline_timeout: "Flight Delayed",
};

interface BadgeProps {
  state: string;
  className?: string;
}

export function Badge({ state, className = "" }: BadgeProps) {
  const colors = STATE_COLORS[state] || STATE_COLORS.new;
  const label = STATE_LABELS[state] || state.replace(/_/g, " ");

  return (
    <motion.span
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={`
        inline-flex items-center gap-1.5 px-2.5 py-1
        text-xs font-medium rounded-full capitalize
        ${colors.bg} ${colors.text} ${className}
      `}
    >
      <motion.span
        className={`w-1.5 h-1.5 rounded-full ${colors.dot}`}
        animate={
          ["analyzing", "uploading", "exporting"].includes(state)
            ? { opacity: [1, 0.3, 1] }
            : {}
        }
        transition={{ repeat: Infinity, duration: 1.5 }}
      />
      {label}
    </motion.span>
  );
}
