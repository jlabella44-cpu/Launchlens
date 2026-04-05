"use client";

/**
 * Simplified 5-stage horizontal pipeline tracker.
 *
 * Upload → Analyze → Review → Create → Delivered
 */

const STAGES = [
  {
    key: "upload",
    label: "Upload",
    states: ["new", "uploading"],
  },
  {
    key: "analyze",
    label: "Analyze",
    states: ["analyzing", "coverage", "floorplan", "packaging", "compliance"],
  },
  {
    key: "review",
    label: "Review",
    states: ["awaiting_review", "in_review", "approved"],
  },
  {
    key: "create",
    label: "Create",
    states: ["content", "brand_social", "chapters", "social_cuts", "mls_export", "exporting"],
  },
  {
    key: "delivered",
    label: "Delivered",
    states: ["delivered"],
  },
];

const ERROR_STATES = new Set(["failed", "pipeline_timeout", "cancelled"]);

function getStageIndex(state: string): number {
  for (let i = 0; i < STAGES.length; i++) {
    if (STAGES[i].states.includes(state)) return i;
  }
  return -1;
}

interface PipelineStatusProps {
  state: string;
}

export function PipelineStatus({ state }: PipelineStatusProps) {
  const isError = ERROR_STATES.has(state);
  const activeIndex = getStageIndex(state);
  // For delivered, all stages are complete
  const isDelivered = state === "delivered";

  return (
    <div className="w-full rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] px-5 py-4">
      <div className="flex items-center">
        {STAGES.map((stage, i) => {
          const isActive = i === activeIndex;
          const isPast = isDelivered || i < activeIndex;
          const isCurrent = isActive && !isDelivered;

          let dotColor: string;
          let dotScale = "";
          let labelColor: string;

          if (isError && isActive) {
            dotColor = "bg-red-500";
            dotScale = "ring-2 ring-red-200 ring-offset-1";
            labelColor = "text-red-600";
          } else if (isPast) {
            dotColor = "bg-emerald-500";
            labelColor = "text-[var(--color-text-secondary)]";
          } else if (isCurrent) {
            dotColor = "bg-blue-500";
            dotScale = "ring-2 ring-blue-200 ring-offset-1 scale-125";
            labelColor = "text-blue-600 font-semibold";
          } else {
            dotColor = "bg-slate-200 dark:bg-slate-600";
            labelColor = "text-[var(--color-text-tertiary)]";
          }

          return (
            <div key={stage.key} className="flex items-center flex-1 last:flex-none">
              {/* Stage dot + label */}
              <div className="flex flex-col items-center gap-1.5">
                <div className={`w-3.5 h-3.5 rounded-full transition-all duration-300 ${dotColor} ${dotScale}`}>
                  {isPast && !isCurrent && (
                    <svg className="w-3.5 h-3.5 text-white" viewBox="0 0 14 14" fill="none">
                      <path d="M3.5 7L6 9.5L10.5 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </div>
                <span className={`text-[11px] leading-tight whitespace-nowrap ${labelColor}`}>
                  {stage.label}
                </span>
              </div>

              {/* Connector line */}
              {i < STAGES.length - 1 && (
                <div className="flex-1 mx-2 -mt-5">
                  <div
                    className={`h-0.5 rounded-full transition-all duration-300 ${
                      isPast ? "bg-emerald-400" : "bg-slate-200 dark:bg-slate-600"
                    }`}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
