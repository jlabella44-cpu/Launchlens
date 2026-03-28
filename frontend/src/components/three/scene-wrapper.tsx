"use client";

import { Canvas } from "@react-three/fiber";
import { Suspense, type ReactNode } from "react";
import { SceneErrorBoundary } from "./error-boundary";

interface SceneWrapperProps {
  children: ReactNode;
  className?: string;
  camera?: { position: [number, number, number]; fov?: number };
}

function FallbackGradient() {
  return (
    <div className="w-full h-full rounded-xl bg-gradient-to-br from-[var(--color-primary)]/20 to-[var(--color-secondary)]/10 animate-pulse" />
  );
}

export function SceneWrapper({
  children,
  className = "",
  camera = { position: [0, 0, 5], fov: 50 },
}: SceneWrapperProps) {
  return (
    <div className={`relative ${className}`}>
      <SceneErrorBoundary fallback={<FallbackGradient />}>
        <Suspense fallback={<FallbackGradient />}>
          <Canvas camera={camera} style={{ borderRadius: "var(--radius-md)" }}>
            <ambientLight intensity={0.6} />
            <directionalLight position={[5, 5, 5]} intensity={0.8} />
            {children}
          </Canvas>
        </Suspense>
      </SceneErrorBoundary>
    </div>
  );
}
