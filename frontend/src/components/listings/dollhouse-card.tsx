"use client";

import { useEffect, useState } from "react";
import apiClient from "@/lib/api-client";
import { DollhouseViewer } from "./dollhouse-viewer";

type DollhouseResponse = Awaited<ReturnType<typeof apiClient.getDollhouse>>;

interface DollhouseCardProps {
  listingId: string;
}

export function DollhouseCard({ listingId }: DollhouseCardProps) {
  const [data, setData] = useState<DollhouseResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiClient.getDollhouse(listingId);
        if (!cancelled) setData(res);
      } catch {
        if (!cancelled) setNotFound(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [listingId]);

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-100 p-5">
        <h3
          className="text-base font-semibold text-[var(--color-text)] mb-3"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          3D Dollhouse
        </h3>
        <div className="h-48 rounded-xl bg-gradient-to-br from-slate-100 to-slate-50 animate-pulse" />
      </div>
    );
  }

  if (notFound || !data) {
    return null;
  }

  const floorCount = data.scene_json?.floors?.length ?? 0;

  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-5">
      <div className="flex items-start justify-between mb-3">
        <h3
          className="text-base font-semibold text-[var(--color-text)]"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          3D Dollhouse
          {floorCount > 0 && (
            <span className="ml-2 text-xs text-slate-400 font-normal">
              {floorCount} {floorCount === 1 ? "floor" : "floors"} &middot; {data.room_count} rooms
            </span>
          )}
        </h3>
      </div>

      {data.scene_json?.floors?.length ? (
        <DollhouseViewer sceneJson={data.scene_json} />
      ) : data.render_url ? (
        <div className="rounded-xl overflow-hidden border border-slate-100 bg-[#FAF7F0]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={data.render_url}
            alt="3D dollhouse render of the property"
            className="w-full h-auto object-contain"
          />
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
          <svg
            className="w-10 h-10 mx-auto mb-2 text-slate-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3.75 21h16.5M4.5 3h15M5.25 3v18M18.75 3v18M9 6.75h1.5M9 12h1.5M9 17.25h1.5M13.5 6.75H15M13.5 12H15M13.5 17.25H15"
            />
          </svg>
          <p className="text-xs text-slate-400">
            Scene detected &middot; render in progress
          </p>
        </div>
      )}
    </div>
  );
}
