"use client";

import { useRef, useMemo } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Float } from "@react-three/drei";
import * as THREE from "three";
import type { Points, Mesh, Group } from "three";

/** Aperture/shutter blades — spinning camera lens meets jet engine */
function ApertureBlades() {
  const groupRef = useRef<Group>(null);
  const bladeCount = 8;

  useFrame((state) => {
    if (!groupRef.current) return;
    groupRef.current.rotation.z = state.clock.elapsedTime * 0.3;
  });

  const blades = useMemo(() => {
    return Array.from({ length: bladeCount }, (_, i) => {
      const angle = (i / bladeCount) * Math.PI * 2;
      return { angle, key: i };
    });
  }, []);

  return (
    <group ref={groupRef}>
      {blades.map(({ angle, key }) => (
        <mesh
          key={key}
          position={[Math.cos(angle) * 1.2, Math.sin(angle) * 1.2, 0]}
          rotation={[0, 0, angle + Math.PI / 6]}
        >
          <planeGeometry args={[1.4, 0.15]} />
          <meshStandardMaterial
            color="#2563EB"
            emissive="#2563EB"
            emissiveIntensity={0.3}
            transparent
            opacity={0.5}
            side={THREE.DoubleSide}
          />
        </mesh>
      ))}
    </group>
  );
}

/** Inner ring — glowing engine core */
function EngineCore() {
  const ref = useRef<Mesh>(null);

  useFrame((state) => {
    if (!ref.current) return;
    const s = 1 + Math.sin(state.clock.elapsedTime * 2) * 0.06;
    ref.current.scale.set(s, s, s);
  });

  return (
    <group>
      {/* Core glow */}
      <mesh ref={ref}>
        <torusGeometry args={[0.6, 0.08, 16, 48]} />
        <meshStandardMaterial
          color="#F97316"
          emissive="#F97316"
          emissiveIntensity={0.8}
          transparent
          opacity={0.7}
        />
      </mesh>
      {/* Center dot */}
      <mesh>
        <sphereGeometry args={[0.15, 16, 16]} />
        <meshStandardMaterial
          color="#F97316"
          emissive="#F97316"
          emissiveIntensity={0.6}
          transparent
          opacity={0.5}
        />
      </mesh>
    </group>
  );
}

/** Outer ring — jet engine housing */
function EngineHousing() {
  const ref = useRef<Mesh>(null);

  useFrame((state) => {
    if (!ref.current) return;
    ref.current.rotation.z = -state.clock.elapsedTime * 0.1;
  });

  return (
    <mesh ref={ref}>
      <torusGeometry args={[2.0, 0.03, 8, 64]} />
      <meshStandardMaterial
        color="#3B82F6"
        emissive="#3B82F6"
        emissiveIntensity={0.4}
        transparent
        opacity={0.4}
      />
    </mesh>
  );
}

/** Speed particles — exhaust trail */
function ExhaustParticles() {
  const ref = useRef<Points>(null);
  const mouseRef = useRef({ x: 0, y: 0 });
  const { viewport } = useThree();

  const { positions, velocities } = useMemo(() => {
    const count = 150;
    const pos = new Float32Array(count * 3);
    const vel = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const r = 0.8 + Math.random() * 2;
      pos[i * 3] = Math.cos(angle) * r;
      pos[i * 3 + 1] = Math.sin(angle) * r;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 3;
      vel[i * 3] = (Math.random() - 0.5) * 0.002;
      vel[i * 3 + 1] = (Math.random() - 0.5) * 0.002;
      vel[i * 3 + 2] = Math.random() * 0.01 + 0.005;
    }
    return { positions: pos, velocities: vel };
  }, []);

  useFrame((state) => {
    if (!ref.current) return;

    const mx = (state.pointer.x * viewport.width) / 2;
    const my = (state.pointer.y * viewport.height) / 2;
    mouseRef.current.x += (mx - mouseRef.current.x) * 0.05;
    mouseRef.current.y += (my - mouseRef.current.y) * 0.05;

    const pos = ref.current.geometry.attributes.position.array as Float32Array;
    for (let i = 0; i < pos.length / 3; i++) {
      pos[i * 3] += velocities[i * 3];
      pos[i * 3 + 1] += velocities[i * 3 + 1];
      pos[i * 3 + 2] += velocities[i * 3 + 2];

      // Reset particles that fly too far
      if (pos[i * 3 + 2] > 2) {
        const angle = Math.random() * Math.PI * 2;
        const r = 0.5 + Math.random() * 1.5;
        pos[i * 3] = Math.cos(angle) * r;
        pos[i * 3 + 1] = Math.sin(angle) * r;
        pos[i * 3 + 2] = -1;
      }

      // Mouse repulsion
      const dx = pos[i * 3] - mouseRef.current.x;
      const dy = pos[i * 3 + 1] - mouseRef.current.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 1.5) {
        const force = (1.5 - dist) * 0.1;
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
        color="#93C5FD"
        size={0.03}
        transparent
        opacity={0.6}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}

/** Floating geometric accents */
function FloatingAccents() {
  const shapes = useMemo(() => {
    return Array.from({ length: 6 }, (_, i) => ({
      position: [
        (Math.random() - 0.5) * 6,
        (Math.random() - 0.5) * 4,
        (Math.random() - 0.5) * 2 - 1,
      ] as [number, number, number],
      scale: Math.random() * 0.15 + 0.05,
      speed: Math.random() * 0.4 + 0.2,
      color: i % 2 === 0 ? "#F97316" : "#3B82F6",
    }));
  }, []);

  return (
    <group>
      {shapes.map((s, i) => (
        <Float key={i} position={s.position} speed={s.speed} rotationIntensity={0.3} floatIntensity={0.5}>
          <mesh scale={s.scale}>
            <octahedronGeometry args={[1, 0]} />
            <meshStandardMaterial color={s.color} wireframe transparent opacity={0.4} />
          </mesh>
        </Float>
      ))}
    </group>
  );
}

export function HeroScene() {
  return (
    <group>
      <EngineCore />
      <ApertureBlades />
      <EngineHousing />
      <ExhaustParticles />
      <FloatingAccents />
    </group>
  );
}
