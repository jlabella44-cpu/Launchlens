"use client";

const DEMO_STAGES = [
  { key: "demo", label: "Upload", color: "#8B5CF6" },
  { key: "analyzing", label: "AI Analysis", color: "#6366F1" },
  { key: "awaiting_review", label: "Packaged", color: "#F59E0B" },
  { key: "delivered", label: "Ready", color: "#10B981" },
];

interface DemoPipelineStatusProps {
  state: string;
}

export function DemoPipelineStatus({ state }: DemoPipelineStatusProps) {
  const currentIndex = DEMO_STAGES.findIndex((s) => s.key === state);
  const activeIndex = currentIndex === -1 ? DEMO_STAGES.length - 1 : currentIndex;

  return (
    <div className="w-full rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] p-4">
      <div className="flex items-center gap-2">
        {DEMO_STAGES.map((stage, i) => {
          const isActive = i === activeIndex;
          const isPast = i < activeIndex;

          return (
            <div key={stage.key} className="flex items-center gap-2 flex-1">
              <div className="flex flex-col items-center gap-1.5 flex-1">
                <div
                  className={`w-4 h-4 rounded-full transition-all ${isActive ? "ring-2 ring-offset-2 animate-pulse" : ""}`}
                  style={{
                    backgroundColor: isPast || isActive ? stage.color : "var(--color-border)",
                    opacity: isPast ? 0.5 : isActive ? 1 : 0.2,
                    outlineColor: isActive ? stage.color : undefined,
                  }}
                />
                <span
                  className="text-xs font-medium"
                  style={{
                    color: isActive ? stage.color : isPast ? "var(--color-text-secondary)" : "var(--color-text-tertiary)",
                  }}
                >
                  {stage.label}
                </span>
              </div>
              {i < DEMO_STAGES.length - 1 && (
                <div
                  className="h-0.5 flex-1 rounded-full -mt-5"
                  style={{
                    backgroundColor: isPast ? stage.color : "var(--color-border)",
                    opacity: isPast ? 0.7 : 0.15,
                  }}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
