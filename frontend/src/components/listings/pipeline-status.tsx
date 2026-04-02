"use client";

const PHASES = [
  {
    label: "Phase 1",
    color: "#6366F1",
    steps: [
      { key: "uploading", label: "Ingest" },
      { key: "analyzing", label: "Vision" },
      { key: "coverage", label: "Coverage" },
      { key: "floorplan", label: "Floorplan" },
      { key: "packaging", label: "Package" },
      { key: "compliance", label: "Comply" },
    ],
  },
  {
    label: "Review",
    color: "#F59E0B",
    steps: [
      { key: "awaiting_review", label: "Queue" },
      { key: "in_review", label: "Review" },
      { key: "approved", label: "Approved" },
    ],
  },
  {
    label: "Phase 2",
    color: "#10B981",
    steps: [
      { key: "content", label: "Content" },
      { key: "brand_social", label: "Brand" },
      { key: "chapters", label: "Chapters" },
      { key: "social_cuts", label: "Cuts" },
      { key: "mls_export", label: "MLS" },
      { key: "exporting", label: "Export" },
      { key: "delivered", label: "Done" },
    ],
  },
];

const ALL_STEPS = PHASES.flatMap((p) => p.steps);

interface PipelineStatusProps {
  state: string;
}

export function PipelineStatus({ state }: PipelineStatusProps) {
  const currentIndex = ALL_STEPS.findIndex((s) => s.key === state);

  return (
    <div className="w-full rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-4">
      <div className="flex gap-6">
        {PHASES.map((phase) => (
          <div key={phase.label} className="flex-1">
            <div
              className="text-xs font-medium mb-2"
              style={{ color: phase.color }}
            >
              {phase.label}
            </div>
            <div className="flex items-center gap-1">
              {phase.steps.map((step, i) => {
                const globalIndex = ALL_STEPS.indexOf(step);
                const isActive = globalIndex === currentIndex;
                const isPast = globalIndex < currentIndex;

                return (
                  <div key={step.key} className="flex items-center gap-1 flex-1">
                    <div className="flex flex-col items-center gap-1 flex-1">
                      <div
                        className={`w-3 h-3 rounded-full transition-all ${isActive ? "ring-2 ring-offset-1 scale-125" : ""}`}
                        style={{
                          backgroundColor: isPast || isActive ? phase.color : "var(--color-border)",
                          opacity: isPast ? 0.5 : isActive ? 1 : 0.3,
                          outlineColor: isActive ? phase.color : undefined,
                        }}
                      />
                      <span
                        className="text-[10px] leading-tight text-center"
                        style={{
                          color: isActive ? phase.color : isPast ? "var(--color-text-secondary)" : "var(--color-text-tertiary)",
                        }}
                      >
                        {step.label}
                      </span>
                    </div>
                    {i < phase.steps.length - 1 && (
                      <div
                        className="h-0.5 flex-1 rounded-full -mt-4"
                        style={{
                          backgroundColor: isPast ? phase.color : "var(--color-border)",
                          opacity: isPast ? 0.5 : 0.2,
                        }}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
