"use client";

import { Text } from "@react-three/drei";

interface Phase {
  label: string;
  color: string;
  steps: { key: string; label: string }[];
}

const PHASES: Phase[] = [
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

interface PipelineVisualizerProps {
  currentState: string;
}

export function PipelineVisualizer({ currentState }: PipelineVisualizerProps) {
  const currentIndex = ALL_STEPS.findIndex((s) => s.key === currentState);
  const totalSteps = ALL_STEPS.length;
  const spacing = 0.75;
  const startX = -(totalSteps - 1) * spacing * 0.5;

  let stepIndex = 0;

  return (
    <group position={[0, 0, 0]}>
      {PHASES.map((phase, phaseIdx) => {
        const phaseStartIdx = stepIndex;
        const phaseNodes = phase.steps.map((step, i) => {
          const globalIdx = stepIndex++;
          const x = startX + globalIdx * spacing;
          const isActive = globalIdx === currentIndex;
          const isPast = globalIdx < currentIndex;
          const opacity = isPast ? 0.4 : isActive ? 1 : 0.15;
          const scale = isActive ? 1.2 : 0.8;

          return (
            <group key={step.key} position={[x, 0, 0]}>
              <mesh scale={scale}>
                <sphereGeometry args={[0.14, 16, 16]} />
                <meshStandardMaterial
                  color={phase.color}
                  emissive={isActive ? phase.color : "#000000"}
                  emissiveIntensity={isActive ? 0.8 : 0}
                  transparent
                  opacity={opacity}
                />
              </mesh>
              <Text
                position={[0, -0.32, 0]}
                fontSize={0.07}
                color={isActive ? phase.color : "#94A3B8"}
                anchorX="center"
              >
                {step.label}
              </Text>
              {globalIdx < totalSteps - 1 && (
                <mesh position={[spacing / 2, 0, 0]}>
                  <boxGeometry args={[spacing - 0.35, 0.02, 0.02]} />
                  <meshStandardMaterial
                    color={isPast ? phase.color : "#CBD5E1"}
                    transparent
                    opacity={isPast ? 0.5 : 0.15}
                  />
                </mesh>
              )}
            </group>
          );
        });

        // Phase label above the group
        const phaseCenterX =
          startX + (phaseStartIdx + (phase.steps.length - 1) / 2) * spacing;

        return (
          <group key={phase.label}>
            <Text
              position={[phaseCenterX, 0.45, 0]}
              fontSize={0.08}
              color={phase.color}
              anchorX="center"
              fontWeight="bold"
            >
              {phase.label}
            </Text>
            {phaseNodes}
          </group>
        );
      })}
    </group>
  );
}
