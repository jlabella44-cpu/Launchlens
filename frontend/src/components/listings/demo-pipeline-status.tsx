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

const DemoPipelineViz = dynamic(
  () => import("@/components/three/demo-pipeline-viz").then((m) => ({ default: m.DemoPipelineViz })),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full rounded-xl bg-gradient-to-br from-[var(--color-primary)]/10 to-[var(--color-secondary)]/5 animate-pulse" />
    ),
  }
);

interface DemoPipelineStatusProps {
  state: string;
}

export function DemoPipelineStatus({ state }: DemoPipelineStatusProps) {
  return (
    <SceneWrapper
      className="w-full h-[100px]"
      camera={{ position: [0, 0, 5], fov: 45 }}
    >
      <DemoPipelineViz currentState={state} />
    </SceneWrapper>
  );
}
