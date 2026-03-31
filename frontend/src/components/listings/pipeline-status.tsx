"use client";

import dynamic from "next/dynamic";

const SceneWrapper = dynamic(
  () => import("@/components/three/scene-wrapper").then((m) => ({ default: m.SceneWrapper })),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full rounded-xl bg-gradient-to-br from-[var(--color-primary)]/10 to-[var(--color-secondary)]/5 animate-pulse" />
    ),
  }
);
const PipelineVisualizer = dynamic(
  () => import("@/components/three/pipeline-visualizer").then((m) => ({ default: m.PipelineVisualizer })),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full rounded-xl bg-gradient-to-br from-[var(--color-primary)]/10 to-[var(--color-secondary)]/5 animate-pulse" />
    ),
  }
);

interface PipelineStatusProps {
  state: string;
}

export function PipelineStatus({ state }: PipelineStatusProps) {
  return (
    <SceneWrapper
      className="w-full h-[120px]"
      camera={{ position: [0, 0, 6], fov: 45 }}
    >
      <PipelineVisualizer currentState={state} />
    </SceneWrapper>
  );
}
