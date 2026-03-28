"use client";

import { Text } from "@react-three/drei";

const STAGES = [
  { key: "new", label: "New", color: "#94A3B8" },
  { key: "uploading", label: "Upload", color: "#3B82F6" },
  { key: "analyzing", label: "Analyze", color: "#6366F1" },
  { key: "awaiting_review", label: "Review", color: "#F59E0B" },
  { key: "in_review", label: "In Review", color: "#F97316" },
  { key: "approved", label: "Approved", color: "#22C55E" },
  { key: "exporting", label: "Export", color: "#06B6D4" },
  { key: "delivered", label: "Delivered", color: "#10B981" },
];

interface PipelineVisualizerProps {
  currentState: string;
}

export function PipelineVisualizer({ currentState }: PipelineVisualizerProps) {
  const currentIndex = STAGES.findIndex((s) => s.key === currentState);
  const spacing = 1.4;
  const startX = -(STAGES.length - 1) * spacing * 0.5;

  return (
    <group position={[0, 0, 0]}>
      {STAGES.map((stage, i) => {
        const x = startX + i * spacing;
        const isActive = i === currentIndex;
        const isPast = i < currentIndex;
        const opacity = isPast ? 0.4 : isActive ? 1 : 0.2;
        const scale = isActive ? 1.3 : 1;

        return (
          <group key={stage.key} position={[x, 0, 0]}>
            {/* Node */}
            <mesh scale={scale}>
              <sphereGeometry args={[0.2, 16, 16]} />
              <meshStandardMaterial
                color={stage.color}
                emissive={isActive ? stage.color : "#000000"}
                emissiveIntensity={isActive ? 0.8 : 0}
                transparent
                opacity={opacity}
              />
            </mesh>

            {/* Label */}
            <Text
              position={[0, -0.45, 0]}
              fontSize={0.1}
              color={isActive ? stage.color : "#94A3B8"}
              anchorX="center"
            >
              {stage.label}
            </Text>

            {/* Connector line to next */}
            {i < STAGES.length - 1 && (
              <mesh position={[spacing / 2, 0, 0]}>
                <boxGeometry args={[spacing - 0.5, 0.03, 0.03]} />
                <meshStandardMaterial
                  color={isPast ? stage.color : "#CBD5E1"}
                  transparent
                  opacity={isPast ? 0.6 : 0.2}
                />
              </mesh>
            )}
          </group>
        );
      })}
    </group>
  );
}
