"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { MeshDistortMaterial } from "@react-three/drei";
import type { Mesh, Group } from "three";

export function FloatingHouse() {
  const groupRef = useRef<Group>(null);
  const roofRef = useRef<Mesh>(null);

  useFrame((state) => {
    if (!groupRef.current) return;
    groupRef.current.rotation.y = state.clock.elapsedTime * 0.15;
    groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.5) * 0.15;
  });

  return (
    <group ref={groupRef} scale={1.2}>
      {/* House body */}
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[1.6, 1.2, 1.2]} />
        <meshStandardMaterial color="#2563EB" roughness={0.3} metalness={0.1} />
      </mesh>

      {/* Roof */}
      <mesh ref={roofRef} position={[0, 0.9, 0]} rotation={[0, Math.PI / 4, 0]}>
        <coneGeometry args={[1.3, 0.8, 4]} />
        <meshStandardMaterial color="#1E293B" roughness={0.4} metalness={0.2} />
      </mesh>

      {/* Door */}
      <mesh position={[0, -0.2, 0.61]}>
        <boxGeometry args={[0.35, 0.6, 0.05]} />
        <meshStandardMaterial color="#F97316" roughness={0.5} />
      </mesh>

      {/* Windows */}
      {[[-0.45, 0.2, 0.61], [0.45, 0.2, 0.61]].map((pos, i) => (
        <mesh key={i} position={pos as [number, number, number]}>
          <boxGeometry args={[0.3, 0.3, 0.05]} />
          <MeshDistortMaterial color="#93C5FD" distort={0.15} speed={2} roughness={0.1} metalness={0.8} />
        </mesh>
      ))}

      {/* Ground plane */}
      <mesh position={[0, -0.65, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[1.5, 32]} />
        <meshStandardMaterial color="#22C55E" roughness={0.8} transparent opacity={0.3} />
      </mesh>
    </group>
  );
}
