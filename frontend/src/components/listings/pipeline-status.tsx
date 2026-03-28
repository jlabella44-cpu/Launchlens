"use client";

import dynamic from "next/dynamic";

const SceneWrapper = dynamic(
  () => import("@/components/three/scene-wrapper").then((m) => ({ default: m.SceneWrapper })),
  { ssr: false }
);
const PipelineVisualizer = dynamic(
  () => import("@/components/three/pipeline-visualizer").then((m) => ({ default: m.PipelineVisualizer })),
  { ssr: false }
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
