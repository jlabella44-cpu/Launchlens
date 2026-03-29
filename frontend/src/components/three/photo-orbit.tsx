"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import type { Group } from "three";

interface PhotoOrbitProps {
  photos: { asset_id: string; position: number; composite_score: number }[];
  heroIndex?: number;
}

export function PhotoOrbit({ photos, heroIndex = 0 }: PhotoOrbitProps) {
  const groupRef = useRef<Group>(null);

  useFrame((state) => {
    if (!groupRef.current) return;
    groupRef.current.rotation.y = state.clock.elapsedTime * 0.1;
  });

  const count = photos.length;
  const radius = Math.max(2, count * 0.25);

  return (
    <group ref={groupRef}>
      {/* Center glow */}
      <mesh>
        <sphereGeometry args={[0.3, 16, 16]} />
        <meshStandardMaterial
          color="#FF6B2C"
          emissive="#FF6B2C"
          emissiveIntensity={0.5}
          transparent
          opacity={0.6}
        />
      </mesh>

      {/* Orbiting photo cards */}
      {photos.map((photo, i) => {
        const angle = (i / count) * Math.PI * 2;
        const x = Math.cos(angle) * radius;
        const z = Math.sin(angle) * radius;
        const isHero = i === heroIndex;

        return (
          <group key={photo.asset_id} position={[x, 0, z]}>
            <mesh rotation={[0, -angle + Math.PI / 2, 0]}>
              <boxGeometry args={[1.2, 0.8, 0.05]} />
              <meshStandardMaterial
                color={isHero ? "#FF6B2C" : "#0F1B2D"}
                roughness={0.3}
                metalness={isHero ? 0.3 : 0.1}
              />
            </mesh>
            <Text
              position={[0, -0.55, 0]}
              rotation={[0, -angle + Math.PI / 2, 0]}
              fontSize={0.12}
              color="#64748B"
              anchorX="center"
            >
              {`#${photo.position + 1} (${Math.round(photo.composite_score)})`}
            </Text>
            {isHero && (
              <Text
                position={[0, 0.55, 0]}
                rotation={[0, -angle + Math.PI / 2, 0]}
                fontSize={0.14}
                color="#FF6B2C"
                fontWeight="bold"
                anchorX="center"
              >
                HERO
              </Text>
            )}
          </group>
        );
      })}
    </group>
  );
}
