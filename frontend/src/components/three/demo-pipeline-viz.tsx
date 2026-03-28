"use client";

import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import { useRef } from "react";
import type { Mesh } from "three";

const DEMO_STAGES = [
  { key: "demo", label: "Upload", color: "#8B5CF6" },
  { key: "analyzing", label: "AI Analysis", color: "#6366F1" },
  { key: "awaiting_review", label: "Packaged", color: "#F59E0B" },
  { key: "delivered", label: "Ready", color: "#10B981" },
];

interface DemoPipelineVizProps {
  currentState: string;
}

export function DemoPipelineViz({ currentState }: DemoPipelineVizProps) {
  const currentIndex = DEMO_STAGES.findIndex((s) => s.key === currentState);
  // If state not in demo stages, assume complete
  const activeIndex = currentIndex === -1 ? DEMO_STAGES.length - 1 : currentIndex;
  const spacing = 2.2;
  const startX = -(DEMO_STAGES.length - 1) * spacing * 0.5;

  return (
    <group position={[0, 0, 0]}>
      <ambientLight intensity={0.6} />
      <pointLight position={[5, 5, 5]} intensity={0.8} />
      {DEMO_STAGES.map((stage, i) => {
        const x = startX + i * spacing;
        const isActive = i === activeIndex;
        const isPast = i < activeIndex;

        return (
          <group key={stage.key} position={[x, 0, 0]}>
            <PulsingNode
              color={stage.color}
              isActive={isActive}
              isPast={isPast}
            />

            <Text
              position={[0, -0.5, 0]}
              fontSize={0.14}
              color={isActive ? stage.color : isPast ? "#64748B" : "#CBD5E1"}
              anchorX="center"
              font={undefined}
            >
              {stage.label}
            </Text>

            {i < DEMO_STAGES.length - 1 && (
              <mesh position={[spacing / 2, 0, 0]}>
                <boxGeometry args={[spacing - 0.6, 0.04, 0.04]} />
                <meshStandardMaterial
                  color={isPast ? stage.color : "#CBD5E1"}
                  transparent
                  opacity={isPast ? 0.7 : 0.15}
                />
              </mesh>
            )}
          </group>
        );
      })}
    </group>
  );
}

function PulsingNode({ color, isActive, isPast }: { color: string; isActive: boolean; isPast: boolean }) {
  const ref = useRef<Mesh>(null);

  useFrame(({ clock }) => {
    if (ref.current && isActive) {
      const pulse = 1 + Math.sin(clock.elapsedTime * 3) * 0.15;
      ref.current.scale.setScalar(pulse);
    }
  });

  const opacity = isPast ? 0.5 : isActive ? 1 : 0.15;
  const scale = isActive ? 1.2 : isPast ? 0.9 : 0.8;

  return (
    <mesh ref={ref} scale={scale}>
      <sphereGeometry args={[0.22, 16, 16]} />
      <meshStandardMaterial
        color={color}
        emissive={isActive ? color : "#000000"}
        emissiveIntensity={isActive ? 0.6 : 0}
        transparent
        opacity={opacity}
      />
    </mesh>
  );
}
