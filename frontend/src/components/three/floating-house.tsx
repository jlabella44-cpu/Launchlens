"use client";

import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { Group, Points } from "three";

// House wireframe vertices — modern house silhouette
const HOUSE_LINES = [
  // Base
  [-1.2, 0, -0.8], [1.2, 0, -0.8],
  [1.2, 0, -0.8], [1.2, 0, 0.8],
  [1.2, 0, 0.8], [-1.2, 0, 0.8],
  [-1.2, 0, 0.8], [-1.2, 0, -0.8],
  // Walls
  [-1.2, 0, -0.8], [-1.2, 1, -0.8],
  [1.2, 0, -0.8], [1.2, 1, -0.8],
  [1.2, 0, 0.8], [1.2, 1, 0.8],
  [-1.2, 0, 0.8], [-1.2, 1, 0.8],
  // Top walls
  [-1.2, 1, -0.8], [1.2, 1, -0.8],
  [1.2, 1, -0.8], [1.2, 1, 0.8],
  [1.2, 1, 0.8], [-1.2, 1, 0.8],
  [-1.2, 1, 0.8], [-1.2, 1, -0.8],
  // Roof
  [-1.2, 1, -0.8], [0, 1.7, -0.8],
  [0, 1.7, -0.8], [1.2, 1, -0.8],
  [-1.2, 1, 0.8], [0, 1.7, 0.8],
  [0, 1.7, 0.8], [1.2, 1, 0.8],
  [0, 1.7, -0.8], [0, 1.7, 0.8],
  // Door
  [-0.15, 0, 0.81], [-0.15, 0.55, 0.81],
  [-0.15, 0.55, 0.81], [0.15, 0.55, 0.81],
  [0.15, 0.55, 0.81], [0.15, 0, 0.81],
  // Windows
  [-0.8, 0.45, 0.81], [-0.8, 0.75, 0.81],
  [-0.8, 0.75, 0.81], [-0.45, 0.75, 0.81],
  [-0.45, 0.75, 0.81], [-0.45, 0.45, 0.81],
  [-0.45, 0.45, 0.81], [-0.8, 0.45, 0.81],
  [0.45, 0.45, 0.81], [0.45, 0.75, 0.81],
  [0.45, 0.75, 0.81], [0.8, 0.75, 0.81],
  [0.8, 0.75, 0.81], [0.8, 0.45, 0.81],
  [0.8, 0.45, 0.81], [0.45, 0.45, 0.81],
];

function HouseWireframe() {
  const ref = useRef<THREE.LineSegments>(null);

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(HOUSE_LINES.flat());
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    return geo;
  }, []);

  useFrame((state) => {
    if (!ref.current) return;
    const material = ref.current.material as THREE.LineBasicMaterial;
    material.opacity = 0.6 + Math.sin(state.clock.elapsedTime * 2) * 0.15;
  });

  return (
    <lineSegments ref={ref} geometry={geometry}>
      <lineBasicMaterial color="#60A5FA" transparent opacity={0.7} linewidth={1} />
    </lineSegments>
  );
}

function GlowParticles() {
  const ref = useRef<Points>(null);

  const { positions, velocities } = useMemo(() => {
    const count = 120;
    const pos = new Float32Array(count * 3);
    const vel = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      // Distribute particles around the house shape
      pos[i * 3] = (Math.random() - 0.5) * 3.5;
      pos[i * 3 + 1] = Math.random() * 2.2;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 2.5;
      vel[i * 3] = (Math.random() - 0.5) * 0.003;
      vel[i * 3 + 1] = Math.random() * 0.005 + 0.002;
      vel[i * 3 + 2] = (Math.random() - 0.5) * 0.003;
    }
    return { positions: pos, velocities: vel };
  }, []);

  useFrame(() => {
    if (!ref.current) return;
    const pos = ref.current.geometry.attributes.position.array as Float32Array;
    for (let i = 0; i < pos.length / 3; i++) {
      pos[i * 3] += velocities[i * 3];
      pos[i * 3 + 1] += velocities[i * 3 + 1];
      pos[i * 3 + 2] += velocities[i * 3 + 2];
      // Reset particles that float too high
      if (pos[i * 3 + 1] > 2.5) {
        pos[i * 3] = (Math.random() - 0.5) * 3;
        pos[i * 3 + 1] = -0.2;
        pos[i * 3 + 2] = (Math.random() - 0.5) * 2;
      }
    }
    ref.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={positions.length / 3}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        color="#F97316"
        size={0.035}
        transparent
        opacity={0.8}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}

function FloorGrid() {
  const ref = useRef<THREE.LineSegments>(null);

  const geometry = useMemo(() => {
    const lines: number[] = [];
    const extent = 3;
    const step = 0.4;
    for (let x = -extent; x <= extent; x += step) {
      lines.push(x, 0, -extent, x, 0, extent);
    }
    for (let z = -extent; z <= extent; z += step) {
      lines.push(-extent, 0, z, extent, 0, z);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(lines), 3));
    return geo;
  }, []);

  return (
    <lineSegments ref={ref} geometry={geometry} position={[0, -0.01, 0]}>
      <lineBasicMaterial color="#2563EB" transparent opacity={0.12} />
    </lineSegments>
  );
}

export function FloatingHouse() {
  const groupRef = useRef<Group>(null);

  useFrame((state) => {
    if (!groupRef.current) return;
    groupRef.current.rotation.y = state.clock.elapsedTime * 0.12;
    groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.6) * 0.1;
  });

  return (
    <group ref={groupRef}>
      <HouseWireframe />
      <GlowParticles />
      <FloorGrid />
    </group>
  );
}
