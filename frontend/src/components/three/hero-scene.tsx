"use client";

import { useRef, useMemo } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Float, Text } from "@react-three/drei";
import * as THREE from "three";
import type { Points, Mesh, Group } from "three";

/** Floating icosahedrons that drift and pulse */
function FloatingShapes() {
  const groupRef = useRef<Group>(null);

  const shapes = useMemo(() => {
    return Array.from({ length: 12 }, (_, i) => ({
      position: [
        (Math.random() - 0.5) * 8,
        (Math.random() - 0.5) * 5,
        (Math.random() - 0.5) * 4 - 2,
      ] as [number, number, number],
      scale: Math.random() * 0.3 + 0.1,
      speed: Math.random() * 0.5 + 0.3,
      color: i % 3 === 0 ? "#FF6B2C" : i % 3 === 1 ? "#1E3A5F" : "#2563EB",
    }));
  }, []);

  return (
    <group ref={groupRef}>
      {shapes.map((s, i) => (
        <Float
          key={i}
          position={s.position}
          speed={s.speed}
          rotationIntensity={0.4}
          floatIntensity={0.6}
        >
          <mesh scale={s.scale}>
            <icosahedronGeometry args={[1, 0]} />
            <meshStandardMaterial
              color={s.color}
              wireframe
              transparent
              opacity={0.6}
            />
          </mesh>
        </Float>
      ))}
    </group>
  );
}

/** Particle field that follows the mouse */
function InteractiveParticles() {
  const ref = useRef<Points>(null);
  const mouseRef = useRef({ x: 0, y: 0 });
  const { viewport } = useThree();

  const { positions, basePositions } = useMemo(() => {
    const count = 200;
    const pos = new Float32Array(count * 3);
    const base = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const x = (Math.random() - 0.5) * 12;
      const y = (Math.random() - 0.5) * 8;
      const z = (Math.random() - 0.5) * 6 - 1;
      pos[i * 3] = x;
      pos[i * 3 + 1] = y;
      pos[i * 3 + 2] = z;
      base[i * 3] = x;
      base[i * 3 + 1] = y;
      base[i * 3 + 2] = z;
    }
    return { positions: pos, basePositions: base };
  }, []);

  useFrame((state) => {
    if (!ref.current) return;

    // Track mouse in world coordinates
    const mx = (state.pointer.x * viewport.width) / 2;
    const my = (state.pointer.y * viewport.height) / 2;
    mouseRef.current.x += (mx - mouseRef.current.x) * 0.05;
    mouseRef.current.y += (my - mouseRef.current.y) * 0.05;

    const pos = ref.current.geometry.attributes.position.array as Float32Array;
    const t = state.clock.elapsedTime;

    for (let i = 0; i < pos.length / 3; i++) {
      const bx = basePositions[i * 3];
      const by = basePositions[i * 3 + 1];

      // Gentle wave motion
      pos[i * 3] = bx + Math.sin(t * 0.3 + i * 0.1) * 0.15;
      pos[i * 3 + 1] = by + Math.cos(t * 0.4 + i * 0.15) * 0.1;

      // Repel from mouse
      const dx = pos[i * 3] - mouseRef.current.x;
      const dy = pos[i * 3 + 1] - mouseRef.current.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 2) {
        const force = (2 - dist) * 0.15;
        pos[i * 3] += (dx / dist) * force;
        pos[i * 3 + 1] += (dy / dist) * force;
      }
    }
    ref.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        color="#1E3A5F"
        size={0.04}
        transparent
        opacity={0.7}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}

/** Central glowing orb */
function CenterOrb() {
  const ref = useRef<Mesh>(null);

  useFrame((state) => {
    if (!ref.current) return;
    const s = 1 + Math.sin(state.clock.elapsedTime * 1.5) * 0.08;
    ref.current.scale.set(s, s, s);
  });

  return (
    <mesh ref={ref}>
      <sphereGeometry args={[0.5, 32, 32]} />
      <meshStandardMaterial
        color="#0F1B2D"
        emissive="#0F1B2D"
        emissiveIntensity={0.4}
        transparent
        opacity={0.3}
        roughness={0.1}
        metalness={0.8}
      />
    </mesh>
  );
}

/** Orbiting ring */
function OrbitRing() {
  const ref = useRef<Mesh>(null);

  useFrame((state) => {
    if (!ref.current) return;
    ref.current.rotation.z = state.clock.elapsedTime * 0.3;
    ref.current.rotation.x = Math.PI / 3;
  });

  return (
    <mesh ref={ref}>
      <torusGeometry args={[1.8, 0.01, 8, 64]} />
      <meshStandardMaterial
        color="#FF6B2C"
        emissive="#FF6B2C"
        emissiveIntensity={0.6}
        transparent
        opacity={0.5}
      />
    </mesh>
  );
}

export function HeroScene() {
  return (
    <group>
      <CenterOrb />
      <OrbitRing />
      <FloatingShapes />
      <InteractiveParticles />
    </group>
  );
}
