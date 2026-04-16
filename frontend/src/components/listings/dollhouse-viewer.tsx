"use client";

import { useEffect, useRef } from "react";

interface Room {
  id?: string;
  label?: string;
  type?: string;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
}

interface Floor {
  level?: number;
  label?: string;
  rooms?: Room[];
}

interface SceneJson {
  floors?: Floor[];
  width?: number;
  height?: number;
}

interface DollhouseViewerProps {
  sceneJson: SceneJson;
  className?: string;
}

const ROOM_COLORS: Record<string, string> = {
  kitchen:      "#FFF3CD",
  living:       "#D4EDDA",
  bedroom:      "#CCE5FF",
  bathroom:     "#E2E3E5",
  dining:       "#FDE2D8",
  garage:       "#F0F0F0",
  office:       "#EDE7F6",
  laundry:      "#E1F5FE",
  foyer:        "#FFF8E7",
  hallway:      "#F5F5F5",
  default:      "#EEF2FF",
};

function roomColor(room: Room): string {
  const label = (room.label ?? room.type ?? "").toLowerCase();
  for (const key of Object.keys(ROOM_COLORS)) {
    if (label.includes(key)) return ROOM_COLORS[key];
  }
  return ROOM_COLORS.default;
}

export function DollhouseViewer({ sceneJson, className = "" }: DollhouseViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const floors = sceneJson.floors ?? [];
    if (floors.length === 0) return;

    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    // Layout floors side-by-side with tilt for dollhouse feel
    const floorW = Math.floor(W / Math.max(floors.length, 1)) - 12;
    const floorH = H - 40;

    floors.forEach((floor, fi) => {
      const offsetX = fi * (floorW + 12) + 6;
      const offsetY = 20;
      const rooms = floor.rooms ?? [];

      // Compute bounding box of rooms to auto-scale
      if (rooms.length === 0) {
        // Draw empty floor plate
        ctx.fillStyle = "#F8FAFC";
        ctx.strokeStyle = "#CBD5E1";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(offsetX, offsetY, floorW, floorH, 4);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = "#94A3B8";
        ctx.font = "11px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(floor.label ?? `Floor ${fi + 1}`, offsetX + floorW / 2, offsetY + floorH / 2);
        return;
      }

      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      for (const r of rooms) {
        const rx = r.x ?? 0, ry = r.y ?? 0;
        const rw = r.width ?? 100, rh = r.height ?? 100;
        if (rx < minX) minX = rx;
        if (ry < minY) minY = ry;
        if (rx + rw > maxX) maxX = rx + rw;
        if (ry + rh > maxY) maxY = ry + rh;
      }
      const srcW = maxX - minX || 1;
      const srcH = maxY - minY || 1;
      const pad = 8;
      const scaleX = (floorW - pad * 2) / srcW;
      const scaleY = (floorH - pad * 2 - 20) / srcH;
      const scale = Math.min(scaleX, scaleY);

      // Floor label
      ctx.fillStyle = "#475569";
      ctx.font = "bold 10px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(floor.label ?? `Floor ${fi + 1}`, offsetX + floorW / 2, offsetY + 12);

      for (const room of rooms) {
        const rx = offsetX + pad + ((room.x ?? 0) - minX) * scale;
        const ry = offsetY + 20 + ((room.y ?? 0) - minY) * scale;
        const rw = (room.width ?? 100) * scale;
        const rh = (room.height ?? 100) * scale;

        // Room fill
        ctx.fillStyle = roomColor(room);
        ctx.strokeStyle = "#94A3B8";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(rx, ry, rw, rh, 2);
        ctx.fill();
        ctx.stroke();

        // Room label (only if room is large enough)
        if (rw > 30 && rh > 18) {
          ctx.fillStyle = "#334155";
          ctx.font = `${Math.min(10, rw / 6)}px sans-serif`;
          ctx.textAlign = "center";
          const label = room.label ?? room.type ?? "";
          ctx.fillText(label, rx + rw / 2, ry + rh / 2 + 4, rw - 4);
        }
      }
    });
  }, [sceneJson]);

  return (
    <canvas
      ref={canvasRef}
      width={480}
      height={220}
      className={`w-full rounded-xl border border-slate-100 bg-slate-50 ${className}`}
      aria-label="Interactive floorplan view"
    />
  );
}
